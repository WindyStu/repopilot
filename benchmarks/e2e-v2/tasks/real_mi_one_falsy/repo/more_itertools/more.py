def one(iterable, too_short=None, too_long=None):
    iterator = iter(iterable)
    for first in iterator:
        for second in iterator:
            msg = (
                f"Expected exactly one item in iterable, but got {first!r}, "
                f"{second!r}, and perhaps more."
            )
            raise too_long or ValueError(msg)
        return first
    raise too_short or ValueError("too few items in iterable (expected 1)")


def only(iterable, default=None, too_long=None):
    iterator = iter(iterable)
    for first in iterator:
        for second in iterator:
            msg = (
                f"Expected exactly one item in iterable, but got {first!r}, "
                f"{second!r}, and perhaps more."
            )
            raise too_long or ValueError(msg)
        return first
    return default
