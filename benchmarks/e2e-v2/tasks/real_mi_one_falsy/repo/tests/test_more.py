import pytest

from more_itertools import one, only


def test_default_behaviour():
    assert one([1]) == 1
    assert only([], default="missing") == "missing"
    with pytest.raises(ValueError):
        one([1, 2])
