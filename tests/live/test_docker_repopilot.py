import os
import shutil

import pytest

from minisweagent.repopilot.verification import (
    DockerSafetyConfig,
    run_docker_verification,
    run_hidden_verification,
)

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


def test_real_container_runs_read_only_hidden_tests_and_writes_junit(tmp_path):
    workspace = tmp_path / "repo"
    hidden = tmp_path / "hidden"
    artifacts = tmp_path / "artifacts"
    workspace.mkdir()
    hidden.mkdir()
    artifacts.mkdir()
    (workspace / "calculator.py").write_text("def add(left, right):\n    return left + right\n")
    (hidden / "test_calculator.py").write_text(
        "import os\n"
        "from calculator import add\n\n"
        "def test_hidden_addition_without_credentials():\n"
        "    assert add(2, 3) == 5\n"
        "    assert os.getenv('GEMINI_API_KEY') is None\n"
        "    assert os.getenv('DEEPSEEK_API_KEY') is None\n"
    )
    config = DockerSafetyConfig(image="repopilot-runner:py312", user=f"{os.getuid()}:{os.getgid()}")

    outcome = run_hidden_verification(
        workspace,
        hidden,
        artifacts,
        "pytest -q /repopilot-hidden",
        config,
        timeout=60,
    )

    assert outcome.result.success is True, outcome.result.output
    assert outcome.counts.total == 1
    assert outcome.counts.passed == 1
    assert (artifacts / "junit.xml").is_file()
