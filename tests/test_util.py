# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import date

from gentoo_reminders.util import previous_month


def test_previous_month():
    assert previous_month(date(2026, 10, 1)) == (date(2026, 9, 1), date(2026, 9, 30))
    assert previous_month(date(2026, 3, 31)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert previous_month(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 31))

