import os
import shutil

import pytest

from minisweagent.repopilot.verification import DockerSafetyConfig, run_docker_verification

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="requires Docker")


def test_real_container_runs_tests_without_gemini_credential(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "test_sample.py").write_text("def test_ok():\n    assert 2 + 2 == 4\n")
    config = DockerSafetyConfig(image="repopilot-runner:py312", user=f"{os.getuid()}:{os.getgid()}")

    result = run_docker_verification(
        workspace,
        "test -z \"${GEMINI_API_KEY:-}\" && pytest -q",
        config,
        timeout=60,
    )

    assert result.success is True, result.output
    assert "1 passed" in result.output
