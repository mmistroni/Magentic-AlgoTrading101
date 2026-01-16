from agent_crawler.tools.character_counter import count_characters

def test_count_characters():
    sample_text = 'A sample sentence'
    assert count_characters(sample_text) == len(sample_text)
