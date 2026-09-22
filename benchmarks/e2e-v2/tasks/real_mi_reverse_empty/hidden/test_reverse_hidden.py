from more_itertools import numeric_range


def test_reverse_empty_zero_stop_is_empty():
    assert list(reversed(numeric_range(0))) == []


def test_reverse_empty_equal_bounds_is_empty():
    assert list(reversed(numeric_range(3, 3))) == []


def test_reverse_nonempty_behavior_is_unchanged():
    assert list(reversed(numeric_range(2, 7, 2))) == [6, 4, 2]
