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
        sliced = self._range[key]
        return numeric_range(sliced.start, sliced.stop, sliced.step)

    def __reversed__(self):
        return iter(
            numeric_range(
                self._get_by_index(-1), self._start - self._step, -self._step
            )
        )
