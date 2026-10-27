# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass, field
from datetime import date

from ..config import Config
from ..maintainers import Maintainer
from ..util import previous_month


@dataclass(frozen=True)
class Item:
    """One line of a section, rendered as `ref` followed by `text`."""
    ref: str
    text: str = ""
    url: str | None = None


@dataclass
class Section:
    title: str
    items: list[Item] = field(default_factory=list)
    text: str = ""  # preformatted, shown instead of items
    urls_in_text: bool = False  # also print each item's URL in the text part


class Collector:
    def __init__(self, config: Config, month: tuple[date, date] | None = None):
        self.config = config
        # First and last days of the month reported on, by default the
        # previous one
        self.month = month or previous_month()
        self.month_name = f"{self.month[0]:%B %Y}"

    async def setup(self) -> None:
        """Fetch data shared by all maintainers."""

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        raise NotImplementedError

    def finish(self) -> None:
        """Report on the run, once every maintainer has been processed."""


class PackageCollector(Collector):
    """A collector of items by package, set in `setup()`."""
    title: str
    urls_in_text = False
    items: dict[str, list[Item]]

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        # An item can be under several of the maintainer's packages.
        items = dict.fromkeys(
            item
            for package in maintainer.packages
            for item in self.items.get(package, ())
        )
        return [Section(self.title, list(items), urls_in_text=self.urls_in_text)]
