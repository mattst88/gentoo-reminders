# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from gentoodo.config import load_config


def test_unknown_options(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\ngentoo_repo = "/gentoo"\nfoo = 1\n'
                    '[bugzila]\napi_key = "x"\n')
    with pytest.raises(SystemExit, match=r"unknown option: \[bugzila\], \[general\] foo"):
        load_config(str(path))


def test_sections(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\ngentoo_repo = "/gentoo"\n[github]\nrepo = "a/b"\n')
    assert load_config(str(path)).github_repo == "a/b"


def test_github_repo_needs_owner(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\ngentoo_repo = "/gentoo"\n[github]\nrepo = "gentoo"\n')
    with pytest.raises(SystemExit, match="not owner/name"):
        load_config(str(path))


def write_secret_config(tmp_path, secret_file, section="bugzilla"):
    path = tmp_path / "config.toml"
    path.write_text(f'[general]\ngentoo_repo = "/gentoo"\n'
                    f'[{section}]\nsecret_file = "{secret_file}"\n')
    return str(path)


def test_secret_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "key").write_text("secret\n")
    config = load_config(write_secret_config(tmp_path, "~/key"))
    assert config.bugzilla_api_key == "secret"


def test_github_secret_file(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("secret\n")
    config = load_config(write_secret_config(tmp_path, token_file, "github"))
    assert config.github_token == "secret"


def test_secret_file_missing(tmp_path):
    with pytest.raises(SystemExit, match="No such file"):
        load_config(write_secret_config(tmp_path, tmp_path / "key"))


def test_secret_file_not_text(tmp_path):
    secret_file = tmp_path / "key"
    secret_file.write_bytes(b"\xff")
    with pytest.raises(SystemExit, match="can't decode"):
        load_config(write_secret_config(tmp_path, secret_file))


@pytest.mark.parametrize("section, key", [("github", "token"), ("bugzilla", "api_key")])
def test_no_secrets_in_config(tmp_path, section, key):
    path = tmp_path / "config.toml"
    path.write_text(f'[general]\ngentoo_repo = "/gentoo"\n[{section}]\n{key} = "x"\n')
    with pytest.raises(SystemExit, match="unknown option"):
        load_config(str(path))
