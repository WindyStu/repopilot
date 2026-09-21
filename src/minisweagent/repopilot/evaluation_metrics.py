"""Metric extraction from immutable RepoPilot trajectory artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrajectoryMetrics:
    strong_model_calls: int
    input_tokens: int | None
    output_tokens: int | None
    cache_hit_input_tokens: int | None
    cache_miss_input_tokens: int | None
    retrieved_files: tuple[str, ...]
    analysis_source: str | None


def _sum_optional(usages: list[dict[str, Any]], field: str) -> int | None:
    values = [usage[field] for usage in usages if isinstance(usage.get(field), int)]
    return sum(values) if values else None


def extract_trajectory_metrics(path: Path) -> TrajectoryMetrics:
    """Read provider-reported usage and RepoPilot retrieval evidence."""

    trajectory = json.loads(path.read_text())
    usages = []
    for message in trajectory.get("messages", []):
        response = message.get("extra", {}).get("response")
        if isinstance(response, dict) and isinstance(response.get("usage"), dict):
            usages.append(response["usage"])

    info = trajectory.get("info", {})
    model_stats = info.get("model_stats", {})
    repopilot = info.get("repopilot", {})
    retrieved = tuple(
        item["path"]
        for item in repopilot.get("retrieved_files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    )
    calls = model_stats.get("api_calls")
    if not isinstance(calls, int):
        calls = len(usages)
    source = repopilot.get("analysis_source")
    return TrajectoryMetrics(
        strong_model_calls=calls,
        input_tokens=_sum_optional(usages, "prompt_tokens"),
        output_tokens=_sum_optional(usages, "completion_tokens"),
        cache_hit_input_tokens=_sum_optional(usages, "prompt_cache_hit_tokens"),
        cache_miss_input_tokens=_sum_optional(usages, "prompt_cache_miss_tokens"),
        retrieved_files=retrieved,
        analysis_source=source if isinstance(source, str) else None,
    )


def recall_at_k(relevant_files: tuple[str, ...], retrieved_files: tuple[str, ...], *, k: int = 5) -> float:
    """Return labeled-file recall within the first k retrieved paths."""

    if not relevant_files:
        msg = "Recall requires at least one manually labeled relevant file"
        raise ValueError(msg)
    if k <= 0:
        msg = "k must be positive"
        raise ValueError(msg)
    relevant = set(relevant_files)
    return len(relevant.intersection(retrieved_files[:k])) / len(relevant)
