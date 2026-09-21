"""Versioned fixture dataset definitions for controlled agent evaluation."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class EvaluationTask:
    task_id: str
    issue: str
    repository: Path
    hidden_tests: Path
    reference_patch: Path
    relevant_files: tuple[str, ...]
    allowed_changes: tuple[str, ...]
    test_command: str


@dataclass(frozen=True)
class EvaluationDataset:
    name: str
    root: Path
    tasks: tuple[EvaluationTask, ...]


@dataclass(frozen=True)
class WorkspaceAudit:
    valid: bool
    changed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    patch: str


def _resolve_inside(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        msg = f"Dataset path is outside dataset root: {value}"
        raise ValueError(msg)
    if not path.is_dir():
        msg = f"Dataset directory does not exist: {value}"
        raise ValueError(msg)
    return path


def _resolve_file_inside(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        msg = f"Dataset path is outside dataset root: {value}"
        raise ValueError(msg)
    if not path.is_file():
        msg = f"Dataset file does not exist: {value}"
        raise ValueError(msg)
    return path


def load_dataset(manifest: Path) -> EvaluationDataset:
    """Load a dataset manifest while rejecting missing or escaping paths."""

    manifest = manifest.resolve(strict=True)
    root = manifest.parent
    raw = json.loads(manifest.read_text())
    tasks = []
    seen_ids = set()
    for item in raw.get("tasks", []):
        task_id = item["task_id"]
        if task_id in seen_ids:
            msg = f"Duplicate task ID: {task_id}"
            raise ValueError(msg)
        seen_ids.add(task_id)
        tasks.append(
            EvaluationTask(
                task_id=task_id,
                issue=item["issue"],
                repository=_resolve_inside(root, item["repository"]),
                hidden_tests=_resolve_inside(root, item["hidden_tests"]),
                reference_patch=_resolve_file_inside(root, item["reference_patch"]),
                relevant_files=tuple(item["relevant_files"]),
                allowed_changes=tuple(item["allowed_changes"]),
                test_command=item["test_command"],
            )
        )
    if not tasks:
        msg = "Evaluation dataset must contain at least one task"
        raise ValueError(msg)
    return EvaluationDataset(name=raw["dataset"], root=root, tasks=tuple(tasks))


def materialize_task(task: EvaluationTask, destination: Path) -> Path:
    """Copy only the visible repository template into a fresh workspace."""

    destination = destination.resolve()
    if destination.exists():
        msg = f"Task workspace already exists: {destination}"
        raise FileExistsError(msg)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.repository, destination, ignore=shutil.ignore_patterns(".git", ".env", ".env.*", "__pycache__"))
    return destination


def _git(workspace: Path, *args: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=not binary,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        stderr = completed.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        msg = stderr.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(msg)
    return completed.stdout


def _split_nul_paths(raw: bytes) -> tuple[str, ...]:
    return tuple(part.decode("utf-8", errors="surrogateescape") for part in raw.split(b"\0") if part)


def _normalize_allowed(path: str) -> str:
    normalized = PurePosixPath(path.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        msg = f"Allowed change must be a repository-relative path: {path}"
        raise ValueError(msg)
    return normalized.as_posix()


def audit_workspace(workspace: Path, allowed_changes: tuple[str, ...]) -> WorkspaceAudit:
    """Capture all Git changes and reject empty or out-of-scope patches."""

    workspace = workspace.resolve(strict=True)
    allowed = {_normalize_allowed(path) for path in allowed_changes}
    tracked_raw = _git(workspace, "diff", "--name-only", "-z", "HEAD", "--", binary=True)
    untracked_raw = _git(
        workspace,
        "ls-files",
        "-z",
        "--others",
        "--exclude-standard",
        "--",
        binary=True,
    )
    assert isinstance(tracked_raw, bytes)
    assert isinstance(untracked_raw, bytes)
    def is_system_cache(path: str) -> bool:
        return path == ".repopilot" or path.startswith(".repopilot/")

    tracked = tuple(path for path in _split_nul_paths(tracked_raw) if not is_system_cache(path))
    untracked = tuple(path for path in _split_nul_paths(untracked_raw) if not is_system_cache(path))
    if untracked:
        _git(workspace, "add", "-N", "--", *untracked)
    changed = tuple(sorted(set(tracked) | set(untracked)))
    patch = _git(workspace, "diff", "--binary", "--no-ext-diff", "HEAD", "--")
    assert isinstance(patch, str)
    forbidden = tuple(path for path in changed if path not in allowed)
    return WorkspaceAudit(
        valid=bool(changed) and not forbidden,
        changed_paths=changed,
        forbidden_paths=forbidden,
        patch=patch,
    )
