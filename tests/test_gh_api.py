import datetime as dt
import json

import pytest
from packaging.version import Version
from pytest_mock import MockerFixture

from check_workflow.gh_api import Release, fetch_releases, fetch_workflows
from tests import SAMPLE_DATA_DIR


@pytest.mark.asyncio
async def test_fetch_workflows(mocker: MockerFixture) -> None:
    SAMPLE_RESPONSE = SAMPLE_DATA_DIR / "workflow_query.json"
    with SAMPLE_RESPONSE.open("r") as f:
        resp = json.load(f)

    mock_session = mocker.AsyncMock()
    mock_session.execute.return_value = resp

    workflows = await fetch_workflows(
        session=mock_session, owner="sco1", repo_name="flake8_annotations"
    )
    assert workflows.keys() == {"lint_test.yml", "pypi_release.yml"}


@pytest.mark.asyncio
async def test_fetch_workflows_no_token_raises(mocker: MockerFixture) -> None:
    mocker.patch("check_workflow.gh_api.TOK", "")

    # Shouldn't get as far as the network request, but stub it out just in case
    mock_session = mocker.AsyncMock()
    mock_session.execute.return_value = {}

    with pytest.raises(RuntimeError, match="API token"):
        await fetch_workflows(session=mock_session, owner="sco1", repo_name="check-workflow")


def test_release_from_node() -> None:
    SAMPLE_NODE = {
        "tagName": "v3.1.1",
        "publishedAt": "2024-05-17T14:07:20Z",
        "url": "https://github.com/sco1/flake8-annotations/releases/tag/v3.1.1",
        "tagCommit": {"oid": "d27be86996bb75bf0867eb24fe710cdb39ec5188"},
    }

    TRUTH_RELEASE = Release(
        ver=Version("3.1.1"),
        published=dt.datetime.fromisoformat("2024-05-17T14:07:20Z"),
        url="https://github.com/sco1/flake8-annotations/releases/tag/v3.1.1",
        tag_hash="d27be86996bb75bf0867eb24fe710cdb39ec5188",
    )

    assert Release.from_node(SAMPLE_NODE) == TRUTH_RELEASE


@pytest.mark.asyncio
async def test_release_query_no_token_raises(mocker: MockerFixture) -> None:
    mocker.patch("check_workflow.gh_api.TOK", "")

    # Shouldn't get as far as the network request, but stub it out just in case
    mock_session = mocker.AsyncMock()
    mock_session.execute.return_value = {}

    with pytest.raises(RuntimeError, match="API token"):
        await fetch_releases(session=mock_session, owner="sco1", repo_name="check-workflow")


@pytest.mark.asyncio
async def test_release_query_single(mocker: MockerFixture) -> None:
    SAMPLE_RESPONSE = SAMPLE_DATA_DIR / "release_query_single.json"
    with SAMPLE_RESPONSE.open("r") as f:
        resp = json.load(f)

    mock_session = mocker.AsyncMock()
    mock_session.execute.return_value = resp

    TRUTH_OUT = [
        Release(
            ver=Version("3.1.1"),
            published=dt.datetime.fromisoformat("2024-05-17T14:07:20Z"),
            url="https://github.com/sco1/flake8-annotations/releases/tag/v3.1.1",
            tag_hash="d27be86996bb75bf0867eb24fe710cdb39ec5188",
        )
    ]

    releases = await fetch_releases(
        session=mock_session, owner="scor", repo_name="flake8-annotations"
    )
    assert releases == TRUTH_OUT


@pytest.mark.asyncio
async def test_release_query_multi(mocker: MockerFixture) -> None:
    SAMPLE_RESPONSE = SAMPLE_DATA_DIR / "release_query_multi.json"
    with SAMPLE_RESPONSE.open("r") as f:
        resp = json.load(f)

    mock_session = mocker.AsyncMock()
    mock_session.execute.return_value = resp

    TRUTH_OUT = [
        Release(
            ver=Version("3.1.1"),
            published=dt.datetime.fromisoformat("2024-05-17T14:07:20Z"),
            url="https://github.com/sco1/flake8-annotations/releases/tag/v3.1.1",
            tag_hash="d27be86996bb75bf0867eb24fe710cdb39ec5188",
        ),
        Release(
            ver=Version("3.1.0"),
            published=dt.datetime.fromisoformat("2024-05-06T18:47:23Z"),
            url="https://github.com/sco1/flake8-annotations/releases/tag/v3.1.0",
            tag_hash="ec8b88b35613b5274148a87decf2dfbecec1df31",
        ),
        Release(
            ver=Version("3.0.1"),
            published=dt.datetime.fromisoformat("2023-05-03T02:43:51Z"),
            url="https://github.com/sco1/flake8-annotations/releases/tag/v3.0.1",
            tag_hash="d831807bedbda4b084b184032daa9262705f2b71",
        ),
    ]

    releases = await fetch_releases(
        session=mock_session, owner="sco1", repo_name="flake8_annotations", n_latest=3
    )
    assert releases == TRUTH_OUT

    query = mock_session.execute.call_args.args[0].payload
    assert query["variables"]["n_latest"] == 3


@pytest.mark.asyncio
async def test_release_query_multi_sorted(mocker: MockerFixture) -> None:
    SAMPLE_RESPONSE = SAMPLE_DATA_DIR / "release_query_multi_unsorted.json"
    with SAMPLE_RESPONSE.open("r") as f:
        resp = json.load(f)

    mock_session = mocker.AsyncMock()
    mock_session.execute.return_value = resp

    TRUTH_OUT = [
        Release(
            ver=Version("3.1.0"),
            published=dt.datetime.fromisoformat("2024-05-06T18:47:23Z"),
            url="https://github.com/sco1/flake8-annotations/releases/tag/v3.1.0",
            tag_hash="abc456",
        ),
        Release(
            ver=Version("3.0.1"),
            published=dt.datetime.fromisoformat("2023-05-03T02:43:51Z"),
            url="https://github.com/sco1/flake8-annotations/releases/tag/v3.0.1",
            tag_hash="abc789",
        ),
        Release(
            ver=Version("2.1.2"),
            published=dt.datetime.fromisoformat("2024-05-17T14:07:20Z"),
            url="https://github.com/sco1/flake8-annotations/releases/tag/v2.1.2",
            tag_hash="abc123",
        ),
    ]

    releases = await fetch_releases(
        session=mock_session, owner="sco1", repo_name="flake8_annotations", n_latest=3
    )
    assert releases == TRUTH_OUT

    query = mock_session.execute.call_args.args[0].payload
    assert query["variables"]["n_latest"] == 3
