"""Offline benchmark for RepoPilot retrieval against a no-RAG baseline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from minisweagent.repopilot.index import build_repository_index
from minisweagent.repopilot.retrieval import retrieve
from minisweagent.repopilot.task_analysis import analyze_task_fallback


def _recall(expected: set[str], retrieved: list[str]) -> float:
    if not expected:
        return 0.0
    return len(expected & set(retrieved[:5])) / len(expected)


def run_retrieval_benchmark(repository: Path, manifest: Path) -> dict[str, Any]:
    """Evaluate deterministic hybrid retrieval and an empty-context baseline."""

    definition = json.loads(manifest.read_text())
    tasks = definition.get("tasks", [])
    if not tasks:
        msg = "Benchmark manifest must contain at least one task"
        raise ValueError(msg)
    index = build_repository_index(repository).index
    task_results = []
    baseline_recalls = []
    hybrid_recalls = []
    for task in tasks:
        expected = set(task["expected_files"])
        analysis = analyze_task_fallback(task["issue"])
        hybrid = [result.path for result in retrieve(index, analysis, limit=5)]
        baseline_recall = _recall(expected, [])
        hybrid_recall = _recall(expected, hybrid)
        baseline_recalls.append(baseline_recall)
        hybrid_recalls.append(hybrid_recall)
        task_results.append(
            {
                "task_id": task["task_id"],
                "issue": task["issue"],
                "expected_files": sorted(expected),
                "baseline_top_5": [],
                "baseline_recall_at_5": baseline_recall,
                "hybrid_top_5": hybrid,
                "hybrid_recall_at_5": hybrid_recall,
            }
        )
    count = len(task_results)
    return {
        "dataset": definition.get("dataset", manifest.stem),
        "task_count": count,
        "repository": repository.resolve().name,
        "variants": {
            "baseline": {"description": "no retrieved context", "recall_at_5": sum(baseline_recalls) / count},
            "hybrid": {
                "description": "BM25 + exact symbol/path + one-hop dependencies",
                "recall_at_5": sum(hybrid_recalls) / count,
            },
        },
        "tasks": task_results,
    }
