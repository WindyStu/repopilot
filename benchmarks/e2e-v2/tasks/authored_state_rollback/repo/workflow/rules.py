from workflow.models import State

ALLOWED_TRANSITIONS = {
    State.PENDING: {State.RUNNING},
    State.RUNNING: {State.COMPLETE, State.FAILED},
    State.COMPLETE: set(),
    State.FAILED: set(),
}


def can_transition(current: State, target: State) -> bool:
    return target in ALLOWED_TRANSITIONS[current]
