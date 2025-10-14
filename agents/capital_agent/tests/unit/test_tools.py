from capital_agent.tools import get_capital_city

def test_get_capital_city_known():
    assert get_capital_city("France") == "Paris"
    assert get_capital_city("japan") == "Tokyo"
    assert get_capital_city("CANADA") == "Ottawa"
    assert get_capital_city("Morocco") == "Sorry, I don't know the capital of Morocco."
