from typer.testing import CliRunner

from minisweagent.repopilot.cli import app, build_safe_run_args, prepare_workspace


def test_cli_exposes_explicit_run_subcommand():
    root = CliRunner().invoke(app, ["--help"])
    result = CliRunner().invoke(app, ["run", "--help"])

    assert root.exit_code == 0
    assert "Commands" in root.stdout
    assert "run" in root.stdout
    assert result.exit_code == 0
    assert "--repo" in result.stdout


def test_prepare_workspace_copies_source_but_excludes_git_secrets_and_agent_artifacts(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('safe')\n")
    (source / ".env").write_text("GEMINI_API_KEY=secret\n")
    (source / "service-account.json").write_text("{}")
    (source / ".git").mkdir()
    (source / ".git" / "config").write_text("remote secret")
    (source / ".codex").mkdir()
    (source / ".codex" / "state.json").write_text("{}")
    destination = tmp_path / "run" / "workspace"

    prepare_workspace(source, destination)

    assert (destination / "app.py").read_text() == "print('safe')\n"
    assert not (destination / ".env").exists()
    assert not (destination / "service-account.json").exists()
    assert not (destination / ".git").exists()
    assert not (destination / ".codex").exists()


def test_safe_agent_container_args_mount_only_workspace_and_do_not_forward_credentials(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    args = build_safe_run_args(workspace, uid=1000, gid=1000)
    joined = " ".join(args)

    assert "--network none" in joined
    assert "--user 1000:1000" in joined
    assert "--memory 1g" in joined
    assert "--cpus 1.0" in joined
    assert "--pids-limit 128" in joined
    assert f"{workspace.resolve()}:/workspace" in joined
    assert "GEMINI_API_KEY" not in joined
    assert "--env" not in joined
