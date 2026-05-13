# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass, field

from ..config import Config
from ..maintainers import Maintainer


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
    def __init__(self, config: Config):
        self.config = config

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
