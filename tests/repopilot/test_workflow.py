from minisweagent.repopilot.workflow import VerificationResult, run_repair_loop


def test_repair_loop_stops_after_first_passing_verification():
    prompts = []

    def solve(prompt):
        prompts.append(prompt)
        return "patch-1"

    outcome = run_repair_loop("Fix parser", solve, lambda: VerificationResult.passed("2 passed"), max_repairs=2)

    assert outcome.success is True
    assert outcome.attempt_count == 1
    assert prompts == ["Fix parser"]


def test_repair_loop_feeds_bounded_failure_back_and_then_recovers():
    prompts = []
    results = iter(
        [
            VerificationResult.failed("FAILED tests/test_parser.py::test_empty\nexpected []", command="pytest -q"),
            VerificationResult.passed("1 passed", command="pytest -q"),
        ]
    )

    def solve(prompt):
        prompts.append(prompt)
        return f"patch-{len(prompts)}"

    outcome = run_repair_loop("Fix parser", solve, lambda: next(results), max_repairs=1)

    assert outcome.success is True
    assert outcome.attempt_count == 2
    assert "Verification failed on attempt 1" in prompts[1]
    assert "FAILED tests/test_parser.py::test_empty" in prompts[1]
    assert [attempt.candidate for attempt in outcome.attempts] == ["patch-1", "patch-2"]


def test_repair_loop_preserves_last_candidate_when_budget_is_exhausted():
    outcome = run_repair_loop(
        "Fix parser",
        lambda prompt: "last-patch",
        lambda: VerificationResult.failed("still failing"),
        max_repairs=1,
    )

    assert outcome.success is False
    assert outcome.exhausted is True
    assert outcome.attempt_count == 2
    assert outcome.final_candidate == "last-patch"
