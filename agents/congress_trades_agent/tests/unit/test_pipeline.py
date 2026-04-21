import pytest
import json
import os
import shutil

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# Import your actual pipeline
from congress_trades_agent.congress_agents import CONGRESS_PIPELINE


# =============================================================================
# DEEP MOCKS (Intercepting the APIs, NOT the Tool Pointers)
# =============================================================================

# 1. Mock the internal BigQuery helper for Congress Signals
def mock_get_bq_data(analysis_date: str) -> list:
    print(f"\n---> 🛑 BQ MOCK HIT: Returning 3 Congress signals for {analysis_date}")
    return [
        {"ticker": "BE", "net_buy_activity": 85, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date},
        {"ticker": "MOH", "net_buy_activity": 15, "market_uptrend": False, "signal_date": analysis_date, "last_trade_date": analysis_date},
        {"ticker": "EQIX", "net_buy_activity": 50, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date}
    ]

# 2. Mock yfinance.Ticker to prevent internet calls in Fundamentals Tool
class MockYFTicker:
    def __init__(self, ticker):
        self.ticker = ticker
        db = {
            "BE": {"sector": "Technology", "industry": "Software", "marketCap": 10_000_000_000, "beta": 1.5, "forwardPE": 25, "debtToEquity": 50},
            "MOH": {"sector": "Healthcare", "industry": "Medical", "marketCap": 5_000_000_000, "beta": 0.8, "forwardPE": 15, "debtToEquity": 80},
            "EQIX": {"sector": "Real Estate", "industry": "REIT", "marketCap": 80_000_000_000, "beta": 1.1, "forwardPE": 60, "debtToEquity": 250}
        }
        # Provide fallback if ticker isn't in DB
        self.info = db.get(ticker.upper(), {"sector": "Unknown", "marketCap": 0, "beta": 1.0, "forwardPE": 10, "debtToEquity": 10})
        print(f"---> 🛑 YFINANCE MOCK HIT: Returning fundamentals for {ticker}")

# 3. Mock BigQuery Client specifically for the Lobbying Tool
class MockLobbyingRow:
    def __init__(self, ticker):
        self.ticker = ticker
        self.client_name = f"{ticker} Corp"
        self.total_spend = 5000000 if ticker == "BE" else 0
        self.latest_filing = "2024-10-01"
        self.number_of_filings = 5
        self.top_issues = "Green Energy Subsidies" if ticker == "BE" else "None"

class MockLobbyingQuery:
    def __init__(self, ticker):
        self.ticker = ticker
    def result(self):
        # Only return results for BE to test confluence logic
        if self.ticker == "BE":
            return [MockLobbyingRow(self.ticker)]
        return []

class MockLobbyingClient:
    def __init__(self, *args, **kwargs): 
        pass
    def query(self, query, job_config=None):
        # Safely extract the ticker from the query parameters
        ticker = job_config.query_parameters[0].value
        print(f"---> 🛑 LOBBYING BQ MOCK HIT: Returning lobbying data for {ticker}")
        return MockLobbyingQuery(ticker)

# Note: We do NOT need to mock fetch_form4_signals_tool! 
# Your extra_tools.py already has `mock_form4_db` built into the function natively!


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def cleanup_temp_data():
    temp_dir = "./temp_data"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    yield
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def alpha_workflow_runner(cleanup_temp_data):
    session_service = InMemorySessionService()
    runner = Runner(
        agent=CONGRESS_PIPELINE, 
        session_service=session_service,
        app_name="AlphaTradingApp" 
    )
    return runner, session_service


# =============================================================================
# THE INTEGRATION TEST
# =============================================================================

