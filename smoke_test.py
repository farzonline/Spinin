# SPDX-License-Identifier: GPL-3.0-or-later
# smoke_test.py
# Builds the whole app once, offscreen, and quits.
#
# This is the closest thing to "does it run" that works without a display or a controller,
# which makes it the check that matters most for the macOS port: it proves every module
# imports, the platform backends resolve, the window and all its dialogs construct, and the
# action catalog matches the key table — none of which the per-module self-checks cover
# together.
#
# The MIDI, window-tracking and DJ-watching threads are stubbed out: they would reach for
# hardware and for the real foreground window, neither of which exists on a CI runner.
#
# Run it:  QT_QPA_PLATFORM=offscreen python smoke_test.py

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Point the config at a throwaway file before anything can construct a ConfigManager, so a
# real installation's mappings are never read or written by a test run.
import config_manager
config_manager.CONFIG_FILE = os.path.join(tempfile.mkdtemp(prefix="spinin-smoke-"),
                                          "mappings.json")

from PyQt6.QtWidgets import QApplication  # noqa: E402

import chrome  # noqa: E402
import midi_listener  # noqa: E402
import context_tracker  # noqa: E402
import dj_guard  # noqa: E402

midi_listener.MidiListenerThread.start = lambda self: None
midi_listener.MidiListenerThread.resume = lambda self: None
midi_listener.MidiListenerThread.stop = lambda self: None
context_tracker.ActiveWindowTracker.start = lambda self: None
dj_guard.DjSoftwareWatcher.start = lambda self: None

import actions as catalog  # noqa: E402
import main_windows as mw  # noqa: E402
import userinput  # noqa: E402


def main():
    app = QApplication(sys.argv)
    app.setStyle(chrome.SpininStyle("Fusion"))
    app.setStyleSheet(mw.stylesheet())

    window = mw.MidiMapperApp()
    window.resize(1480, 880)
    window.show()
    assert window.isVisible(), "the main window should be up"
    assert window.title_bar.buttons, "the title bar should have its window buttons"

    # Every control the canvas knows must be selectable, and every action kind must render
    # its own editor without tripping over a field the other kinds use.
    for control_id in ("PAD_L_3", "JOG_ROTATE_L", "FADER_L", "PLAY_L", "BROWSER_ENCODER"):
        window.on_control_selected(control_id)
        assert window.insp_title.text(), f"{control_id} should name itself in the inspector"

    # Each action in the catalog must survive being chosen: this is what catches an entry
    # whose backend or options the editor does not know how to show.
    for action in catalog.ACTIONS:
        kind = {"press": "PLAY_L", "turn": "JOG_ROTATE_L", "range": "FADER_L"}[action["kind"]]
        window.on_control_selected(kind)
        window.pending_action = action
        window.sync_action_editor()
    assert window.choose_btn.text(), "the action button should still be labelled"

    # The dialogs, since a broken one only shows up when somebody opens it.
    picker = mw.ActionPicker("press", "Deck 1 Pad 3", None, window)
    assert picker.list.count() > 20, "the action library should not be empty"
    picker.reject()
    about = mw.AboutDialog(window.app_icon(), window)
    about.reject()
    apps = mw.InstalledAppPicker(window)
    apps.reject()

    # Standing down for DJ software, and picking the controller back up.
    window.on_dj_software_changed("rekordbox", True)
    assert window.dj_app == "rekordbox"
    window.on_dj_software_changed("", False)
    assert not window.dj_app

    # Every theme must build a stylesheet and repaint without raising.
    for name in mw.THEMES:
        window.set_theme(name)
    window.set_theme("voltage")

    window.closing = True
    window.close()
    app.processEvents()

    print(f"smoke test OK on {sys.platform} — "
          f"{len(catalog.ACTIONS)} actions, {len(userinput.KEYS)} keys, "
          f"{len(mw.THEMES)} themes, window built and closed cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
