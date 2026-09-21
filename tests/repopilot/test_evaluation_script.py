import subprocess
from pathlib import Path


def test_one_command_evaluation_script_is_valid_and_keeps_qwen_off_proxy():
    script = Path("scripts/run_controlled_evaluation.sh")

    result = subprocess.run(["bash", "-n", script], capture_output=True, text=True, check=False)
    content = script.read_text()

    assert result.returncode == 0, result.stderr
    assert "unset HTTP_PROXY HTTPS_PROXY ALL_PROXY" in content
    assert "NO_PROXY=127.0.0.1,localhost" in content
    assert "Qwen--Qwen3-0.6B/snapshots/master" in content
    assert "repopilot evaluate" in content
    assert "DEEPSEEK_API_KEY" in content
