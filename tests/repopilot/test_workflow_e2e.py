import subprocess
import sys

from minisweagent.repopilot.workflow import VerificationResult, run_repair_loop


def test_issue_to_code_change_with_failed_verification_and_automatic_repair(tmp_path):
    repository = tmp_path / "calculator"
    repository.mkdir()
    module = repository / "calculator.py"
    module.write_text("def divide(a, b):\n    return a // b\n")
    (repository / "test_calculator.py").write_text(
        "from calculator import divide\n\n"
        "def test_divide_keeps_fraction():\n"
        "    assert divide(3, 2) == 1.5\n"
    )
    solve_prompts = []

    def solve(prompt):
        solve_prompts.append(prompt)
        if len(solve_prompts) == 2:
            module.write_text("def divide(a, b):\n    return a / b\n")
        return module.read_text()

    def verify():
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=repository,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        output = completed.stdout + completed.stderr
        if completed.returncode == 0:
            return VerificationResult.passed(output, command="pytest -q")
        return VerificationResult.failed(output, command="pytest -q")

    outcome = run_repair_loop(
        "divide(3, 2) should return 1.5 instead of truncating to 1",
        solve,
        verify,
        max_repairs=1,
    )

    assert outcome.success is True
    assert outcome.attempt_count == 2
    assert "Verification failed on attempt 1" in solve_prompts[1]
    assert module.read_text() == "def divide(a, b):\n    return a / b\n"
    assert "1 passed" in outcome.attempts[-1].verification.output
