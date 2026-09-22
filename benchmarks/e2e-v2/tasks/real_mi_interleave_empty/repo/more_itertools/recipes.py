def roundrobin(*iterables):
    for values in zip(*iterables):
        yield from values
