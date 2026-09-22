from dataclasses import dataclass

from workflow.models import State


@dataclass(frozen=True)
class TransitionRecord:
    job_id: str
    previous: State
    current: State
