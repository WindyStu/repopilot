import pytest

from more_itertools import interleave_evenly


def test_empty_inferred_input_returns_empty_iterator():
    assert list(interleave_evenly([])) == []


def test_empty_explicit_lengths_returns_empty_iterator():
    assert list(interleave_evenly([], lengths=[])) == []


def test_mismatched_lengths_still_raise():
    with pytest.raises(ValueError, match="Mismatching"):
        list(interleave_evenly([[1]], lengths=[]))
