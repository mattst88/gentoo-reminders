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
    subject_prefix: str = "[Gentoo Reminder]"
    multipart: bool = True
    github_repo: str = "gentoo/gentoo"
    bugzilla_api_key: str | None = None


# Each section's options, as Config fields with this prefix
SECTIONS = {"general": "", "github": "github_", "bugzilla": "bugzilla_"}


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    known = {f.name for f in fields(Config)}
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
    return config
