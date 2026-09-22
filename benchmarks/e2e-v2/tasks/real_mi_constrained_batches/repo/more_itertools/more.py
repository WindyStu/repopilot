def constrained_batches(iterable, max_size, max_count=None, get_len=len, strict=True):
    if max_size <= 0:
        raise ValueError("maximum size must be greater than zero")

    batch = []
    batch_size = 0
    batch_count = 0
    for item in iterable:
        item_len = get_len(item)
        if item_len > max_size and strict:
            raise ValueError("item size exceeds maximum size")
        reached_count = batch_count == max_count
        if batch and (batch_size + item_len > max_size or reached_count):
            yield tuple(batch)
            batch = []
            batch_size = 0
            batch_count = 0
        batch.append(item)
        batch_size += item_len
        batch_count += 1
    if batch:
        yield tuple(batch)
