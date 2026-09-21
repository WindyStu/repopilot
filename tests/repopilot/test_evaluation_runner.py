import json
from decimal import Decimal
from pathlib import Path

from minisweagent.repopilot.deepseek_provider import BudgetGuard
from minisweagent.repopilot.evaluation_dataset import EvaluationDataset, EvaluationTask, WorkspaceAudit
from minisweagent.repopilot.evaluation_runner import (
    classify_session,
    run_evaluation_session,
    run_paired_evaluation,
    variant_order,
)
from minisweagent.repopilot.verification import (
    HiddenVerificationOutcome,
    JUnitCounts,
    VerificationResult,
)


def hidden(success=True):
    result = VerificationResult.passed("ok") if success else VerificationResult.failed("failed")
    return HiddenVerificationOutcome(
        result=result,
        counts=JUnitCounts(total=2, passed=2 if success else 1, failed=0 if success else 1, errors=0, skipped=0),
    )


def audit(*, valid=True, changed=("source.py",), forbidden=()):
    return WorkspaceAudit(valid=valid, changed_paths=changed, forbidden_paths=forbidden, patch="diff" if changed else "")


def test_pair_order_alternates_to_reduce_provider_time_bias():
    assert variant_order(0) == ("baseline", "enhanced")
    assert variant_order(1) == ("enhanced", "baseline")
    assert variant_order(2) == ("baseline", "enhanced")


def test_strict_success_requires_submission_allowed_patch_tests_and_qwen():
    classification = classify_session(
        variant="enhanced",
        exit_status="Submitted",
        workspace_audit=audit(),
        hidden_outcome=hidden(),
        analysis_sources=("local_model",),
    )

    assert classification.success is True
    assert classification.failure_class == ""


def test_forbidden_modification_fails_even_when_hidden_tests_pass():
    classification = classify_session(
        variant="baseline",
        exit_status="Submitted",
        workspace_audit=audit(valid=False, forbidden=("tests/test_source.py",)),
        hidden_outcome=hidden(),
        analysis_sources=(),
    )

    assert classification.success is False
    assert classification.failure_class == "forbidden_modification"


def test_enhanced_qwen_fallback_is_retained_but_ineligible():
    classification = classify_session(
        variant="enhanced",
        exit_status="Submitted",
        workspace_audit=audit(),
        hidden_outcome=hidden(),
        analysis_sources=("fallback",),
    )

    assert classification.success is False
    assert classification.failure_class == "qwen_fallback"


def test_failure_precedence_distinguishes_infrastructure_empty_patch_exit_and_tests():
    assert classify_session(
        variant="baseline",
        exit_status="Submitted",
        workspace_audit=audit(),
        hidden_outcome=hidden(),
        analysis_sources=(),
        infrastructure_error="docker unavailable",
    ).failure_class == "infrastructure_failure"
    assert classify_session(
        variant="baseline",
        exit_status="Submitted",
        workspace_audit=audit(valid=False, changed=()),
        hidden_outcome=hidden(),
        analysis_sources=(),
    ).failure_class == "empty_patch"
    assert classify_session(
        variant="baseline",
        exit_status="LimitsExceeded",
        workspace_audit=audit(),
        hidden_outcome=hidden(),
        analysis_sources=(),
    ).failure_class == "step_limit"
    assert classify_session(
        variant="baseline",
        exit_status="Submitted",
        workspace_audit=audit(),
        hidden_outcome=hidden(False),
        analysis_sources=(),
    ).failure_class == "tests_failed"


