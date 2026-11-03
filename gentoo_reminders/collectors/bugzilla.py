# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json
from collections import defaultdict
from collections.abc import Callable
from urllib.error import HTTPError
from urllib.parse import urlencode

from .base import Collector, Item, Section, omitted
from ..maintainers import Maintainer
from ..util import fetch

URL = "https://bugs.gentoo.org"
PAGE_SIZE = 10000  # the most the server returns per request
FIELDS = "id,summary,component,assigned_to,last_change_time"
# Stabilization and keywording bugs
ARCH_COMPONENTS = {"Stabilization", "Keywording"}


async def search(api_key: str | None, **params: str | list[str]) -> list[dict]:
    if not api_key:
        raise RuntimeError("no Bugzilla API key, set secret_file in [bugzilla]")

    bugs: list[dict] = []
    while True:
        query = urlencode({
            **params,
            "include_fields": FIELDS,
            "order": "bug_id",
            "limit": PAGE_SIZE,
            "offset": len(bugs),
            # bugs.gentoo.org ignores the X-BUGZILLA-API-KEY header.
            "Bugzilla_api_key": api_key,
        }, doseq=True)
        try:
            data = await asyncio.to_thread(fetch, f"{URL}/rest/bug?{query}")
        except HTTPError as e:
            try:
                message = json.loads(e.read())["message"]
            except (ValueError, KeyError):
                raise e from None
            raise RuntimeError(f"Bugzilla: {message}") from None
        page = json.loads(data)["bugs"]
        bugs += page
        if len(page) < PAGE_SIZE:
            return bugs


def by_assignee(bugs: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for bug in bugs:
        grouped[bug["assigned_to"].lower()].append(bug)
    return grouped


def item(bug: dict, note: str = "") -> Item:
    return Item(f"Bug #{bug['id']}", f": {bug['summary']}{note}", f"{URL}/{bug['id']}")


def section(title: str, bugs: list[dict],
            note: Callable[[dict], str] = lambda bug: "") -> Section:
    """List bugs, but only count stabilization and keywording bugs."""
    items = [item(bug, note(bug)) for bug in bugs
             if bug["component"] not in ARCH_COMPONENTS]
    return Section(title, items, omitted=omitted(len(bugs) - len(items), "bug"))


class BugsCollector(Collector):
    async def setup(self) -> None:
        self.bugs = by_assignee(await search(
            self.config.bugzilla_api_key,
            status=["UNCONFIRMED", "CONFIRMED", "IN_PROGRESS"]))

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        return [section("Open Bugs", self.bugs.get(maintainer.email, []),
                        lambda bug: f" (last changed {bug['last_change_time'][:10]})")]


class NewBugsCollector(Collector):
    """Bugs filed and closed in the month reported on."""

    async def setup(self) -> None:
        # Bugzilla's time zone is UTC. Both ends of the range are included.
        first, last = self.month
        dates = {"chfieldfrom": first.isoformat(), "chfieldto": last.isoformat()}
        api_key = self.config.bugzilla_api_key
        new, closed = await asyncio.gather(
            search(api_key, chfield="[Bug creation]", **dates),
            search(api_key, status=["RESOLVED", "VERIFIED"], chfield="bug_status",
                   chfieldvalue="RESOLVED", **dates),
        )
        self.new = by_assignee(new)
        self.closed = by_assignee(closed)

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        return [
            section(f"Bugs Filed in {self.month_name}",
                    self.new.get(maintainer.email, [])),
            section(f"Bugs Closed in {self.month_name}",
                    self.closed.get(maintainer.email, [])),
        ]
