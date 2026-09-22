import pytest

from more_itertools import one, only


class FalsyError(Exception):
    def __bool__(self):
        return False


def test_one_raises_falsy_too_short_instance():
    error = FalsyError("too few")
    with pytest.raises(FalsyError) as caught:
        one([], too_short=error)
    assert caught.value is error


def test_one_raises_falsy_too_long_instance():
    error = FalsyError("too many")
    with pytest.raises(FalsyError) as caught:
        one([1, 2], too_long=error)
    assert caught.value is error


def test_only_raises_falsy_too_long_instance():
    error = FalsyError("too many")
    with pytest.raises(FalsyError) as caught:
        only([1, 2], too_long=error)
    assert caught.value is error


def test_custom_exception_does_not_evaluate_item_repr():
    class NoRepr:
        def __repr__(self):
            raise RuntimeError("repr should not be called")

    with pytest.raises(OverflowError):
        one([NoRepr(), NoRepr()], too_long=OverflowError("many"))
