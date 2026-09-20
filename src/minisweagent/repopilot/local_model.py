import json
import re
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

import requests
from pydantic import BaseModel, ValidationError

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LocalModelError(RuntimeError):
    pass


class MalformedStructuredOutputError(LocalModelError):
    pass


class LocalModelTimeoutError(LocalModelError):
    pass


class LocalModelConnectionError(LocalModelError):
    pass


class LocalModelTruncatedOutputError(LocalModelError):
    pass


@dataclass(frozen=True)
class LocalModelResult(Generic[SchemaT]):
    value: SchemaT
    latency_seconds: float
    prompt_tokens: int | None
    completion_tokens: int | None


@dataclass(frozen=True)
class SGLangClient:
    base_url: str = "http://127.0.0.1:30000/v1"
    model: str = "Qwen/Qwen3-0.6B"
    timeout: float = 10

    def complete(self, prompt: str, schema: type[SchemaT], max_tokens: int = 256) -> LocalModelResult[SchemaT]:
        started_at = time.perf_counter()
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
                    },
                },
                timeout=self.timeout,
            )
        except requests.Timeout as error:
            raise LocalModelTimeoutError(f"Local model request timed out after {self.timeout} seconds") from error
        except requests.ConnectionError as error:
            raise LocalModelConnectionError(f"Could not connect to local model at {self.base_url}") from error
        response.raise_for_status()
        body = response.json()
        if body["choices"][0].get("finish_reason") == "length":
            raise LocalModelTruncatedOutputError(f"Local model output was truncated at {max_tokens} tokens")
        usage = body.get("usage", {})
        return LocalModelResult(
            value=parse_structured_output(body["choices"][0]["message"]["content"], schema),
            latency_seconds=time.perf_counter() - started_at,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )


def parse_structured_output(content: str, schema: type[SchemaT]) -> SchemaT:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", content):
        try:
            value, _ = decoder.raw_decode(content, match.start())
            return schema.model_validate(value)
        except (json.JSONDecodeError, ValidationError):
            continue
    raise MalformedStructuredOutputError("Response does not contain valid structured output")
