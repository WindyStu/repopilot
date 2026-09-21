"""Controlled paired evaluation runner for RepoPilot."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from minisweagent.environments.docker import DockerEnvironment
from minisweagent.repopilot.agent import RepoPilotAgent
from minisweagent.repopilot.deepseek_provider import BudgetGuard
from minisweagent.repopilot.evaluation_dataset import (
    EvaluationDataset,
    EvaluationTask,
    WorkspaceAudit,
    audit_workspace,
    materialize_task,
)
from minisweagent.repopilot.evaluation_metrics import extract_trajectory_metrics, recall_at_k
from minisweagent.repopilot.evaluation_report import build_aggregate, render_markdown
from minisweagent.repopilot.verification import (
    DockerSafetyConfig,
    HiddenVerificationOutcome,
    JUnitCounts,
    VerificationResult,
    bound_output,
    run_hidden_verification,
)


@dataclass(frozen=True)
class SessionClassification:
    success: bool
    failure_class: str


def variant_order(task_index: int) -> tuple[str, str]:
    """Alternate pair order to reduce provider-time bias."""

    if task_index < 0:
        msg = "Task index cannot be negative"
        raise ValueError(msg)
    return ("baseline", "enhanced") if task_index % 2 == 0 else ("enhanced", "baseline")


def classify_session(
    *,
    variant: str,
    exit_status: str,
    workspace_audit: WorkspaceAudit,
    hidden_outcome: HiddenVerificationOutcome,
    analysis_sources: tuple[str, ...],
    infrastructure_error: str = "",
) -> SessionClassification:
    """Apply the experiment's strict success definition in stable precedence order."""

    if infrastructure_error:
        return SessionClassification(False, "infrastructure_failure")
    if variant == "enhanced" and (not analysis_sources or any(source != "local_model" for source in analysis_sources)):
        return SessionClassification(False, "qwen_fallback")
    if not workspace_audit.changed_paths:
        return SessionClassification(False, "empty_patch")
    if workspace_audit.forbidden_paths:
        return SessionClassification(False, "forbidden_modification")
    if exit_status == "LimitsExceeded":
        return SessionClassification(False, "step_limit")
    if exit_status == "TimeExceeded":
        return SessionClassification(False, "time_limit")
    if exit_status != "Submitted":
        return SessionClassification(False, "model_failure")
    if not hidden_outcome.result.success:
        return SessionClassification(False, "tests_failed")
    return SessionClassification(True, "")


def _git(workspace: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", *args], cwd=workspace, capture_output=True, text=True, check=False, timeout=30
    )
    if completed.returncode != 0:
        msg = completed.stderr.strip() or completed.stdout.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(msg)


def _snapshot_workspace(workspace: Path) -> None:
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
        "baseline",
    )


def _agent_templates() -> tuple[str, str]:
    system = "You are a software engineering agent. Use the bash tool to inspect, edit, and test the repository."
    instance = """Solve this issue: {{task}}

Work only in /workspace. Inspect the repository evidence, edit only source files needed for the fix, and run available tests.
{% if repopilot_context %}
Retrieved repository evidence:
{{repopilot_context}}
{% endif %}
When finished, run `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` as a command by itself.
"""
    return system, instance


def _safe_run_args(workspace: Path, *, uid: int, gid: int) -> list[str]:
    return [
        "--rm",
        "--network",
        "none",
        "--user",
        f"{uid}:{gid}",
        "--memory",
        "1g",
        "--cpus",
        "1.0",
        "--pids-limit",
        "128",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--volume",
        f"{workspace.resolve()}:/workspace",
    ]


def _empty_hidden_failure(message: str) -> HiddenVerificationOutcome:
    return HiddenVerificationOutcome(
        result=VerificationResult.failed(message),
        counts=JUnitCounts(total=0, passed=0, failed=0, errors=0, skipped=0),
    )


def _sum_known(values: list[int | None]) -> int | None:
    known = [value for value in values if value is not None]
    return sum(known) if known else None


