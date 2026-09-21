"""Safe verification primitives for untrusted generated code."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


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
