from collections.abc import Callable

from workflow.models import Job, State
from workflow.rules import can_transition


def advance(job: Job, target: State, persist: Callable[[Job], None]) -> Job:
    if not can_transition(job.state, target):
        raise ValueError(f"invalid transition: {job.state.value} -> {target.value}")
    job.state = target
    persist(job)
    return job
