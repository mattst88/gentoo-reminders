# SPDX-License-Identifier: GPL-3.0-or-later

import re
from datetime import UTC, datetime, time, timedelta

from pkgcheck.objects import KEYWORDS

from .base import Item, PackageCollector
from .. import ci

# Line numbers, [ lists ] and (N total), which change without the warning
# being new
VOLATILE = re.compile(r"\b(on )?lines?: [\d, ]+|\[ [^]]* \]|\(\d+ total\)")


def key(result: dict[str, str]) -> tuple[str, ...]:
    return (result["class"], result["category"], result["package"],
            VOLATILE.sub("", result["msg"]))


def new_warnings(before: list[dict[str, str]],
                 after: list[dict[str, str]]) -> dict[str, list[Item]]:
    """Group by package the errors and warnings in `after` that are not in
    `before`, skipping checks with no results in `before`, which may be
    new to pkgcheck."""
    known = {result["class"] for result in before}
    old = {key(result) for result in before if "package" in result}

    def new(result: dict[str, str]) -> bool:
        keyword = KEYWORDS.get(result["class"])
        return ("package" in result and result["class"] in known
                and keyword is not None and keyword.level in ("error", "warning")
                and key(result) not in old)

    return ci.by_package(filter(new, after),
                         lambda r: f": {r['class']}: {r['msg']}", "/qa-report")


class QACollector(PackageCollector):
    """pkgcheck errors and warnings new in the month reported on."""

    async def setup(self) -> None:
        first, last = self.month
        self.title = f"New QA Warnings in {self.month_name}"
        # git log --before includes its own time.
        start = datetime.combine(first, time(), UTC) - timedelta(seconds=1)
        end = datetime.combine(last, time(23, 59, 59), UTC)
        self.items = new_warnings(
            await ci.report(self.config.cache_dir, start),
            await ci.report(self.config.cache_dir, end))
