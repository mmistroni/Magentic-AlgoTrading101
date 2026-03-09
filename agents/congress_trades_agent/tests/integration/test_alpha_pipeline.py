import pytest
import json
import os
import shutil

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# 1. Import your actual pipeline and agents
# (Adjust 'my_stock_app' to whatever your actual folder/module is named)
from congress_trades_agent.congress_agents import CONGRESS_PIPELINE
from congress_trades_agent.congress_agents import congress_researcher, insider_analyst, congress_trader

# -----------------------------------------------------------------------------
# --- FIXTURES (MOCK DATA) ---
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_congress_data():
    """Mocks the BigQuery output for Congress trades."""
    return json.dumps([
        {
            "ticker": "BE", 
            "net_buy_activity": 25, 
            "market_uptrend": True, 
            "buying_days_count": 4,
            "senator": "Sen. Carper"
        }
    ])

@pytest.fixture
def mock_lobbying_data():
    """Mocks the BigQuery Lobbying tool output."""
    return json.dumps({
        "ticker": "BE",
        "company_name": "Bloom Energy",
        "total_spend_last_12m": 150000.0,
        "number_of_filings": 2,
        "top_lobbied_issues": "Hydrogen Tax Credits, Clean Energy Infrastructure"
    })

@pytest.fixture
def mock_form4_data():
    """Mocks the Form 4 Insider trading tool output."""
    return json.dumps({
        "ticker": "BE",
        "insider_title": "CEO",
        "transaction_type": "Buy",
        "shares": 25000,
        "signal_strength": "Strong Buy Confluence"
    })

@pytest.fixture
def mock_fundamentals_data():
    """Mocks the Yahoo Finance fundamentals output."""
    return json.dumps({
        "ticker": "BE",
        "sector": "Energy",
        "market_cap_B": 4.2,
        "beta": 1.2,
        "forward_pe": 25.5,
        "debt_to_equity": 120.0,
        "dividend_yield": 0.0
    })

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
    """Initializes the ADK Runner with our Alpha Council pipeline."""
    session_service = InMemorySessionService()
    
    runner = Runner(
        agent=CONGRESS_PIPELINE, 
        session_service=session_service,
        app_name="AlphaCouncilApp" 
    )
    return runner, session_service

# -----------------------------------------------------------------------------
# --- THE INTEGRATION TEST ---
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_alpha_council_full_run_with_mocks(mocker, 
                                                 mock_congress_data,
                                                 mock_lobbying_data,
                                                 mock_form4_data,
                                                 mock_fundamentals_data,
                                                 alpha_workflow_runner):
    """
    Tests the full pipeline execution: Researcher -> Analyst -> Trader.
    Verifies that state is passed correctly via output_keys and tools are called.
    """
    runner, session_service = alpha_workflow_runner 

    # 1. Patch all 4 tools to return our Mock Data
    # (Update 'my_stock_app.tools' to your actual module path)
    mocker.patch('my_stock_app.tools.fetch_congress_signals_tool', return_value=mock_congress_data)
    mocker.patch('my_stock_app.tools.fetch_lobbying_signals_tool', return_value=mock_lobbying_data)
    mocker.patch('my_stock_app.tools.fetch_form4_signals_tool', return_value=mock_form4_data)
    mocker.patch('my_stock_app.tools.check_fundamentals_tool', return_value=mock_fundamentals_data)

    session_id = "test_alpha_session_001"
    user_id = "test_quant"
    app_name = "AlphaCouncilApp"
    
    # We trigger the pipeline with a request for a specific date
    test_prompt = "Run the Congress Alpha strategy for 2024-10-15. Check for tailwinds."

    # 2. CREATE AND INITIALIZE THE SESSION
    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={} 
    )
    
    # 3. ACT: Run the agent pipeline
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )
    
    print("\n" + "="*70)
    print("🕵️ DEEP TRACE: Alpha Council Execution")
    print("="*70)

    # 4. Consume and Trace the Async Generator
    async for event in final_events_generator:
        
        # Track Agent Handoffs
        if hasattr(event, 'agent_call'):
            print(f"\n🚀 [AGENT] Active: {event.agent_call.agent_name}")
        
        # Track LLM Reasoning
        if hasattr(event, 'model_response') and event.model_response:
            thought = event.model_response.text.strip()
            if thought:
                print(f"🧠 [THOUGHT]: {thought[:150]}...")

        # Track Tool Execution
        if hasattr(event, 'tool_call'):
            print(f"🛠️ [TOOL CALL]: {event.tool_call.function_name}")
            print(f"📥 [ARGS]: {event.tool_call.arguments}")

        # Track State Mutations
        if hasattr(event, 'state_update') and event.state_update:
            for key in event.state_update.keys():
                print(f"💾 [STATE UPDATE]: Key '{key}' committed to session.")

    print("\n" + "="*70)

    # =========================================================================
    # 5. ASSERT: State Verification (Did the baton get passed?)
    # =========================================================================
    
    final_session = await session_service.get_session(
        app_name=app_name, 
        user_id=user_id, 
        session_id=session_id
    )
    final_state = final_session.state
    
    # 1. Did the Researcher output the Context?
    assert 'political_context' in final_state, "Researcher failed to output political_context"
    print("✅ Researcher State verified.")

    # 2. Did the Insider Analyst output the Confluence Report?
    assert 'confluence_report' in final_state, "Analyst failed to output confluence_report"
    print("✅ Insider Analyst State verified.")

    # 3. Did the Trader output the Final Plan?
    final_plan = final_state.get('final_trade_plan')
    assert final_plan is not None, "Trader failed to generate final_trade_plan"
    print("✅ Trader State verified.")
    
    print(f"\n📊 FINAL TRADE PLAN:\n{final_plan}")