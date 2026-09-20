import re
from typing import Literal, Protocol

from jinja2 import Template
from pydantic import BaseModel

from minisweagent.repopilot.local_model import LocalModelError, LocalModelResult


class TaskAnalysis(BaseModel):
    task_type: Literal["bugfix", "feature", "refactor", "test", "unknown"]
    identifiers: list[str]
    paths: list[str]
    exceptions: list[str]
    search_terms: list[str]


class TaskAnalysisOutcome(BaseModel):
    analysis: TaskAnalysis
    source: Literal["local_model", "fallback"]
    latency_seconds: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error_type: str | None = None


class TaskAnalysisClient(Protocol):
    def complete(
        self, prompt: str, schema: type[TaskAnalysis], max_tokens: int
    ) -> LocalModelResult[TaskAnalysis]: ...


_ANALYSIS_PROMPT = Template(
    """Analyze this software-engineering task for repository retrieval.
Return only JSON matching the supplied schema. Do not include reasoning.

Task:
{{ task }}"""
)


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "bug",
    "fails",
    "file",
    "fix",
    "for",
    "from",
    "in",
    "is",
    "it",
    "last",
    "line",
    "most",
    "of",
    "on",
    "or",
    "recent",
    "return",
    "returns",
    "should",
    "the",
    "this",
    "to",
    "traceback",
    "when",
    "with",
}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _task_type(task: str) -> Literal["bugfix", "feature", "refactor", "test", "unknown"]:
    lowered = task.casefold()
    if re.search(r"\b(refactor|cleanup|restructure)\b", lowered):
        return "refactor"
    if re.search(r"\b(add|implement|feature)\b", lowered):
        return "feature"
    if re.search(r"\b(test|coverage)\b", lowered):
        return "test"
    if re.search(r"\b(bug|fix|fail(?:s|ed|ure)?|error|exception|traceback|wrong)\b", lowered):
        return "bugfix"
    return "unknown"


def analyze_task_fallback(task: str) -> TaskAnalysis:
    paths = _unique(re.findall(r"(?<![\w.-])(?:[\w.-]+/)*[\w.-]+\.py\b", task))
    exceptions = _unique(re.findall(r"\b[A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning)\b", task))
    identifiers = _unique(
        re.findall(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)`", task)
        + re.findall(r"\bin\s+([A-Za-z_]\w*)\s*$", task, re.MULTILINE)
        + [
            value
            for value in re.findall(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b", task)
            if not value.endswith(".py")
        ]
        + re.findall(r"\b[A-Za-z_]\w*_\w+\b", task)
    )
    words = [
        word.casefold()
        for word in re.findall(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b", task)
        if word.casefold() not in _STOP_WORDS
    ]
    return TaskAnalysis(
        task_type=_task_type(task),
        identifiers=identifiers,
        paths=paths,
        exceptions=exceptions,
        search_terms=_unique(paths + identifiers + exceptions + words),
    )


def analyze_task(task: str, client: TaskAnalysisClient) -> TaskAnalysisOutcome:
    try:
        result = client.complete(_ANALYSIS_PROMPT.render(task=task), TaskAnalysis, max_tokens=256)
    except LocalModelError as error:
        return TaskAnalysisOutcome(
            analysis=analyze_task_fallback(task),
            source="fallback",
            error_type=type(error).__name__,
        )
    return TaskAnalysisOutcome(
        analysis=result.value,
        source="local_model",
        latency_seconds=result.latency_seconds,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    )
