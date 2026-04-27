# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess

import pytest

from gentoo_reminders.maintainers import Maintainer, find_last_commits, load_maintainers

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


@pytest.fixture
def git_env(monkeypatch):
    # GIT_DIR and the like name another repository when the tests are run
    # from a git hook or `git rebase --exec`.
    for name in os.environ:
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")


def commit(repo, subject, author, committer, date):
    subprocess.run(
        ["git", "-C", repo, "commit", "-q", "--allow-empty", "-m", subject],
        check=True,
        env=os.environ | {
            "GIT_AUTHOR_NAME": "A", "GIT_AUTHOR_EMAIL": author,
            "GIT_COMMITTER_NAME": "C", "GIT_COMMITTER_EMAIL": committer,
            "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date,
        })


def test_find_last_commits(tmp_path, git_env):
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    commit(tmp_path, "first", "Dev@gentoo.org", "dev@gentoo.org", "2026-01-01T00:00:00+01:00")
    commit(tmp_path, "second", "dev@gentoo.org", "other@gentoo.org", "2026-01-02T00:00:00+01:00")
    commit(tmp_path, "third", "xdev@gentoo.org", "other@gentoo.org", "2026-01-03T00:00:00+01:00")

    dev = Maintainer("dev@gentoo.org", person=True)
    idle = Maintainer("idle@gentoo.org", person=True)
    project = Maintainer("other@gentoo.org")
    find_last_commits(tmp_path, [dev, idle, project])

    assert dev.last_authored == "2026-01-02T00:00:00+01:00 second"
    assert dev.last_committed == "2026-01-01T00:00:00+01:00 first"
    assert idle.last_authored is None and idle.last_committed is None
    assert project.last_committed is None

