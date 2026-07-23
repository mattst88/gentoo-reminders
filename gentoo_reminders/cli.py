# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import asyncio
import logging
import sys

from .collectors.base import Collector, Section
from .collectors.bugzilla import BugsCollector, NewBugsCollector
from .collectors.github_prs import GitHubPRsCollector
from .collectors.outdated import OutdatedCollector
from .collectors.redundant import RedundantVersionsCollector
from .collectors.shortlog import ShortlogCollector
from .collectors.stable_requests import StableRequestsCollector
from .config import Config, load_config
from .email import render, write_email
from .maintainers import Maintainer, find_last_commits, load_maintainers
from .util import run

log = logging.getLogger(__name__)

# In the order their sections appear in the email
COLLECTORS = {
    "outdated": OutdatedCollector,
    "stable_requests": StableRequestsCollector,
    "github_prs": GitHubPRsCollector,
    "redundant": RedundantVersionsCollector,
    "shortlog": ShortlogCollector,
    "new_bugs": NewBugsCollector,
    "bugs": BugsCollector,
}


def collector_names(value: str) -> list[str]:
    names = value.split(",")
    if unknown := set(names) - set(COLLECTORS):
        raise argparse.ArgumentTypeError(
            f"unknown collector {', '.join(sorted(unknown))} "
            f"(available: {', '.join(COLLECTORS)})")
    return [name for name in COLLECTORS if name in names]


def positive_int(value: str) -> int:
    if (n := int(value)) < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1: {value}")
    return n


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gentoo-reminders",
        description="Generate reminder emails for Gentoo package maintainers",
    )
    parser.add_argument("--config", required=True,
                        help="path to the TOML configuration file")
    parser.add_argument("--maintainer",
                        help="only process the maintainer with this email address")
    parser.add_argument("--dry-run", action="store_true",
                        help="print emails instead of writing them")
    parser.add_argument("--collectors", type=collector_names, default=list(COLLECTORS),
                        help="comma-separated collectors to run (default: all)")
    parser.add_argument("--no-pull", action="store_true",
                        help="do not update the gentoo repository first")
    parser.add_argument("-j", "--jobs", type=positive_int, default=8,
                        help="maintainers to process concurrently (default: %(default)s)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="enable debug logging")
    return parser.parse_args(argv)


async def collect(collector: Collector, maintainer: Maintainer) -> list[Section]:
    try:
        return await collector.collect(maintainer)
    except Exception as e:
        log.warning("%s failed for %s: %s", type(collector).__name__,
                    maintainer.email, e, exc_info=log.isEnabledFor(logging.DEBUG))
        return []


async def process(config: Config, maintainer: Maintainer, collectors: list[Collector],
                  dry_run: bool, semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        results = await asyncio.gather(
            *(collect(c, maintainer) for c in collectors))
        sections = [s for result in results for s in result if s.items or s.text]
        if not sections:
            log.info("Nothing to report for %s", maintainer.email)
            return

        try:
            msg = render(config, maintainer, sections)
            if dry_run:
                print(msg.as_bytes().decode())
                return
            log.info("Wrote %s", write_email(config.output_dir, maintainer.email, msg))
        except Exception:
            log.exception("Failed to write reminder for %s", maintainer.email)


async def async_main(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    repo = str(config.gentoo_repo)

    if not args.no_pull:
        log.info("Updating %s", repo)
        try:
            await run("git", "-C", repo, "pull", "--ff-only")
        except RuntimeError as e:
            sys.exit(f"{e}\nUse --no-pull to run on the repository as it is.")

    maintainers = load_maintainers(config.gentoo_repo)
    log.info("Found %d maintainers", len(maintainers))
    if args.maintainer:
        maintainer = maintainers.get(args.maintainer.lower())
        if maintainer is None:
            sys.exit(f"{args.maintainer} maintains no packages in {repo}")
        selected = [maintainer]
    else:
        selected = list(maintainers.values())

    collectors = [COLLECTORS[name](config) for name in args.collectors]
    try:
        await asyncio.gather(
            asyncio.to_thread(find_last_commits, config.gentoo_repo, selected),
            *(c.setup() for c in collectors),
        )
    except Exception as e:
        sys.exit(f"Failed to fetch data: {e}")

    semaphore = asyncio.Semaphore(args.jobs)
    await asyncio.gather(*(
        process(config, m, collectors, args.dry_run, semaphore)
        for m in selected
    ))

    for collector in collectors:
        collector.finish()


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    asyncio.run(async_main(args))
