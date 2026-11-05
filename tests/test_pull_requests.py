# SPDX-License-Identifier: GPL-3.0-or-later

from gentoodo.collectors.pull_requests import PullRequest, group_by_package


def test_group_by_package():
    prs = [
        PullRequest(2, "Bump both", "https://example.org/2", [
            "x11-libs/libdrm/libdrm-2.ebuild",
            "x11-libs/libdrm/Manifest",
            "media-libs/mesa/mesa-2.ebuild",
        ]),
        PullRequest(1, "New eclass", "https://example.org/1", [
            "eclass/foo.eclass",
            "media-libs/mesa/files/foo.patch",
        ]),
    ]

    grouped = group_by_package(prs)

    assert set(grouped) == {"x11-libs/libdrm", "media-libs/mesa"}
    assert [item.ref for item in grouped["x11-libs/libdrm"]] == ["PR #2"]
    mesa = {item.ref: item.url for item in grouped["media-libs/mesa"]}
    assert mesa == {"PR #1": "https://example.org/1", "PR #2": "https://example.org/2"}
