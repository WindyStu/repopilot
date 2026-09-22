class _InstanceOf:
    def __init__(self, expected_type):
        self.expected_type = expected_type

    def __call__(self, instance, attribute, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f"{value!r} must be {self.expected_type.__name__}")


def instance_of(expected_type):
    return _InstanceOf(expected_type)


class _DeepMapping:
    def __init__(self, key_validator, value_validator, mapping_validator=None):
        if not callable(key_validator) or not callable(value_validator):
            raise TypeError("key and value validators must be callable")
        if mapping_validator is not None and not callable(mapping_validator):
            raise TypeError("mapping validator must be callable")
        self.key_validator = key_validator
        self.value_validator = value_validator
        self.mapping_validator = mapping_validator

    def __call__(self, instance, attribute, value):
        if self.mapping_validator is not None:
            self.mapping_validator(instance, attribute, value)
        for key in value:
            self.key_validator(instance, attribute, key)
            self.value_validator(instance, attribute, value[key])


def deep_mapping(key_validator, value_validator, mapping_validator=None):
    return _DeepMapping(key_validator, value_validator, mapping_validator)
