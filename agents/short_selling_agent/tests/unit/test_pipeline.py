import pytest
import json
from unittest.mock import patch, MagicMock

# 1. Import your State Manager
from short_selling_agent.state import CURRENT_RUN_STATE

# 2. Import the wrapper tools you just built
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates,
    tool_stage_news,
    tool_stage_insiders,
    tool_read_full_dossier
)

# 3. Import your Pydantic schemas so we can build fake data
from short_selling_agent.schemas import (
    StockNewsReport, 
    InsiderTradingReport, 
    NewsArticle, 
    InsiderTrade
)

# ==========================================
# FIXTURE: Reset Memory Bank Before Each Test
# ==========================================
@pytest.fixture(autouse=True)
def clean_memory_bank():
    """This runs automatically before every single test to ensure a blank slate."""
    CURRENT_RUN_STATE.reset()
    yield

# ==========================================
# TEST 1: Agent 1's BigQuery Tool
# ==========================================
@patch('short_selling_agent.stage_tools.bigquery.Client')
def test_tool_fetch_bq_candidates_offline(mock_bq_client):
    """Tests that Agent 1 can fetch data from BQ and save it to Python memory."""
    
    # Setup Fake BigQuery Response
    mock_query_job = MagicMock()
    fake_row_1 = MagicMock(ticker="AAPL", price=150.0, change_pct=-5.0)
    fake_row_2 = MagicMock(ticker="TSLA", price=200.0, change_pct=-8.0)
    mock_query_job.result.return_value = [fake_row_1, fake_row_2]
    
    mock_bq_client.return_value.query.return_value = mock_query_job

    # Agent 1 Executes the Tool
    result_string = tool_fetch_bq_candidates()

    # Assertions: Did the state update correctly?
    assert "AAPL" in result_string
    assert "TSLA" in result_string
    assert len(CURRENT_RUN_STATE.dossier.market_losers) == 2
    assert CURRENT_RUN_STATE.dossier.market_losers[0].ticker == "AAPL"
    assert CURRENT_RUN_STATE.dossier.market_losers[1].change_pct == -8.0

# ==========================================
# TEST 2: Agent 2's News Tool
# ==========================================
# Notice we patch your ORIGINAL tool, not the wrapper tool!
@patch('short_selling_agent.stage_tools.get_fmp_news') 
def test_tool_stage_news_offline(mock_get_fmp_news):
    """Tests that Agent 2 can fetch news and save it to the global state."""
    
    # Setup Fake Pydantic Return Value for the original tool
    mock_get_fmp_news.return_value = StockNewsReport(
        ticker="AAPL",
        articles=[NewsArticle(date="2023-10-01", title="AAPL Earnings Miss")]
    )

    # Agent 2 Executes the Wrapper Tool
    result_string = tool_stage_news("AAPL")

    # Assertions
    assert "Success" in result_string
    assert len(CURRENT_RUN_STATE.dossier.news_reports) == 1
    assert CURRENT_RUN_STATE.dossier.news_reports[0].ticker == "AAPL"
    assert CURRENT_RUN_STATE.dossier.news_reports[0].articles[0].title == "AAPL Earnings Miss"

# ==========================================
# TEST 3: Agent 3's Insider Tool
# ==========================================
@patch('short_selling_agent.stage_tools.get_bearish_insider_sales')
def test_tool_stage_insiders_offline(mock_get_insiders):
    """Tests that Agent 3 can fetch insider sales and save them to the state."""
    
    # Setup Fake Pydantic Return Value
    mock_get_insiders.return_value = InsiderTradingReport(
        ticker="TSLA",
        total_dollars_dumped=5000000.0,
        significant_sales=[
            InsiderTrade(date="2023-10-01", name="Elon", title="CEO", value_sold=5000000.0)
        ]
    )

    # Agent 3 Executes the Wrapper Tool
    result_string = tool_stage_insiders("TSLA")

    # Assertions
    assert "Success" in result_string
    assert len(CURRENT_RUN_STATE.dossier.insider_reports) == 1
    assert CURRENT_RUN_STATE.dossier.insider_reports[0].total_dollars_dumped == 5000000.0

# ==========================================
# TEST 4: Agent 4's Reading Tool (The Integration Test)
# ==========================================
def test_tool_read_full_dossier():
    """Tests that Agent 4 receives a perfectly formatted JSON string of all accumulated data."""
    
    # 1. Manually inject fake data into the state (simulating Agents 1, 2, and 3 finishing)
    from short_selling_agent.schemas import MarketLoser
    CURRENT_RUN_STATE.dossier.market_losers.append(MarketLoser(ticker="MSFT", price=300.0, change_pct=-2.0))
    
    CURRENT_RUN_STATE.dossier.news_reports.append(StockNewsReport(
        ticker="MSFT", articles=[NewsArticle(date="Today", title="Bad news")]
    ))
    
    CURRENT_RUN_STATE.dossier.insider_reports.append(InsiderTradingReport(
        ticker="MSFT", total_dollars_dumped=0.0, significant_sales=[]
    ))

    # 2. Agent 4 Executes its reading tool
    json_output = tool_read_full_dossier()
    
    # 3. Parse the JSON back into a dict to verify it
    parsed_data = json.loads(json_output)
    
    # 4. Assertions: Does the Quant get the right JSON?
    assert len(parsed_data["market_losers"]) == 1
    assert parsed_data["market_losers"][0]["ticker"] == "MSFT"
    assert len(parsed_data["news_reports"]) == 1
    assert parsed_data["news_reports"][0]["articles"][0]["title"] == "Bad news"
    assert len(parsed_data["insider_reports"]) == 1