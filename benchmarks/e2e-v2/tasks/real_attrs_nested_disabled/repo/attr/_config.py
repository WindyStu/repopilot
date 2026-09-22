_run_validators = True


def get_run_validators():
    return _run_validators


def set_run_validators(run):
    global _run_validators
    _run_validators = bool(run)
