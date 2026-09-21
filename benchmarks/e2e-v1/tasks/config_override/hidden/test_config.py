from app.config import build_config
from app.defaults import DEFAULTS


def test_overrides_win_over_defaults():
    assert build_config({"port": 9000, "debug": True}) == {
        "host": "127.0.0.1",
        "port": 9000,
        "debug": True,
    }


def test_inputs_and_defaults_are_not_mutated():
    overrides = {"host": "example.test"}
    original_defaults = DEFAULTS.copy()
    result = build_config(overrides)
    result["port"] = 1234

    assert overrides == {"host": "example.test"}
    assert DEFAULTS == original_defaults


def test_empty_override_mapping_is_supported():
    assert build_config({}) == DEFAULTS
    assert build_config({}) is not DEFAULTS
