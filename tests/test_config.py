# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from gentoo_reminders.config import load_config


def test_unknown_options(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\ngentoo_repo = "/gentoo"\nfoo = 1\n'
                    '[bugzila]\napi_key = "x"\n')
    with pytest.raises(SystemExit, match=r"unknown option: \[bugzila\], \[general\] foo"):
        load_config(str(path))


def test_sections(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\ngentoo_repo = "/gentoo"\n'
                    '[github]\nrepo = "a/b"\n[bugzilla]\napi_key = "x"\n')
    config = load_config(str(path))
    assert (config.github_repo, config.bugzilla_api_key) == ("a/b", "x")
