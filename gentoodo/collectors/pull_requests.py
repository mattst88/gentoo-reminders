# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from collections import defaultdict
from dataclasses import dataclass

from ..maintainers import Maintainer
from .base import Item, PackageCollector, Section

log = logging.getLogger(__name__)


@dataclass
class PullRequest:
    number: int
    title: str
    url: str
    files: list[str]


def number(item: Item) -> int:
    return int(item.ref.removeprefix("PR #"))


def group_by_package(prs: list[PullRequest]) -> dict[str, list[Item]]:
    """Map each package to the pull requests that touch its files."""
    grouped: dict[str, list[Item]] = defaultdict(list)
    for pr in prs:
        item = Item(f"PR #{pr.number}", f": {pr.title}", pr.url)
        # Files outside packages, like eclass/foo.eclass or
        # profiles/arch/amd64/eapi, give keys no maintainer has.
        packages = {
            "/".join(parts[:2])
            for f in pr.files
            if len(parts := f.split("/")) >= 3
        }
        for package in packages:
            grouped[package].append(item)
    return grouped


class PullRequestsCollector(PackageCollector):
    """The open pull requests of a forge, by the packages they touch."""
    forge: str
    urls_in_text = True
    items: dict[str, list[Item]] | None  # None if the forge could not be read

    async def fetch(self) -> list[PullRequest]:
        raise NotImplementedError

    async def setup(self) -> None:
        try:
            self.items = group_by_package(await self.fetch())
        except Exception as e:
            log.warning("Failed to fetch %s pull requests: %s", self.forge, e)
            self.items = None

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        if self.items is None:
            return [Section(self.title, text=f"Could not be fetched from {self.forge}.",
                            notice=True)]
        sections = await super().collect(maintainer)
        for section in sections:
            section.items.sort(key=number)
        return sections
