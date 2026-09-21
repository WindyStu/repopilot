"""Provider-independent bounded repair workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from minisweagent.repopilot.verification import VerificationResult, bound_output


@dataclass(frozen=True)
class RepairAttempt:
    number: int
    candidate: Any
    verification: VerificationResult


@dataclass(frozen=True)
class RepairOutcome:
    success: bool
    exhausted: bool
    attempts: tuple[RepairAttempt, ...]

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def final_candidate(self) -> Any:
        return self.attempts[-1].candidate if self.attempts else None


def _repair_prompt(task: str, previous: RepairAttempt) -> str:
    evidence = bound_output(previous.verification.output, limit=4_000)
    command = f"\nVerification command: {previous.verification.command}" if previous.verification.command else ""
    return (
        f"{task}\n\nVerification failed on attempt {previous.number}.{command}\n"
        f"Failure evidence:\n{evidence}\n\nRepair the existing working tree and verify the fix."
    )


def run_repair_loop(
    task: str,
    solve: Callable[[str], Any],
    verify: Callable[[], VerificationResult],
    *,
    max_repairs: int = 1,
) -> RepairOutcome:
    """Run a solver once plus a bounded number of verification-driven repairs."""

    if max_repairs < 0:
        msg = "max_repairs cannot be negative"
        raise ValueError(msg)

    attempts: list[RepairAttempt] = []
    prompt = task
    for number in range(1, max_repairs + 2):
        candidate = solve(prompt)
        result = verify()
        attempt = RepairAttempt(number=number, candidate=candidate, verification=result)
        attempts.append(attempt)
        if result.success:
            return RepairOutcome(success=True, exhausted=False, attempts=tuple(attempts))
        prompt = _repair_prompt(task, attempt)
    return RepairOutcome(success=False, exhausted=True, attempts=tuple(attempts))
