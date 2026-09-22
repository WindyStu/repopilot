from attr import disabled, get_run_validators


def test_single_context_disables_then_restores():
    assert get_run_validators() is True
    with disabled():
        assert get_run_validators() is False
    assert get_run_validators() is True
