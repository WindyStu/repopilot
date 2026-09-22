from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    state: State = State.PENDING
