# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
from pathlib import Path

from gentoo_reminders.collectors import redundant
from gentoo_reminders.collectors.redundant import RedundantVersionsCollector
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer


def test_redundant_versions(monkeypatch):
    async def report(cache_dir):
        return [
            {"category": "dev-lang", "package": "perl", "version": "5.40.2",
             "class": "RedundantVersion",
             "msg": "slot(0) keywords are overshadowed by version: 5.42.2"},
            {"category": "dev-lang", "package": "perl", "version": "5.42.2",
             "class": "VariableScope",
             "msg": "variable 'EROOT' used in 'src_configure' on line: 670"},
        ]

    monkeypatch.setattr(redundant.ci, "report", report)
    collector = RedundantVersionsCollector(Config(gentoo_repo=Path("/nonexistent")))
    asyncio.run(collector.setup())
    [section] = asyncio.run(collector.collect(Maintainer("perl@gentoo.org",
                                                        packages=["dev-lang/perl"])))

    [item] = section.items
    assert item.ref == "dev-lang/perl-5.40.2"
    assert item.text == ": slot(0) keywords are overshadowed by version: 5.42.2"
