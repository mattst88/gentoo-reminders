# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
from pathlib import Path

import pytest

from gentoo_reminders.collectors import github_prs
from gentoo_reminders.collectors.github_prs import GitHubPRsCollector, group_by_package
from gentoo_reminders.config import Config


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


def setup(monkeypatch, errors):
    calls = []

    async def run(*args, timeout):
        calls.append(args)
        if errors:
            raise RuntimeError(errors.pop(0))
        return "[]"

    async def sleep(delay):
        pass

    monkeypatch.setattr(github_prs, "run", run)
    monkeypatch.setattr(github_prs.asyncio, "sleep", sleep)
    collector = GitHubPRsCollector(Config(gentoo_repo=Path("/nonexistent")))
    asyncio.run(collector.setup())
    return calls


def test_retries_server_errors(monkeypatch):
    error = "gh exited with status 1: HTTP 502: 502 Bad Gateway (https://api.github.com/graphql)"
    assert len(setup(monkeypatch, [error, error])) == 3
    with pytest.raises(RuntimeError, match="502"):
        setup(monkeypatch, [error] * 3)


def test_does_not_retry_other_errors(monkeypatch):
    with pytest.raises(RuntimeError, match="HTTP 401"):
        setup(monkeypatch, ["gh exited with status 1: HTTP 401: Bad credentials"])
