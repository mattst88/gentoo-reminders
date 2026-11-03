# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
from datetime import UTC, date, datetime
from pathlib import Path

from gentoo_reminders.collectors import shortlog
from gentoo_reminders.collectors.shortlog import ShortlogCollector, parse_projects
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer
from gentoo_reminders.util import previous_month

PROJECTS = b"""<?xml version="1.0" encoding="UTF-8"?>
<projects>
  <project>
    <email>x11@gentoo.org</email>
    <member><email>Larry@gentoo.org</email></member>
  </project>
</projects>
"""

LOG = (
    "Larry the Cow\0larry@gentoo.org\0app-misc/foo: bar\n"
    "Somebody\0somebody@example.com\0app-misc/foo: baz\n"
    "Larry the Cow\0larry@gentoo.org\0app-misc/foo: qux\n"
)


def collect(monkeypatch, maintainer, month=None, log=LOG):
    commands = []

    async def run(*args):
        commands.append(args)
        return log

    monkeypatch.setattr(shortlog, "run", run)
    monkeypatch.setattr(shortlog, "fetch", lambda url: PROJECTS)
    collector = ShortlogCollector(Config(gentoo_repo=Path("/nonexistent")), month)
    asyncio.run(collector.setup())
    return commands, asyncio.run(collector.collect(maintainer))


def test_shortlog_for_previous_month(monkeypatch):
    maintainer = Maintainer("larry@gentoo.org", packages=["app-misc/foo"])
    commands, [section] = collect(monkeypatch, maintainer)

    first, last = previous_month(datetime.now(UTC).date())
    assert f"--since={first} 00:00:00 +0000" in commands[0]
    assert f"--until={last} 23:59:59 +0000" in commands[0]
    assert commands[0][-2:] == ("--", "app-misc/foo")
    assert section.title == f"Changes in {first:%B %Y}"
    assert section.text == (
        "Larry the Cow (2):\n"
        "      app-misc/foo: bar\n"
        "      app-misc/foo: qux\n"
        "\n"
        "Somebody (1):\n"
        "      app-misc/foo: baz"
    )


def test_shortlog_split_by_project_members(monkeypatch):
    maintainer = Maintainer("x11@gentoo.org", packages=["app-misc/foo"])
    _, [members, others] = collect(monkeypatch, maintainer)

    month = previous_month(datetime.now(UTC).date())[0].strftime("%B %Y")
    assert members.title == f"Changes by Project Members in {month}"
    assert members.text == (
        "Larry the Cow (2):\n"
        "      app-misc/foo: bar\n"
        "      app-misc/foo: qux"
    )
    assert others.title == f"Changes by Others in {month}"
    assert others.text == "Somebody (1):\n      app-misc/foo: baz"


def test_shortlog_for_given_month(monkeypatch):
    maintainer = Maintainer("larry@gentoo.org", packages=["app-misc/foo"])
    month = (date(2026, 2, 1), date(2026, 2, 28))
    commands, [section] = collect(monkeypatch, maintainer, month)

    assert "--since=2026-02-01 00:00:00 +0000" in commands[0]
    assert "--until=2026-02-28 23:59:59 +0000" in commands[0]
    assert section.title == "Changes in February 2026"


def test_parse_projects():
    projects = parse_projects(b"""<?xml version="1.0" encoding="UTF-8"?>
<projects>
  <project>
    <email>emacs@gentoo.org</email>
    <subproject ref="gnu-emacs@gentoo.org" inherit-members="1"/>
    <subproject ref="xemacs@gentoo.org"/>
    <member><email>Larry@gentoo.org</email></member>
  </project>
  <project>
    <email>gnu-emacs@gentoo.org</email>
    <subproject ref="emacs@gentoo.org" inherit-members="1"/>
    <member><email>ulm@gentoo.org</email></member>
  </project>
  <project>
    <email>xemacs@gentoo.org</email>
    <member><email>xemacs-dev@gentoo.org</email></member>
  </project>
</projects>
""")

    assert projects["emacs@gentoo.org"] == {"larry@gentoo.org", "ulm@gentoo.org"}
    assert projects["gnu-emacs@gentoo.org"] == {"larry@gentoo.org", "ulm@gentoo.org"}
    assert projects["xemacs@gentoo.org"] == {"xemacs-dev@gentoo.org"}


def test_shortlog_arch_commits_only_counted(monkeypatch):
    log = (
        "Larry the Cow\0larry@gentoo.org\0app-misc/foo: bar\n"
        "Arch Tester\0arch@gentoo.org\0app-misc/foo: Stabilize 1.0 amd64, #123\n"
        "Arch Tester\0arch@gentoo.org\0app-misc/foo: Keyword 1.0 ~riscv, #124\n"
        "Somebody\0somebody@example.com\0app-misc/foo: stabilize 1.0 for ALLARCHES\n"
        "Somebody\0somebody@example.com\0app-misc/foo: keyword 1.0 for ~arm64\n"
        "Somebody\0somebody@example.com\0app-misc/foo: Stabilize on amd64 is broken\n"
        "Somebody\0somebody@example.com\0app-misc/foo: unkeyword 1.0 for ~x86\n"
    )
    maintainer = Maintainer("x11@gentoo.org", packages=["app-misc/foo"])
    _, [members, others] = collect(monkeypatch, maintainer, log=log)

    assert members.text == "Larry the Cow (1):\n      app-misc/foo: bar"
    assert members.omitted == ""
    assert others.text == (
        "Somebody (2):\n"
        "      app-misc/foo: Stabilize on amd64 is broken\n"
        "      app-misc/foo: unkeyword 1.0 for ~x86"
    )
    assert others.omitted == "4 stabilization and keywording commits not shown"


def test_shortlog_only_arch_commits(monkeypatch):
    log = "Arch Tester\0arch@gentoo.org\0app-misc/foo: Stabilize 1.0 amd64, #123\n"
    maintainer = Maintainer("larry@gentoo.org", packages=["app-misc/foo"])
    _, [section] = collect(monkeypatch, maintainer, log=log)

    assert section.text == ""
    assert section.omitted == "1 stabilization and keywording commit not shown"