@pytest.mark.asyncio
async def test_alpha_pipeline_logic_and_guardrails(mocker, alpha_workflow_runner):
    runner, session_service = alpha_workflow_runner 

    # -------------------------------------------------------------------------
    # 🎯 APPLYING DEEP MOCKS
    # -------------------------------------------------------------------------
    mocker.patch('congress_trades_agent.tools._get_bq_data', side_effect=mock_get_bq_data)
    mocker.patch('congress_trades_agent.tools.yf.Ticker', side_effect=MockYFTicker)
    mocker.patch('congress_trades_agent.extra_tools.bigquery.Client', side_effect=MockLobbyingClient)

    session_id = "test_session_alpha_004"
    user_id = "test_quant"
    app_name = "AlphaTradingApp"
    
    test_prompt = "Run the Alpha strategy for 2024-10-15."

    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={} 
    )
    
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )
    
    print("\n" + "="*70)
    print("🕵️ TRACE: Pipeline Execution & Reasoning")
    print("="*70)

    async for event in final_events_generator:
        if hasattr(event, 'agent_call'):
            print(f"\n🚀 [AGENT HANDOFF]: {event.agent_call.agent_name}")
            
        if hasattr(event, 'tool_call'):
            print(f"🛠️ [TOOL CALL ATTEMPT]: {event.tool_call.function_name}({event.tool_call.arguments})")

        if hasattr(event, 'model_response') and event.model_response:
            thought = event.model_response.text.strip()
            if thought:
                print(f"🧠 [AGENT THOUGHT]: {thought[:250]}...\n") 

    print("="*70)

    # --- FINAL ASSERTIONS ---
    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    final_state = final_session.state
    
    print(f"\n📊 RAW STATE OUTPUT: {json.dumps(final_state, indent=2)}\n")

    final_plan_str = final_state.get('final_trade_plan')
    assert final_plan_str is not None, "Trader failed to output a final plan in state!"
    
    clean_json_str = final_plan_str.replace("```json", "").replace("```", "").strip()
    trade_plan = json.loads(clean_json_str)

    actions = {trade["ticker"]: trade["action"] for trade in trade_plan}
    print(f"######----- Returned Actions: {actions} -----")
    
    # 🎯 Verify against our mock logic
    # 🎯 Verify against our mock logic
    assert "BE" in actions, "Agent entirely skipped BE!"
    # Check if "BUY" is IN the string, so it catches "BUY" or "STRONG BUY"
    assert "BUY" in actions["BE"], f"Agent failed to buy BE! It decided to: {actions['BE']}"
    
    assert "MOH" in actions, "Agent entirely skipped MOH!"
    assert "PASS" in actions["MOH"], f"Agent mistakenly bought a FALLING KNIFE (MOH)! Action was: {actions['MOH']}"
    
    assert "EQIX" in actions, "Agent entirely skipped EQIX!"
    assert "PASS" in actions["EQIX"], f"Agent ignored the Safety Rails and bought EQIX! Action was: {actions['EQIX']}"

    print("✅ All Agent Logic and Guardrails passed successfully!")


# =============================================================================
# DEEP MOCKS: EDGE CASES (JPM, GHOST, AAPL)
# =============================================================================

def mock_get_bq_data_edge_cases(analysis_date: str) -> list:
    print(f"\n---> 🛑 BQ MOCK HIT: Returning Edge Case signals for {analysis_date}")
    return [
        {"ticker": "JPM", "net_buy_activity": 45, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date},
        {"ticker": "GHOST", "net_buy_activity": 30, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date},
        {"ticker": "AAPL", "net_buy_activity": 25, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date}
    ]

class MockYFTickerEdgeCases:
    def __init__(self, ticker):
        self.ticker = ticker
        
        # Simulate Yahoo Finance missing a ticker
        if ticker.upper() == "GHOST":
            raise Exception("Simulated API Failure - Data Unavailable")
            
        db = {
            "JPM": {"sector": "Financial Services", "industry": "Banks", "marketCap": 500_000_000_000, "beta": 1.1, "forwardPE": 12, "debtToEquity": 450}, # INTENTIONAL HIGH DEBT
            "AAPL": {"sector": "Technology", "industry": "Consumer Electronics", "marketCap": 3_000_000_000_000, "beta": 1.2, "forwardPE": 28, "debtToEquity": 140},
        }
        self.info = db.get(ticker.upper(), {"sector": "Unknown", "marketCap": 0, "beta": 1.0, "forwardPE": 10, "debtToEquity": 10})
        print(f"---> 🛑 YFINANCE MOCK HIT: Returning fundamentals for {ticker}")

