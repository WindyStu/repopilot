from minisweagent.agents import get_agent_class
from minisweagent.repopilot.agent import RepoPilotAgent


class StaticModel:
    def format_message(self, **kwargs):
        return kwargs

    def get_template_vars(self, **kwargs):
        return {}

    def serialize(self):
        return {}


class StaticEnvironment:
    def get_template_vars(self, **kwargs):
        return {}

    def serialize(self):
        return {}


class OneStepRepoPilotAgent(RepoPilotAgent):
    def step(self):
        return self.add_messages(
            {
                "role": "exit",
                "content": "done",
                "extra": {"exit_status": "Submitted", "submission": "done"},
            }
        )


def test_repopilot_agent_is_available_by_short_name():
    assert get_agent_class("repopilot") is RepoPilotAgent


def make_agent(repository, retrieval_enabled):
    return OneStepRepoPilotAgent(
        model=StaticModel(),
        env=StaticEnvironment(),
        system_template="System",
        instance_template=(
            "Task: {{task}}"
            "{% if repopilot_context %}\n\nRetrieved context:\n{{repopilot_context}}{% endif %}"
        ),
        repository_path=repository,
        retrieval_enabled=retrieval_enabled,
        local_analysis_enabled=False,
        context_budget_chars=1_000,
    )


def test_repopilot_agent_baseline_mode_preserves_upstream_style_initial_messages(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "parser.py").write_text("def parse_value(value):\n    return value\n")
    agent = make_agent(repository, retrieval_enabled=False)

    agent.run("Fix parse_value")

    assert agent.messages[:2] == [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Task: Fix parse_value"},
    ]
    assert agent.serialize()["info"]["repopilot"]["enabled"] is False


def test_repopilot_agent_injects_retrieved_context_and_evidence_without_cross_run_leaks(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "parser.py").write_text("def parse_value(value):\n    return int(value)\n")
    agent = make_agent(repository, retrieval_enabled=True)

    agent.run("Fix parse_value in parser.py")

    assert "Retrieved context:\n### parser.py:1-2" in agent.messages[1]["content"]
    assert "def parse_value(value):" in agent.messages[1]["content"]
    info = agent.serialize()["info"]["repopilot"]
    assert info["enabled"] is True
    assert info["analysis_source"] == "fallback"
    assert info["retrieved_files"][0]["path"] == "parser.py"
    assert info["context"]["used_chars"] <= 1_000

    agent.run("Discuss quantum zebra")

    assert agent.messages[1]["content"] == "Task: Discuss quantum zebra"
    assert agent.serialize()["info"]["repopilot"]["retrieved_files"] == []
