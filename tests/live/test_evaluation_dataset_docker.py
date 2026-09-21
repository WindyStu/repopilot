import os
import shutil
import subprocess
from pathlib import Path

import pytest

from minisweagent.repopilot.evaluation_dataset import (
    audit_workspace,
    load_dataset,
    materialize_task,
)
from minisweagent.repopilot.verification import DockerSafetyConfig, run_hidden_verification

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="requires Docker")


def git(workspace: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True, text=True)


def snapshot(workspace: Path) -> None:
    git(workspace, "init", "--quiet")
    git(workspace, "add", "-A")
    git(
        workspace,
        "-c",
        "user.name=RepoPilot",
        "-c",
        "user.email=repopilot@localhost",
        "commit",
        "--quiet",
        "-m",
        "baseline",
    )


def test_pilot_fixtures_fail_when_buggy_and_pass_with_reference_patch(tmp_path):
    manifest = Path("benchmarks/e2e-v1/manifest.json")
    dataset = load_dataset(manifest)
    config = DockerSafetyConfig(image="repopilot-runner:py312", user=f"{os.getuid()}:{os.getgid()}")

    assert len(dataset.tasks) == 3
    for task in dataset.tasks:
        workspace = materialize_task(task, tmp_path / task.task_id / "workspace")
        snapshot(workspace)
        buggy_artifacts = tmp_path / task.task_id / "buggy-artifacts"
        fixed_artifacts = tmp_path / task.task_id / "fixed-artifacts"
        buggy_artifacts.mkdir()
        fixed_artifacts.mkdir()

        buggy = run_hidden_verification(
            workspace,
            task.hidden_tests,
            buggy_artifacts,
            task.test_command,
            config,
            timeout=60,
        )
        assert buggy.result.success is False, f"{task.task_id} unexpectedly passed before repair"
        assert buggy.counts.failed + buggy.counts.errors > 0

        git(workspace, "apply", str(task.reference_patch))
        audit = audit_workspace(workspace, task.allowed_changes)
        assert audit.valid is True, (task.task_id, audit)

        fixed = run_hidden_verification(
            workspace,
            task.hidden_tests,
            fixed_artifacts,
            task.test_command,
            config,
            timeout=60,
        )
        assert fixed.result.success is True, f"{task.task_id}: {fixed.result.output}"
        assert fixed.counts.total > 0
        assert fixed.counts.passed == fixed.counts.total
