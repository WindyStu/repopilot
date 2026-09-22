from typing import ClassVar


class FrozenError(AttributeError):
    msg = "can't set attribute"
    args: ClassVar[tuple[str]] = [msg]


class FrozenInstanceError(FrozenError):
    pass


class FrozenAttributeError(FrozenError):
    pass
