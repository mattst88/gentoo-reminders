# SPDX-License-Identifier: GPL-3.0-or-later

from .base import PackageCollector
from .. import ci


class RedundantVersionsCollector(PackageCollector):
    """pkgcheck's RedundantVersion results in the latest CI report."""
    title = "Redundant Versions"

    async def setup(self) -> None:
        results = await ci.report(self.config.cache_dir)
        self.items = ci.by_package(
            (r for r in results if r["class"] == "RedundantVersion"),
            lambda r: f": {r['msg']}")
