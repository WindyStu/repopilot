import os

import pytest

from minisweagent.repopilot.deepseek_provider import build_deepseek_model, fetch_cny_balance

pytestmark = pytest.mark.skipif(not os.getenv("DEEPSEEK_API_KEY"), reason="requires DEEPSEEK_API_KEY")


def test_deepseek_balance_is_available():
    assert fetch_cny_balance() > 0


def test_deepseek_flash_returns_bash_tool_call_with_usage():
    model = build_deepseek_model()

    response = model.query(
        [
            {"role": "system", "content": "Use the bash tool exactly once and do not explain."},
            {"role": "user", "content": "Run printf repopilot-deepseek-check"},
        ]
    )

    actions = response["extra"]["actions"]
    usage = response["extra"]["response"]["usage"]
    assert len(actions) == 1
    assert "printf" in actions[0]["command"]
    assert usage["prompt_tokens"] > 0
