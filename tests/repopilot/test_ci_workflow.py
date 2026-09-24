import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_pytest_workflow_collects_only_the_maintained_test_suite():
    workflow = (REPOSITORY_ROOT / ".github/workflows/pytest.yaml").read_text()
    run_step = workflow.split("- name: Run pytest", maxsplit=1)[1].split("- name:", maxsplit=1)[0]

    assert re.search(r"(?:^|\s)tests/?(?:\s|$)", run_step), (
        "The CI pytest command must target tests/ explicitly so benchmark and example fixtures are not collected."
    )
