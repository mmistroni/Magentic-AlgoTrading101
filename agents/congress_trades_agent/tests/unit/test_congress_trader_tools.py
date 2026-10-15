from unittest.mock import patch
from congress_trader.tools import get_fundamentals
from schemas import FundamentalEvaluation

@patch("congress_trader.tools.fetch_fmp_fundamentals")
def test_get_fundamentals_tool_wraps_pydantic(mock_fetch):
    mock_fetch.return_value = {
        "ticker": "MSFT",
        "pe_ratio": 28.0,
        "forward_pe": 25.0,
        "debt_to_equity": 0.8,
        "free_cash_flow_yield": 0.03,
        "return_on_equity": 0.35,
        "valuation_verdict": "FAIRLY_VALUED",
        "fundamental_health_score": 70.0,
        "error": None
    }

    result = get_fundamentals("msft")
    
    # Ensure it returns the strongly-typed Pydantic instance or model-dumped structure expected by ADK
    assert isinstance(result, FundamentalEvaluation)
    assert result.ticker == "MSFT"
    assert result.valuation_verdict == "FAIRLY_VALUED"
    mock_fetch.assert_called_once_with("msft")