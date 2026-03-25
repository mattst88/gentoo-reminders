# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
from pathlib import Path

from gentoo_reminders.collectors import shortlog
from gentoo_reminders.collectors.shortlog import ShortlogCollector
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer
from gentoo_reminders.util import previous_month


def test_shortlog_for_previous_month(monkeypatch):
    commands = []

    async def run(*args):
        commands.append(args)
        return "Larry the Cow (1):\n      foo: bar\n"

    monkeypatch.setattr(shortlog, "run", run)
    collector = ShortlogCollector(Config(gentoo_repo=Path("/nonexistent")))
    asyncio.run(collector.setup())
    maintainer = Maintainer("larry@gentoo.org", packages=["app-misc/foo"])
    [section] = asyncio.run(collector.collect(maintainer))

    first, last = previous_month()
    assert f"--since={first} 00:00:00 +0000" in commands[0]
    assert f"--until={last} 23:59:59 +0000" in commands[0]
    assert commands[0][-2:] == ("--", "app-misc/foo")
    assert section.title == f"Changes in {first:%B %Y}"
    assert section.text == "Larry the Cow (1):\n      foo: bar"
