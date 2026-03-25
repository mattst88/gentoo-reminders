# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import contextlib
from datetime import UTC, date, datetime, timedelta

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


def previous_month(today: date | None = None) -> tuple[date, date]:
    """Return the first and last days of the month before `today`'s, in UTC."""
    today = today or datetime.now(UTC).date()
    last = today.replace(day=1) - timedelta(days=1)
    return last.replace(day=1), last

