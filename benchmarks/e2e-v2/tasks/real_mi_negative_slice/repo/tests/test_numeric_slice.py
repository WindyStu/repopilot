from more_itertools import numeric_range


def test_forward_slice():
    assert list(numeric_range(10)[2:7:2]) == [2, 4, 6]
