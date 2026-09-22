def interleave_evenly(iterables, lengths=None):
    if lengths is None:
        lengths = [len(item) for item in iterables]
    if len(iterables) != len(lengths):
        raise ValueError("Mismatching number of iterables and lengths.")

    dims = len(lengths)
    primary_index = max(range(dims), key=lambda index: lengths[index])
    iterators = [iter(item) for item in iterables]
    remaining = list(lengths)
    while any(remaining):
        for index in range(dims):
            if remaining[index]:
                yield next(iterators[index])
                remaining[index] -= 1
        if remaining[primary_index] < 0:
            raise RuntimeError("invalid length metadata")
