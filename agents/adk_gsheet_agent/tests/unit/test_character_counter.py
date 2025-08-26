import pytest
from adk_gsheet_agent.tools.character_counter import count_characters


# Need to mock initialize_agent_dependencies

def test_count_characters():

    mocker.patch('app.get_external_data', return_value=mocked_return_value)

    sample_text = 'A sample sentence'
    assert count_characters(sample_text) == len(sample_text)
