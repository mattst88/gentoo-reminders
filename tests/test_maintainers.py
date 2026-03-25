# SPDX-License-Identifier: GPL-3.0-or-later

from gentoo_reminders.maintainers import load_maintainers

METADATA = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE pkgmetadata SYSTEM "https://www.gentoo.org/dtd/metadata.dtd">
<pkgmetadata>
{}
</pkgmetadata>
"""


def add_package(repo, package, body):
    path = repo / package / "metadata.xml"
    path.parent.mkdir(parents=True)
    path.write_text(METADATA.format(body))


def test_load_maintainers(tmp_path):
    add_package(tmp_path, "app-editors/emacs", """
        <maintainer type="project">
            <email>Emacs@gentoo.org</email>
        </maintainer>
        <upstream>
            <maintainer><email>upstream@gnu.org</email></maintainer>
        </upstream>""")
    add_package(tmp_path, "app-editors/xemacs", """
        <maintainer type="project"><email>xemacs@gentoo.org</email></maintainer>
        <maintainer type="person" proxied="yes">
            <name>Some Body</name>
            <email>somebody@example.com</email>
        </maintainer>""")
    add_package(tmp_path, "acct-group/emacs", """
        <maintainer type="project"><email>emacs@gentoo.org</email></maintainer>""")
    add_package(tmp_path, "app-misc/orphan", "<!-- maintainer-needed -->")

    maintainers = load_maintainers(tmp_path)

    assert list(maintainers) == [
        "emacs@gentoo.org", "somebody@example.com", "xemacs@gentoo.org"]
    assert maintainers["emacs@gentoo.org"].packages == [
        "acct-group/emacs", "app-editors/emacs"]
    assert not maintainers["emacs@gentoo.org"].person
    assert maintainers["xemacs@gentoo.org"].packages == ["app-editors/xemacs"]
    assert maintainers["somebody@example.com"].person

