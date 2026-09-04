import datetime as dt
from pathlib import Path

from packaging.version import Version

from check_workflow.dep_bumper import bump_workflows
from check_workflow.gh_api import Release
from check_workflow.workflow import JobDependency, OutdatedDep, UsesSpec

SAMPLE_WORKFLOW = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v6
"""


# While bump_workflows won't be called unless there are outdated dependencies in at least one
# workflow, it might not need to touch all workflows so should check that an up-to-date workflow
# passes through
def test_bump_workflows_no_change(tmp_path: Path) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_WORKFLOW)

    OUTDATED: dict[str, list[OutdatedDep]] = {WF_NAME: []}
    bump_workflows(base_dir=tmp_path, outdated=OUTDATED, use_sha=False)
    assert SAMPLE_WF.read_text() == SAMPLE_WORKFLOW

    bump_workflows(base_dir=tmp_path, outdated=OUTDATED, use_sha=True)
    assert SAMPLE_WF.read_text() == SAMPLE_WORKFLOW


SAMPLE_WORKFLOW_SINGLE_BUMP_TRUTH = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v6.0.0

    - name: Set up Python
      uses: actions/setup-python@v6
"""

SAMPLE_WORKFLOW_SINGLE_BUMP_TRUTH_SHA = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@abc123  # 6.0.0

    - name: Set up Python
      uses: actions/setup-python@v6
"""

SINGLE_BUMP_OUTDATED_VER = [
    OutdatedDep(
        spec=JobDependency(
            job="lint",
            step_name=None,
            uses=UsesSpec.from_raw("actions/checkout@v4"),
        ),
        latest=Release(
            ver=Version("6.0.0"), published=dt.datetime.now(), url="a.b.c", tag_hash="abc123"
        ),
    )
]


def test_single_bump_ver(tmp_path: Path) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_WORKFLOW)

    OUTDATED = {WF_NAME: SINGLE_BUMP_OUTDATED_VER}

    bump_workflows(base_dir=tmp_path, outdated=OUTDATED, use_sha=False)
    assert SAMPLE_WF.read_text() == SAMPLE_WORKFLOW_SINGLE_BUMP_TRUTH


def test_single_bump_sha(tmp_path: Path) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_WORKFLOW)

    OUTDATED = {WF_NAME: SINGLE_BUMP_OUTDATED_VER}

    bump_workflows(base_dir=tmp_path, outdated=OUTDATED, use_sha=True)
    assert SAMPLE_WF.read_text() == SAMPLE_WORKFLOW_SINGLE_BUMP_TRUTH_SHA


SAMPLE_WORKFLOW_WITH_COMMENT = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v4  # Retain comment

    - name: Set up Python
      uses: actions/setup-python@v6
"""

SAMPLE_WORKFLOW_BUMPED_WITH_COMMENT = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v6.0.0  # Retain comment

    - name: Set up Python
      uses: actions/setup-python@v6
"""


def test_bump_retain_comment(tmp_path: Path) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_WORKFLOW_WITH_COMMENT)

    OUTDATED = {WF_NAME: SINGLE_BUMP_OUTDATED_VER}

    bump_workflows(base_dir=tmp_path, outdated=OUTDATED, use_sha=False)
    assert SAMPLE_WF.read_text() == SAMPLE_WORKFLOW_BUMPED_WITH_COMMENT
