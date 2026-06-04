import argparse
import asyncio
import datetime as dt
from pathlib import Path

from check_workflow.dep_bumper import bump_workflows
from check_workflow.gh_api import CLIENT, fetch_workflows, parse_cooldown
from check_workflow.workflow import fetch_local, format_outdated, report_outdated


async def _remote_report_pipeline(
    org: str, repo: str, root: str, branch: str, cooldown: dt.timedelta | None, markdown: bool
) -> None:
    async with CLIENT as session:
        workflows = await fetch_workflows(
            session=session,
            owner=org,
            repo_name=repo,
            workflow_root=root,
            branch=branch,
        )
        if not workflows:
            print(f"No workflows found at the provided root: {root}")
            return

        outdated = await report_outdated(session, workflows, cooldown)

    if outdated:
        print(format_outdated(outdated, markdown=markdown))


async def _local_report_pipeline(root: Path, cooldown: dt.timedelta | None, markdown: bool) -> None:
    workflows = fetch_local(root)
    if not workflows:
        print(f"No workflows found at the provided root: {root}")
        return

    async with CLIENT as session:
        outdated = await report_outdated(session, workflows, cooldown)

    if outdated:
        print(format_outdated(outdated, markdown=markdown))


async def _local_bump_pipeline(root: Path, cooldown: dt.timedelta | None, use_sha: bool) -> None:
    workflows = fetch_local(root)
    if not workflows:
        print(f"No workflows found at the provided root: {root}")
        return

    # While this approach does hit each workfile twice, it seems more straighforward to just reuse
    # the existing caching logic since our time is pretty likely to be dominated by network calls. I
    # don't think it's worth trying to be clever here.
    async with CLIENT as session:
        outdated = await report_outdated(session, workflows, cooldown)

    if outdated:
        bump_workflows(base_dir=root, outdated=outdated, use_sha=use_sha)


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser("CheckWorkflow")
    subparsers = parser.add_subparsers(dest="subcommand")

    # Query local project
    local_sub = subparsers.add_parser(
        "local", help="Query local project", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    local_sub.add_argument(
        "-r", "--root", type=Path, default="./.github/workflows/", help="Workflow root"
    )
    local_sub.add_argument(
        "-c", "--cooldown", type=str, default=None, help="Dependency cooldown period, as PnD"
    )
    local_sub.add_argument(
        "-m", "--markdown", action="store_true", help="Format report as markdown"
    )

    # Query remote repo
    remote_sub = subparsers.add_parser(
        "remote",
        help="Query remote repository",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    remote_sub.add_argument("org", type=str, help="Query repository parent")
    remote_sub.add_argument("repo", type=str, help="Query repository")
    remote_sub.add_argument("-b", "--branch", type=str, default="main", help="Query branch")
    remote_sub.add_argument(
        "-r", "--root", type=str, default=".github/workflows/", help="Workflow root"
    )
    remote_sub.add_argument(
        "-c", "--cooldown", type=str, default=None, help="Dependency cooldown period, as PnD"
    )
    remote_sub.add_argument(
        "-m", "--markdown", action="store_true", help="Format report as markdown"
    )

    # Dependency bumper
    bump_sub = subparsers.add_parser(
        "bump",
        help="Bump local workflow dependencies",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    bump_sub.add_argument(
        "-r", "--root", type=Path, default="./.github/workflows/", help="Workflow root"
    )
    bump_sub.add_argument("--sha", action="store_true", help="Pin to SHA")
    bump_sub.add_argument(
        "-c", "--cooldown", type=str, default=None, help="Dependency cooldown period, as PnD"
    )

    args = parser.parse_args()

    if args.cooldown is not None:
        cooldown = parse_cooldown(args.cooldown)
    else:
        cooldown = None

    if args.subcommand == "local":
        asyncio.run(
            _local_report_pipeline(root=args.root, cooldown=cooldown, markdown=args.markdown)
        )
    elif args.subcommand == "bump":
        asyncio.run(_local_bump_pipeline(root=args.root, cooldown=cooldown, use_sha=args.sha))
    else:
        asyncio.run(
            _remote_report_pipeline(
                org=args.org,
                repo=args.repo,
                root=args.root,
                branch=args.branch,
                cooldown=cooldown,
                markdown=args.markdown,
            )
        )


if __name__ == "__main__":
    main()
