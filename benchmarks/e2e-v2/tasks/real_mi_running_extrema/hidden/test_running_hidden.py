from fractions import Fraction

from more_itertools import running_max, running_min


def test_running_min_keeps_first_equal_value_in_window():
    data = [0, 0.0, Fraction(0)]
    assert list(map(type, running_min(data, maxlen=2))) == [int, int, float]


def test_running_max_keeps_first_equal_value_in_window():
    data = [0, 0.0, Fraction(0)]
    assert list(map(type, running_max(data, maxlen=2))) == [int, int, float]


def test_distinct_values_remain_numerically_correct():
    data = [4, 2, 5, 1]
    assert list(running_min(data, maxlen=2)) == [4, 2, 2, 1]
    assert list(running_max(data, maxlen=2)) == [4, 4, 5, 5]
