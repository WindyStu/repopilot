from more_itertools import numeric_range


def test_full_reverse_slice():
    assert list(numeric_range(6)[::-1]) == [5, 4, 3, 2, 1, 0]


def test_open_ended_negative_step():
    assert list(numeric_range(10)[8::-2]) == [8, 6, 4, 2, 0]


def test_bounded_negative_step():
    assert list(numeric_range(10)[8:2:-2]) == [8, 6, 4]


def test_slice_of_nonunit_base_range():
    assert list(numeric_range(2, 14, 2)[::-2]) == [12, 8, 4]
