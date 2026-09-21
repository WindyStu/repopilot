"""Deterministic aggregate and Markdown reports for controlled evaluations."""

from __future__ import annotations

from collections import Counter
from statistics import fmean
from typing import Any


def _rate(passed: int, total: int) -> dict[str, int | float]:
    return {"passed": passed, "total": total, "rate": passed / total if total else 0.0}


def _mean_known(sessions: list[dict[str, Any]], field: str) -> float | None:
    values = [session[field] for session in sessions if isinstance(session.get(field), int | float)]
    return fmean(values) if values else None


def _summarize_variant(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(bool(session.get("success")) for session in sessions)
    hidden_passed = sum(session.get("hidden_test_counts", {}).get("passed", 0) for session in sessions)
    hidden_total = sum(session.get("hidden_test_counts", {}).get("total", 0) for session in sessions)
    recalls = [
        session["retrieval_recall_at_5"]
        for session in sessions
        if isinstance(session.get("retrieval_recall_at_5"), int | float)
    ]
    return {
        "tasks": len(sessions),
        "task_success": _rate(successes, len(sessions)),
        "hidden_tests": _rate(hidden_passed, hidden_total),
        "retrieval_recall_at_5": fmean(recalls) if recalls else None,
        "total_input_tokens": sum(session.get("input_tokens") or 0 for session in sessions),
        "mean_input_tokens": _mean_known(sessions, "input_tokens"),
        "total_strong_model_calls": sum(session.get("strong_model_calls", 0) for session in sessions),
        "mean_strong_model_calls": _mean_known(sessions, "strong_model_calls"),
        "total_active_wall_seconds": sum(session.get("active_wall_seconds", 0.0) for session in sessions),
        "mean_active_wall_seconds": _mean_known(sessions, "active_wall_seconds"),
        "failure_classes": dict(
            sorted(Counter(session["failure_class"] for session in sessions if session.get("failure_class")).items())
        ),
    }


def _delta(enhanced: dict[str, Any], baseline: dict[str, Any], field: str) -> float | None:
    left = enhanced.get(field)
    right = baseline.get(field)
    if left is None or right is None:
        return None
    return left - right


def build_aggregate(experiment: dict[str, Any]) -> dict[str, Any]:
    """Recalculate every public metric from raw session records."""

    sessions = experiment.get("sessions", [])
    baseline_sessions = [session for session in sessions if session.get("variant") == "baseline"]
    enhanced_sessions = [session for session in sessions if session.get("variant") == "enhanced"]
    baseline_ids = {session["task_id"] for session in baseline_sessions}
    enhanced_ids = {session["task_id"] for session in enhanced_sessions}
    if not baseline_sessions or baseline_ids != enhanced_ids:
        msg = "Aggregate requires matching non-empty baseline and enhanced task IDs"
        raise ValueError(msg)
    baseline = _summarize_variant(baseline_sessions)
    enhanced = _summarize_variant(enhanced_sessions)
    deltas = {
        "task_success_rate": enhanced["task_success"]["rate"] - baseline["task_success"]["rate"],
        "hidden_test_pass_rate": enhanced["hidden_tests"]["rate"] - baseline["hidden_tests"]["rate"],
        "mean_input_tokens": _delta(enhanced, baseline, "mean_input_tokens"),
        "mean_strong_model_calls": _delta(enhanced, baseline, "mean_strong_model_calls"),
        "mean_active_wall_seconds": _delta(enhanced, baseline, "mean_active_wall_seconds"),
    }
    return {
        "dataset": experiment["dataset"],
        "paired_tasks": len(baseline_ids),
        "variants": {"baseline": baseline, "enhanced": enhanced},
        "paired_deltas": deltas,
    }


def _format_rate(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def _format_number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def render_markdown(aggregate: dict[str, Any], *, model: str) -> str:
    """Render a concise, limitation-aware comparison for README and interviews."""

    baseline = aggregate["variants"]["baseline"]
    enhanced = aggregate["variants"]["enhanced"]
    delta = aggregate["paired_deltas"]
    rows = [
        ("Task Success Rate", _format_rate(baseline["task_success"]["rate"]), _format_rate(enhanced["task_success"]["rate"]), _format_rate(delta["task_success_rate"])),
        ("Retrieval Recall@5", "N/A", _format_rate(enhanced["retrieval_recall_at_5"]), "N/A"),
        ("Mean input tokens", _format_number(baseline["mean_input_tokens"]), _format_number(enhanced["mean_input_tokens"]), _format_number(delta["mean_input_tokens"])),
        ("Mean strong-model calls", _format_number(baseline["mean_strong_model_calls"]), _format_number(enhanced["mean_strong_model_calls"]), _format_number(delta["mean_strong_model_calls"])),
        ("Mean active wall seconds", _format_number(baseline["mean_active_wall_seconds"]), _format_number(enhanced["mean_active_wall_seconds"]), _format_number(delta["mean_active_wall_seconds"])),
        ("Hidden-test pass rate", _format_rate(baseline["hidden_tests"]["rate"]), _format_rate(enhanced["hidden_tests"]["rate"]), _format_rate(delta["hidden_test_pass_rate"])),
    ]
    table = "\n".join(f"| {name} | {base} | {candidate} | {change} |" for name, base, candidate, change in rows)
    return f"""# Controlled RepoPilot Evaluation

Dataset: `{aggregate['dataset']}` · Model: `{model}` · {aggregate['paired_tasks']} paired tasks.

| Metric | Baseline | Enhanced | Enhanced - baseline |
|---|---:|---:|---:|
{table}

This pilot uses a single run per task. Results are descriptive and do not claim statistical significance.
"""
