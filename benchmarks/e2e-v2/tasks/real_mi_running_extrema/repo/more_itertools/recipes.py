from collections import deque
from itertools import accumulate


def _windowed_running_min(iterator, maxlen):
    candidates = deque()
    for index, value in enumerate(iterator):
        if candidates and candidates[0][0] == index - maxlen:
            candidates.popleft()
        while candidates and not candidates[-1][1] < value:
            candidates.pop()
        candidates.append((index, value))
        yield candidates[0][1]


def running_min(iterable, *, maxlen=None):
    iterator = iter(iterable)
    if maxlen is None:
        return accumulate(iterator, min)
    return _windowed_running_min(iterator, maxlen)


def _windowed_running_max(iterator, maxlen):
    candidates = deque()
    for index, value in enumerate(iterator):
        if candidates and candidates[0][0] == index - maxlen:
            candidates.popleft()
        while candidates and not candidates[-1][1] > value:
            candidates.pop()
        candidates.append((index, value))
        yield candidates[0][1]


def running_max(iterable, *, maxlen=None):
    iterator = iter(iterable)
    if maxlen is None:
        return accumulate(iterator, max)
    return _windowed_running_max(iterator, maxlen)
