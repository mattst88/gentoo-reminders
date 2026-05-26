# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import date

from gentoo_reminders.util import previous_month, redact


def test_previous_month():
    assert previous_month(date(2026, 10, 1)) == (date(2026, 9, 1), date(2026, 9, 30))
    assert previous_month(date(2026, 3, 31)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert previous_month(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 31))


def test_redact():
    assert (redact("https://example.org/rest/bug?id=1&Bugzilla_api_key=secret&limit=5")
            == "https://example.org/rest/bug?id=1&Bugzilla_api_key=REDACTED&limit=5")
    assert redact("https://example.org/rest/bug?id=1") == "https://example.org/rest/bug?id=1"
