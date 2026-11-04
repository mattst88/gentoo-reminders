# SPDX-License-Identifier: GPL-3.0-or-later

"""The clone of gentoo.git that reminders are made from."""

import logging
import shutil
from pathlib import Path

from .config import Config
from .util import run

log = logging.getLogger(__name__)

URL = "https://github.com/gentoo/gentoo.git"


class CloneError(Exception):
    pass


async def _clone(repo: Path) -> None:
    log.info("Cloning %s into %s", URL, repo)
    # Cloned beside it, so that a failed clone is not mistaken for one
    partial = repo.with_name(repo.name + ".partial")
    try:
        shutil.rmtree(partial, ignore_errors=True)
        partial.parent.mkdir(parents=True, exist_ok=True)
        # History is needed, so not shallow, but only metadata.xml
        # contents, fetched when read
        await run("git", "clone", "--quiet", "--bare", "--filter=blob:none",
                  URL, str(partial), timeout=3600)
        await run("git", "-C", str(partial), "config", "remote.origin.fetch",
                  "refs/heads/*:refs/heads/*")
        partial.rename(repo)
    except (OSError, RuntimeError) as e:
        raise CloneError(e) from e


async def update(config: Config, pull: bool) -> Path:
    """Return the repository to read, after updating it if `pull`. Without
    `gentoo_repo` in the configuration, it is a bare partial clone in
    `cache_dir`, made on first use."""
    repo = config.gentoo_repo
    if repo is None:
        repo = config.cache_dir / "gentoo.git"
        if not repo.exists():
            await _clone(repo)
            return repo
    if pull:
        log.info("Updating %s", repo)
        bare = await run("git", "-C", str(repo), "rev-parse", "--is-bare-repository")
        command = ("fetch",) if bare.strip() == "true" else ("pull", "--ff-only")
        await run("git", "-C", str(repo), *command, "--quiet", timeout=900)
    return repo
