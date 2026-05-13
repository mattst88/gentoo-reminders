# SPDX-License-Identifier: GPL-3.0-or-later

from gentoo_reminders.collectors.github_prs import group_by_package


def test_group_by_package():
    prs = [
        {"number": 2, "title": "Bump both", "url": "https://example.org/2", "files": [
            {"path": "x11-libs/libdrm/libdrm-2.ebuild"},
            {"path": "x11-libs/libdrm/Manifest"},
            {"path": "media-libs/mesa/mesa-2.ebuild"},
        ]},
        {"number": 1, "title": "New eclass", "url": "https://example.org/1", "files": [
            {"path": "eclass/foo.eclass"},
            {"path": "media-libs/mesa/files/foo.patch"},
        ]},
    ]

    grouped = group_by_package(prs)

    assert set(grouped) == {"x11-libs/libdrm", "media-libs/mesa"}
    assert [item.ref for item in grouped["x11-libs/libdrm"]] == ["PR #2"]
    assert [item.ref for item in grouped["media-libs/mesa"]] == ["PR #1", "PR #2"]
    assert grouped["media-libs/mesa"][0].url == "https://example.org/1"
