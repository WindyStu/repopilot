from more_itertools import running_max, running_min


def test_windowed_values():
    assert list(running_min([3, 1, 2], maxlen=2)) == [3, 1, 1]
    assert list(running_max([1, 3, 2], maxlen=2)) == [1, 3, 3]
