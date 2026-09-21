from text_utils import slugify


def test_simple_words_are_joined():
    assert slugify("hello world") == "hello-world"
