from click import make_default_short_help


def test_abbreviation_does_not_end_sentence():
    assert make_default_short_help("Weigh apples vs. pears.", 30) == "Weigh apples vs. pears."


def test_abbreviation_is_kept_when_truncating_later_text():
    assert make_default_short_help("Weigh apples vs. pears and plums.", 20) == "Weigh apples vs...."


def test_period_before_uppercase_still_ends_sentence():
    assert make_default_short_help("Pick fruit. Three remain.", 40) == "Pick fruit."


def test_lowercase_after_period_continues_sentence():
    assert make_default_short_help("Use config.toml. then continue", 25) == "Use config.toml. then..."
