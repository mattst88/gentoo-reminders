# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class Maintainer:
    email: str
    person: bool = False
    packages: list[str] = field(default_factory=list)


def load_maintainers(repo: Path) -> dict[str, Maintainer]:
    """Map each maintainer's email to their packages, from metadata.xml."""
    maintainers: dict[str, Maintainer] = {}
    for path in sorted(repo.glob("*/*/metadata.xml")):
        package = f"{path.parts[-3]}/{path.parts[-2]}"
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as e:
            log.warning("Skipping %s: %s", path, e)
            continue

        # Direct children only: <upstream> has <maintainer> elements too.
        for element in root.findall("maintainer"):
            email = (element.findtext("email") or "").strip().lower()
            if not email:
                continue
            maintainer = maintainers.setdefault(email, Maintainer(email))
            maintainer.person |= element.get("type") == "person"
            if package not in maintainer.packages[-1:]:
                maintainer.packages.append(package)

    return dict(sorted(maintainers.items()))

