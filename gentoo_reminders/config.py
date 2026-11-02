# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass
class Config:
    gentoo_repo: Path
    output_dir: Path = Path("~/.local/share/gentoo-reminders/outbox")
    cache_dir: Path = Path("~/.cache/gentoo-reminders")
    from_address: str = "noreply@gentoo.org"
    cc: str | None = None
    subject_prefix: str = "[Gentoo Reminder]"
    multipart: bool = True
    sendmail: str = "/usr/sbin/sendmail"
    github_repo: str = "gentoo/gentoo"
    github_token: str | None = None
    github_secret_file: str | None = None
    bugzilla_api_key: str | None = None
    bugzilla_secret_file: str | None = None


# Each section's options, as Config fields with this prefix
SECTIONS = {"general": "", "github": "github_", "bugzilla": "bugzilla_"}

# Each Config field naming a file, and the one set from that file's contents
SECRETS = {"github_secret_file": "github_token", "bugzilla_secret_file": "bugzilla_api_key"}


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    known = {f.name for f in fields(Config)} - set(SECRETS.values())
    options = {}
    unknown = [f"[{section}]" for section in data if section not in SECTIONS]
    for section, prefix in SECTIONS.items():
        for key, value in data.get(section, {}).items():
            if prefix + key in known:
                options[prefix + key] = value
            else:
                unknown.append(f"[{section}] {key}")
    if unknown:
        sys.exit(f"{path}: unknown option: {', '.join(unknown)}")

    try:
        config = Config(**options)
    except TypeError as e:
        sys.exit(f"{path}: {e}")

    for key in ("gentoo_repo", "output_dir", "cache_dir"):
        setattr(config, key, Path(getattr(config, key)).expanduser())

    for option, secret in SECRETS.items():
        if not (secret_file := getattr(config, option)):
            continue
        try:
            setattr(config, secret, Path(secret_file).expanduser().read_text().strip())
        except (OSError, UnicodeDecodeError) as e:
            sys.exit(f"{path}: {e}")
    return config