class MockLobbyingQueryEdgeCases:
    def __init__(self, ticker):
        self.ticker = ticker
    def result(self):
        # Only JPM gets lobbying data here
        if self.ticker == "JPM":
            class Row:
                ticker = "JPM"
                client_name = "JPMorgan Chase"
                total_spend = 2000000
                latest_filing = "2024-10-01"
                number_of_filings = 2
                top_issues = "Banking Regulations"
            return [Row()]
        return []

class MockLobbyingClientEdgeCases:
    def __init__(self, *args, **kwargs): 
        pass
    def query(self, query, job_config=None):
        ticker = job_config.query_parameters[0].value
        return MockLobbyingQueryEdgeCases(ticker)


# =============================================================================
# INTEGRATION TEST 2: EDGE CASES & RESILIENCE
# =============================================================================

@pytest.mark.asyncio
async def test_alpha_pipeline_edge_cases(mocker, alpha_workflow_runner):
    """Tests Agent resilience to missing data and nuanced sector exemptions."""
    runner, session_service = alpha_workflow_runner 

    # 🎯 PATCH WITH THE EDGE CASE MOCKS
    mocker.patch('congress_trades_agent.tools._get_bq_data', side_effect=mock_get_bq_data_edge_cases)
    mocker.patch('congress_trades_agent.tools.yf.Ticker', side_effect=MockYFTickerEdgeCases)
    mocker.patch('congress_trades_agent.extra_tools.bigquery.Client', side_effect=MockLobbyingClientEdgeCases)

    session_id = "test_session_edge_001"
    user_id = "test_quant"
    app_name = "AlphaTradingApp"
    test_prompt = "Run the Alpha strategy for 2024-10-15."

    await session_service.create_session(
        app_name=app_name, session_id=session_id, user_id=user_id, state={} 
    )
    
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, session_id=session_id, new_message=user_content 
    )
    
    print("\n" + "="*70)
    print("🕵️ TRACE: Edge Case Testing")
    print("="*70)

    # Let the pipeline run silently for this test
    async for event in final_events_generator:
        pass 

    # Fetch final state
    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    final_plan_str = final_session.state.get('final_trade_plan')
    
    clean_json_str = final_plan_str.replace("```json", "").replace("```", "").strip()
    trade_plan = json.loads(clean_json_str)

    actions = {trade["ticker"]: trade["action"] for trade in trade_plan}
    print(f"######----- Returned Edge Case Actions: {actions} -----")
    
    # 🎯 Pattern 1: Sector Exemption Test (Bank Debt)
    assert "JPM" in actions, "Agent entirely skipped JPM!"
    assert "BUY" in actions["JPM"], f"Agent failed the Sector Exemption! It rejected JPM due to high debt despite being a Bank. Action: {actions['JPM']}"

    # 🎯 Pattern 2: Missing Data Resilience Test (Broken API)
    assert "GHOST" in actions, "Agent entirely skipped GHOST!"
    assert "PASS" in actions["GHOST"], f"Agent recklessly bought GHOST despite missing fundamental safety data! Action: {actions['GHOST']}"

    # 🎯 Pattern 3: Baseline Normal Buy Test (No extreme signals)
    assert "AAPL" in actions, "Agent entirely skipped AAPL!"
    assert "STRONG" not in actions["AAPL"], "Agent hallucinated a Strong Buy for AAPL despite missing Golden Confluence (no lobbying/insiders)!"
    assert "BUY" in actions["AAPL"] or "HOLD" in actions["AAPL"], f"Agent failed to issue a baseline buy/hold for AAPL. Action: {actions['AAPL']}"

    print("✅ All Edge Cases and Resilience logic passed successfully!")


    # =============================================================================
