from minisweagent.repopilot.benchmark import BenchmarkResult, compare_variants, summarize


def result(
    task_id,
    variant,
    *,
    success,
    expected=("parser.py",),
    retrieved=("parser.py",),
    calls=1,
    tokens=100,
    wall=1.0,
    failure_class="",
):
    return BenchmarkResult(
        task_id=task_id,
        variant=variant,
        success=success,
        tests_passed=success,
        expected_files=expected,
        retrieved_files=retrieved,
        strong_model_calls=calls,
        input_tokens=tokens,
        wall_seconds=wall,
        failure_class=failure_class,
        trajectory_path=f"artifacts/{variant}/{task_id}.json",
    )


def test_summary_keeps_failures_in_denominator_and_calculates_recall_at_five():
    summary = summarize(
        [
            result("one", "enhanced", success=True, expected=("a.py",), retrieved=("a.py", "x.py")),
            result(
                "two",
                "enhanced",
                success=False,
                expected=("b.py", "c.py"),
                retrieved=("b.py",),
                failure_class="tests_failed",
            ),
        ]
    )

    assert summary.task_count == 2
    assert summary.success_rate == 0.5
    assert summary.test_pass_rate == 0.5
    assert summary.retrieval_recall_at_5 == 0.75
    assert summary.failure_classes == {"tests_failed": 1}
    assert summary.strong_model_calls == 2
    assert summary.input_tokens == 200


def test_variant_comparison_reports_enhanced_minus_baseline_deltas():
    results = [
        result("one", "baseline", success=False, retrieved=(), calls=3, tokens=500, wall=5),
        result("two", "baseline", success=True, retrieved=(), calls=2, tokens=400, wall=4),
        result("one", "enhanced", success=True, calls=2, tokens=300, wall=3),
        result("two", "enhanced", success=True, calls=1, tokens=200, wall=2),
    ]

    comparison = compare_variants(results, baseline="baseline", candidate="enhanced")

    assert comparison.success_rate_delta == 0.5
    assert comparison.strong_model_calls_delta == -2
    assert comparison.input_tokens_delta == -400
    assert comparison.wall_seconds_delta == -4
