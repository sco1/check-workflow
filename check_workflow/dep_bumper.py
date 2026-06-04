from pathlib import Path

from ruamel.yaml import YAML

from check_workflow.workflow import OutdatedDep, UsesSpec


def bump_workflows(base_dir: Path, outdated: dict[str, list[OutdatedDep]], use_sha: bool) -> None:
    """
    Use the provided collection of outdated dependencies to bump the containing workflow files.

    If `use_sha` is `True`, then the dependency will be pinned using the hash of the latest release,
    with the corresponding version commented alongside. Otherwise the dependency will be pinned to
    the full version specification.
    """
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True

    for wf_name, deps in outdated.items():
        dep_lookup = {(d.spec.uses.owner, d.spec.uses.repo): d.latest for d in deps}

        wf = base_dir / wf_name
        wf_data = yaml.load(wf)

        for j in wf_data["jobs"].values():
            for step in j["steps"]:
                uses = step.get("uses")
                if not uses:
                    continue

                spec = UsesSpec.from_raw(uses)
                latest = dep_lookup.get((spec.owner, spec.repo), None)
                if latest is None:
                    continue

                action_base = f"{spec.owner}/{spec.repo}@"
                if use_sha:
                    step["uses"] = f"{action_base}{latest.tag_hash}"
                    step.yaml_add_eol_comment(f"v{latest.ver}", key="uses")
                else:
                    step["uses"] = f"{action_base}v{latest.ver}"

        with wf.open("w") as f:
            yaml.dump(wf_data, f)
