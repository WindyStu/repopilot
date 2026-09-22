import pytest

from more_itertools import constrained_batches


def test_zero_max_count_is_rejected():
    with pytest.raises(ValueError, match="maximum count"):
        list(constrained_batches([b"a"], 10, max_count=0))


def test_negative_max_count_is_rejected():
    with pytest.raises(ValueError, match="maximum count"):
        list(constrained_batches([b"a"], 10, max_count=-2))


def test_positive_count_still_limits_batches():
    assert list(constrained_batches([b"a", b"b", b"c"], 10, max_count=2)) == [
        (b"a", b"b"),
        (b"c",),
    ]
