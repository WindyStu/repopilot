def frozen(*_args):
    from attr.exceptions import FrozenAttributeError

    raise FrozenAttributeError
