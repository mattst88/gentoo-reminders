# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import xml.etree.ElementTree as ET
from collections import defaultdict

from .base import Collector, Section
from ..maintainers import Maintainer
from ..util import fetch, run


PROJECTS_URL = "https://api.gentoo.org/metastructure/projects.xml"


def parse_projects(data: bytes) -> dict[str, set[str]]:
    """Map each project's email to its members' emails, from projects.xml.

    A project also has the members of the subprojects it inherits them from.
    """
    direct: dict[str, set[str]] = {}
    inherits: dict[str, list[str]] = {}
    for project in ET.fromstring(data).findall("project"):
        email = (project.findtext("email") or "").strip().lower()
        direct[email] = {
            (member.findtext("email") or "").strip().lower()
            for member in project.findall("member")
        }
        inherits[email] = [
            (sub.get("ref") or "").strip().lower()
            for sub in project.findall("subproject")
            if sub.get("inherit-members") == "1"
        ]

    def members(email: str, seen: set[str]) -> set[str]:
        seen.add(email)
        result = set(direct.get(email, ()))
        for sub in inherits.get(email, ()):
            if sub not in seen:
                result |= members(sub, seen)
        return result

    return {email: members(email, set()) for email in direct}


def shortlog(commits: list[tuple[str, str]]) -> str:
    """Format (author, subject) pairs, oldest first, like git shortlog."""
    by_author: dict[str, list[str]] = defaultdict(list)
    for author, subject in commits:
        by_author[author].append(subject)
    return "\n\n".join(
        f"{author} ({len(subjects)}):\n" + "\n".join(f"      {s}" for s in subjects)
        for author, subjects in sorted(by_author.items())
    )


class ShortlogCollector(Collector):
    """Commits to the maintainer's packages in the month reported on.

    For a project, those by its members and by others are listed apart.
    """

    async def setup(self) -> None:
        first, last = self.month
        # By commit date, not author date
        self.range = (f"--since={first} 00:00:00 +0000",
                      f"--until={last} 23:59:59 +0000")
        self.projects = parse_projects(await asyncio.to_thread(fetch, PROJECTS_URL))

    async def collect(self, maintainer: Maintainer) -> list[Section]:
        # Authors as .mailmap has them, oldest commit first
        out = await run(
            "git", "-C", str(self.config.gentoo_repo),
            "log", "--reverse", "--format=%aN%x00%aE%x00%s", *self.range,
            "HEAD", "--", *maintainer.packages,
        )
        commits = [line.split("\0") for line in out.splitlines()]

        members = self.projects.get(maintainer.email)
        if members is None:
            return [Section(f"Changes in {self.month_name}",
                            text=shortlog([(name, subject) for name, _, subject in commits]))]
        ours = [(name, subject) for name, email, subject in commits
                if email.lower() in members]
        others = [(name, subject) for name, email, subject in commits
                  if email.lower() not in members]
        return [
            Section(f"Changes by Project Members in {self.month_name}", text=shortlog(ours)),
            Section(f"Changes by Others in {self.month_name}", text=shortlog(others)),
        ]
