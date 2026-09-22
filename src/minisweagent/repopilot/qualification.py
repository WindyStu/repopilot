"""Deterministic Docker qualification and atomic dataset freezing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from minisweagent.repopilot.evaluation_dataset import (
    EvaluationDataset,
    EvaluationTask,
    audit_workspace,
    dataset_digest,
    materialize_task,
    task_digest,
)
from minisweagent.repopilot.verification import (
    DockerSafetyConfig,
    HiddenVerificationOutcome,
    JUnitCounts,
    run_hidden_verification,
)


@dataclass(frozen=True)
class TaskQualification:
    task_id: str
    qualified: bool
    reasons: tuple[str, ...]
    task_sha256: str
    buggy_runs: tuple[JUnitCounts, ...]
    fixed_runs: tuple[JUnitCounts, ...]
    changed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]


def _git(workspace: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(message)


def _snapshot(workspace: Path) -> None:
    _git(workspace, "init", "--quiet")
    _git(workspace, "add", "-A")
    _git(
        workspace,
        "-c",
        "user.name=RepoPilot",
        "-c",
        "user.email=repopilot@localhost",
        "commit",
        "--quiet",
        "-m",
        "buggy baseline",
    )


def _repeat_verification(
    task: EvaluationTask,
    workspace: Path,
    root: Path,
    phase: str,
    config: DockerSafetyConfig,
    verifier: Callable[..., HiddenVerificationOutcome],
) -> tuple[HiddenVerificationOutcome, ...]:
    outcomes = []
    for run_number in range(1, 3):
        artifacts = root / f"{phase}-{run_number}"
        artifacts.mkdir(parents=True)
        outcomes.append(
            verifier(
                workspace,
                task.hidden_tests,
                artifacts,
                task.test_command,
                config,
            )
        )
    return tuple(outcomes)


def _consistent(outcomes: tuple[HiddenVerificationOutcome, ...]) -> bool:
    signatures = {(outcome.result.success, outcome.counts) for outcome in outcomes}
    return len(signatures) == 1


def qualify_task(
    task: EvaluationTask,
    output_dir: Path,
    config: DockerSafetyConfig,
    *,
    verifier: Callable[..., HiddenVerificationOutcome] = run_hidden_verification,
) -> TaskQualification:
    """Qualify one task using two buggy and two reference-fixed Docker runs."""

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    workspace = materialize_task(task, output_dir / "workspace")
    _snapshot(workspace)
    buggy = _repeat_verification(task, workspace, output_dir, "buggy", config, verifier)
    reasons = []
    if not _consistent(buggy):
        reasons.append("buggy results are inconsistent")
    if any(outcome.result.success for outcome in buggy):
        reasons.append("buggy workspace unexpectedly passed")
    if any(
        outcome.counts.total == 0 or outcome.counts.failed + outcome.counts.errors == 0
        for outcome in buggy
    ):
        reasons.append("buggy runs lack a reproducible failing test")

    fixed: tuple[HiddenVerificationOutcome, ...] = ()
    patch_error = ""
    try:
        _git(workspace, "apply", "--whitespace=nowarn", str(task.reference_patch))
    except RuntimeError as error:
        patch_error = str(error)
        reasons.append("reference patch could not be applied")

    audit = audit_workspace(workspace, task.allowed_changes)
    if not audit.changed_paths:
        reasons.append("reference patch is empty")
    if audit.forbidden_paths:
        reasons.append("reference patch changes forbidden paths")
    if not patch_error:
        fixed = _repeat_verification(task, workspace, output_dir, "fixed", config, verifier)
        if not _consistent(fixed):
            reasons.append("fixed results are inconsistent")
        if any(
            not outcome.result.success
            or outcome.counts.total == 0
            or outcome.counts.passed != outcome.counts.total
            for outcome in fixed
        ):
            reasons.append("reference-fixed workspace did not pass every test")

    return TaskQualification(
        task_id=task.task_id,
        qualified=not reasons,
        reasons=tuple(reasons),
        task_sha256=task_digest(task),
        buggy_runs=tuple(outcome.counts for outcome in buggy),
        fixed_runs=tuple(outcome.counts for outcome in fixed),
        changed_paths=audit.changed_paths,
        forbidden_paths=audit.forbidden_paths,
    )


def _qualification_payload(dataset: EvaluationDataset, results: tuple[TaskQualification, ...]) -> dict[str, Any]:
    return {
        "dataset": dataset.name,
        "schema_version": dataset.schema_version,
        "qualified": all(result.qualified for result in results),
        "task_count": len(results),
        "tasks": [asdict(result) for result in results],
    }


def qualify_and_freeze(
    dataset: EvaluationDataset,
    output_dir: Path,
    config: DockerSafetyConfig,
    *,
    task_qualifier: Callable[..., TaskQualification] = qualify_task,
) -> dict[str, Any]:
    """Write qualification and lock files atomically only when every task qualifies."""

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Freeze directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent))
    try:
        results = tuple(
            task_qualifier(task, temporary / "tasks" / task.task_id, config)
            for task in dataset.tasks
        )
        failed = [result.task_id for result in results if not result.qualified]
        if failed:
            raise RuntimeError(f"Dataset qualification failed for: {', '.join(failed)}")
        shutil.rmtree(temporary / "tasks")
        payload = _qualification_payload(dataset, results)
        lock = {
            "dataset": dataset.name,
            "schema_version": dataset.schema_version,
            "dataset_sha256": dataset_digest(dataset),
            "task_sha256": {result.task_id: result.task_sha256 for result in results},
        }
        (temporary / "qualification.json").write_text(json.dumps(payload, indent=2) + "\n")
        (temporary / "dataset-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
        os.replace(temporary, output_dir)
        return payload
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