# DEEP MOCKS: MIXED CONFLICTING CASES (TRAP, BEAR, BUBB)
# =============================================================================

def mock_get_bq_data_mixed(analysis_date: str) -> list:
    print(f"\n---> 🛑 BQ MOCK HIT: Returning Mixed signals for {analysis_date}")
    return [
        {"ticker": "TRAP", "net_buy_activity": 60, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date},
        {"ticker": "BEAR", "net_buy_activity": 80, "market_uptrend": False, "signal_date": analysis_date, "last_trade_date": analysis_date}, # FALSE market regime
        {"ticker": "BUBB", "net_buy_activity": 40, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date}
    ]

class MockYFTickerMixed:
    def __init__(self, ticker):
        self.ticker = ticker
        db = {
            "TRAP": {"sector": "Technology", "industry": "Software", "marketCap": 10_000_000_000, "beta": 1.2, "forwardPE": 20, "debtToEquity": 40},
            "BEAR": {"sector": "Healthcare", "industry": "Medical", "marketCap": 20_000_000_000, "beta": 0.9, "forwardPE": 15, "debtToEquity": 50},
            "BUBB": {"sector": "Technology", "industry": "AI", "marketCap": 5_000_000_000, "beta": 2.5, "forwardPE": 1000, "debtToEquity": 10}, # P/E is 1000! Bubble!
        }
        self.info = db.get(ticker.upper(), {"sector": "Unknown", "marketCap": 0, "beta": 1.0, "forwardPE": 10, "debtToEquity": 10})

class MockLobbyingQueryMixed:
    def __init__(self, ticker):
        self.ticker = ticker
    def result(self):
        # Let's give TRAP and BEAR some lobbying to make them look like "Golden Signals" on the surface
        if self.ticker in ["TRAP", "BEAR"]:
            class Row:
                ticker = self.ticker
                client_name = f"{self.ticker} Corp"
                total_spend = 3000000
                latest_filing = "2024-10-01"
                number_of_filings = 3
                top_issues = "Tax Breaks"
            return [Row()]
        return []

class MockLobbyingClientMixed:
    def __init__(self, *args, **kwargs): pass
    def query(self, query, job_config=None):
        return MockLobbyingQueryMixed(job_config.query_parameters[0].value)

def mock_fetch_form4_mixed(ticker: str, analysis_date: str=""):
    """Custom Form4 Mock for Test 3 to force conflicting insider signals."""
    db = {
        "TRAP": {"ticker": "TRAP", "insider_title": "CFO", "transaction_type": "Sell", "signal_strength": "Warning - Insider Dumping"},
        "BEAR": {"ticker": "BEAR", "insider_title": "CEO", "transaction_type": "Buy", "signal_strength": "Strong Buy Confluence"},
        "BUBB": {"ticker": "BUBB", "insider_title": "Director", "transaction_type": "Hold", "signal_strength": "Neutral"}
    }
    return json.dumps(db.get(ticker.upper(), {"ticker": ticker, "signal_strength": "Neutral"}))


# =============================================================================
# INTEGRATION TEST 3: CONFLICTING SIGNALS & MACRO
# =============================================================================

