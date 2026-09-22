from more_itertools import constrained_batches


def test_batches_respect_size_and_count():
    items = [b"123", b"45", b"6"]
    assert list(constrained_batches(items, 5, max_count=2)) == [(b"123", b"45"), (b"6",)]
