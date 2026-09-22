# Spinin-mac.spec — PyInstaller build of the macOS .app bundle.
# Build with:  pyinstaller --noconfirm Spinin-mac.spec
#
# The Windows build lives in Spinin.spec. Kept apart rather than branched inside one file,
# because almost nothing outside the source list is shared: different icon format, a bundle
# to assemble, and an Info.plist that has to declare what the app intends to do.
#
# NOT YET RUN ON A MAC beyond CI — see docs/MACOS.md.

import re

block_cipher = None

_branding = open("branding.py", encoding="utf-8").read()
version = re.search(r'APP_VERSION = "([^"]+)"', _branding).group(1)
open("VERSION.txt", "w", encoding="utf-8").write(version)

a = Analysis(
    ["main_windows.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("ddj-flx4.webp", "."),   # the controller photo the canvas draws
        ("Spinin2.png", "."),
        ("LICENSE", "."),
    ],
    hiddenimports=[
        # mido picks its backend by module name at run time, so nothing imports these where
        # PyInstaller can see it. Leave them out and the built app never finds the controller.
        "mido.backends.rtmidi",
        "rtmidi",
        # Reached only from inside the macOS branches, which PyInstaller does not follow.
        "Quartz", "AppKit", "Foundation", "objc",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc", "doctest", "pdb", "test",
              "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuick3D", "PyQt6.QtWebEngineCore",
              "PyQt6.QtWebEngineWidgets", "PyQt6.QtMultimedia", "PyQt6.QtBluetooth",
              "PyQt6.QtPositioning", "PyQt6.QtSql", "PyQt6.QtTest",
              "PyQt6.Qt3DCore", "PyQt6.QtCharts", "PyQt6.QtDataVisualization",
              # The Windows backend and its dependencies have no business in a Mac build.
              "win32gui", "win32process", "win32api", "win32con",
              "pycaw", "comtypes", "AppOpener", "_input_win", "_audio_win"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Spinin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,   # the app takes no file arguments, and this breaks the event loop
    target_arch=None,       # whatever the build machine is; universal2 needs fat wheels
    codesign_identity=None,
    entitlements_file=None,
    icon="Spinin2.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Spinin",
)

app = BUNDLE(
    coll,
    name="Spinin.app",
    icon="Spinin2.icns",
    # Must match macos_system.own_identifier(), which is how the app recognises its own
    # window and avoids switching profile while you are editing a mapping.
    bundle_identifier="org.spinin.Spinin",
    version=version,
    info_plist={
        "CFBundleName": "Spinin",
        "CFBundleDisplayName": "Spinin",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "NSHumanReadableCopyright": "Copyright (C) 2026 farzonline. GPL-3.0-or-later.",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        # Spinin's whole job is sending keystrokes to other apps and knowing which app is in
        # front, so macOS will ask the user to grant these. The strings are what that prompt
        # shows; without them the prompt is blank and reads as something to refuse.
        "NSAppleEventsUsageDescription":
            "Spinin uses AppleScript to restart or shut down the Mac when you map a control "
            "to one of those actions.",
        "NSSystemAdministrationUsageDescription":
            "Spinin needs permission to send the keyboard shortcuts you map to your "
            "controller.",
    },
)
