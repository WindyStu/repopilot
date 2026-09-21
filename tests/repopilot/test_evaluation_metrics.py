import json

from minisweagent.repopilot.evaluation_metrics import extract_trajectory_metrics, recall_at_k


def test_extracts_calls_tokens_cache_and_retrieval_from_trajectory(tmp_path):
    trajectory = {
        "info": {
            "model_stats": {"api_calls": 3},
            "repopilot": {
                "analysis_source": "qwen",
                "retrieved_files": [
                    {"path": "app/config.py", "score": 3.0},
                    {"path": "app/defaults.py", "score": 2.0},
                ],
            },
        },
        "messages": [
            {
                "role": "assistant",
                "extra": {
                    "response": {
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 20,
                            "prompt_cache_hit_tokens": 60,
                            "prompt_cache_miss_tokens": 40,
                        }
                    }
                },
            },
            {
                "role": "assistant",
                "extra": {
                    "response": {
                        "usage": {
                            "prompt_tokens": 150,
                            "completion_tokens": 30,
                            "prompt_cache_hit_tokens": 100,
                            "prompt_cache_miss_tokens": 50,
                        }
                    }
                },
            },
        ],
    }
    path = tmp_path / "attempt.traj.json"
    path.write_text(json.dumps(trajectory))

    metrics = extract_trajectory_metrics(path)

    assert metrics.strong_model_calls == 3
    assert metrics.input_tokens == 250
    assert metrics.output_tokens == 50
    assert metrics.cache_hit_input_tokens == 160
    assert metrics.cache_miss_input_tokens == 90
    assert metrics.retrieved_files == ("app/config.py", "app/defaults.py")
    assert metrics.analysis_source == "qwen"


def test_missing_usage_is_preserved_as_unknown_instead_of_inventing_zero(tmp_path):
    path = tmp_path / "attempt.traj.json"
    path.write_text(json.dumps({"info": {"model_stats": {"api_calls": 1}}, "messages": []}))

    metrics = extract_trajectory_metrics(path)

    assert metrics.strong_model_calls == 1
    assert metrics.input_tokens is None
    assert metrics.output_tokens is None
    assert metrics.cache_hit_input_tokens is None
    assert metrics.cache_miss_input_tokens is None


def test_recall_at_k_uses_manually_labeled_files_and_top_k_only():
    recall = recall_at_k(
        relevant_files=("app/config.py", "app/defaults.py"),
        retrieved_files=("README.md", "app/config.py", "a.py", "b.py", "c.py", "app/defaults.py"),
        k=5,
    )

    assert recall == 0.5
