# SPDX-License-Identifier: GPL-3.0-or-later

from gentoo_reminders.cli import collector_names


def test_collector_names_in_email_order():
    assert collector_names("shortlog,github_prs,shortlog") == ["github_prs", "shortlog"]
