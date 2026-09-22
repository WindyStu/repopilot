import pytest

from workflow import Job, State, advance


def test_persistence_failure_rolls_back_in_memory_state():
    job = Job("job-1", State.RUNNING)

    def fail(_job):
        raise OSError("database unavailable")

    with pytest.raises(OSError, match="database unavailable"):
        advance(job, State.COMPLETE, fail)

    assert job.state is State.RUNNING


def test_successful_transition_keeps_new_state_and_persists_once():
    job = Job("job-2", State.RUNNING)
    observed = []

    advance(job, State.FAILED, lambda current: observed.append(current.state))

    assert job.state is State.FAILED
    assert observed == [State.FAILED]


def test_invalid_transition_neither_mutates_nor_persists():
    job = Job("job-3", State.PENDING)
    persisted = []

    with pytest.raises(ValueError, match="invalid transition"):
        advance(job, State.COMPLETE, persisted.append)

    assert job.state is State.PENDING
    assert persisted == []
