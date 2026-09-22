# SPDX-License-Identifier: GPL-3.0-or-later
# dj_guard.py
# Stands down while DJ software is running, so it can have the controller to itself.
#
# Windows hands a MIDI input port to one process at a time. While Spinin holds the DDJ-FLX4,
# rekordbox or Serato cannot open it at all — so "pause" has to mean closing the port, not
# just ignoring what comes through it.
#
# macOS is the opposite: CoreMIDI lets several apps read the same port. Spinin still stands
# down there, because two programs both acting on one jog wheel is its own kind of mess —
# you would be scratching a record and scrolling a web page at the same time.

import sys

import psutil
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Process name (lower case) -> what to call it in the UI.
DJ_APPS = {
    "rekordbox.exe": "rekordbox",
    "rekordboxagent.exe": "rekordbox",
    "serato dj pro.exe": "Serato DJ Pro",
    "seratodjpro.exe": "Serato DJ Pro",
    "serato dj lite.exe": "Serato DJ Lite",
    "serato dj.exe": "Serato DJ",
    "traktor.exe": "Traktor Pro",
    "virtualdj.exe": "VirtualDJ",
    "virtualdj8.exe": "VirtualDJ",
    "djay pro.exe": "djay Pro",
    "djaypro.exe": "djay Pro",
    "mixxx.exe": "Mixxx",
    "engine dj.exe": "Engine DJ",
    "enginedj.exe": "Engine DJ",
    "djuced.exe": "DJUCED",
}

# macOS process names carry no .exe and are usually the bundle's display name. CoreMIDI lets
# several apps share a port, so standing down is a courtesy here rather than a necessity —
# but two programs both acting on the same jog wheel is still nobody's idea of a good time.
MAC_DJ_APPS = {
    "rekordbox": "rekordbox",
    "rekordboxagent": "rekordbox",
    "serato dj pro": "Serato DJ Pro",
    "serato dj lite": "Serato DJ Lite",
    "traktor": "Traktor Pro",
    "virtualdj": "VirtualDJ",
    "djay pro": "djay Pro",
    "djay": "djay",
    "mixxx": "Mixxx",
    "engine dj": "Engine DJ",
    "djuced": "DJUCED",
    "ableton live": "Ableton Live",
}

if sys.platform == "darwin":
    DJ_APPS = MAC_DJ_APPS


def process_name(name):
    """A process name as this platform reports it.

    Windows process names carry the .exe; macOS ones do not. Normalising both ways means a
    name written for either platform still resolves, which matters because `extra_dj_apps`
    travels inside a profile someone may have written on the other one.
    """
    name = str(name).strip().lower()
    if not name:
        return ""
    if sys.platform == "darwin":
        return name.removesuffix(".exe")
    return name if name.endswith(".exe") else name + ".exe"


def running_dj_app(extra=()):
    """The name of the first DJ application found running, or None.

    `extra` adds process names from the user's settings, for software not in the list above.
    """
    wanted = dict(DJ_APPS)
    for name in extra:
        key = process_name(name)
        if key:
            wanted.setdefault(key, str(name).strip())
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info["name"] or "").lower()
        except psutil.Error:
            continue
        if name in wanted:
            return wanted[name]
    return None


class DjSoftwareWatcher(QObject):
    """Polls for DJ software and says when it comes and goes."""

    # (dj_app_name or "", running) — the name is empty when nothing is running.
    changed = pyqtSignal(str, bool)

    def __init__(self, extra_names=(), poll_interval_ms=2000, parent=None):
        super().__init__(parent)
        self.extra_names = list(extra_names)
        self.current = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.poll_interval_ms = poll_interval_ms

    def start(self):
        self.check()
        self.timer.start(self.poll_interval_ms)

    def stop(self):
        self.timer.stop()

    def check(self):
        found = running_dj_app(self.extra_names)
        if found != self.current:
            self.current = found
            self.changed.emit(found or "", bool(found))


if __name__ == "__main__":
    # Asks psutil what it calls this very process, rather than guessing from
    # sys.executable: on macOS the two disagree (a "python" symlink reporting as
    # "python3.13"), which is exactly the sort of thing this check exists to catch.
    me = psutil.Process().name().lower()
    assert running_dj_app([me]) is not None, "a name passed in must be found among live processes"
    assert running_dj_app(["definitely-not-running-xyz"]) is None
    assert running_dj_app([me.removesuffix(".exe")]) is not None, ".exe should be optional"

    # A name written on the other platform still resolves.
    if sys.platform == "darwin":
        assert process_name("rekordbox.exe") == "rekordbox"
        assert process_name("Mixxx") == "mixxx"
    else:
        assert process_name("rekordbox") == "rekordbox.exe"
        assert process_name("Mixxx.exe") == "mixxx.exe"

    seen = []
    w = DjSoftwareWatcher.__new__(DjSoftwareWatcher)
    QObject.__init__(w)
    w.extra_names, w.current = [me], None
    w.changed.connect(lambda name, on: seen.append((name, on)))
    w.check()
    w.check()  # unchanged: must not fire twice
    assert seen == [(me, True)], seen
    w.extra_names = []
    w.check()
    assert seen[-1] == ("", False), seen
    print(f"dj_guard OK — watching {len(DJ_APPS)} process names")
