import datetime as dt
import difflib
import logging
from pathlib import Path

from gql.client import AsyncClientSession
from ruamel.yaml import YAML

from check_workflow import WORKFLOW_T
from check_workflow.dep_bumper import SPEC_RE
from check_workflow.gh_api import Release, fetch_releases
from check_workflow.workflow import UsesSpec, extract_workflow_dependencies

LOGGER = logging.getLogger(__name__)


def _gather_dependencies(raw_workflows: WORKFLOW_T) -> set[tuple[str, str]]:
    """Extract a unified set of actions used by the provided workflows."""
    dependencies: set[tuple[str, str]] = set()  # Store as (owner, repo) tuples
    for wf in raw_workflows.values():
        wf_deps = extract_workflow_dependencies(wf)
        dependencies.update((d.uses.owner, d.uses.repo) for d in wf_deps)

    return dependencies


async def _fetch_all_latest(
    session: AsyncClientSession,
    dependencies: set[tuple[str, str]],
    cooldown: dt.timedelta | None,
) -> dict[tuple[str, str], Release]:
    """
    Fetch the latest release for each of the specified dependencies.

    If `cooldown` is specified, releases that are not older than the specified `timedelta` are
    skipped.
    """
    latest_releases: dict[tuple[str, str], Release] = {}
    for owner, repo in dependencies:
        latest = (
            await fetch_releases(
                session=session,
                owner=owner,
                repo_name=repo,
                cooldown=cooldown,
            )
        )[0]
        latest_releases[(owner, repo)] = latest

    return latest_releases


def swap_to_sha(
    base_dir: Path,
    raw_workflows: WORKFLOW_T,
    latest_releases: dict[tuple[str, str], Release],
    dry_run: bool,
) -> None:
    """
    Swap all version-pinned `uses` statements to the SHA pin of their specified latest version.

    NOTE: Existing comments inline with `uses:` specifications will be overwritten.
    """
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True

    for wf_name, wf in raw_workflows.items():
        print(f"Swapping all pins to SHA in {wf_name} ...")
        changed = False

        # Load YAML to track line numbers, make edits to source lines directly
        wf_filepath = base_dir / wf_name
        wf_data = yaml.load(wf)
        raw_lines = wf_filepath.read_text().splitlines()

        for j in wf_data["jobs"].values():
            for step in j["steps"]:
                uses = step.get("uses")
                if not uses:
                    continue

                spec = UsesSpec.from_raw(uses)
                latest = latest_releases.get((spec.owner, spec.repo), None)
                if latest is None:
                    LOGGER.debug(f"No release found for {spec.owner}/{spec.repo}")
                    continue

                if spec.sha is not None:
                    LOGGER.debug(f"{spec.owner}/{spec.repo} is already pinned to SHA")
                    continue

                LOGGER.debug(f"Pinning {spec.owner}/{spec.repo} to SHA")
                lineno, _ = step.lc.value("uses")
                new_uses = f"{spec.owner}/{spec.repo}@{latest.tag_hash}  # {latest.ver}"
                raw_lines[lineno] = SPEC_RE.sub(new_uses, raw_lines[lineno])
                changed = True

        if changed:
            if not dry_run:
                LOGGER.debug(f"Writing changes to {wf_name}")
                raw_lines.append("")  # Ensure file ends with a newline
                wf_filepath.write_text("\n".join(raw_lines))
            else:
                diff = difflib.unified_diff(
                    wf_filepath.read_text().splitlines(),  # Reload original lines
                    raw_lines,
                    fromfile=wf_name,
                    n=0,
                    lineterm="",
                )

                # Strip trailing whitespace to make testing easier
                print("\n".join(line.rstrip() for line in diff))
