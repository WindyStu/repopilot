import os
import subprocess
import sys
from pathlib import Path

import pytest

from minisweagent.repopilot.evaluation_dataset import load_dataset, materialize_task

AUTHORED_TASK_IDS = {
    "authored_async_retry",
    "authored_cache_invalidation",
    "authored_state_rollback",
    "authored_versioned_json",
    "authored_safe_archive",
}

REAL_TASK_IDS = {
    "real_attrs_deep_mapping",
    "real_attrs_frozen_error",
    "real_attrs_nested_disabled",
    "real_click_choice_metavar",
    "real_click_color_zero",
    "real_click_empty_usage",
    "real_click_parameter_source",
    "real_click_short_help",
    "real_mi_constrained_batches",
    "real_mi_interleave_empty",
    "real_mi_negative_slice",
    "real_mi_one_falsy",
    "real_mi_reverse_empty",
    "real_mi_running_extrema",
    "real_mi_seekable_zero",
}


def test_v2_manifest_contains_five_complete_authored_tasks():
    dataset = load_dataset(Path("benchmarks/e2e-v2/manifest.json"))
    authored = [task for task in dataset.tasks if task.origin_type == "authored"]

    assert dataset.schema_version == 2
    assert {task.task_id for task in authored} == AUTHORED_TASK_IDS
    assert all(task.cross_file_reasoning for task in authored)
    assert all(len(task.relevant_files) >= 2 for task in authored)
    assert all(len(task.plausible_files) >= 3 for task in authored)
    assert all(len(list(task.hidden_tests.glob("test_*.py"))) >= 1 for task in authored)


def test_v2_manifest_has_exact_mixed_distribution_and_traceable_real_sources():
    dataset = load_dataset(Path("benchmarks/e2e-v2/manifest.json"))
    real = [task for task in dataset.tasks if task.origin_type == "real"]

    assert len(dataset.tasks) == 20
    assert {task.task_id for task in real} == REAL_TASK_IDS
    assert {level: sum(task.difficulty == level for task in dataset.tasks) for level in ("easy", "medium", "hard")} == {
        "easy": 5,
        "medium": 10,
        "hard": 5,
    }
    assert sum(task.cross_file_reasoning for task in dataset.tasks) >= 12
    assert sum(len(task.plausible_files) >= 3 for task in dataset.tasks) >= 8
    assert all(task.upstream_repository.startswith("https://github.com/") for task in real)
    assert all(len(task.upstream_revision) == 40 for task in real)
    assert all("/commit/" in task.upstream_issue for task in real)


@pytest.mark.parametrize("task_id", sorted(AUTHORED_TASK_IDS))
def test_authored_task_bug_reproduces_and_reference_patch_passes(task_id, tmp_path):
    dataset = load_dataset(Path("benchmarks/e2e-v2/manifest.json"))
    task = next(task for task in dataset.tasks if task.task_id == task_id)
    workspace = materialize_task(task, tmp_path / task_id)
    environment = {**os.environ, "PYTHONPATH": str(workspace)}
    command = [sys.executable, "-m", "pytest", "-q", str(task.hidden_tests)]

    buggy = subprocess.run(command, cwd=workspace, env=environment, capture_output=True, text=True, check=False)
    assert buggy.returncode != 0

    applied = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", str(task.reference_patch)],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert applied.returncode == 0, applied.stderr
    fixed = subprocess.run(command, cwd=workspace, env=environment, capture_output=True, text=True, check=False)
    assert fixed.returncode == 0, fixed.stdout + fixed.stderr


@pytest.mark.parametrize("task_id", sorted(REAL_TASK_IDS))
def test_real_task_bug_reproduces_and_reference_patch_passes(task_id, tmp_path):
    dataset = load_dataset(Path("benchmarks/e2e-v2/manifest.json"))
    task = next(task for task in dataset.tasks if task.task_id == task_id)
    workspace = materialize_task(task, tmp_path / task_id)
    environment = {**os.environ, "PYTHONPATH": str(workspace)}
    command = [sys.executable, "-m", "pytest", "-q", str(task.hidden_tests)]

    buggy = subprocess.run(command, cwd=workspace, env=environment, capture_output=True, text=True, check=False)
    assert buggy.returncode != 0, f"{task_id} unexpectedly passed in buggy state"

    applied = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", str(task.reference_patch)],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert applied.returncode == 0, f"{task_id}: {applied.stderr}"
    fixed = subprocess.run(command, cwd=workspace, env=environment, capture_output=True, text=True, check=False)
    assert fixed.returncode == 0, f"{task_id}:\n{fixed.stdout}{fixed.stderr}"
