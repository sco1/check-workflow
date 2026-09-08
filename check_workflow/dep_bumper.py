import difflib
import logging
import re
from pathlib import Path

from ruamel.yaml import YAML

from check_workflow.workflow import OutdatedDep, UsesSpec

LOGGER = logging.getLogger(__name__)

SPEC_RE = re.compile(r"(?P<spec>[^'\"\s]+)(?P<comment>[ \t]*(?:#.*)?)$")


def bump_workflows(
    base_dir: Path,
    outdated: dict[str, list[OutdatedDep]],
    use_sha: bool,
    dry_run: bool,
) -> None:
    """
    Use the provided collection of outdated dependencies to bump the containing workflow files.

    If `use_sha` is `True`, then the dependency will be pinned using the hash of the latest release,
    with the corresponding version commented alongside. Otherwise, the dependency will be pinned to
    the full version specification.

    NOTE: Existing comments inline with `uses:` specifications being bumped will be preserved only
    if `use_sha` is `False`.
    """
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True

    for wf_name, deps in outdated.items():
        print(f"Bumping dependencies in {wf_name}...")
        changed = False
        dep_lookup = {(d.spec.uses.owner, d.spec.uses.repo): d.latest for d in deps}

        # Load YAML to track line numbers, make edits to source lines directly
        wf = base_dir / wf_name
        wf_data = yaml.load(wf)
        raw_lines = wf.read_text().splitlines()

        for j in wf_data["jobs"].values():
            for step in j["steps"]:
                uses = step.get("uses")
                if not uses:
                    continue

                spec = UsesSpec.from_raw(uses)
                latest = dep_lookup.get((spec.owner, spec.repo), None)
                if latest is None:
                    continue

                LOGGER.debug(f"Bumping {spec.owner}/{spec.repo} to {latest.ver}")
                lineno, _ = step.lc.value("uses")
                if use_sha:
                    new_uses = f"{spec.owner}/{spec.repo}@{latest.tag_hash}  # {latest.ver}"
                else:
                    new_uses = f"{spec.owner}/{spec.repo}@v{latest.ver}"

                    # Pull regex match so we can use the existing comment
                    match = SPEC_RE.search(raw_lines[lineno])
                    comment = match.group("comment") if match else None

                    if comment:
                        new_uses = f"{new_uses}{comment}"

                raw_lines[lineno] = SPEC_RE.sub(new_uses, raw_lines[lineno])
                changed = True

        if changed:
            if not dry_run:
                LOGGER.debug(f"Writing changes to {wf_name}")
                raw_lines.append("")  # Ensure file ends with a newline
                wf.write_text("\n".join(raw_lines))
            else:
                diff = difflib.unified_diff(
                    wf.read_text().splitlines(),  # Could just stash up above, but this is fine
                    raw_lines,
                    fromfile=wf_name,
                    n=0,
                    lineterm="",
                )

                # Strip trailing whitespace to make testing easier
                print("\n".join(line.rstrip() for line in diff))
