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


def group_by_package(prs: list[dict]) -> dict[str, list[Item]]:
    """Map each package to the pull requests that touch its files."""
    grouped: dict[str, list[Item]] = defaultdict(list)
    for pr in sorted(prs, key=lambda pr: pr["number"]):
        item = Item(f"PR #{pr['number']}", f": {pr['title']}", pr["url"])
        packages = {
            "/".join(parts[:2])
            for f in pr["files"]
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
            self.items = group_by_package(json.loads(await self.fetch()))
        except Exception as e:
            log.warning("Failed to fetch pull requests: %s", e)
            self.items = None

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        if self.items is None:
            return [Section(self.title, text="Could not be fetched from GitHub.", notice=True)]
        return await super().collect(maintainer)

    async def fetch(self) -> str:
        # gh lists at most the first 100 files of each pull request.
        args = ("gh", "pr", "list",
                "--repo", self.config.github_repo,
                "--state", "open",
                "--limit", "10000",
                "--json", "number,title,url,files")
        token = self.config.github_token
        env = {**os.environ, "GH_TOKEN": token} if token else None
        # GitHub sometimes answers this query with a 502.
        for delay in (10, 30):
            try:
                return await run(*args, timeout=900, env=env)
            except RuntimeError as e:
                if not re.search(r"\bHTTP 5\d\d\b", str(e)):
                    raise
                log.warning("%s, retrying in %ds", e, delay)
                await asyncio.sleep(delay)
        return await run(*args, timeout=900, env=env)
