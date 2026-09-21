import pytest

from minisweagent.repopilot.strong_model import MissingProviderCredential, build_gemini_model


def test_build_gemini_model_fails_before_agent_run_when_key_is_missing():
    with pytest.raises(MissingProviderCredential, match="GEMINI_API_KEY"):
        build_gemini_model({})


def test_build_gemini_model_uses_stable_flash_endpoint_without_serializing_key():
    model = build_gemini_model({"GEMINI_API_KEY": "test-only-key"})

    assert model.config.model_name == "gemini/gemini-3.8-flash"
    assert model.config.cost_tracking == "ignore_errors"
    assert "test-only-key" not in str(model.serialize())
    assert "api_key" not in model.config.model_kwargs
    assert model.config.model_kwargs["timeout"] == 60
    assert model.config.model_kwargs["num_retries"] == 2
