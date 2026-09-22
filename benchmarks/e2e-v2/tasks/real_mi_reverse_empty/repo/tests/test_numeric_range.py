from more_itertools import numeric_range


def test_reverse_nonempty_range():
    assert list(reversed(numeric_range(1, 5))) == [4, 3, 2, 1]
