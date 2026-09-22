# SPDX-License-Identifier: GPL-3.0-or-later
# branding.py
# Who the app is, and where its files live in each of the two ways it runs:
# from a source checkout, and installed from the packaged build.

import os
import sys

APP_NAME = "Spinin"
APP_VERSION = "0.1.0"
APP_TAGLINE = "Expand the power of your controller."
APP_URL = "https://github.com/farzonline/Spinin"
APP_AUTHOR = "farzonline"
APP_LICENSE = "GPL-3.0-or-later"
APP_COPYRIGHT = f"© 2026 {APP_AUTHOR}"
APP_DESCRIPTION = ("Map a Pioneer DDJ-FLX4 to keyboard shortcuts, system actions and your own "
                   "commands, with profiles that follow whichever app is in front.")

FROZEN = getattr(sys, "frozen", False)


def resource(*parts):
    """A file shipped with the app: icons, the controller photo. Read-only once installed."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def data_dir():
    """Where settings are written.

    Beside the source when run from a checkout, so a clone stays self-contained. Once
    installed it goes where the platform keeps such things, because an installed app cannot
    write next to itself: %APPDATA% on Windows, ~/Library/Application Support on macOS.
    """
    if not FROZEN:
        base = os.path.dirname(os.path.abspath(__file__))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME)
    else:
        base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
    os.makedirs(base, exist_ok=True)
    return base


if __name__ == "__main__":
    assert os.path.isdir(data_dir())
    assert os.path.isfile(resource("actions.py")), "resource() must point at the app's own files"
    print(f"{APP_NAME} {APP_VERSION} — data in {data_dir()}")
