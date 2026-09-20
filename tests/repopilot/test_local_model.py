import json
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import BaseModel

from minisweagent.repopilot.local_model import (
    LocalModelConnectionError,
    LocalModelTimeoutError,
    LocalModelTruncatedOutputError,
    MalformedStructuredOutputError,
    SGLangClient,
    parse_structured_output,
)
from minisweagent.repopilot.local_server import build_sglang_command, check_sglang


class TaskAnalysis(BaseModel):
    task_type: str
    search_terms: list[str]


class CompletionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(self.server.models_response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.server.request_body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        time.sleep(self.server.delay)
        body = json.dumps(self.server.response_body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def log_message(self, format, *args):
        pass


@contextmanager
def completion_server(response_body, delay=0):
    server = ThreadingHTTPServer(("127.0.0.1", 0), CompletionHandler)
    server.response_body = response_body
    server.request_body = None
    server.delay = delay
    server.models_response = {"data": [{"id": "Qwen/Qwen3-0.6B"}]}
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize(
    ("content",),  # noqa: PT006 - AGENTS.md requires a tuple
    [
        ('{"task_type":"bugfix","search_terms":["parser"]}',),
        ('```json\n{"task_type":"bugfix","search_terms":["parser"]}\n```',),
        ('Result:\n{"task_type":"bugfix","search_terms":["parser"]}\nDone.',),
    ],
)
def test_parse_structured_output_extracts_and_validates_json(content):
    assert parse_structured_output(content, TaskAnalysis) == TaskAnalysis(
        task_type="bugfix", search_terms=["parser"]
    )


@pytest.mark.parametrize(
    ("content",),  # noqa: PT006 - AGENTS.md requires a tuple
    [
        ("not json",),
        ('{"task_type":"bugfix"',),
        ('{"task_type":"bugfix","search_terms":"parser"}',),
    ],
)
def test_parse_structured_output_rejects_malformed_or_invalid_content(content):
    with pytest.raises(MalformedStructuredOutputError, match="valid structured output"):
        parse_structured_output(content, TaskAnalysis)


def test_sglang_client_posts_schema_and_returns_value_with_usage():
    response = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": '{"task_type":"bugfix","search_terms":["parser"]}',
                },
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8},
    }
    with completion_server(response) as server:
        result = SGLangClient(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="Qwen/Qwen3-0.6B",
            timeout=1,
        ).complete("Analyze this bug", TaskAnalysis, max_tokens=64)

    assert result.value == TaskAnalysis(task_type="bugfix", search_terms=["parser"])
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 8
    assert result.latency_seconds >= 0
    assert server.request_body["model"] == "Qwen/Qwen3-0.6B"
    assert server.request_body["max_tokens"] == 64
    assert server.request_body["response_format"]["json_schema"]["schema"] == TaskAnalysis.model_json_schema()


def test_sglang_client_maps_timeout_to_explicit_error():
    response = {
        "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
    }
    with completion_server(response, delay=0.1) as server:
        client = SGLangClient(base_url=f"http://127.0.0.1:{server.server_port}/v1", timeout=0.01)
        with pytest.raises(LocalModelTimeoutError, match="timed out"):
            client.complete("Analyze", TaskAnalysis)


def test_sglang_client_maps_connection_failure_to_explicit_error():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    client = SGLangClient(base_url=f"http://127.0.0.1:{port}/v1", timeout=0.1)
    with pytest.raises(LocalModelConnectionError, match="connect"):
        client.complete("Analyze", TaskAnalysis)


def test_sglang_client_rejects_truncated_completion_before_json_parsing():
    response = {
        "choices": [{"finish_reason": "length", "message": {"content": '{"task_type":'}}],
    }
    with completion_server(response) as server:
        client = SGLangClient(base_url=f"http://127.0.0.1:{server.server_port}/v1")
        with pytest.raises(LocalModelTruncatedOutputError, match="truncated"):
            client.complete("Analyze", TaskAnalysis)


def test_build_sglang_command_preserves_validated_4gb_profile_and_loopback_default():
    command = build_sglang_command("/models/Qwen3-0.6B")

    assert command == [
        "sglang",
        "serve",
        "--model-path",
        "/models/Qwen3-0.6B",
        "--host",
        "127.0.0.1",
        "--port",
        "30000",
        "--mem-fraction-static",
        "0.6",
        "--context-length",
        "4096",
        "--chunked-prefill-size",
        "512",
        "--cuda-graph-backend-decode",
        "disabled",
        "--cuda-graph-backend-prefill",
        "disabled",
        "--attention-backend",
        "triton",
        "--sampling-backend",
        "pytorch",
    ]


def test_check_sglang_verifies_models_and_structured_generation():
    response = {
        "choices": [{"finish_reason": "stop", "message": {"content": '{"ok":true}'}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }
    with completion_server(response) as server:
        health = check_sglang(f"http://127.0.0.1:{server.server_port}/v1", timeout=1)

    assert health.model_ids == ["Qwen/Qwen3-0.6B"]
    assert health.structured_generation is True
    assert health.prompt_tokens == 5
    assert health.completion_tokens == 3
