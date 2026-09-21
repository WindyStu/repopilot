from minisweagent.repopilot.evaluation_report import build_aggregate, render_markdown


def session(task, variant, *, success, calls, tokens, seconds, passed, total, recall=None):
    return {
        "task_id": task,
        "variant": variant,
        "success": success,
        "failure_class": "" if success else "tests_failed",
        "strong_model_calls": calls,
        "input_tokens": tokens,
        "active_wall_seconds": seconds,
        "hidden_test_counts": {"passed": passed, "total": total},
        "retrieval_recall_at_5": recall,
    }


def test_aggregate_reports_exact_counts_means_rates_and_paired_deltas():
    experiment = {
        "dataset": "pilot-v1",
        "completed_pairs": 2,
        "sessions": [
            session("one", "baseline", success=True, calls=4, tokens=400, seconds=4, passed=2, total=2),
            session("one", "enhanced", success=True, calls=3, tokens=300, seconds=5, passed=2, total=2, recall=1.0),
            session("two", "baseline", success=False, calls=6, tokens=600, seconds=6, passed=1, total=2),
            session("two", "enhanced", success=True, calls=3, tokens=300, seconds=5, passed=2, total=2, recall=0.5),
        ],
    }

    aggregate = build_aggregate(experiment)

    baseline = aggregate["variants"]["baseline"]
    enhanced = aggregate["variants"]["enhanced"]
    assert baseline["task_success"] == {"passed": 1, "total": 2, "rate": 0.5}
    assert baseline["hidden_tests"] == {"passed": 3, "total": 4, "rate": 0.75}
    assert baseline["mean_input_tokens"] == 500
    assert baseline["mean_strong_model_calls"] == 5
    assert enhanced["retrieval_recall_at_5"] == 0.75
    assert aggregate["paired_deltas"]["task_success_rate"] == 0.5
    assert aggregate["paired_deltas"]["mean_input_tokens"] == -200
    assert aggregate["paired_deltas"]["mean_strong_model_calls"] == -2
    assert aggregate["paired_deltas"]["mean_active_wall_seconds"] == 0


def test_markdown_states_dataset_size_model_and_single_run_limit():
    experiment = {
        "dataset": "pilot-v1",
        "completed_pairs": 1,
        "sessions": [
            session("one", "baseline", success=True, calls=2, tokens=100, seconds=1, passed=1, total=1),
            session("one", "enhanced", success=True, calls=1, tokens=80, seconds=2, passed=1, total=1, recall=1.0),
        ],
    }

    markdown = render_markdown(build_aggregate(experiment), model="deepseek/deepseek-flash")

    assert "1 paired tasks" in markdown
    assert "deepseek/deepseek-flash" in markdown
    assert "single run per task" in markdown
    assert "Retrieval Recall@5" in markdown
