# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from gentoo_reminders.collectors import bugzilla
from gentoo_reminders.collectors.bugzilla import NewBugsCollector, by_assignee
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer
from gentoo_reminders.util import previous_month


def bug(bug_id, assignee, time):
    return {"id": bug_id, "summary": f"bug {bug_id}", "assigned_to": assignee,
            "last_change_time": time}


def test_by_assignee():
    grouped = by_assignee([
        bug(1, "x11@gentoo.org", "2026-01-01T00:00:00Z"),
        bug(2, "X11@gentoo.org", "2026-01-01T00:00:00Z"),
        bug(3, "Somebody@example.com", "2026-01-01T00:00:00Z"),
    ])

    assert [b["id"] for b in grouped["x11@gentoo.org"]] == [1, 2]
    assert [b["id"] for b in grouped["somebody@example.com"]] == [3]


def test_search_sends_api_key(monkeypatch):
    urls = []

    def fetch(url):
        urls.append(url)
        return json.dumps({"bugs": [bug(1, "x11@gentoo.org", "2026-01-01T00:00:00Z")]}).encode()

    monkeypatch.setattr(bugzilla, "fetch", fetch)
    bugs = asyncio.run(bugzilla.search("secret", status="CONFIRMED"))
    assert [b["id"] for b in bugs] == [1]
    query = parse_qs(urlsplit(urls[0]).query)
    assert query["Bugzilla_api_key"] == ["secret"]
    assert query["status"] == ["CONFIRMED"]


def test_search_requires_api_key():
    with pytest.raises(RuntimeError, match="API key"):
        asyncio.run(bugzilla.search(None))


def test_search_reports_bugzilla_error(monkeypatch):
    def fetch(url):
        body = json.dumps({"message": "The API key you specified is invalid."})
        raise HTTPError(url, 400, "Bad Request", {}, io.BytesIO(body.encode()))

    monkeypatch.setattr(bugzilla, "fetch", fetch)
    with pytest.raises(RuntimeError, match="Bugzilla: The API key"):
        asyncio.run(bugzilla.search("bogus"))


def test_new_bugs_for_previous_month(monkeypatch):
    queries = []

    async def search(api_key, **params):
        queries.append(params)
        return [bug(len(queries), "x11@gentoo.org", "2026-01-01T00:00:00Z")]

    monkeypatch.setattr(bugzilla, "search", search)
    collector = NewBugsCollector(Config(gentoo_repo=Path("/nonexistent")))
    asyncio.run(collector.setup())

    first, last = previous_month(datetime.now(UTC).date())
    for query in queries:
        assert query["chfieldfrom"] == first.isoformat()
        assert query["chfieldto"] == last.isoformat()

    month = first.strftime("%B %Y")
    new, closed = asyncio.run(collector.collect(Maintainer("x11@gentoo.org")))
    assert new.title == f"Bugs Filed in {month}"
    assert closed.title == f"Bugs Closed in {month}"
    assert [item.ref for item in new.items + closed.items] == ["Bug #1", "Bug #2"]
