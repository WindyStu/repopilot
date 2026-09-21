import json
import subprocess

import pytest

from minisweagent.repopilot.evaluation_dataset import (
    audit_workspace,
    load_dataset,
    materialize_task,
)


def write_dataset(root):
    task_root = root / "tasks" / "divide"
    repository = task_root / "repo"
    hidden = task_root / "hidden"
    repository.mkdir(parents=True)
    hidden.mkdir()
    (repository / "calculator.py").write_text("def divide(a, b):\n    return a // b\n")
    (hidden / "test_hidden.py").write_text("from calculator import divide\n\ndef test_fraction():\n assert divide(3, 2) == 1.5\n")
    (task_root / "reference.patch").write_text("reference patch\n")
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "dataset": "pilot-v1",
                "tasks": [
                    {
                        "task_id": "divide",
                        "issue": "divide truncates fractional results",
                        "repository": "tasks/divide/repo",
                        "hidden_tests": "tasks/divide/hidden",
                        "reference_patch": "tasks/divide/reference.patch",
                        "relevant_files": ["calculator.py"],
                        "allowed_changes": ["calculator.py"],
                        "test_command": "pytest -q /repopilot-hidden",
                    }
                ],
            }
        )
    )
    return manifest


def test_load_dataset_resolves_repository_and_hidden_tests_under_dataset_root(tmp_path):
    manifest = write_dataset(tmp_path)

    dataset = load_dataset(manifest)
    task = dataset.tasks[0]

    assert dataset.name == "pilot-v1"
    assert task.repository == (tmp_path / "tasks/divide/repo").resolve()
    assert task.hidden_tests == (tmp_path / "tasks/divide/hidden").resolve()
    assert task.reference_patch == (tmp_path / "tasks/divide/reference.patch").resolve()
    assert task.relevant_files == ("calculator.py",)
    assert task.allowed_changes == ("calculator.py",)


def test_load_dataset_rejects_paths_that_escape_dataset_root(tmp_path):
    manifest = write_dataset(tmp_path)
    data = json.loads(manifest.read_text())
    data["tasks"][0]["hidden_tests"] = "../outside"
    manifest.write_text(json.dumps(data))

    with pytest.raises(ValueError, match="outside dataset root"):
        load_dataset(manifest)


def test_materialized_workspace_never_contains_hidden_tests(tmp_path):
    dataset = load_dataset(write_dataset(tmp_path / "dataset"))
    destination = tmp_path / "run" / "workspace"

    materialize_task(dataset.tasks[0], destination)

    assert (destination / "calculator.py").is_file()
    assert not (destination / "test_hidden.py").exists()
    assert "test_fraction" not in "\n".join(path.read_text() for path in destination.rglob("*.py"))


def git(workspace, *args):
    subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True, text=True)


def snapshot(workspace):
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


def test_audit_workspace_accepts_non_empty_patch_limited_to_allowed_files(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("VALUE = 1\n")
    snapshot(workspace)
    (workspace / "calculator.py").write_text("VALUE = 2\n")
    (workspace / ".repopilot").mkdir()
    (workspace / ".repopilot/index.json").write_text("{}\n")

    audit = audit_workspace(workspace, ("calculator.py",))

    assert audit.valid is True
    assert audit.changed_paths == ("calculator.py",)
    assert audit.forbidden_paths == ()
    assert "VALUE = 2" in audit.patch
    assert ".repopilot" not in audit.patch


def test_audit_workspace_rejects_test_edits_and_untracked_files(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("VALUE = 1\n")
    (workspace / "test_calculator.py").write_text("def test_value():\n    assert True\n")
    snapshot(workspace)
    (workspace / "calculator.py").write_text("VALUE = 2\n")
    (workspace / "test_calculator.py").write_text("def test_value():\n    assert False\n")
    (workspace / "notes.txt").write_text("extra\n")

    audit = audit_workspace(workspace, ("calculator.py",))

    assert audit.valid is False
    assert audit.changed_paths == ("calculator.py", "notes.txt", "test_calculator.py")
    assert audit.forbidden_paths == ("notes.txt", "test_calculator.py")
    assert "notes.txt" in audit.patch


def test_audit_workspace_rejects_an_empty_patch(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("VALUE = 1\n")
    snapshot(workspace)

    audit = audit_workspace(workspace, ("calculator.py",))

    assert audit.valid is False
    assert audit.changed_paths == ()
    assert audit.patch == ""
