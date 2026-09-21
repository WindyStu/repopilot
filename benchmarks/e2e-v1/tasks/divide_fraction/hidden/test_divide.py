import pytest

from calculator import divide


def test_fractional_quotient_is_not_truncated():
    assert divide(3, 2) == 1.5


def test_negative_fraction_is_preserved():
    assert divide(-1, 4) == -0.25


def test_zero_division_behavior_is_preserved():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)
