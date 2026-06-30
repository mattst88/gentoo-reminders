# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
from datetime import UTC, datetime

from gentoo_reminders import ci


def test_report_fetches_and_reads_once(monkeypatch, tmp_path):
    commands = []

    async def run(*args, timeout=300):
        commands.append(args)
        return "abc123\n" if "log" in args else "<checks/>"

    monkeypatch.setattr(ci, "run", run)
    monkeypatch.setattr(ci, "_updated", False)
    monkeypatch.setattr(ci, "_reports", {})
    monkeypatch.setattr(ci, "_lock", asyncio.Lock())

    async def reports():
        # Both at once, as collectors' setup runs
        return await asyncio.gather(
            ci.report(tmp_path),
            ci.report(tmp_path, datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC)))

    # Both resolve to the same report, which is read once.
    assert asyncio.run(reports()) == [[], []]
    assert [c[1:3] for c in commands] == [
        ("clone", "--quiet"), ("-C", str(tmp_path / "gentoo-ci.git")),
        ("-C", str(tmp_path / "gentoo-ci.git")), ("-C", str(tmp_path / "gentoo-ci.git")),
    ]
    assert [c[3] for c in commands[1:]] == ["log", "show", "log"]
    assert "--before=2026-09-30 23:59:59 +0000" in commands[3]
    assert commands[2][-1] == "abc123:output.xml"
