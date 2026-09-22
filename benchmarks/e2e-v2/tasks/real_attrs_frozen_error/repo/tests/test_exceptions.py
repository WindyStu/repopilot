from attr import FrozenError


def test_frozen_error_is_attribute_error():
    assert isinstance(FrozenError(), AttributeError)
