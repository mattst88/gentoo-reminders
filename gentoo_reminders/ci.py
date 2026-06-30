# SPDX-License-Identifier: GPL-3.0-or-later

"""pkgcheck's reports on the gentoo repository from Gentoo's CI."""

import asyncio
import logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from .collectors.base import Item
from .util import run

log = logging.getLogger(__name__)

URL = "https://anongit.gentoo.org/git/report/gentoo-ci.git"

# Cached for the run
_updated = False
_reports: dict[str, list[dict[str, str]]] = {}
_lock = asyncio.Lock()


async def _update(repo: Path) -> None:
    global _updated
    if _updated:
        return
    if repo.exists():
        await run("git", "-C", str(repo), "fetch", "--quiet", timeout=900)
    else:
        repo.parent.mkdir(parents=True, exist_ok=True)
        # Without the reports, which git fetches when they are read
        await run("git", "clone", "--quiet", "--mirror", "--filter=blob:none",
                  URL, str(repo), timeout=900)
    _updated = True


def parse(report: str) -> list[dict[str, str]]:
    """Return each result's fields: class, msg, and category, package and
    version where it has them."""
    return [{e.tag: e.text or "" for e in result} for result in ET.fromstring(report)]


async def report(cache_dir: Path, before: datetime | None = None) -> list[dict[str, str]]:
    """Return the results of the latest report, or of the last one before
    `before`."""
    repo = cache_dir / "gentoo-ci.git"
    async with _lock:
        await _update(repo)

        args = [f"--before={before:%Y-%m-%d %H:%M:%S %z}"] if before else []
        commit = (await run(
            "git", "-C", str(repo), "log", "-1", "--format=%H", *args, "HEAD",
        )).strip()
        if not commit:
            raise RuntimeError(f"no CI report from before {before}")
        if commit not in _reports:
            log.info("Reading CI report %s", commit)
            _reports[commit] = parse(await run(
                "git", "-C", str(repo), "show", f"{commit}:output.xml", timeout=900))
        return _reports[commit]


def by_package(results: Iterable[dict[str, str]],
               text: Callable[[dict[str, str]], str]) -> dict[str, list[Item]]:
    """Group results by package, linking to the package on packages.gentoo.org."""
    grouped: dict[str, list[Item]] = defaultdict(list)
    for result in results:
        package = f"{result['category']}/{result['package']}"
        ref = f"{package}-{result['version']}" if "version" in result else package
        grouped[package].append(Item(
            ref, text(result), f"https://packages.gentoo.org/packages/{package}"))
    return grouped
