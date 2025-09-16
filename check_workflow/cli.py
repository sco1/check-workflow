import argparse
from pathlib import Path

from check_workflow.gh_api import fetch_workflows
from check_workflow.workflow import fetch_local, format_outdated, report_outdated


def _remote_report_pipeline(org: str, repo: str, root: str, branch: str, markdown: bool) -> None:
    workflows = fetch_workflows(owner=org, repo_name=repo, workflow_root=root, branch=branch)
    outdated = report_outdated(workflows)

    if outdated:
        print(format_outdated(outdated, markdown=markdown))


def _local_report_pipeline(root: Path, markdown: bool) -> None:
    workflows = fetch_local(root)
    outdated = report_outdated(workflows)

    if outdated:
        print(format_outdated(outdated, markdown=markdown))


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
        "-m", "--markdown", action="store_true", help="Format report as markdown"
    )

    args = parser.parse_args()
    if args.subcommand == "local":
        _local_report_pipeline(root=args.root, markdown=args.markdown)
    else:
        _remote_report_pipeline(
            org=args.org,
            repo=args.repo,
            root=args.root,
            branch=args.branch,
            markdown=args.markdown,
        )


if __name__ == "__main__":
    main()
