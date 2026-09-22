# SPDX-License-Identifier: GPL-3.0-or-later
# app_scanner.py
# The list of programs installed on this PC, so "Open an app" can be picked from a list
# instead of hunting for an .exe.
#
# The Start Menu is the source: every installer puts a shortcut there, the shortcut carries
# the name a person recognises, and launching the .lnk gets the working directory and any
# arguments for free — which resolving it down to the bare .exe would throw away.

import os
import sys

IS_MAC = sys.platform == "darwin"

# Folders Windows itself hides from the Start Menu, or that hold uninstallers and readmes.
SKIP_WORDS = ("uninstall", "uninstaller", "readme", "release notes", "help", "documentation",
              "license", "licence", "website", "web site", "support", "manual", "eula",
              "report a", "feedback", "repair", "remove ")

START_MENUS = (
    os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                 r"Microsoft\Windows\Start Menu\Programs"),
    os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
)

_cache = None


def _wanted(name):
    low = name.lower()
    return not any(word in low for word in SKIP_WORDS)


def scan(roots=None):
    """[(display name, path to launch)] for the programs on this PC, sorted by name.

    macOS keeps applications as .app bundles in a handful of known folders rather than as
    shortcuts, so that platform scans those instead.
    """
    if IS_MAC:
        from macos_system import scan_apps
        return scan_apps(roots)
    found = {}
    for root in (roots if roots is not None else START_MENUS):
        if not root or not os.path.isdir(root):
            continue
        for folder, _dirs, files in os.walk(root):
            for filename in files:
                stem, ext = os.path.splitext(filename)
                if ext.lower() not in (".lnk", ".url"):
                    continue
                if not _wanted(stem):
                    continue
                # Two Start Menus, and often the same app in both: first one in wins.
                found.setdefault(stem, os.path.join(folder, filename))
    return sorted(found.items(), key=lambda pair: pair[0].lower())


def installed(refresh=False):
    """Same as scan(), cached — walking both Start Menus takes a moment."""
    global _cache
    if _cache is None or refresh:
        _cache = scan()
    return _cache


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "Games"))
        for rel in ("Notepad.lnk", "Games/Solitaire.lnk", "Uninstall Thing.lnk",
                    "Thing Readme.lnk", "Notes.txt", "Site.url"):
            open(os.path.join(tmp, rel), "w").close()
        names = [n for n, _ in scan([tmp])]
        assert names == ["Notepad", "Site", "Solitaire"], names
        assert scan([tmp])[0][1].endswith("Notepad.lnk")
        assert scan([tmp, tmp]) == scan([tmp]), "the same folder twice must not duplicate"
    assert scan(["X:/does/not/exist"]) == []

    real = installed()
    assert real is installed(), "second call must come from the cache"
    print(f"app_scanner OK — {len(real)} programs found on this PC")
    for name, path in real[:5]:
        print(f"   {name}  ->  {os.path.basename(path)}")
