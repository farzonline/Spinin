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


def _app_paths_entry(name):
    """What the Run box would open for this name, from the App Paths registry.

    Windows keeps a key here for programs that want to be launchable by name without being
    on PATH, which is how "chrome" and "spotify" work in Run.
    """
    import winreg
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for key_name in (name, f"{name}.exe"):
            try:
                with winreg.OpenKey(
                        root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{key_name}"
                ) as key:
                    value = winreg.QueryValueEx(key, "")[0]
            except OSError:
                continue
            if value:
                return value.strip('"')
    return None


def resolve(name):
    """A path to open for `name`, or None if nothing on this PC matches.

    Replaces what AppOpener used to do. AppOpener could not be kept: it rebuilt a cache
    inside its own package folder at import time, so once Spinin was installed under
    Program Files every ordinary launch died with a PermissionError before the window
    ever appeared.

    Looks where a person would expect, in order: an actual path, then PATH, then the App
    Paths registry, then the Start Menu by name.
    """
    name = (name or "").strip().strip('"')
    if not name:
        return None
    if os.path.exists(name):
        return name
    import shutil
    found = shutil.which(name) or (None if IS_MAC else shutil.which(f"{name}.exe"))
    if found:
        return found
    if not IS_MAC:
        found = _app_paths_entry(name)
        if found and os.path.exists(found):
            return found
    wanted = name.casefold()
    shortcuts = installed()
    for label, path in shortcuts:
        if label.casefold() == wanted:
            return path
    for label, path in shortcuts:  # "spotify" should still find "Spotify Premium"
        if wanted in label.casefold():
            return path
    return None


if __name__ == "__main__":
    import tempfile

    # scan() means something different per platform, so the fixture has to match: Start Menu
    # shortcuts on Windows, .app bundles on macOS.
    with tempfile.TemporaryDirectory() as tmp:
        if IS_MAC:
            for entry in ("Safari.app", "Mail.app", "Screen Sharing.app", "notes.txt"):
                os.makedirs(os.path.join(tmp, entry), exist_ok=True)
            expected, suffix = ["Mail", "Safari"], "Mail.app"
        else:
            os.makedirs(os.path.join(tmp, "Games"))
            for rel in ("Notepad.lnk", "Games/Solitaire.lnk", "Uninstall Thing.lnk",
                        "Thing Readme.lnk", "Notes.txt", "Site.url"):
                open(os.path.join(tmp, rel), "w").close()
            expected, suffix = ["Notepad", "Site", "Solitaire"], "Notepad.lnk"
        names = [n for n, _ in scan([tmp])]
        assert names == expected, names
        assert scan([tmp])[0][1].endswith(suffix)
        assert scan([tmp, tmp]) == scan([tmp]), "the same folder twice must not duplicate"
    assert scan([os.path.join(tempfile.gettempdir(), "spinin-no-such-folder")]) == []

    real = installed()
    assert real is installed(), "second call must come from the cache"

    # resolve() replaced AppOpener, so it has to handle what AppOpener handled.
    assert resolve("") is None and resolve(None) is None
    assert resolve("definitely-not-an-app-xyz") is None, "an unknown name resolves to nothing"
    here = os.path.abspath(__file__)
    assert resolve(here) == here, "an existing path is used as it stands"
    assert resolve(f'"{here}"') == here, "a quoted path still resolves"
    if not IS_MAC:
        # notepad is on PATH on every Windows install, so this proves the PATH step.
        found = resolve("notepad")
        assert found and found.lower().endswith("notepad.exe"), found
        # Compared case-insensitively: which() echoes back the spelling it was given, and
        # Windows paths do not care either way.
        assert resolve("NOTEPAD").lower() == found.lower(), "matching must not care about case"
        if real:
            by_name = resolve(real[0][0])
            assert by_name, f"a Start Menu entry should resolve: {real[0][0]}"
    # Nothing here may run a shell, so a name with shell characters is just a name.
    assert resolve("foo & echo pwned") is None, "must not treat a name as a command"
    print(f"app_scanner OK — {len(real)} programs found on this PC")
    for name, path in real[:5]:
        print(f"   {name}  ->  {os.path.basename(path)}")
