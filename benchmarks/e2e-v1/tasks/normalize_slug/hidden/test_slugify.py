from text_utils import slugify


def test_normalizes_case_and_surrounding_whitespace():
    assert slugify("  Hello World  ") == "hello-world"


def test_collapses_mixed_whitespace():
    assert slugify("one\t two\nthree") == "one-two-three"


def test_empty_and_whitespace_only_values():
    assert slugify("") == ""
    assert slugify(" \t\n ") == ""
