# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import contextlib
import gzip
import logging
import re
import time
from datetime import UTC, date, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

USER_AGENT = "gentoo-reminders"


async def run(*args: str, timeout: int = 300) -> str:
    """Run a command and return its stdout, raising if it fails or times out."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()
        raise RuntimeError(f"{args[0]} timed out after {timeout}s") from None

    if proc.returncode != 0:
        raise RuntimeError(
            f"{args[0]} exited with status {proc.returncode}: {stderr.decode().strip()}")
    return stdout.decode()


def month_days(day: date) -> tuple[date, date]:
    """Return the first and last days of `day`'s month."""
    first = day.replace(day=1)
    return first, (first + timedelta(days=31)).replace(day=1) - timedelta(days=1)


def previous_month(today: date | None = None) -> tuple[date, date]:
    """Return the first and last days of the month before `today`'s, in UTC."""
    today = today or datetime.now(UTC).date()
    return month_days(today.replace(day=1) - timedelta(days=1))


def redact(url: str) -> str:
    """Hide API keys in a URL, so that it can be logged."""
    return re.sub(r"(api_key=)[^&]*", r"\1REDACTED", url, flags=re.IGNORECASE)


def _get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    with urlopen(request, timeout=120) as response:
        data = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data


def fetch(url: str) -> bytes:
    """GET a URL, retrying server and connection errors."""
    for delay in (1, 4):
        try:
            return _get(url)
        except (URLError, TimeoutError) as e:
            if isinstance(e, HTTPError) and e.code < 500:
                raise
            log.warning("%s: %s, retrying in %ds", redact(url), e, delay)
            time.sleep(delay)
    return _get(url)
