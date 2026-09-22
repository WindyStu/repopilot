from collections import deque
from itertools import chain

_marker = object()


class seekable:
    def __init__(self, iterable, maxlen=None):
        self._source = iter(iterable)
        self._cache = [] if maxlen is None else deque(maxlen=maxlen)
        self._index = None

    def __iter__(self):
        return self

    def __next__(self):
        if self._index is not None:
            try:
                item = self._cache[self._index]
            except IndexError:
                self._index = None
            else:
                self._index += 1
                return item
        item = next(self._source)
        self._cache.append(item)
        return item

    def elements(self):
        return iter(self._cache)

    def peek(self, default=_marker):
        try:
            peeked = next(self)
        except StopIteration:
            if default is _marker:
                raise
            return default
        if self._index is None:
            self._index = len(self._cache)
        self._index -= 1
        return peeked

    def __bool__(self):
        try:
            self.peek()
        except StopIteration:
            return False
        return True
