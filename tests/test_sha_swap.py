import datetime as dt
import typing as t
from pathlib import Path

import pytest
from packaging.version import Version
from pytest_mock import MockerFixture

from check_workflow.gh_api import Release
from check_workflow.sha_swap import _fetch_all_latest, _gather_dependencies, swap_to_sha

SAMPLE_WORKFLOW_A = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v6

    - name: Install dependencies
      run: uv sync --all-extras --dev

    - name: Step with SHA
      uses: ooga/booga@8f4b7f84864484a7bf31766abe9204da3cbe65b3
"""

SAMPLE_WORKFLOW_B = """\
jobs:
  test:
    steps:
    - name: Set up deadsnakes
      uses: deadsnakes/action@v3.2.0
"""

SAMPLE_RAW_WORKFLOWS = {"a.yml": SAMPLE_WORKFLOW_A, "b.yml": SAMPLE_WORKFLOW_B}

TRUTH_GATHER = {
    ("actions", "checkout"),
    ("actions", "setup-python"),
    ("ooga", "booga"),
    ("deadsnakes", "action"),
}


def test_gather_dependencies() -> None:
    gathered = _gather_dependencies(SAMPLE_RAW_WORKFLOWS)
    assert gathered == TRUTH_GATHER


NOW = dt.datetime.now()


async def _mocked_fetch(**kwargs: dict[str, t.Any]) -> list[Release]:
    release_map = {
        ("actions", "checkout"): [
            Release(ver=Version("2.0.0"), published=NOW, url="", tag_hash=""),
            Release(ver=Version("1.0.0"), published=NOW, url="", tag_hash=""),
        ],
        ("actions", "setup-python"): [
            Release(ver=Version("3.0.0"), published=NOW, url="", tag_hash=""),
            Release(ver=Version("2.0.0"), published=NOW, url="", tag_hash=""),
        ],
        ("ooga", "booga"): [
            Release(ver=Version("4.0.0"), published=NOW, url="", tag_hash=""),
            Release(ver=Version("3.0.0"), published=NOW, url="", tag_hash=""),
        ],
        ("deadsnakes", "action"): [
            Release(ver=Version("5.0.0"), published=NOW, url="", tag_hash=""),
            Release(ver=Version("4.0.0"), published=NOW, url="", tag_hash=""),
        ],
    }

    return release_map[(kwargs["owner"], kwargs["repo_name"])]  # type: ignore[index]


@pytest.mark.asyncio
async def test_fetch_all_latest(mocker: MockerFixture) -> None:
    TRUTH_LATEST = {
        ("actions", "checkout"): Release(ver=Version("2.0.0"), published=NOW, url="", tag_hash=""),
        ("actions", "setup-python"): Release(
            ver=Version("3.0.0"), published=NOW, url="", tag_hash=""
        ),
        ("ooga", "booga"): Release(ver=Version("4.0.0"), published=NOW, url="", tag_hash=""),
        ("deadsnakes", "action"): Release(ver=Version("5.0.0"), published=NOW, url="", tag_hash=""),
    }
    mocker.patch("check_workflow.sha_swap.fetch_releases", side_effect=_mocked_fetch)

    latest = await _fetch_all_latest(session="", dependencies=TRUTH_GATHER, cooldown=None)  # type: ignore[arg-type]

    assert latest == TRUTH_LATEST


SAMPLE_SWAP_WORKFLOW = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v1.0.0

    - name: Set up Python
      uses: actions/setup-python@v2
"""

SAMPLE_SWAP_WORKFLOW_SWAP_TRUTH = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@abc123  # 1.0.0

    - name: Set up Python
      uses: actions/setup-python@def456  # 2.0.0
"""

SWAP_LATEST = {
    ("actions", "checkout"): Release(
        ver=Version("1.0.0"), published=NOW, url="", tag_hash="abc123"
    ),
    ("actions", "setup-python"): Release(
        ver=Version("2.0.0"), published=NOW, url="", tag_hash="def456"
    ),
}


def test_swap_to_sha(tmp_path: Path) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_SWAP_WORKFLOW)

    SWAP_WORKFLOWS = {"sample.yml": SAMPLE_SWAP_WORKFLOW}
    swap_to_sha(
        base_dir=tmp_path, raw_workflows=SWAP_WORKFLOWS, latest_releases=SWAP_LATEST, dry_run=False
    )
    assert SAMPLE_WF.read_text() == SAMPLE_SWAP_WORKFLOW_SWAP_TRUTH


def test_swap_to_sha_skip_empty_releases(tmp_path: Path) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_SWAP_WORKFLOW)

    SWAP_WORKFLOWS = {"sample.yml": SAMPLE_SWAP_WORKFLOW}
    swap_to_sha(base_dir=tmp_path, raw_workflows=SWAP_WORKFLOWS, latest_releases={}, dry_run=False)
    assert SAMPLE_WF.read_text() == SAMPLE_SWAP_WORKFLOW


TRUTH_DIFF = """\
Swapping all pins to SHA in sample.yml ...
--- sample.yml
+++
@@ -4 +4 @@
-    - uses: actions/checkout@v1.0.0
+    - uses: actions/checkout@abc123  # 1.0.0
@@ -7 +7 @@
-      uses: actions/setup-python@v2
+      uses: actions/setup-python@def456  # 2.0.0
"""


def test_swap_to_sha_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_SWAP_WORKFLOW)

    SWAP_WORKFLOWS = {"sample.yml": SAMPLE_SWAP_WORKFLOW}
    swap_to_sha(
        base_dir=tmp_path, raw_workflows=SWAP_WORKFLOWS, latest_releases=SWAP_LATEST, dry_run=True
    )
    assert SAMPLE_WF.read_text() == SAMPLE_SWAP_WORKFLOW

    captured = capsys.readouterr()
    assert captured.out == TRUTH_DIFF


SAMPLE_SWAP_WORKFLOW_SKIP_SHA = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3  # 0.5.0

    - name: Set up Python
      uses: actions/setup-python@7f4b7f84864484a7bf31766abe9204da3cbe65b3  # 1.0.0
"""


def test_swap_to_sha_skip_existing(tmp_path: Path) -> None:
    WF_NAME = "sample.yml"
    SAMPLE_WF = tmp_path / WF_NAME
    SAMPLE_WF.write_text(SAMPLE_SWAP_WORKFLOW_SKIP_SHA)

    SWAP_WORKFLOWS = {"sample.yml": SAMPLE_SWAP_WORKFLOW_SKIP_SHA}

    swap_to_sha(
        base_dir=tmp_path, raw_workflows=SWAP_WORKFLOWS, latest_releases=SWAP_LATEST, dry_run=False
    )
    assert SAMPLE_WF.read_text() == SAMPLE_SWAP_WORKFLOW_SKIP_SHA
