# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json
import logging
import re
from collections import defaultdict

from .base import Item, PackageCollector
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

    async def setup(self) -> None:
        # gh lists at most the first 100 files of each pull request.
        args = ("gh", "pr", "list",
                "--repo", self.config.github_repo,
                "--state", "open",
                "--limit", "10000",
                "--json", "number,title,url,files")
        # GitHub sometimes answers this query with a 502.
        for delay in (10, 30):
            try:
                out = await run(*args, timeout=900)
                break
            except RuntimeError as e:
                if not re.search(r"\bHTTP 5\d\d\b", str(e)):
                    raise
                log.warning("%s, retrying in %ds", e, delay)
                await asyncio.sleep(delay)
        else:
            out = await run(*args, timeout=900)
        self.items = group_by_package(json.loads(out))
