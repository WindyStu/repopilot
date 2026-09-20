from minisweagent.repopilot.local_model import LocalModelConnectionError, LocalModelResult
from minisweagent.repopilot.task_analysis import TaskAnalysis, analyze_task, analyze_task_fallback


class SuccessfulClient:
    def complete(self, prompt, schema, max_tokens):
        self.prompt = prompt
        self.schema = schema
        self.max_tokens = max_tokens
        return LocalModelResult(
            value=TaskAnalysis(
                task_type="bugfix",
                identifiers=["parse_value"],
                paths=["app.py"],
                exceptions=[],
                search_terms=["app.py", "parse_value"],
            ),
            latency_seconds=0.25,
            prompt_tokens=30,
            completion_tokens=20,
        )


class FailingClient:
    def complete(self, prompt, schema, max_tokens):
        raise LocalModelConnectionError("offline")


def test_fallback_analysis_extracts_traceback_signals():
    task = """
    Fix `Parser.parse_file` in src/repopilot/parser.py.

    Traceback (most recent call last):
      File "src/repopilot/parser.py", line 42, in parse_file
        return ast.parse(source)
    ValueError: invalid syntax
    """

    analysis = analyze_task_fallback(task)

    assert analysis.task_type == "bugfix"
    assert analysis.paths == ["src/repopilot/parser.py"]
    assert analysis.exceptions == ["ValueError"]
    assert "Parser.parse_file" in analysis.identifiers
    assert "parse_file" in analysis.identifiers
    assert {"src/repopilot/parser.py", "Parser.parse_file", "parse_file", "ValueError"} <= set(
        analysis.search_terms
    )


def test_fallback_analysis_is_stable_and_removes_duplicate_low_information_terms():
    task = "Fix fix the parser bug in app.py when parse_value returns the wrong value."

    first = analyze_task_fallback(task)

    assert first == analyze_task_fallback(task)
    assert len(first.search_terms) == len({term.casefold() for term in first.search_terms})
    assert {"fix", "the", "in", "when", "returns"}.isdisjoint(first.search_terms)
    assert {"app.py", "parser", "parse_value", "wrong", "value"} <= set(first.search_terms)


def test_analyze_task_uses_bounded_local_model_response_with_metadata():
    client = SuccessfulClient()

    outcome = analyze_task("Fix parse_value in app.py", client)

    assert outcome.source == "local_model"
    assert outcome.analysis.paths == ["app.py"]
    assert outcome.latency_seconds == 0.25
    assert outcome.prompt_tokens == 30
    assert outcome.completion_tokens == 20
    assert outcome.error_type is None
    assert client.schema is TaskAnalysis
    assert client.max_tokens <= 256
    assert "Return only JSON" in client.prompt


def test_analyze_task_falls_back_and_records_local_model_failure():
    outcome = analyze_task("Fix parse_value in app.py", FailingClient())

    assert outcome.source == "fallback"
    assert outcome.analysis.task_type == "bugfix"
    assert outcome.analysis.paths == ["app.py"]
    assert outcome.error_type == "LocalModelConnectionError"
    assert outcome.latency_seconds is None
