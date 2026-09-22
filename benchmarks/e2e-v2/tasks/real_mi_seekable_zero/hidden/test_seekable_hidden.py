from more_itertools import seekable


def test_zero_cache_peek_does_not_drop_first_item():
    values = seekable([10, 20, 30], maxlen=0)
    assert values.peek() == 10
    assert list(values) == [10, 20, 30]


def test_zero_cache_repeated_peek_returns_same_item():
    values = seekable([10, 20], maxlen=0)
    assert values.peek() == 10
    assert values.peek() == 10
    assert next(values) == 10


def test_zero_cache_truth_check_preserves_stream():
    values = seekable([10, 20], maxlen=0)
    assert values
    assert list(values) == [10, 20]


def test_empty_zero_cache_is_falsy():
    assert not seekable([], maxlen=0)
