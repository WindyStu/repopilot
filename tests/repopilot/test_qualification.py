from pathlib import Path

import pytest

from minisweagent.repopilot.evaluation_dataset import EvaluationDataset, EvaluationTask
from minisweagent.repopilot.qualification import (
    TaskQualification,
    qualify_and_freeze,
    qualify_task,
)
from minisweagent.repopilot.verification import (
    DockerSafetyConfig,
    HiddenVerificationOutcome,
    JUnitCounts,
    VerificationResult,
)


def make_task(tmp_path: Path) -> EvaluationTask:
    repository = tmp_path / "repo"
    hidden = tmp_path / "hidden"
    repository.mkdir(parents=True)
    hidden.mkdir()
    (repository / "calculator.py").write_text("def divide(a, b):\n    return a // b\n")
    (hidden / "test_hidden.py").write_text("hidden test placeholder\n")
    patch = tmp_path / "reference.patch"
    patch.write_text(
        """diff --git a/calculator.py b/calculator.py
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def divide(a, b):
-    return a // b
+    return a / b
"""
    )
    return EvaluationTask(
        task_id="divide",
        issue="division truncates fractions",
        repository=repository,
        hidden_tests=hidden,
        reference_patch=patch,
        relevant_files=("calculator.py",),
        allowed_changes=("calculator.py",),
        test_command="pytest -q /repopilot-hidden",
    )


def outcome(*, success: bool, passed: int, failed: int) -> HiddenVerificationOutcome:
    result = VerificationResult.passed("ok") if success else VerificationResult.failed("failed")
    return HiddenVerificationOutcome(
        result=result,
        counts=JUnitCounts(total=passed + failed, passed=passed, failed=failed, errors=0, skipped=0),
    )


def test_qualify_task_requires_repeatable_buggy_failure_and_fixed_success(tmp_path):
    task = make_task(tmp_path / "fixture")
    calls = []

    def verifier(workspace, hidden_tests, artifacts, test_command, config):
        calls.append((workspace, hidden_tests, artifacts, test_command, config))
        fixed = "return a / b" in (workspace / "calculator.py").read_text()
        return outcome(success=fixed, passed=3 if fixed else 1, failed=0 if fixed else 2)

    result = qualify_task(
        task,
        tmp_path / "qualification",
        DockerSafetyConfig(image="test-image"),
        verifier=verifier,
    )

    assert result.qualified is True
    assert result.reasons == ()
    assert len(result.buggy_runs) == 2
    assert len(result.fixed_runs) == 2
    assert result.changed_paths == ("calculator.py",)
    assert len(calls) == 4


def test_qualify_task_rejects_inconsistent_buggy_results(tmp_path):
    task = make_task(tmp_path / "fixture")
    run_number = 0

    def verifier(workspace, hidden_tests, artifacts, test_command, config):
        nonlocal run_number
        run_number += 1
        fixed = "return a / b" in (workspace / "calculator.py").read_text()
        if fixed:
            return outcome(success=True, passed=3, failed=0)
        return outcome(success=False, passed=run_number, failed=3 - run_number)

    result = qualify_task(
        task,
        tmp_path / "qualification",
        DockerSafetyConfig(image="test-image"),
        verifier=verifier,
    )

    assert result.qualified is False
    assert "buggy results are inconsistent" in result.reasons


def test_freeze_gate_leaves_no_dataset_artifacts_when_any_task_fails(tmp_path):
    task = make_task(tmp_path / "fixture")
    dataset = EvaluationDataset(name="test-v2", root=tmp_path, tasks=(task,), schema_version=2)
    failed = TaskQualification(
        task_id="divide",
        qualified=False,
        reasons=("buggy workspace unexpectedly passed",),
        task_sha256="a" * 64,
        buggy_runs=(),
        fixed_runs=(),
        changed_paths=(),
        forbidden_paths=(),
    )
    output = tmp_path / "frozen"

    with pytest.raises(RuntimeError, match="divide"):
        qualify_and_freeze(
            dataset,
            output,
            DockerSafetyConfig(image="test-image"),
            task_qualifier=lambda *_args, **_kwargs: failed,
        )

    assert not output.exists()
