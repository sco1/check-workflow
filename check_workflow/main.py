import datetime as dt
import os
import typing as t
from dataclasses import dataclass

from gql import Client, gql
from gql.transport.httpx import HTTPXTransport
from httpx import Timeout

TOK = os.environ.get("PUBLIC_PAT", "")

TIMEOUT = Timeout(5, read=15)  # Extend the read timeout a bit, keep the rest at default
TRANSPORT = HTTPXTransport(
    url="https://api.github.com/graphql",
    headers={"Authorization": f"bearer {TOK}"},
    timeout=TIMEOUT,
)
CLIENT = Client(transport=TRANSPORT, fetch_schema_from_transport=True)

RELEASE_QUERY = """
query GetLatestTag($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
        releases(orderBy: {field: CREATED_AT, direction: DESC}, first: 5) {
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
    tag_name: str
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
        return cls(
            tag_name=node["tagName"],
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
