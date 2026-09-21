"""One-command RepoPilot runner for WSL2."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import typer
from rich.console import Console

from minisweagent.environments.docker import DockerEnvironment
from minisweagent.repopilot.agent import RepoPilotAgent
from minisweagent.repopilot.deepseek_provider import BudgetGuard, build_deepseek_model, fetch_cny_balance
from minisweagent.repopilot.evaluation_dataset import load_dataset
from minisweagent.repopilot.evaluation_runner import run_paired_evaluation
from minisweagent.repopilot.local_server import check_sglang
from minisweagent.repopilot.retrieval_benchmark import run_retrieval_benchmark
from minisweagent.repopilot.strong_model import build_gemini_model
from minisweagent.repopilot.verification import VerificationResult, bound_output
from minisweagent.repopilot.workflow import run_repair_loop

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console(highlight=False)

_IGNORED_NAMES = {
    ".agents",
    ".claude",
    ".codex",
    ".cursor",
    ".git",
    ".repopilot",
    "artifacts",
    "benchmark-results",
    "credentials.json",
    "service-account.json",
}


@app.callback()
def main() -> None:
    """Repository-aware issue-to-patch agent."""


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        lower = name.lower()
        if (
            name in _IGNORED_NAMES
            or lower == ".env"
            or lower.startswith(".env.")
            or lower.endswith((".pem", ".key", ".p12", ".pfx"))
            or name == "__pycache__"
        ):
            ignored.add(name)
    return ignored


def prepare_workspace(source: Path, destination: Path) -> Path:
    """Create a credential-filtered working copy; never edit the source checkout."""

    source = source.resolve(strict=True)
    if not source.is_dir():
        msg = f"Repository must be a directory: {source}"
        raise ValueError(msg)
    destination = destination.resolve()
    if destination.exists():
        msg = f"Run workspace already exists: {destination}"
        raise FileExistsError(msg)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=_copy_ignore)
    return destination


def build_safe_run_args(workspace: Path, *, uid: int, gid: int) -> list[str]:
    """Docker arguments for the persistent agent container."""

    resolved = workspace.resolve(strict=True)
    return [
        "--rm",
        "--network",
        "none",
        "--user",
        f"{uid}:{gid}",
        "--memory",
        "1g",
        "--cpus",
        "1.0",
        "--pids-limit",
        "128",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--volume",
        f"{resolved}:/workspace",
    ]


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=workspace, capture_output=True, text=True, check=False, timeout=30
    )
    if completed.returncode != 0:
        msg = completed.stderr.strip() or completed.stdout.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(msg)
    return completed.stdout


def _snapshot_workspace(workspace: Path) -> None:
    _git(workspace, "init", "--quiet")
    _git(workspace, "add", "-A")
    _git(
        workspace,
        "-c",
        "user.name=RepoPilot",
        "-c",
        "user.email=repopilot@localhost",
        "commit",
        "--quiet",
        "-m",
        "baseline",
    )


def _agent_templates() -> tuple[str, str]:
    system = "You are a software engineering agent. Use the bash tool to inspect, edit, and test the repository."
    instance = """Solve this issue: {{task}}

