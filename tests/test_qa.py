# SPDX-License-Identifier: GPL-3.0-or-later

from gentoo_reminders.collectors.qa import new_warnings


def result(cls, msg, version="5.42.2", package="perl", category="dev-lang"):
    return {"category": category, "package": package, "version": version,
            "class": cls, "msg": msg}


def scope(variable, version, lines):
    return result("EbuildVariableScope",
                  f"variable '{variable}' used in 'src_configure' on lines: {lines}",
                  version)


def use_dep(pkgs):
    return result("MissingUseDepDefault",
                  "DEPEND=\"media-libs/mesa[osmesa]\": USE flag 'osmesa' missing "
                  f"from packages: [ {', '.join(pkgs)} ]",
                  "1.1.0-r1", "aranym", "app-emulation")


def test_new_warnings():
    before = [
        scope("EROOT", "5.40.2", "666, 667"),
        use_dep(["media-libs/mesa-26.1.8"]),
        result("RedundantVersion", "slot(0) keywords are overshadowed by version: 5.42.0"),
        {"class": "EmptyProject", "msg": "Project has no members"},
    ]
    after = [
        # Carried over to a new version, on other lines
        scope("EROOT", "5.42.2", "670, 671"),
        scope("ED", "5.42.2", "680"),
        # Listing a new version of the dependency
        use_dep(["media-libs/mesa-26.1.8", "media-libs/mesa-26.2.5"]),
        # Not an error or a warning
        result("RedundantVersion", "slot(0) keywords are overshadowed by version: 5.42.2"),
        # From a check with no results before, or one pkgcheck does not know
        result("NonexistentBlocker", "nonexistent blocker RDEPEND=\"!<dev-lang/perl-5\""),
        result("SomeFutureCheck", "something"),
        # Not a package's
        {"class": "EmptyProject", "msg": "Project has no members"},
    ]

    warnings = new_warnings(before, after)
    assert list(warnings) == ["dev-lang/perl"]
    [item] = warnings["dev-lang/perl"]
    assert item.ref == "dev-lang/perl-5.42.2"
    assert item.text == ": EbuildVariableScope: variable 'ED' used in 'src_configure' on lines: 680"
