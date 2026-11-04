# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class Maintainer:
    email: str
    person: bool = False
    packages: list[str] = field(default_factory=list)
    # Date and subject of the person's most recent commits
    last_authored: str | None = None
    last_committed: str | None = None


def _git(repo: Path, *args: str, input: bytes | None = None,
         env: dict[str, str] | None = None) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], input=input, env=env,
                            capture_output=True)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} exited with status {result.returncode}: "
                           f"{result.stderr.decode().strip()}")
    return result.stdout


def _fetch_missing(repo: Path, oids: bytes) -> None:
    """Fetch the `oids` a partial clone lacks in one request, not one at a
    time."""
    check = _git(repo, "cat-file", "--batch-check", input=oids,
                 env=os.environ | {"GIT_NO_LAZY_FETCH": "1"})
    missing = [line.split()[0] for line in check.splitlines() if line.endswith(b" missing")]
    if not missing:
        return
    log.info("Fetching %d metadata.xml files", len(missing))
    _git(repo, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "--quiet", "--stdin",
         "origin", input=b"".join(oid + b"\n" for oid in missing))


def _read_metadata(repo: Path) -> list[tuple[str, bytes]]:
    """Return each package and its metadata.xml at HEAD, read from git so
    that the repository can be bare."""
    tree = _git(repo, "ls-tree", "-r", "-z", "--format=%(objectname) %(path)", "HEAD")
    entries = []
    for entry in tree.split(b"\0"):
        if entry.endswith(b"/metadata.xml") and entry.count(b"/") == 2:
            oid, path = entry.split(b" ", 1)
            entries.append((path.decode().removesuffix("/metadata.xml"), oid))
    oids = b"".join(oid + b"\n" for _, oid in entries)
    _fetch_missing(repo, oids)

    data = _git(repo, "cat-file", "--batch", input=oids)
    result = []
    pos = 0
    for package, _ in entries:
        end = data.index(b"\n", pos)
        size = int(data[pos:end].split()[2])
        result.append((package, data[end + 1:end + 1 + size]))
        pos = end + 1 + size + 1
    return result


def load_maintainers(repo: Path) -> dict[str, Maintainer]:
    """Map each maintainer's email to their packages, from metadata.xml."""
    maintainers: dict[str, Maintainer] = {}
    for package, contents in _read_metadata(repo):
        try:
            root = ET.fromstring(contents)
        except ET.ParseError as e:
            log.warning("Skipping %s/metadata.xml: %s", package, e)
            continue

        # Direct children only: <upstream> has <maintainer> elements too.
        for element in root.findall("maintainer"):
            email = (element.findtext("email") or "").strip().lower()
            if not email:
                continue
            maintainer = maintainers.setdefault(email, Maintainer(email))
            maintainer.person |= element.get("type") == "person"
            if package not in maintainer.packages[-1:]:
                maintainer.packages.append(package)

    return dict(sorted(maintainers.items()))


def find_last_commits(repo: Path, maintainers: list[Maintainer]) -> None:
    """Set `last_authored` and `last_committed` on the person maintainers."""
    people = {m.email: m for m in maintainers if m.person}
    missing = 2 * len(people)
    if not missing:
        return

    # One pass over the history for everyone. Those who never committed
    # under their metadata.xml address make this read all of it.
    command = ["git", "-C", str(repo), "log", "--format=%ae%x00%ce%x00%aI%x00%cI%x00%s"]
    with subprocess.Popen(command, stdout=subprocess.PIPE,
                          text=True, errors="replace") as proc:
        for line in proc.stdout:
            author, committer, authored, committed, subject = (
                line.rstrip("\n").split("\0", 4))
            if (m := people.get(author.lower())) and m.last_authored is None:
                m.last_authored = f"{authored} {subject}"
                missing -= 1
            if (m := people.get(committer.lower())) and m.last_committed is None:
                m.last_committed = f"{committed} {subject}"
                missing -= 1
            if not missing:
                proc.terminate()
                break

    if missing and proc.returncode:
        raise RuntimeError(f"git log exited with status {proc.returncode}")