Work only in /workspace. Inspect the retrieved evidence first, then edit and test the code.
{% if repopilot_context %}
Retrieved repository evidence:
{{repopilot_context}}
{% endif %}
When finished, run `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` as a command by itself.
"""
    return system, instance


@app.command("benchmark-retrieval")
def benchmark_retrieval(
    repository: Path = typer.Option(Path("."), "--repo", exists=True, file_okay=False, resolve_path=True),
    manifest: Path = typer.Option(Path("benchmarks/retrieval-v1.json"), "--manifest", exists=True, dir_okay=False),
    output: Path = typer.Option(Path("benchmark-results/retrieval-v1.json"), "--output"),
) -> None:
    """Compare no-RAG baseline and hybrid retrieval on labeled tasks."""

    report = run_retrieval_benchmark(repository, manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    baseline = report["variants"]["baseline"]["recall_at_5"]
    hybrid = report["variants"]["hybrid"]["recall_at_5"]
    console.print(f"Retrieval benchmark: baseline={baseline:.1%}, hybrid={hybrid:.1%}, report={output}")


@app.command()
def evaluate(
    manifest: Path = typer.Option(
        Path("benchmarks/e2e-v1/manifest.json"),
        "--manifest",
        exists=True,
        dir_okay=False,
        resolve_path=True,
    ),
    output_dir: Path | None = typer.Option(None, "--output-dir"),
    image: str = typer.Option("repopilot-runner:py312", "--image"),
    max_spend_cny: float = typer.Option(8.0, "--max-spend-cny", min=0),
    reserve_cny: float = typer.Option(2.0, "--reserve-cny", min=0),
    estimated_pair_cost_cny: float = typer.Option(1.5, "--estimated-pair-cost-cny", min=0),
) -> None:
    """Run the controlled paired DeepSeek baseline evaluation."""

    dataset = load_dataset(manifest)
    root = (
        output_dir
        or Path("benchmark-results/e2e") / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ).resolve()
    check_sglang("http://127.0.0.1:30000/v1", timeout=30)
    starting_balance = fetch_cny_balance()
    first_query = True

    def balance_fetcher() -> Decimal:
        nonlocal first_query
        if first_query:
            first_query = False
            return starting_balance
        return fetch_cny_balance()

    report = run_paired_evaluation(
        dataset,
        root,
        model_factory=build_deepseek_model,
        balance_fetcher=balance_fetcher,
        budget=BudgetGuard(
            starting_balance=starting_balance,
            max_spend=Decimal(str(max_spend_cny)),
            reserve=Decimal(str(reserve_cny)),
        ),
        estimated_pair_cost=Decimal(str(estimated_pair_cost_cny)),
        image=image,
        uid=os.getuid(),
        gid=os.getgid(),
    )
    console.print(
        f"Controlled evaluation completed {report['completed_pairs']} pairs; "
        f"measured spend CNY {report['measured_spend_cny']}; artifacts={root}"
    )


@app.command()
def run(
    repository: Path = typer.Option(..., "--repo", exists=True, file_okay=False, resolve_path=True),
    issue: str = typer.Option(..., "--issue"),
    test_command: str = typer.Option("pytest -q", "--test-command"),
    output_dir: Path | None = typer.Option(None, "--output-dir"),
    image: str = typer.Option("repopilot-runner:py312", "--image"),
    max_repairs: int = typer.Option(1, "--max-repairs", min=0, max=3),
    baseline: bool = typer.Option(False, "--baseline"),
    no_local_model: bool = typer.Option(False, "--no-local-model"),
) -> None:
    """Solve one issue in an isolated copy and retain the patch and trajectories."""

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = (output_dir or Path("artifacts") / run_id).resolve()
    workspace = prepare_workspace(repository, root / "workspace")
    _snapshot_workspace(workspace)
    model = build_gemini_model()
    system_template, instance_template = _agent_templates()
    env = DockerEnvironment(
        image=image,
        cwd="/workspace",
        env={"HOME": "/tmp", "PAGER": "cat", "PIP_PROGRESS_BAR": "off"},
        forward_env=[],
        run_args=build_safe_run_args(workspace, uid=os.getuid(), gid=os.getgid()),
        timeout=120,
        container_timeout="30m",
    )
    attempt_number = 0

    def solve(prompt: str) -> dict:
        nonlocal attempt_number
        attempt_number += 1
        trajectory = root / f"attempt-{attempt_number}.traj.json"
        agent = RepoPilotAgent(
            model=model,
            env=env,
            system_template=system_template,
            instance_template=instance_template,
            repository_path=workspace,
            retrieval_enabled=not baseline,
            local_analysis_enabled=not baseline and not no_local_model,
            context_budget_chars=12_000,
            step_limit=30,
            cost_limit=0,
            wall_time_limit_seconds=900,
            output_path=trajectory,
        )
        result = agent.run(prompt)
        return {"result": result, "trajectory": str(trajectory)}

    def verify() -> VerificationResult:
        output = env.execute({"command": test_command}, timeout=300)
        evidence = bound_output(output.get("output", ""), 8_000)
        if output.get("returncode") == 0:
            return VerificationResult.passed(evidence, command=test_command)
        exception = output.get("exception_info", "")
        return VerificationResult.failed(bound_output(f"{evidence}\n{exception}", 8_000), command=test_command)

    try:
        outcome = run_repair_loop(issue, solve, verify, max_repairs=max_repairs)
    finally:
        env.cleanup()

    patch = _git(workspace, "diff", "--binary", "HEAD")
    (root / "solution.patch").write_text(patch)
    report = {
        "run_id": run_id,
        "source_repository": str(repository),
        "workspace": str(workspace),
        "baseline": baseline,
        "model": "gemini/gemini-3.8-flash",
        "test_command": test_command,
        "success": outcome.success,
        "exhausted": outcome.exhausted,
        "attempts": [
            {
                "number": attempt.number,
                "candidate": attempt.candidate,
                "verification": asdict(attempt.verification),
            }
            for attempt in outcome.attempts
        ],
        "patch_path": str(root / "solution.patch"),
    }
    (root / "report.json").write_text(json.dumps(report, indent=2))
    status = "PASSED" if outcome.success else "FAILED"
    console.print(f"RepoPilot {status}: {root}")
    if not outcome.success:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
