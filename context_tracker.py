# SPDX-License-Identifier: GPL-3.0-or-later
# context_tracker.py
import os
import sys

import psutil
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

IS_MAC = sys.platform == "darwin"

if not IS_MAC:
    import win32gui
    import win32process

class ActiveWindowTracker(QObject):
    # Signals active process change (e.g. "photoshop.exe", "vlc.exe", or "global")
    process_changed = pyqtSignal(str, str) # (process_name, window_title)

    def __init__(self, poll_interval_ms=250, parent=None):
        super().__init__(parent)
        self.last_process = None
        self.last_title = None
        
        # Setup polling timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_active_window)
        self.poll_interval_ms = poll_interval_ms

    def start(self):
        self.timer.start(self.poll_interval_ms)

    def stop(self):
        self.timer.stop()

    def get_active_process_info(self):
        """Returns (identifier, window_title) for the app in front.

        The identifier is what a profile is keyed on: a process name on Windows
        ("photoshop.exe"), a bundle id on macOS ("com.adobe.Photoshop"). Returns None for
        our own window, so editing a mapping does not switch the profile under you.
        """
        if IS_MAC:
            from macos_system import frontmost_app, own_identifier
            identifier, title = frontmost_app()
            return (None, title) if identifier == own_identifier() else (identifier, title)
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "global", "No Active Window"

        # Get window title
        title = win32gui.GetWindowText(hwnd)

        # Get PID
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == 0:
                return "global", title
            if pid == os.getpid():
                return None, title  # our own window: don't switch profile while editing
            
            process_name = psutil.Process(pid).name().lower()
            if process_name == "applicationframehost.exe":
                # Store apps (Calculator, Settings…) are hosted; the real app owns a child window.
                process_name = self._hosted_app_name(hwnd, pid) or process_name
            return process_name, title
        except Exception:
            return "global", title

    @staticmethod
    def _hosted_app_name(hwnd, host_pid):
        found = []

        def visit(child, _):
            _, cpid = win32process.GetWindowThreadProcessId(child)
            if cpid != host_pid:
                found.append(cpid)
                return False
            return True

        try:
            win32gui.EnumChildWindows(hwnd, visit, None)
        except Exception:
            pass  # pywin32 raises when the callback stops enumeration early
        return psutil.Process(found[0]).name().lower() if found else None

    def check_active_window(self):
        """Checks if active window process has changed and emits a signal if it has."""
        process_name, title = self.get_active_process_info()
        if process_name is None:
            return
        if process_name != self.last_process:
            self.last_process = process_name
            self.last_title = title
            self.process_changed.emit(process_name, title)
        elif title != self.last_title:
            self.last_title = title
            # Emitting even if title changed to update UI, though mappings are process-based
            self.process_changed.emit(process_name, title)
