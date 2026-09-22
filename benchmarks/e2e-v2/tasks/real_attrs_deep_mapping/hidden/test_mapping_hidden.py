import pytest

from attr import deep_mapping, instance_of


def test_key_validator_can_be_omitted():
    validator = deep_mapping(value_validator=instance_of(int))
    validator(None, "field", {1: 2, object(): 3})


def test_value_validator_can_be_omitted():
    validator = deep_mapping(key_validator=instance_of(str))
    validator(None, "field", {"a": object(), "b": None})


def test_neither_key_nor_value_validator_is_rejected():
    with pytest.raises(ValueError, match="At least one"):
        deep_mapping()


def test_present_validator_still_runs():
    validator = deep_mapping(value_validator=instance_of(int))
    with pytest.raises(TypeError, match="must be int"):
        validator(None, "field", {"a": "wrong"})
