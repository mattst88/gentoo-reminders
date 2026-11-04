# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import subprocess
from pathlib import Path

import pytest

from gentoodo import repo
from gentoodo.config import Config
from gentoodo.maintainers import load_maintainers

METADATA = "<pkgmetadata><maintainer><email>foo@gentoo.org</email></maintainer></pkgmetadata>"


def git(path, *args):
    subprocess.run(["git", "-C", path, "-c", "user.name=A", "-c", "user.email=a@gentoo.org",
                    *args], check=True, capture_output=True)


def add_file(path, name, text="x"):
    (path / name).parent.mkdir(parents=True, exist_ok=True)
    (path / name).write_text(text)
    git(path, "add", name)
    git(path, "commit", "-q", "-m", f"add {name}")


@pytest.fixture
def upstream(tmp_path, git_env, monkeypatch):
    path = tmp_path / "upstream"
    git(tmp_path, "init", "-q", "-b", "master", str(path))
    git(path, "config", "uploadpack.allowFilter", "true")
    add_file(path, "app-misc/foo/metadata.xml", METADATA)
    add_file(path, "app-misc/foo/foo-1.ebuild")
    monkeypatch.setattr(repo, "URL", path.as_uri())
    return path


def is_bare(path):
    return subprocess.run(["git", "-C", path, "rev-parse", "--is-bare-repository"],
                          check=True, capture_output=True, text=True).stdout.strip() == "true"


def test_clone_and_fetch(tmp_path, upstream):
    config = Config(cache_dir=tmp_path / "cache")
    path = asyncio.run(repo.update(config, pull=True))
    assert path == tmp_path / "cache" / "gentoo.git"
    assert is_bare(path)
    assert not (tmp_path / "cache" / "gentoo.git.partial").exists()
    # A partial clone, which fetches the metadata.xml files it lacks
    missing = subprocess.run(["git", "-C", path, "rev-list", "--objects", "--missing=print",
                              "HEAD"], check=True, capture_output=True, text=True).stdout
    assert missing.count("?") == 2
    assert list(load_maintainers(path)) == ["foo@gentoo.org"]

    add_file(upstream, "app-misc/bar/metadata.xml", METADATA)
    asyncio.run(repo.update(config, pull=False))
    assert load_maintainers(path)["foo@gentoo.org"].packages == ["app-misc/foo"]
    asyncio.run(repo.update(config, pull=True))
    assert load_maintainers(path)["foo@gentoo.org"].packages == [
        "app-misc/bar", "app-misc/foo"]


def test_failed_clone(tmp_path, upstream, monkeypatch):
    monkeypatch.setattr(repo, "URL", (tmp_path / "missing").as_uri())
    config = Config(cache_dir=tmp_path / "cache")
    with pytest.raises(repo.CloneError):
        asyncio.run(repo.update(config, pull=True))
    assert not (tmp_path / "cache" / "gentoo.git").exists()


def test_own_repository(tmp_path, upstream):
    config = Config(gentoo_repo=upstream, cache_dir=tmp_path / "cache")
    assert asyncio.run(repo.update(config, pull=False)) == upstream
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("bare", [True, False])
def test_own_repository_update(tmp_path, upstream, bare):
    own = tmp_path / "own"
    git(tmp_path, "clone", "-q", *(["--mirror"] if bare else []), str(upstream), str(own))
    add_file(upstream, "app-misc/bar/metadata.xml", METADATA)
    config = Config(gentoo_repo=own, cache_dir=tmp_path / "cache")
    asyncio.run(repo.update(config, pull=True))
    assert "app-misc/bar" in load_maintainers(own)["foo@gentoo.org"].packages


def test_own_repository_missing(tmp_path, git_env):
    config = Config(gentoo_repo=Path(tmp_path / "missing"), cache_dir=tmp_path / "cache")
    with pytest.raises(RuntimeError):
        asyncio.run(repo.update(config, pull=True))
