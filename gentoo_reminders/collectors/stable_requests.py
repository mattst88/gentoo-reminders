# SPDX-License-Identifier: GPL-3.0-or-later

import re

from .base import PackageCollector
from .. import ci

AGE = re.compile(r"no change in (\d+) days")


def age(result: dict[str, str]) -> str:
    match = AGE.search(result["msg"])
    return f" ({match[1]} days)" if match else ""


class StableRequestsCollector(PackageCollector):
    """pkgcheck's StableRequest results in the latest CI report."""
    title = "Packages Needing Stable Requests"

    async def setup(self) -> None:
        results = await ci.report(self.config.cache_dir)
        self.items = ci.by_package(
            (r for r in results if r["class"] == "StableRequest"), age)
