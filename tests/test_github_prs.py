# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json
from pathlib import Path

import pytest

from gentoo_reminders.collectors import github_prs
from gentoo_reminders.collectors.github_prs import GitHubPRsCollector, group_by_package
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer


def test_group_by_package():
    prs = [
        {"number": 2, "title": "Bump both", "url": "https://example.org/2", "files": {"nodes": [
            {"path": "x11-libs/libdrm/libdrm-2.ebuild"},
            {"path": "x11-libs/libdrm/Manifest"},
            {"path": "media-libs/mesa/mesa-2.ebuild"},
        ]}},
        {"number": 1, "title": "New eclass", "url": "https://example.org/1", "files": {"nodes": [
            {"path": "eclass/foo.eclass"},
            {"path": "media-libs/mesa/files/foo.patch"},
        ]}},
    ]

    grouped = group_by_package(prs)

    assert set(grouped) == {"x11-libs/libdrm", "media-libs/mesa"}
    assert [item.ref for item in grouped["x11-libs/libdrm"]] == ["PR #2"]
    mesa = {item.ref: item.url for item in grouped["media-libs/mesa"]}
    assert mesa == {"PR #1": "https://example.org/1", "PR #2": "https://example.org/2"}


def page(prs=(), cursor=None):
    return json.dumps({"data": {"repository": {"pullRequests": {
        "pageInfo": {"hasNextPage": cursor is not None, "endCursor": cursor},
        "nodes": list(prs),
    }}}})


def setup(monkeypatch, responses=(), **options):
    calls = []
    responses = list(responses)

    async def run(*args, env):
        calls.append((args, env))
        response = responses.pop(0) if responses else page()
        if isinstance(response, Exception):
            raise response
        return response

    async def sleep(delay):
        pass

    monkeypatch.setattr(github_prs, "run", run)
    monkeypatch.setattr(github_prs.asyncio, "sleep", sleep)
    collector = GitHubPRsCollector(Config(gentoo_repo=Path("/nonexistent"), **options))
    asyncio.run(collector.setup())
    return collector, calls


BAD_GATEWAY = RuntimeError("gh exited with status 1: gh: HTTP 502")
RATE_LIMIT = RuntimeError("gh exited with status 1: gh: You have exceeded a secondary rate "
                          "limit. Please wait a few minutes before you try again. (HTTP 403)")


def pr(number, package):
    return {"number": number, "title": "Bump", "url": f"https://example.org/{number}",
            "files": {"nodes": [{"path": f"{package}/foo-1.ebuild"}]}}


def test_pages(monkeypatch):
    pages = [page([pr(1, "a/b")], "next"), page([pr(2, "c/d")])]
    collector, calls = setup(monkeypatch, pages)
    assert set(collector.items) == {"a/b", "c/d"}
    assert [args[-1] for args, _ in calls] == ["name=gentoo", "cursor=next"]


def test_retry_keeps_earlier_pages(monkeypatch):
    responses = [page([pr(1, "a/b")], "next"), BAD_GATEWAY, page([pr(2, "c/d")])]
    collector, calls = setup(monkeypatch, responses)
    assert set(collector.items) == {"a/b", "c/d"}
    assert [args[-1] for args, _ in calls] == ["name=gentoo", "cursor=next", "cursor=next"]


def test_token(monkeypatch):
    _, calls = setup(monkeypatch, [BAD_GATEWAY] * 3, github_token="secret")
    assert [env["GH_TOKEN"] for _, env in calls] == ["secret"] * 4


def test_no_token(monkeypatch):
    _, calls = setup(monkeypatch)
    assert [env for _, env in calls] == [None]


@pytest.mark.parametrize("error", [BAD_GATEWAY, RATE_LIMIT])
def test_retries(monkeypatch, error):
    collector, calls = setup(monkeypatch, [error] * 3)
    assert len(calls) == 4
    assert collector.items == {}


def test_gives_up_after_retries(monkeypatch):
    collector, calls = setup(monkeypatch, [BAD_GATEWAY] * 4)
    assert len(calls) == 4
    assert collector.items is None


def test_does_not_retry_other_errors(monkeypatch):
    _, calls = setup(
        monkeypatch, [RuntimeError("gh exited with status 1: gh: Bad credentials (HTTP 401)")])
    assert len(calls) == 1


def test_sorted_by_number(monkeypatch):
    # Packages in metadata.xml order, not alphabetical, and a PR on two of them
    prs = [pr(5, "z/z"), pr(3, "a/a"), pr(4, "m/m"), pr(1, "m/m"), pr(2, "z/z")]
    prs[0]["files"]["nodes"].append({"path": "a/a/foo-2.ebuild"})
    collector, _ = setup(monkeypatch, [page(prs)])
    maintainer = Maintainer("x@gentoo.org", packages=["m/m", "z/z", "a/a"])

    [section] = asyncio.run(collector.collect(maintainer))

    assert [item.ref for item in section.items] == [f"PR #{n}" for n in range(1, 6)]


def test_failure_is_a_notice(monkeypatch):
    collector, _ = setup(monkeypatch, [BAD_GATEWAY] * 4)
    maintainer = Maintainer("x11@gentoo.org", packages=["x11-libs/libdrm"])

    [section] = asyncio.run(collector.collect(maintainer))

    assert section.notice
    assert section.title == "Open GitHub Pull Requests"
    assert section.text == "Could not be fetched from GitHub."
