# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass
class Config:
    # None for a clone in cache_dir that is kept up to date
    gentoo_repo: Path | None = None
    output_dir: Path = Path("~/.local/share/gentoodo/outbox")
    cache_dir: Path = Path("~/.cache/gentoodo")
    from_address: str = "noreply@gentoo.org"
    cc: str | None = None
    subject_prefix: str = "[Gentoo Reminder]"
    multipart: bool = True
    sendmail: str = "/usr/sbin/sendmail"
    github_repo: str = "gentoo/gentoo"
    github_token: str | None = None
    github_secret_file: str | None = None
    codeberg_repo: str = "gentoo/gentoo"
    bugzilla_api_key: str | None = None
    bugzilla_secret_file: str | None = None


# Each section's options, as Config fields with this prefix
SECTIONS = {"general": "", "github": "github_", "codeberg": "codeberg_", "bugzilla": "bugzilla_"}

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
        if (value := getattr(config, key)) is not None:
            setattr(config, key, Path(value).expanduser())

    for section in ("github", "codeberg"):
        if (repo := getattr(config, f"{section}_repo")).count("/") != 1:
            sys.exit(f"{path}: [{section}] repo is not owner/name: {repo}")

    for option, secret in SECRETS.items():
        if not (secret_file := getattr(config, option)):
            continue
        try:
            setattr(config, secret, Path(secret_file).expanduser().read_text().strip())
        except (OSError, UnicodeDecodeError) as e:
            sys.exit(f"{path}: {e}")
    return config