@pytest.mark.asyncio
async def test_alpha_pipeline_mixed_cases(mocker, alpha_workflow_runner):
    """Tests Agent handling of conflicting signals, bad macro, and valuation bubbles."""
    runner, session_service = alpha_workflow_runner 

    # 🎯 PATCH WITH THE MIXED MOCKS
    mocker.patch('congress_trades_agent.tools._get_bq_data', side_effect=mock_get_bq_data_mixed)
    mocker.patch('congress_trades_agent.tools.yf.Ticker', side_effect=MockYFTickerMixed)
    mocker.patch('congress_trades_agent.extra_tools.bigquery.Client', side_effect=MockLobbyingClientMixed)
    # Patch the form4 tool specifically for this test so we can test the CFO dump
    mocker.patch('congress_trades_agent.extra_tools.fetch_form4_signals_tool', side_effect=mock_fetch_form4_mixed)

    session_id = "test_session_mixed_002"
    user_id = "test_quant"
    app_name = "AlphaTradingApp"
    test_prompt = "Run the Alpha strategy for 2024-10-15."

    await session_service.create_session(
        app_name=app_name, session_id=session_id, user_id=user_id, state={} 
    )
    
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content)
    
    print("\n" + "="*70)
    print("🕵️ TRACE: Mixed Conflicting Cases Testing")
    print("="*70)

    # We will print the Agent's thoughts here because it's fascinating to see how it resolves conflicts
    async for event in final_events_generator:
        if hasattr(event, 'model_response') and event.model_response:
            thought = event.model_response.text.strip()
            if thought:
                print(f"🧠 [THOUGHT]: {thought[:150]}...\n") 

    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    final_plan_str = final_session.state.get('final_trade_plan')
    
    clean_json_str = final_plan_str.replace("```json", "").replace("```", "").strip()
    trade_plan = json.loads(clean_json_str)
    actions = {trade["ticker"]: trade["action"] for trade in trade_plan}
    
    print(f"######----- Returned Mixed Actions: {actions} -----")
    
    # 🎯 Pattern 1: The Trap (Insider Dumping)
    assert "TRAP" in actions, "Agent skipped TRAP!"
    assert "PASS" in actions["TRAP"], f"Agent bought TRAP despite CFO dumping shares! Action: {actions['TRAP']}"

    # 🎯 Pattern 2: The Macro Headwind (Bear Market)
    assert "BEAR" in actions, "Agent skipped BEAR!"
    assert "STRONG BUY" not in actions["BEAR"], "Agent issued a Strong Buy in a Bear Market!"
    assert "PASS" in actions["BEAR"] or "HOLD" in actions["BEAR"], f"Agent failed to respect bearish regime! Action: {actions['BEAR']}"

    # 🎯 Pattern 3: Valuation Bubble (P/E 1000)
    assert "BUBB" in actions, "Agent skipped BUBB!"
    assert "BUY" not in actions["BUBB"], f"Agent bought a massive bubble (P/E 1000)! Action: {actions['BUBB']}"
    assert "PASS" in actions["BUBB"] or "HOLD" in actions["BUBB"], "Agent should have passed on BUBB due to valuation."

    print("✅ All Mixed Conflicting Cases passed successfully!")


# =============================================================================
# DEEP MOCKS: MIXED CONFLICTING CASES (MOH, BE, NDAQ)
# =============================================================================

def mock_get_bq_data_mixed(analysis_date: str) -> list:
    print(f"\n---> 🛑 BQ MOCK HIT: Returning Mixed signals for {analysis_date}")
    return [
        # MOH is the TRAP (Real Form4 tool says CFO Selling)
        {"ticker": "MOH", "net_buy_activity": 60, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date},
        # BE is the BEAR (Real Form4 tool says CEO Buying, but we force market_uptrend=False)
        {"ticker": "BE", "net_buy_activity": 80, "market_uptrend": False, "signal_date": analysis_date, "last_trade_date": analysis_date}, 
        # NDAQ is the BUBBLE (Real Form4 tool says Neutral, we force P/E = 1000)
        {"ticker": "NDAQ", "net_buy_activity": 40, "market_uptrend": True, "signal_date": analysis_date, "last_trade_date": analysis_date}
    ]

class MockYFTickerMixed:
    def __init__(self, ticker):
        self.ticker = ticker
        db = {
            # Give MOH great fundamentals so the ONLY reason to pass is the Insider Selling Trap
            "MOH": {"sector": "Technology", "industry": "Software", "marketCap": 10_000_000_000, "beta": 1.2, "forwardPE": 20, "debtToEquity": 40}, 
            "BE": {"sector": "Healthcare", "industry": "Medical", "marketCap": 20_000_000_000, "beta": 0.9, "forwardPE": 15, "debtToEquity": 50},
            # Give NDAQ a massive valuation bubble!
            "NDAQ": {"sector": "Technology", "industry": "Finance", "marketCap": 5_000_000_000, "beta": 2.5, "forwardPE": 1000, "debtToEquity": 10}, 
        }
        self.info = db.get(ticker.upper(), {"sector": "Unknown", "marketCap": 0, "beta": 1.0, "forwardPE": 10, "debtToEquity": 10})

