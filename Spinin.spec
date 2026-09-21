# Spinin.spec — PyInstaller build for the Spinin release.
# Build with:  pyinstaller --noconfirm Spinin.spec
#
# One folder rather than one file: a --onefile build unpacks itself to a temp directory on
# every launch, which costs a few seconds of start-up and trips some antivirus heuristics.
# The installer hides the folder anyway, so there is nothing to gain from it.

import re

block_cipher = None

_branding = open("branding.py", encoding="utf-8").read()
version = re.search(r'APP_VERSION = "([^"]+)"', _branding).group(1)
parts = tuple(int(n) for n in (version.split(".") + ["0", "0", "0"])[:4])

# Written from branding.py rather than kept by hand, so the version in the file properties
# can never drift from the version the About box reports.
open("version_info.txt", "w", encoding="utf-8").write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={parts}, prodvers={parts}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'farzonline'),
      StringStruct('FileDescription', 'Spinin — DDJ-FLX4 controller mapper'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'Spinin'),
      StringStruct('LegalCopyright', 'Copyright (C) 2026 farzonline. GPL-3.0-or-later.'),
      StringStruct('OriginalFilename', 'Spinin.exe'),
      StringStruct('ProductName', 'Spinin'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")

# installer.iss reads this rather than asking the built exe for its version: Inno Setup's
# GetVersionNumbersString() returns the padded four-part FIXEDFILEINFO (0.1.0.0), not the
# three-part version everywhere else in the app calls itself.
open("VERSION.txt", "w", encoding="utf-8").write(version)

a = Analysis(
    ["main_windows.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("ddj-flx4.webp", "."),   # the controller photo the canvas draws
        ("Spinin2.ico", "."),
        ("Spinin2.png", "."),
        ("LICENSE", "."),
    ],
    hiddenimports=[
        "win32gui", "win32process", "win32api", "win32con",
        "comtypes.stream",          # pycaw reaches for this only at run time
        "pycaw.pycaw",
        # mido picks its backend by module name at run time, so nothing imports these where
        # PyInstaller can see it. Leave them out and the built app never finds the
        # controller: "No module named 'mido.backends.rtmidi'".
        "mido.backends.rtmidi",
        "mido.backends.rtmidi_python",
        "rtmidi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Nothing here is imported by the app; leaving them in roughly doubles the build.
    excludes=["tkinter", "unittest", "pydoc", "doctest", "pdb", "test",
              "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuick3D", "PyQt6.QtWebEngineCore",
              "PyQt6.QtWebEngineWidgets", "PyQt6.QtMultimedia", "PyQt6.QtBluetooth",
              "PyQt6.QtNetwork", "PyQt6.QtPositioning", "PyQt6.QtSql", "PyQt6.QtTest",
              "PyQt6.Qt3DCore", "PyQt6.QtCharts", "PyQt6.QtDataVisualization"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    upx=False,          # UPX-packed executables are a common false positive for antivirus
    console=False,      # a GUI app must not flash a console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="Spinin2.ico",
    version="version_info.txt",
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
