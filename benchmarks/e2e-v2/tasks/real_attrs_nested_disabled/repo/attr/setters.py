def pipe(*hooks):
    def apply(instance, attribute, value):
        for hook in hooks:
            value = hook(instance, attribute, value)
        return value

    return apply
