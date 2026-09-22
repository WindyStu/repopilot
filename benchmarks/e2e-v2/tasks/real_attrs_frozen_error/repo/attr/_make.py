def frozen_setattr(*_args):
    from attr.exceptions import FrozenInstanceError

    raise FrozenInstanceError