def run_evaluation_session(
    task: EvaluationTask,
    variant: str,
    session_dir: Path,
    *,
    model: Any,
    image: str,
    uid: int,
    gid: int,
    max_strong_calls: int = 8,
    max_repairs: int = 1,
) -> dict[str, Any]:
    """Run one immutable baseline or enhanced session and persist raw evidence."""

    if variant not in {"baseline", "enhanced"}:
        msg = f"Unknown evaluation variant: {variant}"
        raise ValueError(msg)
    session_dir = session_dir.resolve()
    if session_dir.exists():
        msg = f"Session directory already exists: {session_dir}"
        raise FileExistsError(msg)
    session_dir.mkdir(parents=True)
    workspace = materialize_task(task, session_dir / "workspace")
    _snapshot_workspace(workspace)
    system_template, instance_template = _agent_templates()
    docker_config = DockerSafetyConfig(image=image, user=f"{uid}:{gid}")
    started = time.perf_counter()
    environment = None
    attempt_records: list[dict[str, Any]] = []
    trajectory_metrics = []
    hidden_outcome = _empty_hidden_failure("Session did not reach hidden verification")
    infrastructure_error = ""
    exit_status = ""
    prompt = task.issue
    calls_used = 0
    try:
        environment = DockerEnvironment(
            image=image,
            cwd="/workspace",
            env={"HOME": "/tmp", "PAGER": "cat", "PIP_PROGRESS_BAR": "off"},
            forward_env=[],
            run_args=_safe_run_args(workspace, uid=uid, gid=gid),
            timeout=120,
            container_timeout="30m",
        )
        for attempt_number in range(1, max_repairs + 2):
            remaining_calls = max_strong_calls - calls_used
            if remaining_calls <= 0:
                exit_status = "LimitsExceeded"
                break
            trajectory = session_dir / f"attempt-{attempt_number}.traj.json"
            agent = RepoPilotAgent(
                model=model,
                env=environment,
                system_template=system_template,
                instance_template=instance_template,
                repository_path=workspace,
                retrieval_enabled=variant == "enhanced",
                local_analysis_enabled=variant == "enhanced",
                local_model_timeout=30,
                context_budget_chars=12_000,
                step_limit=remaining_calls,
                cost_limit=0,
                wall_time_limit_seconds=900,
                output_path=trajectory,
            )
            result = agent.run(prompt)
            exit_status = result.get("exit_status", "")
            metrics = extract_trajectory_metrics(trajectory)
            trajectory_metrics.append(metrics)
            calls_used += metrics.strong_model_calls
            verification_dir = session_dir / f"verification-{attempt_number}"
            verification_dir.mkdir()
            hidden_outcome = run_hidden_verification(
                workspace,
                task.hidden_tests,
                verification_dir,
                task.test_command,
                docker_config,
                timeout=300,
            )
            attempt_records.append(
                {
                    "number": attempt_number,
                    "exit_status": exit_status,
                    "trajectory": trajectory.name,
                    "strong_model_calls": metrics.strong_model_calls,
                    "input_tokens": metrics.input_tokens,
                    "output_tokens": metrics.output_tokens,
                    "analysis_source": metrics.analysis_source,
                    "hidden_verification": {
                        "result": asdict(hidden_outcome.result),
                        "counts": asdict(hidden_outcome.counts),
                    },
                }
            )
            if hidden_outcome.result.success or attempt_number > max_repairs or calls_used >= max_strong_calls:
                break
            prompt = (
                f"{task.issue}\n\nThe previous repair failed external verification. "
                f"Use this bounded failure evidence and repair the existing working tree:\n"
                f"{bound_output(hidden_outcome.result.output, 4_000)}"
            )
    except Exception as error:
        infrastructure_error = type(error).__name__
    finally:
        if environment is not None:
            environment.cleanup()

    audit = audit_workspace(workspace, task.allowed_changes)
    (session_dir / "solution.patch").write_text(audit.patch)
    sources = tuple(metric.analysis_source or "" for metric in trajectory_metrics if variant == "enhanced")
    classification = classify_session(
        variant=variant,
        exit_status=exit_status,
        workspace_audit=audit,
        hidden_outcome=hidden_outcome,
        analysis_sources=sources,
        infrastructure_error=infrastructure_error,
    )
    first_retrieval = trajectory_metrics[0].retrieved_files if trajectory_metrics else ()
    recall = recall_at_k(task.relevant_files, first_retrieval, k=5) if variant == "enhanced" else None
    report = {
        "task_id": task.task_id,
        "variant": variant,
        "success": classification.success,
        "failure_class": classification.failure_class,
        "exit_status": exit_status,
        "infrastructure_error": infrastructure_error,
        "attempts": attempt_records,
        "changed_paths": list(audit.changed_paths),
        "forbidden_paths": list(audit.forbidden_paths),
        "strong_model_calls": sum(metric.strong_model_calls for metric in trajectory_metrics),
        "input_tokens": _sum_known([metric.input_tokens for metric in trajectory_metrics]),
        "output_tokens": _sum_known([metric.output_tokens for metric in trajectory_metrics]),
        "cache_hit_input_tokens": _sum_known(
            [metric.cache_hit_input_tokens for metric in trajectory_metrics]
        ),
        "cache_miss_input_tokens": _sum_known(
            [metric.cache_miss_input_tokens for metric in trajectory_metrics]
        ),
        "retrieved_files": list(first_retrieval),
        "retrieval_recall_at_5": recall,
        "analysis_sources": list(sources),
        "hidden_test_counts": asdict(hidden_outcome.counts),
        "active_wall_seconds": time.perf_counter() - started,
        "model": "deepseek/deepseek-flash",
        "image": image,
    }
    (session_dir / "session.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def run_paired_evaluation(
    dataset: EvaluationDataset,
    output_dir: Path,
    *,
    model_factory: Callable[[], Any],
    balance_fetcher: Callable[[], Decimal],
    budget: BudgetGuard,
    image: str,
    uid: int,
    gid: int,
    session_runner: Callable[..., dict[str, Any]] = run_evaluation_session,
    estimated_pair_cost: Decimal = Decimal("1.50"),
) -> dict[str, Any]:
    """Run indivisible alternating pairs while preserving the balance reserve."""

    output_dir = output_dir.resolve()
    if output_dir.exists():
        msg = f"Experiment directory already exists: {output_dir}"
        raise FileExistsError(msg)
    output_dir.mkdir(parents=True)
    sessions_root = output_dir / "sessions"
    sessions_root.mkdir()
    starting_balance = balance_fetcher()
    if starting_balance != budget.starting_balance:
        msg = "Budget starting balance does not match the live starting balance"
        raise ValueError(msg)
    current_balance = starting_balance
    completed_pairs = 0
    records: list[dict[str, Any]] = []
    balance_history = [str(starting_balance)]
    state_path = output_dir / "run-state.json"
    jsonl_path = output_dir / "sessions.jsonl"

    for task_index, task in enumerate(dataset.tasks):
        if not budget.can_start_pair(
            current_balance=current_balance,
            estimated_pair_cost=estimated_pair_cost,
        ):
            break
        pair_records = []
        for variant in variant_order(task_index):
            session_dir = sessions_root / task.task_id / variant
            record = session_runner(
                task,
                variant,
                session_dir,
                model=model_factory(),
                image=image,
                uid=uid,
                gid=gid,
            )
            pair_records.append(record)
        with jsonl_path.open("a", encoding="utf-8") as stream:
            for record in pair_records:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        records.extend(pair_records)
        completed_pairs += 1
        current_balance = balance_fetcher()
        balance_history.append(str(current_balance))
        _write_json_atomic(
            state_path,
            {
                "dataset": dataset.name,
                "completed_pairs": completed_pairs,
                "completed_task_ids": [item.task_id for item in dataset.tasks[:completed_pairs]],
                "starting_balance_cny": str(starting_balance),
                "current_balance_cny": str(current_balance),
                "measured_spend_cny": str(max(Decimal("0"), starting_balance - current_balance)),
            },
        )

    report = {
        "dataset": dataset.name,
        "completed_pairs": completed_pairs,
        "starting_balance_cny": str(starting_balance),
        "ending_balance_cny": str(current_balance),
        "measured_spend_cny": str(max(Decimal("0"), starting_balance - current_balance)),
        "balance_history_cny": balance_history,
        "sessions": records,
    }
    _write_json_atomic(output_dir / "experiment.json", report)
    aggregate = build_aggregate(report)
    _write_json_atomic(output_dir / "aggregate.json", aggregate)
    markdown_path = output_dir / "report.md"
    temporary_markdown = markdown_path.with_suffix(".md.tmp")
    temporary_markdown.write_text(render_markdown(aggregate, model="deepseek/deepseek-flash"))
    temporary_markdown.replace(markdown_path)
    return report
