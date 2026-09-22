def pipe(*validators):
    def validate(instance, attribute, value):
        for validator in validators:
            validator(instance, attribute, value)

    return validate