def test_session_materializes_runs_verifies_audits_and_records_metrics(tmp_path, monkeypatch):
    repository = tmp_path / "fixture" / "repo"
    hidden_tests = tmp_path / "fixture" / "hidden"
    repository.mkdir(parents=True)
    hidden_tests.mkdir()
    (repository / "source.py").write_text("VALUE = 1\n")
    reference_patch = tmp_path / "fixture" / "reference.patch"
    reference_patch.write_text("unused\n")
    task = EvaluationTask(
        task_id="one",
        issue="Change VALUE to 2",
        repository=repository,
        hidden_tests=hidden_tests,
        reference_patch=reference_patch,
        relevant_files=("source.py",),
        allowed_changes=("source.py",),
        test_command="pytest -q /repopilot-hidden",
    )

    class FakeEnvironment:
        def __init__(self, **kwargs):
            self.cleaned = False

        def cleanup(self):
            self.cleaned = True

    class FakeAgent:
        def __init__(self, **kwargs):
            self.workspace = Path(kwargs["repository_path"])
            self.output_path = Path(kwargs["output_path"])
            self.retrieval_enabled = kwargs["retrieval_enabled"]
            assert kwargs["local_model_timeout"] == 30

        def run(self, prompt):
            (self.workspace / "source.py").write_text("VALUE = 2\n")
            self.output_path.write_text(
                json.dumps(
                    {
                        "info": {
                            "model_stats": {"api_calls": 2},
                            "repopilot": {
                                "analysis_source": "local_model",
                                "retrieved_files": [{"path": "source.py"}],
                            },
                        },
                        "messages": [
                            {
                                "role": "assistant",
                                "extra": {
                                    "response": {
                                        "usage": {"prompt_tokens": 40, "completion_tokens": 10}
                                    }
                                },
                            }
                        ],
                    }
                )
            )
            return {"exit_status": "Submitted", "submission": "done"}

    monkeypatch.setattr("minisweagent.repopilot.evaluation_runner.DockerEnvironment", FakeEnvironment)
    monkeypatch.setattr("minisweagent.repopilot.evaluation_runner.RepoPilotAgent", FakeAgent)
    monkeypatch.setattr(
        "minisweagent.repopilot.evaluation_runner.run_hidden_verification",
        lambda *args, **kwargs: hidden(True),
    )

    report = run_evaluation_session(
        task,
        "enhanced",
        tmp_path / "runs" / "one-enhanced",
        model=object(),
        image="runner:test",
        uid=1000,
        gid=1000,
    )

    assert report["success"] is True
    assert report["failure_class"] == ""
    assert report["strong_model_calls"] == 2
    assert report["input_tokens"] == 40
    assert report["retrieval_recall_at_5"] == 1.0
    assert report["changed_paths"] == ["source.py"]
    assert (tmp_path / "runs/one-enhanced/solution.patch").is_file()
    assert (tmp_path / "runs/one-enhanced/session.json").is_file()


def test_paired_scheduler_alternates_order_checks_balance_after_complete_pairs_and_persists_state(tmp_path):
    fixture = tmp_path / "fixture"
    repository = fixture / "repo"
    hidden_tests = fixture / "hidden"
    repository.mkdir(parents=True)
    hidden_tests.mkdir()
    reference_patch = fixture / "reference.patch"
    reference_patch.write_text("unused\n")
    tasks = tuple(
        EvaluationTask(
            task_id=f"task-{number}",
            issue="fix it",
            repository=repository,
            hidden_tests=hidden_tests,
            reference_patch=reference_patch,
            relevant_files=("source.py",),
            allowed_changes=("source.py",),
            test_command="pytest -q /repopilot-hidden",
        )
        for number in range(3)
    )
    dataset = EvaluationDataset(name="test-v1", root=fixture, tasks=tasks)
    balances = iter((Decimal("9.00"), Decimal("8.80"), Decimal("8.50"), Decimal("8.20")))
    calls = []

    def fake_session(task, variant, session_dir, **kwargs):
        session_dir.mkdir(parents=True)
        calls.append((task.task_id, variant))
        return {
            "task_id": task.task_id,
            "variant": variant,
            "success": True,
            "input_tokens": 10,
            "strong_model_calls": 1,
            "active_wall_seconds": 0.1,
            "hidden_test_counts": {"total": 1, "passed": 1, "failed": 0, "errors": 0, "skipped": 0},
            "retrieval_recall_at_5": 1.0 if variant == "enhanced" else None,
        }

    report = run_paired_evaluation(
        dataset,
        tmp_path / "experiment",
        model_factory=object,
        balance_fetcher=lambda: next(balances),
        budget=BudgetGuard(
            starting_balance=Decimal("9.00"),
            max_spend=Decimal("7.00"),
            reserve=Decimal("2.00"),
        ),
        session_runner=fake_session,
        estimated_pair_cost=Decimal("1.00"),
        image="runner:test",
        uid=1000,
        gid=1000,
    )

    assert calls == [
        ("task-0", "baseline"),
        ("task-0", "enhanced"),
        ("task-1", "enhanced"),
        ("task-1", "baseline"),
        ("task-2", "baseline"),
        ("task-2", "enhanced"),
    ]
    assert report["completed_pairs"] == 3
    assert report["starting_balance_cny"] == "9.00"
    assert report["ending_balance_cny"] == "8.20"
    assert (tmp_path / "experiment/run-state.json").is_file()
    assert len((tmp_path / "experiment/sessions.jsonl").read_text().splitlines()) == 6
