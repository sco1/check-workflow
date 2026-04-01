import datetime as dt
import operator
import os
import platform
import typing as t
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv
from gql import Client
from gql import __version__ as __gql_ver__
from gql import gql
from gql.client import AsyncClientSession
from gql.transport.httpx import HTTPXAsyncTransport
from httpx import Timeout
from packaging.version import Version

from check_workflow import WORKFLOW_T, __url__, __version__

load_dotenv()
TOK = os.environ.get("PUBLIC_PAT", "")

TIMEOUT = Timeout(5, read=15)  # Extend the read timeout a bit, keep the rest at default
USER_AGENT = (
    f"check-workflow/{__version__} ({__url__}) "
    f"gql/{__gql_ver__} "
    f"httpx/{httpx.__version__} "
    f"{platform.python_implementation()}/{platform.python_version()}"
)
TRANSPORT = HTTPXAsyncTransport(
    url="https://api.github.com/graphql",
    headers={"Authorization": f"bearer {TOK}", "User-Agent": USER_AGENT},
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


async def fetch_workflows(
    session: AsyncClientSession,
    owner: str,
    repo_name: str,
    workflow_root: str = ".github/workflows/",
    branch: str = "main",
) -> WORKFLOW_T:
    """
    Fetch all workflow files for the query API using GH's GraphQL API.

    The return is a dictionary of <filename>:<file contents> items.
    """
    if not TOK:
        raise RuntimeError("No API token available")

    query = gql(WORKFLOW_QUERY)
    query.variable_values = {
        "owner": owner,
        "repo": repo_name,
        "target": f"{branch}:{workflow_root}",
    }
    result = await session.execute(query)

    raw_workflows = {}
    for wf in result["repository"]["object"]["entries"]:
        raw_workflows[wf["name"]] = wf["object"]["text"]

    return raw_workflows


RELEASE_QUERY = """
query GetLatestReleases($owner: String!, $repo: String!, $n_latest: Int!) {
    repository(owner: $owner, name: $repo) {
        releases(orderBy: {field: CREATED_AT, direction: DESC}, first: $n_latest) {
            nodes {
                tagName
                publishedAt
                url
                tagCommit { oid }
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
    tag_hash: str

    @classmethod
    def from_node(cls, node: dict) -> t.Self:
        """
        Build a `Release` instance from the provided node.

        The node is assumed to contain the following keys:
            * `"tagName"`
            * `"publishedAt"`
            * `"url"`
            * `"tagCommit"` - nested dict with `"oid"` key
        """
        raw_ver = node["tagName"].removeprefix("v")
        return cls(
            ver=Version(raw_ver),
            published=dt.datetime.fromisoformat(node["publishedAt"]),
            url=node["url"],
            tag_hash=node["tagCommit"]["oid"],
        )


async def fetch_releases(
    session: AsyncClientSession,
    owner: str,
    repo_name: str,
    n_latest: int = 5,
) -> list[Release]:
    """
    Fetch the `n_latest` most recent releases from the query repo using GH's GraphQL API.

    NOTE: Releases are sorted in version order, descending.
    """
    if not TOK:
        raise RuntimeError("No API token available")

    query = gql(RELEASE_QUERY)
    query.variable_values = {"owner": owner, "repo": repo_name, "n_latest": n_latest}

    releases = []
    result = await session.execute(query)
    for r in result["repository"]["releases"]["nodes"]:
        releases.append(Release.from_node(r))

    releases.sort(key=operator.attrgetter("ver"), reverse=True)
    return releases
