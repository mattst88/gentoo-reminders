# SPDX-License-Identifier: GPL-3.0-or-later

import os

import pytest


@pytest.fixture
def git_env(monkeypatch):
    # GIT_DIR and the like name another repository when the tests are run
    # from a git hook or `git rebase --exec`.
    for name in os.environ:
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
