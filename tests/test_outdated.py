# SPDX-License-Identifier: GPL-3.0-or-later

from gentoo_reminders.collectors.base import Item
from gentoo_reminders.collectors.outdated import parse_feed

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Outdated Packages for X11 &lt;x11@gentoo.org&gt;</title>
  <entry>
    <title>dev-libs/libevdev</title>
    <summary type="html">Version 1.14.0 is available, while the latest version in the Gentoo tree is 1.13.7.</summary>
  </entry>
  <entry>
    <title>x11-libs/libdrm</title>
    <summary type="html">Something else.</summary>
  </entry>
</feed>
"""


def test_parse_feed():
    assert parse_feed(FEED) == [
        Item("dev-libs/libevdev", ": 1.13.7 -> 1.14.0",
             "https://packages.gentoo.org/packages/dev-libs/libevdev"),
        Item("x11-libs/libdrm", ": Something else.",
             "https://packages.gentoo.org/packages/x11-libs/libdrm"),
    ]
