# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
from pathlib import Path

from gentoo_reminders.collectors import github_prs
from gentoo_reminders.collectors.github_prs import GitHubPRsCollector, group_by_package
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer


def test_group_by_package():
    prs = [
        {"number": 2, "title": "Bump both", "url": "https://example.org/2", "files": [
            {"path": "x11-libs/libdrm/libdrm-2.ebuild"},
            {"path": "x11-libs/libdrm/Manifest"},
            {"path": "media-libs/mesa/mesa-2.ebuild"},
        ]},
        {"number": 1, "title": "New eclass", "url": "https://example.org/1", "files": [
            {"path": "eclass/foo.eclass"},
            {"path": "media-libs/mesa/files/foo.patch"},
        ]},
    ]

    grouped = group_by_package(prs)

    assert set(grouped) == {"x11-libs/libdrm", "media-libs/mesa"}
    assert [item.ref for item in grouped["x11-libs/libdrm"]] == ["PR #2"]
    assert [item.ref for item in grouped["media-libs/mesa"]] == ["PR #1", "PR #2"]
    assert grouped["media-libs/mesa"][0].url == "https://example.org/1"


def setup(monkeypatch, errors, **options):
    calls = []

    async def run(*args, timeout, env):
        calls.append((args, env))
        if errors:
            raise RuntimeError(errors.pop(0))
        return "[]"

    async def sleep(delay):
        pass

    monkeypatch.setattr(github_prs, "run", run)
    monkeypatch.setattr(github_prs.asyncio, "sleep", sleep)
    collector = GitHubPRsCollector(Config(gentoo_repo=Path("/nonexistent"), **options))
    asyncio.run(collector.setup())
    return collector, calls


BAD_GATEWAY = "gh exited with status 1: HTTP 502: 502 Bad Gateway (https://api.github.com/graphql)"


def test_token(monkeypatch):
    _, calls = setup(monkeypatch, [BAD_GATEWAY] * 2, github_token="secret")
    assert [env["GH_TOKEN"] for _, env in calls] == ["secret"] * 3


def test_no_token(monkeypatch):
    _, calls = setup(monkeypatch, [])
    assert [env for _, env in calls] == [None]


def test_retries(monkeypatch):
    collector, calls = setup(monkeypatch, [BAD_GATEWAY] * 2)
    assert len(calls) == 3
    assert collector.items == {}


def test_gives_up_after_retries(monkeypatch):
    collector, calls = setup(monkeypatch, [BAD_GATEWAY] * 3)
    assert len(calls) == 3
    assert collector.items is None


def test_does_not_retry_other_errors(monkeypatch):
    _, calls = setup(monkeypatch, ["gh exited with status 1: HTTP 401: Bad credentials"])
    assert len(calls) == 1


def test_failure_is_a_notice(monkeypatch):
    collector, _ = setup(monkeypatch, [BAD_GATEWAY] * 3)
    maintainer = Maintainer("x11@gentoo.org", packages=["x11-libs/libdrm"])

    [section] = asyncio.run(collector.collect(maintainer))

    assert section.notice
    assert section.title == "Open GitHub Pull Requests"
    assert section.text == "Could not be fetched from GitHub."
