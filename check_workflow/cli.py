import argparse

from check_workflow.gh_api import fetch_workflows
from check_workflow.workflow import format_outdated, report_outdated


def _report_pipeline(org: str, repo: str, root: str, branch: str) -> None:
    workflows = fetch_workflows(owner=org, repo_name=repo, workflow_root=root, branch=branch)
    outdated = report_outdated(workflows)

    if outdated:
        print(format_outdated(outdated))


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(
        "CheckWorkflow", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("org", type=str, help="Query repository parent")
    parser.add_argument("repo", type=str, help="Query repository")
    parser.add_argument(
        "-r", "--root", type=str, default=".github/workflows/", help="Workflow root"
    )
    parser.add_argument("-b", "--branch", type=str, default="main", help="Query branch")

    args = parser.parse_args()
    _report_pipeline(org=args.org, repo=args.repo, root=args.root, branch=args.branch)


if __name__ == "__main__":
    main()