class MockLobbyingQueryMixed:
    def __init__(self, ticker):
        self.ticker = ticker
    def result(self):
        # Give MOH and BE strong lobbying to make them look like Golden Signals initially
        if self.ticker in ["MOH", "BE"]:
            class Row:
                ticker = self.ticker
                client_name = f"{self.ticker} Corp"
                total_spend = 3000000
                latest_filing = "2024-10-01"
                number_of_filings = 3
                top_issues = "Tax Breaks"
            return [Row()]
        return []

class MockLobbyingClientMixed:
    def __init__(self, *args, **kwargs): pass
    def query(self, query, job_config=None):
        return MockLobbyingQueryMixed(job_config.query_parameters[0].value)

# =============================================================================
# INTEGRATION TEST 3: CONFLICTING SIGNALS & MACRO
# =============================================================================

@pytest.mark.asyncio
async def test_alpha_pipeline_mixed_cases(mocker, alpha_workflow_runner):
    """Tests Agent handling of conflicting signals, bad macro, and valuation bubbles."""
    runner, session_service = alpha_workflow_runner 

    # 🎯 PATCH WITH THE MIXED MOCKS (No need to patch Form4 anymore!)
    mocker.patch('congress_trades_agent.tools._get_bq_data', side_effect=mock_get_bq_data_mixed)
    mocker.patch('congress_trades_agent.tools.yf.Ticker', side_effect=MockYFTickerMixed)
    mocker.patch('congress_trades_agent.extra_tools.bigquery.Client', side_effect=MockLobbyingClientMixed)

    session_id = "test_session_mixed_002"
    user_id = "test_quant"
    app_name = "AlphaTradingApp"
    test_prompt = "Run the Alpha strategy for 2024-10-15."

    await session_service.create_session(
        app_name=app_name, session_id=session_id, user_id=user_id, state={} 
    )
    
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content)
    
    print("\n" + "="*70)
    print("🕵️ TRACE: Mixed Conflicting Cases Testing")
    print("="*70)

    async for event in final_events_generator:
        pass 

    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    final_plan_str = final_session.state.get('final_trade_plan')
    
    clean_json_str = final_plan_str.replace("```json", "").replace("```", "").strip()
    trade_plan = json.loads(clean_json_str)
    actions = {trade["ticker"]: trade["action"] for trade in trade_plan}
    
    print(f"######----- Returned Mixed Actions: {actions} -----")
    
    # 🎯 Pattern 1: The Trap (MOH - Insider Dumping overrides Congress Buying)
    assert "MOH" in actions, "Agent skipped MOH!"
    assert "PASS" in actions["MOH"], f"Agent bought MOH despite CFO dumping shares! Action: {actions['MOH']}"

    # 🎯 Pattern 2: The Macro Headwind (BE - Bear Market overrides Golden Signal)
    assert "BE" in actions, "Agent skipped BE!"
    assert "STRONG BUY" not in actions["BE"], "Agent issued a Strong Buy in a Bear Market!"
    assert "PASS" in actions["BE"] or "HOLD" in actions["BE"], f"Agent failed to respect bearish regime! Action: {actions['BE']}"

    # 🎯 Pattern 3: Valuation Bubble (NDAQ - P/E 1000 overrides Congress Buying)
    assert "NDAQ" in actions, "Agent skipped NDAQ!"
    assert "BUY" not in actions["NDAQ"], f"Agent bought a massive bubble (P/E 1000)! Action: {actions['NDAQ']}"
    assert "PASS" in actions["NDAQ"] or "HOLD" in actions["NDAQ"], "Agent should have passed on NDAQ due to valuation."

    print("✅ All Mixed Conflicting Cases passed successfully!")