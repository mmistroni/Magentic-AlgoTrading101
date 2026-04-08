import pytest
import json
import os
import shutil

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# 1. Import your actual pipeline
from congress_trades_agent.agent import CONGRESS_PIPELINE

# =============================================================================
# INLINE MOCK FUNCTIONS (No need for external mock_tools.py!)
# =============================================================================

def mock_fetch_congress(analysis_date: str):
    print(f"Mocking Congress signals for {analysis_date}")
    return json.dumps([
        {"ticker": "BE", "net_buy_activity": 85, "market_uptrend": True},
        {"ticker": "MOH", "net_buy_activity": 15, "market_uptrend": False},
        {"ticker": "EQIX", "net_buy_activity": 50, "market_uptrend": True}
    ])

def mock_check_fundamentals(ticker: str):
    print(f"Mocking fundamentals for {ticker}")
    db = {
        "BE": {"ticker": "BE", "sector": "Technology", "forward_pe": 25, "debt_to_equity": 50, "market_cap_B": 10},
        "MOH": {"ticker": "MOH", "sector": "Healthcare", "forward_pe": 15, "debt_to_equity": 80, "market_cap_B": 5},
        "EQIX": {"ticker": "EQIX", "sector": "Real Estate", "forward_pe": 60, "debt_to_equity": 250, "market_cap_B": 80} # High Debt + High PE = Trap
    }
    return json.dumps(db.get(ticker.upper(), {"error": "Not Found"}))

def mock_fetch_form4(ticker: str, analysis_date: str=""):
    print(f"Mocking Form 4 for {ticker}")
    db = {
        "BE": {"ticker": "BE", "insider_title": "CEO", "transaction_type": "Buy", "signal_strength": "Strong"},
        "MOH": {"ticker": "MOH", "insider_title": "CFO", "transaction_type": "Sell", "signal_strength": "Warning"},
    }
    return json.dumps(db.get(ticker.upper(), {"ticker": ticker, "signal_strength": "Neutral"}))

def mock_fetch_lobbying(ticker: str):
    print(f"Mocking Lobbying for {ticker}")
    db = {
        "BE": {"ticker": "BE", "total_spend_last_12m": 5000000, "top_lobbied_issues": "Green Energy Subsidies"},
    }
    return json.dumps(db.get(ticker.upper(), {"ticker": ticker, "lobbying_status": "No activity"}))


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
    """Initializes the ADK Runner with our pipeline."""
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

    # --- PATCH THE REAL TOOLS WITH OUR INLINE MOCKS ---
    # Note: These paths must match exactly where the tools are imported in agent.py
    mocker.patch('congress_trades_agent.tools.fetch_congress_signals_tool', side_effect=mock_fetch_congress)
    mocker.patch('congress_trades_agent.tools.check_fundamentals_tool', side_effect=mock_check_fundamentals)
    
    mocker.patch('congress_trades_agent.extra_tools.fetch_form4_signals_tool', side_effect=mock_fetch_form4)
    mocker.patch('congress_trades_agent.extra_tools.fetch_lobbying_signals_tool', side_effect=mock_fetch_lobbying)

    session_id = "test_session_alpha_003"
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
            print(f"🛠️ [TOOL CALLED]: {event.tool_call.function_name}({event.tool_call.arguments})")

        if hasattr(event, 'model_response') and event.model_response:
            thought = event.model_response.text.strip()
            if thought:
                print(f"🧠 [THOUGHT/OUTPUT]: {thought[:200]}...\n")

    print("="*70)

    # --- FINAL ASSERTIONS ---
    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    final_state = final_session.state
    
    final_plan_str = final_state.get('final_trade_plan')
    assert final_plan_str is not None, "Trader failed to output a final plan!"
    
    # Extract JSON safely
    clean_json_str = final_plan_str.replace("```json", "").replace("```", "").strip()
    trade_plan = json.loads(clean_json_str)

    actions = {trade["ticker"]: trade["action"] for trade in trade_plan}
    
    # 🎯 Verify against our mock logic
    assert "BUY" in actions["BE"], "Agent failed to buy the Golden Confluence stock (BE)!"
    assert actions["MOH"] == "PASS", "Agent mistakenly bought a FALLING KNIFE (MOH)!"
    assert actions["EQIX"] == "PASS", "Agent ignored the Safety Rails and bought EQIX!"

    print("✅ All Agent Logic and Guardrails passed successfully!")