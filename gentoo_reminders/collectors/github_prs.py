# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json
import logging
import os
import re
from collections import defaultdict

from .base import Item, PackageCollector, Section
from ..maintainers import Maintainer
from ..util import run

log = logging.getLogger(__name__)

# GitHub often answers with a 502 when asked for many more of these at once.
# It lists at most the first 100 files of each pull request.
QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 50, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { number title url files(first: 100) { nodes { path } } }
    }
  }
}
"""


async def request(*args: str, env: dict[str, str] | None) -> str:
    # GitHub sometimes answers with a 502, or a rate limit that asks to wait
    # a few minutes.
    for delay in (10, 30, 300):
        try:
            return await run(*args, env=env)
        except RuntimeError as e:
            if not re.search(r"\bHTTP 5\d\d\b|rate limit", str(e)):
                raise
            log.warning("%s, retrying in %ds", e, delay)
            await asyncio.sleep(delay)
    return await run(*args, env=env)


def number(item: Item) -> int:
    return int(item.ref.removeprefix("PR #"))


def group_by_package(prs: list[dict]) -> dict[str, list[Item]]:
    """Map each package to the pull requests that touch its files."""
    grouped: dict[str, list[Item]] = defaultdict(list)
    for pr in prs:
        item = Item(f"PR #{pr['number']}", f": {pr['title']}", pr["url"])
        packages = {
            "/".join(parts[:2])
            for f in pr["files"]["nodes"]
            if len(parts := f["path"].split("/")) >= 3
        }
        for package in packages:
            grouped[package].append(item)
    return grouped


class GitHubPRsCollector(PackageCollector):
    title = "Open GitHub Pull Requests"
    urls_in_text = True
    items: dict[str, list[Item]] | None  # None if GitHub could not be read

    async def setup(self) -> None:
        try:
            self.items = group_by_package(await self.fetch())
        except Exception as e:
            log.warning("Failed to fetch pull requests: %s", e)
            self.items = None

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        if self.items is None:
            return [Section(self.title, text="Could not be fetched from GitHub.", notice=True)]
        sections = await super().collect(maintainer)
        for section in sections:
            section.items.sort(key=number)
        return sections

    async def fetch(self) -> list[dict]:
        owner, name = self.config.github_repo.split("/")
        args = ("gh", "api", "graphql", "-f", f"query={QUERY}",
                "-f", f"owner={owner}", "-f", f"name={name}")
        token = self.config.github_token
        env = {**os.environ, "GH_TOKEN": token} if token else None

        prs = []
        after = ()
        while True:
            out = await request(*args, *after, env=env)
            page = json.loads(out)["data"]["repository"]["pullRequests"]
            prs += page["nodes"]
            if not page["pageInfo"]["hasNextPage"]:
                return prs
            after = ("-f", f"cursor={page['pageInfo']['endCursor']}")
