from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

from minisweagent.repopilot.verification import (
    DockerSafetyConfig,
    bound_output,
    build_docker_command,
    run_docker_verification,
)


def test_safe_docker_command_is_non_root_bounded_offline_and_mounts_only_workspace(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    config = DockerSafetyConfig(image="python:3.12-slim", memory="1g", cpus=1.0, pids_limit=128)

    command = build_docker_command(workspace, "pytest -q", config)
    joined = " ".join(command)

    assert command[:3] == ["docker", "run", "--rm"]
    assert "--network none" in joined
    assert "--user 65532:65532" in joined
    assert "--memory 1g" in joined
    assert "--cpus 1.0" in joined
    assert "--pids-limit 128" in joined
    assert f"{workspace.resolve()}:/workspace" in joined
    assert str(Path.home()) not in joined
    assert "GEMINI_API_KEY" not in joined
    assert command[-3:] == ["bash", "-lc", "pytest -q"]


def test_output_bounding_preserves_head_tail_and_marks_omission():
    output = "HEAD\n" + ("x" * 200) + "\nTAIL"

    bounded = bound_output(output, limit=60)

    assert bounded.startswith("HEAD")
    assert bounded.endswith("TAIL")
    assert "omitted" in bounded
    assert len(bounded) <= 100


def test_docker_verifier_returns_structured_success_without_shell_or_forwarded_env(tmp_path, monkeypatch):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return CompletedProcess(command, 0, stdout="3 passed\n", stderr="")

    monkeypatch.setattr("minisweagent.repopilot.verification.subprocess.run", fake_run)

    result = run_docker_verification(
        workspace,
        "pytest -q",
        DockerSafetyConfig(image="python:3.12-slim"),
        timeout=45,
    )

    assert result.success is True
    assert result.command == "pytest -q"
    assert result.output == "3 passed\n"
    assert observed["kwargs"]["shell"] is False
    assert observed["kwargs"]["timeout"] == 45
    assert "env" not in observed["kwargs"]


def test_docker_verifier_maps_timeout_to_bounded_failure(tmp_path, monkeypatch):
    workspace = tmp_path / "repo"
    workspace.mkdir()

    def time_out(command, **kwargs):
        raise TimeoutExpired(command, kwargs["timeout"], output="partial output")

    monkeypatch.setattr("minisweagent.repopilot.verification.subprocess.run", time_out)

    result = run_docker_verification(
        workspace,
        "pytest -q",
        DockerSafetyConfig(image="python:3.12-slim"),
        timeout=1,
    )

    assert result.success is False
    assert "timed out after 1s" in result.output
    assert "partial output" in result.output
