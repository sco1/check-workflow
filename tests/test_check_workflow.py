import datetime as dt
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pytest_mock import MockerFixture

from check_workflow.gh_api import Release
from check_workflow.workflow import (
    JobDependency,
    OutdatedDep,
    UsesSpec,
    extract_workflow_dependencies,
    fetch_local,
    report_outdated,
)

SPEC_FROM_RAW_TEST_CASES = (
    (
        "actions/setup-python@v6",
        UsesSpec(owner="actions", repo="setup-python", spec=SpecifierSet("~=6.0")),
    ),
    (
        "deadsnakes/action@v3.2.0",
        UsesSpec(owner="deadsnakes", repo="action", spec=SpecifierSet("~=3.2.0")),
    ),
)


@pytest.mark.parametrize(("raw_spec", "truth_out"), SPEC_FROM_RAW_TEST_CASES)
def test_spec_from_raw(raw_spec: str, truth_out: UsesSpec) -> None:
    spec = UsesSpec.from_raw(raw_spec)
    assert spec == truth_out


SAMPLE_WORKFLOW = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v6

    - name: Install dependencies
      run: uv sync --all-extras --dev

  test:
    steps:
    - name: Set up deadsnakes
      uses: deadsnakes/action@v3.2.0
"""

TRUTH_DEPENDENCIES = [
    JobDependency(job="lint", step_name=None, uses=UsesSpec.from_raw("actions/checkout@v4")),
    JobDependency(
        job="lint", step_name="Set up Python", uses=UsesSpec.from_raw("actions/setup-python@v6")
    ),
    JobDependency(
        job="test",
        step_name="Set up deadsnakes",
        uses=UsesSpec.from_raw("deadsnakes/action@v3.2.0"),
    ),
]


def test_extract_dependencies() -> None:
    extracted = extract_workflow_dependencies(SAMPLE_WORKFLOW)
    assert extracted == TRUTH_DEPENDENCIES


def test_report_outdated(mocker: MockerFixture) -> None:
    LATEST_RELEASES = (
        [Release(ver=Version("5.0"), published=dt.datetime.now(), url="")],  # checkout
        [Release(ver=Version("6.1"), published=dt.datetime.now(), url="")],  # setup-python
        [Release(ver=Version("3.2.0"), published=dt.datetime.now(), url="")],  # deadsnakes
    )
    WORKFLOWS = {"wf.yml": SAMPLE_WORKFLOW}
    TRUTH_OUTDATED = {
        "wf.yml": [OutdatedDep(spec=TRUTH_DEPENDENCIES[0], latest=LATEST_RELEASES[0][0])]
    }

    mocker.patch("check_workflow.workflow.fetch_releases", side_effect=LATEST_RELEASES)

    outdated = report_outdated(WORKFLOWS)
    assert outdated == TRUTH_OUTDATED


SAMPLE_WORKFLOW_REPEAT_DEP = """\
jobs:
  lint:
    steps:
    - uses: actions/checkout@v4

  test:
    steps:
    - uses: actions/checkout@v4
"""


def test_report_outdated_caches(mocker: MockerFixture) -> None:
    WORKFLOWS = {"wf.yml": SAMPLE_WORKFLOW_REPEAT_DEP}
    LATEST = [Release(ver=Version("5.0"), published=dt.datetime.now(), url="")]
    patched = mocker.patch("check_workflow.workflow.fetch_releases", return_value=LATEST)

    _ = report_outdated(WORKFLOWS)
    patched.assert_called_once()


def test_fetch_local(tmp_path: Path) -> None:
    YML_NAMES = {"abcd.yml", "another.yml"}
    for fn in YML_NAMES:
        (tmp_path / fn).touch()

    workflows = fetch_local(tmp_path)
    assert workflows.keys() == YML_NAMES
