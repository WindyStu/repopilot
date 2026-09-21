import os

import pytest

from minisweagent.repopilot.strong_model import build_gemini_model

pytestmark = pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="requires a rotated GEMINI_API_KEY")


def test_gemini_flash_returns_a_bash_tool_call():
    model = build_gemini_model()

    response = model.query(
        [
            {"role": "system", "content": "Use the bash tool exactly once and do not explain."},
            {"role": "user", "content": "Run printf repopilot-live-check"},
        ]
    )

    actions = response["extra"]["actions"]
    assert len(actions) == 1
    assert "printf" in actions[0]["command"]
