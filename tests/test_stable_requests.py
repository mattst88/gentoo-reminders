# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
from pathlib import Path

from gentoo_reminders.collectors import stable_requests
from gentoo_reminders.collectors.stable_requests import StableRequestsCollector
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer


def result(package, version, cls, msg):
    category, name = package.split("/")
    return {"category": category, "package": name, "version": version,
            "class": cls, "msg": msg}


def test_stable_requests(monkeypatch):
    async def report(cache_dir):
        return [
            result("x11-libs/libdrm", "2.4.124", "StableRequest",
                   "slot(0) no change in 120 days for unstable keywords: [ ~amd64, ~x86 ]"),
            result("dev-libs/libevdev", "1.13.7", "StableRequest",
                   "slot(0) no change in 90 days for unstable keyword: [ ~amd64 ]"),
            result("x11-libs/libdrm", "2.4.125", "PotentialStable",
                   "slot(0), stabled arch: [ x86 ], potential: [ ~amd64 ]"),
        ]

    monkeypatch.setattr(stable_requests.ci, "report", report)
    collector = StableRequestsCollector(Config(gentoo_repo=Path("/nonexistent")))
    asyncio.run(collector.setup())
    [section] = asyncio.run(collector.collect(Maintainer("x11@gentoo.org",
                                                        packages=["x11-libs/libdrm"])))

    assert [(item.ref, item.text) for item in section.items] == [
        ("x11-libs/libdrm-2.4.124", " (120 days)"),
    ]
