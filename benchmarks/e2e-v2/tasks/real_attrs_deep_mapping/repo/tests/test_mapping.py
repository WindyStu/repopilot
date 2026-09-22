from attr import deep_mapping, instance_of


def test_both_validators_accept_valid_mapping():
    validator = deep_mapping(instance_of(str), instance_of(int))
    validator(None, "field", {"a": 1})
