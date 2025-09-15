import typing as t

import yaml
from packaging.specifiers import SpecifierSet


class UsesSpec(t.NamedTuple):  # noqa: D101
    owner: str
    repo: str
    spec: SpecifierSet

    @classmethod
    def from_raw(cls, raw_spec: str) -> t.Self:
        """
        Build a `UsesSpec` instance from the provided workflow dependency specification.

        Dependency specifications are assumed to be of the form `<user>/<repo>@<ver>`, for example:
            * `actions/setup-python@v6`
            * `deadsnakes/action@v3.2.0`

        The resulting instance's `spec` attribute is built using a compatible release clause (`~=`).
        """
        action, raw_ver = raw_spec.split("@")
        *_, raw_ver = raw_ver.split("/")  # May use a branch, which we don't care about
        raw_ver = raw_ver.removeprefix("v")  # Some repos may prefix their tags
        owner, repo = action.split("/")

        if len(raw_ver.split(".")) == 1:
            # Major-only version spec needs special handling, otherwise SpecifierSet will raise
            spec = SpecifierSet(f"~={raw_ver}.0")
        else:
            spec = SpecifierSet(f"~={raw_ver}")

        return cls(owner=owner, repo=repo, spec=spec)


class JobDependency(t.NamedTuple):  # noqa: D101
    job: str
    step_name: str | None
    uses: UsesSpec


def extract_workflow_dependencies(raw_workflow: str) -> list[JobDependency]:
    """Extract job dependencies from the provided raw workflow YAML."""
    loaded = yaml.safe_load(raw_workflow)

    extracted_dependencies = []
    for job, job_params in loaded["jobs"].items():
        for step in job_params["steps"]:
            uses = step.get("uses", None)

            if uses:
                extracted_dependencies.append(
                    JobDependency(
                        job=job,
                        step_name=step.get("name", None),
                        uses=UsesSpec.from_raw(uses),
                    )
                )

    return extracted_dependencies
