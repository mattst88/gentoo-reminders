# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import subprocess
from datetime import UTC, datetime
from email.message import EmailMessage
from email.parser import BytesHeaderParser
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .collectors.base import Section
from .config import Config
from .maintainers import Maintainer

log = logging.getLogger(__name__)

env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(("html.j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render(config: Config, maintainer: Maintainer,
           sections: list[Section]) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = maintainer.email
    msg["From"] = config.from_address
    msg["Subject"] = f"{config.subject_prefix} Your package maintenance summary"
    msg["Date"] = formatdate(usegmt=True)
    domain = parseaddr(config.from_address)[1].rpartition("@")[2]
    msg["Message-ID"] = make_msgid(domain=domain or None)

    context = {"maintainer": maintainer, "sections": sections}
    text = env.get_template("reminder.txt.j2").render(context)
    msg.set_content(text, cte=cte(text))
    if config.multipart:
        html = env.get_template("reminder.html.j2").render(context)
        msg.add_alternative(html, subtype="html", cte=cte(html))
    return msg


def cte(text: str) -> str | None:
    """Avoid quoted-printable and base64 where possible, to keep the files
    readable."""
    if any(len(line) > 998 for line in text.splitlines()):
        return None
    return "7bit" if text.isascii() else "8bit"


def write_email(output_dir: Path, email: str, msg: EmailMessage) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    name = email.replace("@", "_at_").replace("/", "_")
    path = output_dir / f"{name}_{timestamp}.eml"
    path.write_bytes(msg.as_bytes())
    return path


def send_outbox(output_dir: Path, sendmail: str, dry_run: bool = False) -> int:
    """Send each .eml file in `output_dir`, moving it to `sent` there once
    sent. Return how many failed, which are left to be retried."""
    sent = output_dir / "sent"
    failed = 0
    for path in sorted(output_dir.glob("*.eml")):
        data = path.read_bytes()
        to = BytesHeaderParser().parsebytes(data)["To"]
        if dry_run:
            log.info("Would send %s to %s", path.name, to)
            continue
        try:
            result = subprocess.run([sendmail, "-t", "-oi"], input=data,
                                    capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            log.error("Failed to send %s: %s timed out", path.name, sendmail)
            failed += 1
            continue
        if result.returncode:
            log.error("Failed to send %s: %s exited with status %d: %s", path.name,
                      sendmail, result.returncode, result.stderr.decode().strip())
            failed += 1
            continue
        sent.mkdir(exist_ok=True)
        path.rename(sent / path.name)
        log.info("Sent %s to %s", path.name, to)
    return failed
