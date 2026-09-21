import json
import subprocess
from dataclasses import dataclass

import typer
from pydantic import BaseModel

from minisweagent.repopilot.local_model import SGLangClient, local_http_session


class _HealthResponse(BaseModel):
    ok: bool


@dataclass(frozen=True)
class HealthCheckResult:
    model_ids: list[str]
    structured_generation: bool
    prompt_tokens: int | None
    completion_tokens: int | None


def build_sglang_command(
    model_path: str = "Qwen/Qwen3-0.6B",
    host: str = "127.0.0.1",
    port: int = 30_000,
) -> list[str]:
    return [
        "sglang",
        "serve",
        "--model-path",
        model_path,
        "--host",
        host,
        "--port",
        str(port),
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


def check_sglang(base_url: str = "http://127.0.0.1:30000/v1", timeout: float = 10) -> HealthCheckResult:
    with local_http_session() as session:
        response = session.get(f"{base_url.rstrip('/')}/models", timeout=timeout)
    response.raise_for_status()
    model_ids = [model["id"] for model in response.json()["data"]]
    generation = SGLangClient(base_url=base_url, model=model_ids[0], timeout=timeout).complete(
        "Return only this JSON object: {\"ok\": true}",
        _HealthResponse,
        max_tokens=16,
    )
    return HealthCheckResult(
        model_ids=model_ids,
        structured_generation=generation.value.ok,
        prompt_tokens=generation.prompt_tokens,
        completion_tokens=generation.completion_tokens,
    )


app = typer.Typer(help="Run and validate RepoPilot's local Qwen3-0.6B SGLang service.")


@app.command()
def serve(
    model_path: str = typer.Option("Qwen/Qwen3-0.6B", help="SGLang model id or local snapshot path."),
    host: str = typer.Option("127.0.0.1", help="Bind address. Use 0.0.0.0 only when external access is intended."),
    port: int = typer.Option(30_000),
) -> None:
    subprocess.run(build_sglang_command(model_path, host, port), check=True)


@app.command()
def health(
    base_url: str = typer.Option("http://127.0.0.1:30000/v1"),
    timeout: float = typer.Option(10),
) -> None:
    print(json.dumps(check_sglang(base_url, timeout).__dict__, indent=2))
