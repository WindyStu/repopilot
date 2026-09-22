def chunked(iterable, size):
    iterator = iter(iterable)
    while chunk := tuple(next(iterator, None) for _ in range(size)):
        yield tuple(item for item in chunk if item is not None)
