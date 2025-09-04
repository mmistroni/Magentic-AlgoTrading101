import pytest_asyncio
import pytest
from agent_team.tools import get_weather

@pytest.mark.parametrize(
    "input_city, expected_status",
    [
        ('New York', 'success'),
        ('London', 'success'),
        ('Paris', 'error'),
        ('Tokyo', 'success'),
        ('Berlin', 'error'),
    ]
)
def test_get_weather(input_city, expected_status):
    res = get_weather(input_city)
    assert res['status'] == expected_status