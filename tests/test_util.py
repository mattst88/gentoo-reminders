# SPDX-License-Identifier: GPL-3.0-or-later

import gzip
import io
from datetime import date

from gentoo_reminders import util
from gentoo_reminders.util import fetch, month_days, previous_month, redact


def test_previous_month():
    assert previous_month(date(2026, 10, 1)) == (date(2026, 9, 1), date(2026, 9, 30))
    assert previous_month(date(2026, 3, 31)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert previous_month(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 31))


def test_month_days():
    assert month_days(date(2026, 10, 27)) == (date(2026, 10, 1), date(2026, 10, 31))
    assert month_days(date(2028, 2, 1)) == (date(2028, 2, 1), date(2028, 2, 29))
    assert month_days(date(2026, 12, 31)) == (date(2026, 12, 1), date(2026, 12, 31))


def test_redact():
    assert (redact("https://example.org/rest/bug?id=1&Bugzilla_api_key=secret&limit=5")
            == "https://example.org/rest/bug?id=1&Bugzilla_api_key=REDACTED&limit=5")
    assert redact("https://example.org/rest/bug?id=1") == "https://example.org/rest/bug?id=1"


class Response(io.BytesIO):
    def __init__(self, data, headers):
        super().__init__(data)
        self.headers = headers


def test_fetch_decompresses(monkeypatch):
    requests = []

    def urlopen(request, timeout):
        requests.append(request)
        return Response(gzip.compress(b"data"), {"Content-Encoding": "gzip"})

    monkeypatch.setattr(util, "urlopen", urlopen)
    assert fetch("https://example.org/") == b"data"
    assert requests[0].get_header("Accept-encoding") == "gzip"

    monkeypatch.setattr(util, "urlopen", lambda request, timeout: Response(b"data", {}))
    assert fetch("https://example.org/") == b"data"
