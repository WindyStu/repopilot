from more_itertools import seekable


def test_regular_cache_can_peek_without_consuming():
    values = seekable([1, 2, 3])
    assert values.peek() == 1
    assert list(values) == [1, 2, 3]
