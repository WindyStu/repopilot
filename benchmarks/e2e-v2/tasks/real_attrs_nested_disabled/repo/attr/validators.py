from contextlib import contextmanager

from attr._config import get_run_validators, set_run_validators


@contextmanager
def disabled():
    set_run_validators(False)
    try:
        yield
    finally:
        set_run_validators(True)
