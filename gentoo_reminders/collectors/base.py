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


class Collector:
    def __init__(self, config: Config):
        self.config = config

    async def setup(self) -> None:
        """Fetch data shared by all maintainers."""

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        raise NotImplementedError

    def finish(self) -> None:
        """Report on the run, once every maintainer has been processed."""

