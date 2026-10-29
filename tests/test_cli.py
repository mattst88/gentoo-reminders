# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
from datetime import date

import pytest

from gentoo_reminders import __version__
from gentoo_reminders.cli import collector_names, month, parse_args


def test_collector_names_in_email_order():
    assert collector_names("shortlog,github_prs,shortlog") == ["github_prs", "shortlog"]


def test_month():
    assert month("2026-10") == (date(2026, 10, 1), date(2026, 10, 31))
    for value in ("2026-13", "October", "2026-10-01"):
        with pytest.raises(argparse.ArgumentTypeError):
            month(value)


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        parse_args(["--version"])
    assert e.value.code == 0
    assert capsys.readouterr().out == f"gentoo-reminders {__version__}\n"
