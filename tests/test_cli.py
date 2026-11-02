# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import asyncio
from datetime import date
from pathlib import Path

import pytest

from gentoo_reminders import __version__, cli
from gentoo_reminders.cli import collector_names, month, parse_args, process
from gentoo_reminders.collectors.base import Collector, Item, Section
from gentoo_reminders.config import Config
from gentoo_reminders.maintainers import Maintainer


class FakeCollector(Collector):
    def __init__(self, sections):
        self.sections = sections

    async def collect(self, maintainer):
        return self.sections


def written(tmp_path, *sections):
    config = Config(gentoo_repo=Path("/nonexistent"), output_dir=tmp_path)
    maintainer = Maintainer("x11@gentoo.org", packages=["x11-libs/libdrm"])
    asyncio.run(process(config, maintainer, [FakeCollector(list(sections))], False,
                        asyncio.Semaphore(1)))
    return list(tmp_path.glob("*.eml"))


NOTICE = Section("Open GitHub Pull Requests", text="Could not be fetched from GitHub.",
                 notice=True)


def test_notice_alone_sends_no_email(tmp_path):
    assert not written(tmp_path, NOTICE)


def test_notice_is_shown_with_other_sections(tmp_path):
    [email] = written(tmp_path, NOTICE, Section("Open Bugs", [Item("Bug #1")]))
    assert b"Could not be fetched from GitHub." in email.read_bytes()


def test_collector_names_in_email_order():
    assert collector_names("shortlog,github_prs,shortlog") == ["github_prs", "shortlog"]


def test_month():
    assert month("2026-10") == (date(2026, 10, 1), date(2026, 10, 31))
    for value in ("2026-13", "October", "2026-10-01"):
        with pytest.raises(argparse.ArgumentTypeError):
            month(value)


def test_send_outbox_maintainer(tmp_path, monkeypatch):
    config = Config(gentoo_repo=Path("/nonexistent"), output_dir=tmp_path)
    calls = []
    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "send_outbox", lambda *args: calls.append(args) or 0)

    cli.main(["--config", "x", "--send-outbox", "--maintainer", "larry@gentoo.org"])
    assert calls == [(tmp_path, config.sendmail, False, "larry@gentoo.org")]


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        parse_args(["--version"])
    assert e.value.code == 0
    assert capsys.readouterr().out == f"gentoo-reminders {__version__}\n"
