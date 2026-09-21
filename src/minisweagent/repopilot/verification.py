"""Safe verification primitives for untrusted generated code."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True)
class DockerSafetyConfig:
    """Resource and isolation limits for a disposable verifier container."""

    image: str
    executable: str = "docker"
    memory: str = "1g"
    cpus: float = 1.0
    pids_limit: int = 128
    user: str = "65532:65532"


@dataclass(frozen=True)
class VerificationResult:
    success: bool
    output: str
    command: str = ""

    @classmethod
    def passed(cls, output: str, command: str = "") -> VerificationResult:
        return cls(success=True, output=output, command=command)

    @classmethod
    def failed(cls, output: str, command: str = "") -> VerificationResult:
        return cls(success=False, output=output, command=command)


@dataclass(frozen=True)
class JUnitCounts:
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int


@dataclass(frozen=True)
class HiddenVerificationOutcome:
    result: VerificationResult
    counts: JUnitCounts


def build_docker_command(workspace: Path, test_command: str, config: DockerSafetyConfig) -> list[str]:
    """Build a Docker invocation without inheriting host credentials or home mounts."""

    resolved = workspace.resolve(strict=True)
    if not resolved.is_dir():
        msg = f"Workspace must be a directory: {resolved}"
        raise ValueError(msg)
    return [
        config.executable,
        "run",
        "--rm",
        "--network",
        "none",
        "--user",
        config.user,
        "--memory",
        config.memory,
        "--cpus",
        str(config.cpus),
        "--pids-limit",
        str(config.pids_limit),
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--workdir",
        "/workspace",
        "--volume",
        f"{resolved}:/workspace",
        config.image,
        "bash",
        "-lc",
        test_command,
    ]


def build_hidden_test_command(
    workspace: Path,
    hidden_tests: Path,
    artifacts: Path,
    test_command: str,
    config: DockerSafetyConfig,
) -> list[str]:
    """Build a one-shot verifier with hidden tests mounted read-only."""

    workspace = workspace.resolve(strict=True)
    hidden_tests = hidden_tests.resolve(strict=True)
    artifacts = artifacts.resolve(strict=True)
    for path in (workspace, hidden_tests, artifacts):
        if not path.is_dir():
            msg = f"Verification mount must be a directory: {path}"
            raise ValueError(msg)
    command = f"{test_command} --junitxml=/repopilot-artifacts/junit.xml"
    return [
        config.executable,
        "run",
        "--rm",
        "--network",
        "none",
        "--user",
        config.user,
        "--memory",
        config.memory,
        "--cpus",
        str(config.cpus),
        "--pids-limit",
        str(config.pids_limit),
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--workdir",
        "/workspace",
        "--env",
        "PYTHONPATH=/workspace",
        "--volume",
        f"{workspace}:/workspace",
        "--volume",
        f"{hidden_tests}:/repopilot-hidden:ro",
        "--volume",
        f"{artifacts}:/repopilot-artifacts",
        config.image,
        "bash",
        "-lc",
        command,
    ]


def parse_junit_counts(report: Path) -> JUnitCounts:
    """Count outcomes from JUnit test cases without relying on suite summaries."""

    root = ElementTree.parse(report).getroot()
    cases = list(root.iter("testcase"))
    failed = sum(case.find("failure") is not None for case in cases)
    errors = sum(case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    return JUnitCounts(
        total=len(cases),
        passed=len(cases) - failed - errors - skipped,
        failed=failed,
        errors=errors,
        skipped=skipped,
    )


def bound_output(output: str, limit: int = 8_000) -> str:
    """Keep useful head and tail evidence while bounding model-facing output."""

    if limit < 32:
        msg = "Output limit must be at least 32 characters"
        raise ValueError(msg)
    if len(output) <= limit:
        return output
    marker = f"\n... {len(output) - limit} characters omitted ...\n"
    available = max(2, limit - len(marker))
    head_size = available // 2
    tail_size = available - head_size
    return output[:head_size] + marker + output[-tail_size:]


def run_docker_verification(
    workspace: Path,
    test_command: str,
    config: DockerSafetyConfig,
    *,
    timeout: int = 120,
    output_limit: int = 8_000,
) -> VerificationResult:
    """Run tests in the isolated container and return bounded evidence."""

    command = build_docker_command(workspace, test_command, config)
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as error:
        partial = error.output or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        evidence = bound_output(f"Verification timed out after {timeout}s.\n{partial}", output_limit)
        return VerificationResult.failed(evidence, command=test_command)
    except (FileNotFoundError, subprocess.SubprocessError) as error:
        evidence = bound_output(f"Container runtime failed: {type(error).__name__}: {error}", output_limit)
        return VerificationResult.failed(evidence, command=test_command)

    evidence = bound_output(completed.stdout or "", output_limit)
    if completed.returncode == 0:
        return VerificationResult.passed(evidence, command=test_command)
    return VerificationResult.failed(evidence, command=test_command)


def run_hidden_verification(
    workspace: Path,
    hidden_tests: Path,
    artifacts: Path,
    test_command: str,
    config: DockerSafetyConfig,
    *,
    timeout: int = 300,
    output_limit: int = 8_000,
) -> HiddenVerificationOutcome:
    """Run externally mounted hidden tests and return JUnit-backed evidence."""

    command = build_hidden_test_command(workspace, hidden_tests, artifacts, test_command, config)
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as error:
        empty = JUnitCounts(total=0, passed=0, failed=0, errors=0, skipped=0)
        evidence = bound_output(f"Hidden verification failed: {type(error).__name__}: {error}", output_limit)
        return HiddenVerificationOutcome(VerificationResult.failed(evidence, test_command), empty)

    report = artifacts / "junit.xml"
    counts = (
        parse_junit_counts(report)
        if report.is_file()
        else JUnitCounts(total=0, passed=0, failed=0, errors=0, skipped=0)
    )
    evidence = bound_output(completed.stdout or "", output_limit)
    success = completed.returncode == 0 and report.is_file()
    result = (
        VerificationResult.passed(evidence, test_command)
        if success
        else VerificationResult.failed(evidence, test_command)
    )
    return HiddenVerificationOutcome(result=result, counts=counts)
