from attr import FrozenAttributeError, FrozenError, FrozenInstanceError


def test_base_error_carries_message_in_base_exception_args():
    error = FrozenError()
    assert str(error) == "can't set attribute"
    assert error.args == ("can't set attribute",)


def test_instance_error_carries_message():
    error = FrozenInstanceError()
    assert error.msg == error.args[0] == "can't set attribute"
    assert str(error) == "can't set attribute"


def test_attribute_error_carries_message():
    error = FrozenAttributeError()
    assert error.msg == error.args[0] == "can't set attribute"
    assert str(error) == "can't set attribute"
