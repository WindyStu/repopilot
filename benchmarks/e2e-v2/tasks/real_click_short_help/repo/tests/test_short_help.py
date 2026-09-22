from click import make_default_short_help


def test_first_sentence_is_used():
    assert make_default_short_help("First sentence. Second sentence.", 40) == "First sentence."
