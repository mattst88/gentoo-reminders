# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from gentoodo.collectors import codeberg_prs
from gentoodo.collectors.codeberg_prs import CodebergPRsCollector, next_link
from gentoodo.config import Config
from gentoodo.maintainers import Maintainer

API = "https://codeberg.org/api/v1/repos/gentoo/gentoo/pulls"


@pytest.mark.parametrize("header,expected", [
    (f'<{API}?page=2>; rel="next",<{API}?page=5>; rel="last"', f"{API}?page=2"),
    (f'<{API}?page=1>; rel="first", <{API}?page=3>; rel="next"', f"{API}?page=3"),
    (f'<{API}?page=2>;rel=next', f"{API}?page=2"),
    (f'<{API}?page=1>; rel="first",<{API}?page=4>; rel="prev"', None),
    ("", None),
    (None, None),
])
def test_next_link(header, expected):
    assert next_link(header) == expected


def pr(number):
    return {"number": number, "title": "Bump", "html_url": f"https://example.org/{number}"}


def files(*packages):
    return [{"filename": f"{package}/foo-1.ebuild"} for package in packages]


def setup(monkeypatch, responses, **options):
    """Answer each URL with a list of responses, each a JSON value and an optional next URL."""
    calls = []
    responses = {url: list(answers) for url, answers in responses.items()}

    def fetch_with_headers(url):
        calls.append(url)
        response = responses[url].pop(0)
        if isinstance(response, Exception):
            raise response
        value, next_url = response if isinstance(response, tuple) else (response, None)
        headers = {"Link": f'<{next_url}>; rel="next"'} if next_url else {}
        return json.dumps(value).encode(), headers

    monkeypatch.setattr(codeberg_prs, "fetch_with_headers", fetch_with_headers)
    collector = CodebergPRsCollector(Config(gentoo_repo=Path("/nonexistent"), **options))
    asyncio.run(collector.setup())
    return collector, calls


def test_pages(monkeypatch):
    collector, calls = setup(monkeypatch, {
        f"{API}?state=open&limit=50": [([pr(1), pr(2)], f"{API}?page=2")],
        f"{API}?page=2": [[pr(3), None]],
        f"{API}/1/files?limit=50": [files("a/b")],
        f"{API}/2/files?limit=50": [files("c/d")],
        f"{API}/3/files?limit=50": [files("e/f")],
    })
    assert set(collector.items) == {"a/b", "c/d", "e/f"}
    assert len(calls) == 5


def test_single_page_without_link(monkeypatch):
    collector, _ = setup(monkeypatch, {
        f"{API}?state=open&limit=50": [[pr(1)]],
        f"{API}/1/files?limit=50": [files("a/b")],
    })
    assert set(collector.items) == {"a/b"}


def test_files_pages(monkeypatch):
    collector, _ = setup(monkeypatch, {
        f"{API}?state=open&limit=50": [[pr(1)]],
        f"{API}/1/files?limit=50": [(files("a/b"), f"{API}/1/files?page=2")],
        f"{API}/1/files?page=2": [files("c/d")],
    })
    assert set(collector.items) == {"a/b", "c/d"}


def test_repo(monkeypatch):
    other = "https://codeberg.org/api/v1/repos/larry/overlay/pulls"
    _, calls = setup(monkeypatch, {f"{other}?state=open&limit=50": [[]]},
                     codeberg_repo="larry/overlay")
    assert calls == [f"{other}?state=open&limit=50"]


def test_sorted_by_number(monkeypatch):
    # Packages in metadata.xml order, not alphabetical, and a PR on two of them
    packages = {5: ["z/z", "a/a"], 3: ["a/a"], 4: ["m/m"], 1: ["m/m"], 2: ["z/z"]}
    responses = {f"{API}?state=open&limit=50": [[pr(n) for n in packages]]}
    for n, pkgs in packages.items():
        responses[f"{API}/{n}/files?limit=50"] = [files(*pkgs)]
    collector, _ = setup(monkeypatch, responses)
    maintainer = Maintainer("x@gentoo.org", packages=["m/m", "z/z", "a/a"])

    [section] = asyncio.run(collector.collect(maintainer))

    assert [item.ref for item in section.items] == [f"PR #{n}" for n in range(1, 6)]


def test_failure_is_a_notice(monkeypatch):
    error = HTTPError(API, 404, "Not Found", {}, None)
    collector, _ = setup(monkeypatch, {f"{API}?state=open&limit=50": [error]})
    maintainer = Maintainer("x11@gentoo.org", packages=["x11-libs/libdrm"])

    [section] = asyncio.run(collector.collect(maintainer))

    assert collector.items is None
    assert section.notice
    assert section.title == "Open Codeberg Pull Requests"
    assert section.text == "Could not be fetched from Codeberg."
