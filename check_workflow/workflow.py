import string
import typing as t
from collections import defaultdict
from pathlib import Path

import yaml
from gql.client import AsyncClientSession
from packaging.specifiers import SpecifierSet
from prettytable import PrettyTable, TableStyle

from check_workflow import WORKFLOW_T
from check_workflow.gh_api import Release, fetch_releases


class UsesSpec(t.NamedTuple):  # noqa: D101
    owner: str
    repo: str
    spec: SpecifierSet | None
    sha: str | None

    @classmethod
    def from_raw(cls, raw_spec: str) -> t.Self:
        """
        Build a `UsesSpec` instance from the provided workflow dependency specification.

        Dependency specifications are assumed to be of the form `<user>/<repo>@<ver>` or a full SHA
        hash, e.g. :
            * `"actions/setup-python@v6"`
            * `"deadsnakes/action@v3.2.0"`
            * `"actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3"`

        If a version specifier is used, the resulting instance's `spec` attribute is built using a
        compatible release clause (`~=`) and the `sha` attribute will be `None`. Otherwise, `spec`
        will be `None` and `sha` will be the pinned SHA.
        """
        action, raw_ver = raw_spec.split("@")
        *_, raw_ver = raw_ver.split("/")  # May use a branch, which we don't care about
        owner, repo = action.split("/")

        # Discriminate between version pin and SHA
        if len(raw_ver) == 40 and all(c in string.hexdigits for c in raw_ver):
            spec = None
            sha = raw_ver
        else:
            sha = None
            raw_ver = raw_ver.removeprefix("v")  # Some repos may prefix their tags

            if len(raw_ver.split(".")) == 1:
                # Major-only version spec needs special handling, otherwise SpecifierSet will raise
                spec = SpecifierSet(f"~={raw_ver}.0")
            else:
                spec = SpecifierSet(f"~={raw_ver}")

        return cls(owner=owner, repo=repo, spec=spec, sha=sha)


class JobDependency(t.NamedTuple):  # noqa: D101
    job: str
    step_name: str | None
    uses: UsesSpec


def extract_workflow_dependencies(raw_workflow: str) -> list[JobDependency]:
    """
    Extract job dependencies from the provided raw workflow YAML.

    NOTE: Only versioned actions are considered. Other specifications, such as local or docker
    actions, are skipped.
    """
    loaded = yaml.safe_load(raw_workflow)

    extracted_dependencies = []
    for job, job_params in loaded["jobs"].items():
        for step in job_params["steps"]:
            uses = step.get("uses", None)

            if uses is None:
                continue

            if uses.startswith("docker"):
                continue
            elif uses.startswith("./") or uses.startswith("../"):
                continue

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


async def report_outdated(
    session: AsyncClientSession, raw_workflows: WORKFLOW_T
) -> dict[str, list[OutdatedDep]]:
    """Parse the provided workflow files and return a per-file list of outdated dependencies."""
    # Cache latest release info to cut down on API calls; keyed by (owner, repo) tuples
    seen_releases: dict[tuple[str, str], Release] = {}

    outdated: dict[str, list[OutdatedDep]] = defaultdict(list)
    for wf_name, wf in raw_workflows.items():
        wf_deps = extract_workflow_dependencies(wf)
        for dep in wf_deps:
            cache_key = (dep.uses.owner, dep.uses.repo)
            if cache_key not in seen_releases:
                latest = (
                    await fetch_releases(
                        session=session, owner=dep.uses.owner, repo_name=dep.uses.repo
                    )
                )[0]
                seen_releases[cache_key] = latest
            else:
                latest = seen_releases[cache_key]

            # Switch behavior based on whether we've pinned a version vs. SHA
            # If sha is None then spec is defined & vice-versa; since this is the only place this
            # comparison happens we can go with this assumption vs. adding more narrowing logic
            is_outdated = False
            if dep.uses.sha is None:
                if latest.ver not in dep.uses.spec:  # type: ignore[operator]
                    is_outdated = True
            else:
                if latest.tag_hash != dep.uses.sha:
                    is_outdated = True

            if is_outdated:
                outdated[wf_name].append(OutdatedDep(spec=dep, latest=latest))

    return outdated


def format_outdated(
    outdated: dict[str, list[OutdatedDep]], markdown: bool = False
) -> str:  # pragma: no cover
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

            # If spec is None then SHA is defined & vice-versa
            if dep.spec.uses.spec is not None:
                uses_spec = dep.spec.uses.spec
                latest_spec = dep.latest.ver
            else:
                uses_spec = dep.spec.uses.sha[:7]  # type: ignore[index,assignment]
                latest_spec = dep.latest.tag_hash[:7]  # type: ignore[assignment]

            table.add_row(
                [
                    dep.spec.job,
                    dep.spec.step_name,
                    action_string,
                    uses_spec,
                    latest_spec,
                ]
            )

        comps.append(table.get_string())
        comps.append("")

    return "\n".join(comps)


def fetch_local(base_dir: Path) -> WORKFLOW_T:
    """Parse all `*.yml` files present in the specified base directory."""
    workflows = {}
    for yml in base_dir.glob("*.yml", case_sensitive=False):
        workflows[yml.name] = yml.read_text()

    return workflows
