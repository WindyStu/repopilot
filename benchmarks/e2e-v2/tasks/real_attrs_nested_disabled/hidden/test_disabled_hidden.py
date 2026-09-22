from attr import disabled, get_run_validators, set_run_validators


def test_nested_context_remains_disabled_after_inner_exit():
    with disabled():
        with disabled():
            assert get_run_validators() is False
        assert get_run_validators() is False
    assert get_run_validators() is True


def test_preexisting_disabled_state_is_restored():
    set_run_validators(False)
    try:
        with disabled():
            assert get_run_validators() is False
        assert get_run_validators() is False
    finally:
        set_run_validators(True)


def test_nested_context_restores_enabled_state_at_outer_exit():
    set_run_validators(True)
    with disabled(), disabled():
        assert get_run_validators() is False
    assert get_run_validators() is True
