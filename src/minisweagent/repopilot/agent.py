from pathlib import Path
from typing import Any

from minisweagent import Environment, Model
from minisweagent.agents.default import AgentConfig, DefaultAgent
from minisweagent.repopilot.context import pack_context
from minisweagent.repopilot.index import build_repository_index
from minisweagent.repopilot.local_model import SGLangClient
from minisweagent.repopilot.retrieval import retrieve
from minisweagent.repopilot.task_analysis import TaskAnalysisOutcome, analyze_task, analyze_task_fallback


class RepoPilotAgentConfig(AgentConfig):
    repository_path: Path
    retrieval_enabled: bool = True
    local_analysis_enabled: bool = True
    context_budget_chars: int = 12_000
    local_model_base_url: str = "http://127.0.0.1:30000/v1"
    local_model_name: str = "Qwen/Qwen3-0.6B"
    local_model_timeout: float = 10


class RepoPilotAgent(DefaultAgent):
    config: RepoPilotAgentConfig

    def __init__(self, model: Model, env: Environment, **kwargs):
        super().__init__(model, env, config_class=RepoPilotAgentConfig, **kwargs)
        self.repopilot_info: dict[str, Any] = {}

    def _prepare_context(self, task: str) -> None:
        self.extra_template_vars["repopilot_context"] = ""
        self.repopilot_info = {"enabled": self.config.retrieval_enabled, "retrieved_files": []}
        if not self.config.retrieval_enabled:
            return
        index_result = build_repository_index(self.config.repository_path)
        if self.config.local_analysis_enabled:
            analysis = analyze_task(
                task,
                SGLangClient(
                    base_url=self.config.local_model_base_url,
                    model=self.config.local_model_name,
                    timeout=self.config.local_model_timeout,
                ),
            )
        else:
            analysis = TaskAnalysisOutcome(analysis=analyze_task_fallback(task), source="fallback")
        results = retrieve(index_result.index, analysis.analysis)
        context = pack_context(index_result.index, results, self.config.context_budget_chars)
        self.extra_template_vars["repopilot_context"] = context.text
        self.repopilot_info = {
            "enabled": True,
            "analysis_source": analysis.source,
            "analysis": analysis.analysis.model_dump(),
            "analysis_error_type": analysis.error_type,
            "index": {
                "indexed_files": index_result.indexed_files,
                "reused_files": index_result.reused_files,
                "warnings": index_result.warnings,
            },
            "retrieved_files": [result.model_dump() for result in results],
            "context": context.model_dump(),
        }

    def run(self, task: str = "", **kwargs) -> dict:
        self._prepare_context(task)
        return super().run(task, **kwargs)

    def serialize(self, *extra_dicts) -> dict:
        return super().serialize({"info": {"repopilot": self.repopilot_info}}, *extra_dicts)
