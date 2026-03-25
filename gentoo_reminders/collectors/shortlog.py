# SPDX-License-Identifier: GPL-3.0-or-later

from .base import Collector, Section
from ..maintainers import Maintainer
from ..util import previous_month, run


class ShortlogCollector(Collector):
    """Commits to the maintainer's packages in the previous calendar month."""

    async def setup(self) -> None:
        first, last = previous_month()
        self.month = f"{first:%B %Y}"
        # By commit date, not author date
        self.range = (f"--since={first} 00:00:00 +0000",
                      f"--until={last} 23:59:59 +0000")

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        out = await run(
            "git", "-C", str(self.config.gentoo_repo),
            "shortlog", *self.range, "HEAD", "--", *maintainer.packages,
        )
        return [Section(f"Changes in {self.month}", text=out.strip())]
