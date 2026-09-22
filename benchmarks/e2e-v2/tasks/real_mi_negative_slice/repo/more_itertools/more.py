from collections.abc import Sequence


class numeric_range(Sequence):
    def __init__(self, start, stop=None, step=1):
        if stop is None:
            start, stop = 0, start
        self._start = start
        self._stop = stop
        self._step = step
        self._range = range(start, stop, step)
        self._len = len(self._range)

    def __len__(self):
        return self._len

    def _get_by_index(self, index):
        return self._range[index]

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._get_by_index(key)
        if isinstance(key, slice):
            step = self._step if key.step is None else key.step * self._step
            if key.start is None or key.start <= -self._len:
                start = self._start
            elif key.start >= self._len:
                start = self._stop
            else:
                start = self._get_by_index(key.start)
            if key.stop is None or key.stop >= self._len:
                stop = self._stop
            elif key.stop <= -self._len:
                stop = self._start
            else:
                stop = self._get_by_index(key.stop)
            return numeric_range(start, stop, step)
        raise TypeError("numeric range indices must be integers or slices")
