import datetime as dt
import os
import typing as t
from dataclasses import dataclass

from gql import Client, gql
from gql.transport.httpx import HTTPXTransport
from httpx import Timeout
from packaging.version import Version

TOK = os.environ.get("PUBLIC_PAT", "")

TIMEOUT = Timeout(5, read=15)  # Extend the read timeout a bit, keep the rest at default
TRANSPORT = HTTPXTransport(
    url="https://api.github.com/graphql",
    headers={"Authorization": f"bearer {TOK}"},
    timeout=TIMEOUT,
)
CLIENT = Client(transport=TRANSPORT, fetch_schema_from_transport=True)

WORKFLOW_QUERY = """
query GetWorkflows($owner: String!, $repo: String!, $target: String!) {
    repository(owner: $owner, name: $repo) {
        object(expression: $target) {
            ... on Tree {
                entries {
                    name
                    object {
                        ... on Blob {
                        text
                        }
                    }
                }
            }
        }
    }
}
"""


def fetch_workflows(
    owner: str, repo_name: str, workflow_root: str = ".github/workflows/", branch: str = "main"
) -> dict[str, str]:
    query = gql(WORKFLOW_QUERY)
    query.variable_values = {
        "owner": owner,
        "repo": repo_name,
        "target": f"{branch}:{workflow_root}",
    }
    result = CLIENT.execute(query)

    raw_workflows = {}
    for wf in result["repository"]["object"]["entries"]:
        raw_workflows[wf["name"]] = wf["object"]["text"]

    return raw_workflows


RELEASE_QUERY = """
query GetLatestRelease($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
        releases(orderBy: {field: CREATED_AT, direction: DESC}, first: 1) {
            nodes {
                tagName
                publishedAt
                url
            }
        }
    }
}
"""


@dataclass(slots=True, frozen=True)
class Release:  # noqa: D101
    ver: Version
    published: dt.datetime
    url: str

    @classmethod
    def from_node(cls, node: dict) -> t.Self:
        """
        Build a `Release` instance from the provided node.

        The node is assumed to contain the following keys:
            * `"tagName"`
            * `"publishedAt"`
            * `"url"`
        """
        raw_ver = node["tagName"].removeprefix("v")
        return cls(
            ver=Version(raw_ver),
            published=dt.datetime.fromisoformat(node["publishedAt"]),
            url=node["url"],
        )


def fetch_releases(owner: str, repo_name: str) -> list[Release]:
    query = gql(RELEASE_QUERY)
    query.variable_values = {"owner": owner, "repo": repo_name}

    releases = []
    result = CLIENT.execute(query)
    for r in result["repository"]["releases"]["nodes"]:
        releases.append(Release.from_node(r))

    return releases
