import pytest
from packaging.specifiers import SpecifierSet

from check_workflow.workflow import JobDependency, UsesSpec, extract_workflow_dependencies

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
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v6
      with:
        python-version-file: "pyproject.toml"

    - name: Install dependencies
      run: uv sync --all-extras --dev

  test:
    steps:
    - name: Set up (deadsnakes) Python ${{ matrix.python-version }}
      uses: deadsnakes/action@v3.2.0
      if: endsWith(matrix.python-version, '-dev')
      with:
        python-version: ${{ matrix.python-version }}
"""

TRUTH_DEPENDENCIES = [
    JobDependency(job="lint", step_name=None, uses=UsesSpec.from_raw("actions/checkout@v4")),
    JobDependency(
        job="lint", step_name="Set up Python", uses=UsesSpec.from_raw("actions/setup-python@v6")
    ),
    JobDependency(
        job="test",
        step_name="Set up (deadsnakes) Python ${{ matrix.python-version }}",
        uses=UsesSpec.from_raw("deadsnakes/action@v3.2.0"),
    ),
]


def test_extract_dependencies() -> None:
    extracted = extract_workflow_dependencies(SAMPLE_WORKFLOW)
    assert extracted == TRUTH_DEPENDENCIES
