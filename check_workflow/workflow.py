import typing as t
from collections import defaultdict

import yaml
from packaging.specifiers import SpecifierSet
from prettytable import PrettyTable, TableStyle

from check_workflow.gh_api import Release, fetch_releases


class UsesSpec(t.NamedTuple):  # noqa: D101
    owner: str
    repo: str
    spec: SpecifierSet

    @classmethod
    def from_raw(cls, raw_spec: str) -> t.Self:
        """
        Build a `UsesSpec` instance from the provided workflow dependency specification.

        Dependency specifications are assumed to be of the form `<user>/<repo>@<ver>`, for example:
            * `"actions/setup-python@v6"`
            * `"deadsnakes/action@v3.2.0"`

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


class OutdatedDep(t.NamedTuple):  # noqa: D101
    spec: JobDependency
    latest: Release


def report_outdated(raw_workflows: dict[str, str]) -> dict[str, list[OutdatedDep]]:
    """Parse the provided workflow files and return a per-file list of outdated dependencies."""
    # Cache latest release info to cut down on API calls; keyed by (owner, repo) tuples
    seen_releases: dict[tuple[str, str], Release] = {}

    outdated: dict[str, list[OutdatedDep]] = defaultdict(list)
    for wf_name, wf in raw_workflows.items():
        wf_deps = extract_workflow_dependencies(wf)
        for dep in wf_deps:
            cache_key = (dep.uses.owner, dep.uses.repo)
            if cache_key not in seen_releases:
                latest = fetch_releases(owner=dep.uses.owner, repo_name=dep.uses.repo)[0]
                seen_releases[cache_key] = latest
            else:
                latest = seen_releases[cache_key]

            if latest.ver not in dep.uses.spec:
                outdated[wf_name].append(OutdatedDep(spec=dep, latest=latest))

    return outdated


def format_outdated(outdated: dict[str, list[OutdatedDep]], markdown: bool = False) -> str:
    """
    Prettyprint the provided outdated dependencies into a table.

    If `markdown` is `True`, outdated dependencies are summarized into a markdown-styled table,
    otherwise the table is output in a terminal friendly form.
    """
    comps = []
    fields = ["Job", "Step Name", "Action", "Specified", "Latest"]
    for workflow, deps in outdated.items():
        if markdown:
            comps.append(f"### `{workflow}`")
        else:
            comps.append(f"{workflow}")

        table = PrettyTable()
        table.field_names = fields
        table.align = "c"

        if markdown:
            table.set_style(TableStyle.MARKDOWN)

        for dep in deps:
            action_string = f"{dep.spec.uses.owner}/{dep.spec.uses.repo}"
            table.add_row(
                [
                    dep.spec.job,
                    dep.spec.step_name,
                    action_string,
                    dep.spec.uses.spec,
                    dep.latest.ver,
                ]
            )

        comps.append(table.get_string())
        comps.append("")

    return "\n".join(comps)
