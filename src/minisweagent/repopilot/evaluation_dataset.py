"""Versioned fixture dataset definitions for controlled agent evaluation."""

from __future__ import annotations

import hashlib
import json
import re
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
    origin_type: str = "authored"
    upstream_repository: str | None = None
    upstream_revision: str | None = None
    upstream_issue: str | None = None
    license_spdx: str = "MIT"
    difficulty: str = "easy"
    category: str = "legacy"
    cross_file_reasoning: bool = False
    plausible_files: tuple[str, ...] = ()
    adaptations: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationDataset:
    name: str
    root: Path
    tasks: tuple[EvaluationTask, ...]
    schema_version: int = 1
    manifest: Path | None = None


@dataclass(frozen=True)
class WorkspaceAudit:
    valid: bool
    changed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    patch: str


_ALLOWED_LICENSES = frozenset({"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0"})
_IMMUTABLE_COMMIT = re.compile(r"[0-9a-fA-F]{40}\Z")


def _validate_v2_task(item: dict[str, object]) -> None:
    origin_type = item.get("origin_type")
    if origin_type not in {"authored", "real"}:
        raise ValueError("Task origin_type must be 'authored' or 'real'")
    license_spdx = item.get("license_spdx")
    if license_spdx not in _ALLOWED_LICENSES:
        raise ValueError(f"Unsupported task license: {license_spdx}")
    if item.get("difficulty") not in {"easy", "medium", "hard"}:
        raise ValueError("Task difficulty must be easy, medium, or hard")
    if not isinstance(item.get("category"), str) or not item["category"]:
        raise ValueError("Task category must be a non-empty string")
    plausible_files = item.get("plausible_files")
    if not isinstance(plausible_files, list) or not plausible_files:
        raise ValueError("Task plausible_files must contain at least one path")
    for path in plausible_files:
        if not isinstance(path, str):
            raise ValueError("Task plausible_files entries must be strings")
        _normalize_allowed(path)
    if not isinstance(item.get("cross_file_reasoning"), bool):
        raise ValueError("Task cross_file_reasoning must be a boolean")
    adaptations = item.get("adaptations")
    if not isinstance(adaptations, list) or not all(isinstance(value, str) for value in adaptations):
        raise ValueError("Task adaptations must be a list of strings")
    if origin_type == "real":
        repository = item.get("upstream_repository")
        issue = item.get("upstream_issue")
        revision = item.get("upstream_revision")
        if not isinstance(repository, str) or not repository.startswith("https://"):
            raise ValueError("Real task upstream_repository must be an HTTPS URL")
        if not isinstance(issue, str) or not issue.startswith("https://"):
            raise ValueError("Real task upstream_issue must be an HTTPS URL")
        if not isinstance(revision, str) or _IMMUTABLE_COMMIT.fullmatch(revision) is None:
            raise ValueError("Real task upstream_revision must be an immutable 40-character commit")


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
    schema_version = raw.get("schema_version", 1)
    if schema_version not in {1, 2}:
        raise ValueError(f"Unsupported dataset schema version: {schema_version}")
    tasks = []
    seen_ids = set()
    for item in raw.get("tasks", []):
        task_id = item["task_id"]
        if task_id in seen_ids:
            msg = f"Duplicate task ID: {task_id}"
            raise ValueError(msg)
        seen_ids.add(task_id)
        if schema_version == 2:
            _validate_v2_task(item)
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
                origin_type=item.get("origin_type", "authored"),
                upstream_repository=item.get("upstream_repository"),
                upstream_revision=item.get("upstream_revision"),
                upstream_issue=item.get("upstream_issue"),
                license_spdx=item.get("license_spdx", "MIT"),
                difficulty=item.get("difficulty", "easy"),
                category=item.get("category", "legacy"),
                cross_file_reasoning=item.get("cross_file_reasoning", False),
                plausible_files=tuple(item.get("plausible_files", ())),
                adaptations=tuple(item.get("adaptations", ())),
            )
        )
    if not tasks:
        msg = "Evaluation dataset must contain at least one task"
        raise ValueError(msg)
    return EvaluationDataset(
        name=raw["dataset"],
        root=root,
        tasks=tuple(tasks),
        schema_version=schema_version,
        manifest=manifest,
    )


def _digest_part(digest: object, label: str, content: bytes) -> None:
    label_bytes = label.encode()
    digest.update(len(label_bytes).to_bytes(8, "big"))
    digest.update(label_bytes)
    digest.update(len(content).to_bytes(8, "big"))
    digest.update(content)


def _digest_tree(digest: object, label: str, root: Path) -> None:
    excluded = {".git", ".repopilot", "__pycache__"}
    files = sorted(
        path for path in root.rglob("*") if path.is_file() and not any(part in excluded for part in path.parts)
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        _digest_part(digest, f"{label}/{relative}", path.read_bytes())


def dataset_digest(dataset: EvaluationDataset) -> str:
    """Return a deterministic SHA-256 fingerprint of all evaluation inputs."""

    digest = hashlib.sha256()
    if dataset.manifest is not None:
        raw_manifest = json.loads(dataset.manifest.read_text())
        canonical_manifest = json.dumps(raw_manifest, sort_keys=True, separators=(",", ":")).encode()
    else:
        canonical_manifest = json.dumps(
            {"dataset": dataset.name, "schema_version": dataset.schema_version},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    _digest_part(digest, "manifest.json", canonical_manifest)
    for task in sorted(dataset.tasks, key=lambda value: value.task_id):
        _digest_tree(digest, f"{task.task_id}/repository", task.repository)
        _digest_tree(digest, f"{task.task_id}/hidden_tests", task.hidden_tests)
        _digest_part(digest, f"{task.task_id}/reference.patch", task.reference_patch.read_bytes())
    return digest.hexdigest()


def task_digest(task: EvaluationTask) -> str:
    """Return a deterministic SHA-256 fingerprint for one task."""

    digest = hashlib.sha256()
    metadata = {
        "task_id": task.task_id,
        "issue": task.issue,
        "relevant_files": task.relevant_files,
        "allowed_changes": task.allowed_changes,
        "test_command": task.test_command,
        "origin_type": task.origin_type,
        "upstream_repository": task.upstream_repository,
        "upstream_revision": task.upstream_revision,
        "upstream_issue": task.upstream_issue,
        "license_spdx": task.license_spdx,
        "difficulty": task.difficulty,
        "category": task.category,
        "cross_file_reasoning": task.cross_file_reasoning,
        "plausible_files": task.plausible_files,
        "adaptations": task.adaptations,
    }
    _digest_part(
        digest,
        "task.json",
        json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode(),
    )
    _digest_tree(digest, "repository", task.repository)
    _digest_tree(digest, "hidden_tests", task.hidden_tests)
    _digest_part(digest, "reference.patch", task.reference_patch.read_bytes())
    return digest.hexdigest()


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
