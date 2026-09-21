import json

from minisweagent.repopilot.retrieval_benchmark import run_retrieval_benchmark


def test_retrieval_benchmark_compares_empty_baseline_with_hybrid_results(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "parser.py").write_text("def parse_token(token):\n    return token.strip()\n")
    (repository / "unrelated.py").write_text("def paint_wall(color):\n    return color\n")
    manifest = tmp_path / "tasks.json"
    manifest.write_text(
        json.dumps(
            {
                "dataset": "tiny-v1",
                "tasks": [
                    {
                        "task_id": "parser-token",
                        "issue": "parse_token in parser.py keeps surrounding whitespace",
                        "expected_files": ["parser.py"],
                    }
                ],
            }
        )
    )

    report = run_retrieval_benchmark(repository, manifest)

    assert report["dataset"] == "tiny-v1"
    assert report["task_count"] == 1
    assert report["variants"]["baseline"]["recall_at_5"] == 0.0
    assert report["variants"]["hybrid"]["recall_at_5"] == 1.0
    assert report["tasks"][0]["hybrid_top_5"][0] == "parser.py"
