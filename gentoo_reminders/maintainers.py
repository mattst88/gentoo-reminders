# SPDX-License-Identifier: GPL-3.0-or-later

import logging
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


def load_maintainers(repo: Path) -> dict[str, Maintainer]:
    """Map each maintainer's email to their packages, from metadata.xml."""
    maintainers: dict[str, Maintainer] = {}
    for path in sorted(repo.glob("*/*/metadata.xml")):
        package = f"{path.parts[-3]}/{path.parts[-2]}"
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as e:
            log.warning("Skipping %s: %s", path, e)
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

