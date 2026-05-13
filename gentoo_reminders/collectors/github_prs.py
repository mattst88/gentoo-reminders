# SPDX-License-Identifier: GPL-3.0-or-later

import json
from collections import defaultdict

from .base import Item, PackageCollector
from ..util import run


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
        out = await run(
            "gh", "pr", "list",
            "--repo", self.config.github_repo,
            "--state", "open",
            "--limit", "10000",
            "--json", "number,title,url,files",
            timeout=900,
        )
        self.items = group_by_package(json.loads(out))
