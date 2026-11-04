# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
from urllib.parse import quote

from .base import Collector, Item, Section
from ..maintainers import Maintainer
from ..util import fetch

log = logging.getLogger(__name__)

URL = "https://packages.gentoo.org"
ATOM = "{http://www.w3.org/2005/Atom}"
SUMMARY_RE = re.compile(
    r"Version (.+?) is available, while the latest version in the Gentoo tree is (.+)\.")


def parse_feed(data: bytes) -> list[Item]:
    items = []
    for entry in ET.fromstring(data).iter(f"{ATOM}entry"):
        package = entry.findtext(f"{ATOM}title", "")
        summary = entry.findtext(f"{ATOM}summary", "")
        if match := SUMMARY_RE.search(summary):
            summary = f"{match[2]} -> {match[1]}"
        items.append(Item(package, f": {summary}", f"{URL}/packages/{package}"))
    return items


class OutdatedCollector(Collector):
    async def setup(self) -> None:
        self.not_found: list[str] = []

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        url = f"{URL}/maintainer/{quote(maintainer.email)}/outdated.atom"
        try:
            data = await asyncio.to_thread(fetch, url)
        except HTTPError as e:
            if e.code != 404:
                raise
            self.not_found.append(maintainer.email)
            return []
        return [Section("Outdated Packages", parse_feed(data))]

    def finish(self) -> None:
        # The site does not know these maintainers, so they may no longer
        # be valid.
        if self.not_found:
            log.warning("No outdated feed for %d maintainers: %s",
                        len(self.not_found), ", ".join(sorted(self.not_found)))
