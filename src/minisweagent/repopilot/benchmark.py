"""Deterministic benchmark records and baseline comparisons."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkResult:
    task_id: str
    variant: str
    success: bool
    tests_passed: bool
    expected_files: tuple[str, ...] = ()
    retrieved_files: tuple[str, ...] = ()
    strong_model_calls: int = 0
    input_tokens: int = 0
    wall_seconds: float = 0.0
    failure_class: str = ""
    trajectory_path: str = ""


@dataclass(frozen=True)
class BenchmarkSummary:
    variant: str
    task_count: int
    success_rate: float
    test_pass_rate: float
    retrieval_recall_at_5: float | None
    strong_model_calls: int
    input_tokens: int
    wall_seconds: float
    failure_classes: dict[str, int]


@dataclass(frozen=True)
class VariantComparison:
    baseline: BenchmarkSummary
    candidate: BenchmarkSummary
    success_rate_delta: float
    strong_model_calls_delta: int
    input_tokens_delta: int
    wall_seconds_delta: float


def _recall_at_five(result: BenchmarkResult) -> float | None:
    expected = set(result.expected_files)
    if not expected:
        return None
    retrieved = set(result.retrieved_files[:5])
    return len(expected & retrieved) / len(expected)


def summarize(results: list[BenchmarkResult]) -> BenchmarkSummary:
    if not results:
        msg = "Cannot summarize an empty benchmark"
        raise ValueError(msg)
    variants = {result.variant for result in results}
    if len(variants) != 1:
        msg = "summarize() requires results from exactly one variant"
        raise ValueError(msg)

    task_count = len(results)
    recalls = [recall for result in results if (recall := _recall_at_five(result)) is not None]
    failures = Counter(result.failure_class for result in results if result.failure_class)
    return BenchmarkSummary(
        variant=results[0].variant,
        task_count=task_count,
        success_rate=sum(result.success for result in results) / task_count,
        test_pass_rate=sum(result.tests_passed for result in results) / task_count,
        retrieval_recall_at_5=sum(recalls) / len(recalls) if recalls else None,
        strong_model_calls=sum(result.strong_model_calls for result in results),
        input_tokens=sum(result.input_tokens for result in results),
        wall_seconds=sum(result.wall_seconds for result in results),
        failure_classes=dict(sorted(failures.items())),
    )


def compare_variants(
    results: list[BenchmarkResult], *, baseline: str, candidate: str
) -> VariantComparison:
    baseline_summary = summarize([result for result in results if result.variant == baseline])
    candidate_summary = summarize([result for result in results if result.variant == candidate])
    baseline_tasks = {result.task_id for result in results if result.variant == baseline}
    candidate_tasks = {result.task_id for result in results if result.variant == candidate}
    if baseline_tasks != candidate_tasks:
        msg = "Baseline and candidate must contain the same task IDs"
        raise ValueError(msg)
    return VariantComparison(
        baseline=baseline_summary,
        candidate=candidate_summary,
        success_rate_delta=candidate_summary.success_rate - baseline_summary.success_rate,
        strong_model_calls_delta=candidate_summary.strong_model_calls - baseline_summary.strong_model_calls,
        input_tokens_delta=candidate_summary.input_tokens - baseline_summary.input_tokens,
        wall_seconds_delta=candidate_summary.wall_seconds - baseline_summary.wall_seconds,
    )
