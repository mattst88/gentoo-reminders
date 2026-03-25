# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .collectors.base import Section
from .config import Config
from .maintainers import Maintainer

env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
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
