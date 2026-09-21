# SPDX-License-Identifier: GPL-3.0-or-later
# Spinin — map a Pioneer DDJ-FLX4 to keyboard shortcuts and Windows actions.
# Copyright (C) 2026 farzonline
#
# This program is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.

# main_windows.py
import html
import math
import os
import sys
import time
import traceback

from PyQt6.QtCore import (Qt, pyqtSignal, QTimer, QRectF, QPointF, QEvent, QSize, QFileInfo,
                          QT_VERSION_STR)
from PyQt6.QtGui import (QPixmap, QColor, QPainter, QPen, QBrush, QFont, QPainterPath,
                         QFontMetricsF, QIcon)
from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                             QLabel, QComboBox, QLineEdit, QFormLayout, QPlainTextEdit,
                             QFileDialog, QMessageBox, QInputDialog, QStackedWidget,
                             QTabWidget, QSlider, QSpinBox, QCheckBox, QFrame, QProgressBar,
                             QButtonGroup, QDialog, QListWidget, QListWidgetItem,
                             QStyledItemDelegate, QStyle, QSystemTrayIcon, QMenu,
                             QFileIconProvider, QScrollArea)

import actions as catalog
import app_scanner
import audio_devices
import branding
import profile_io
import win_chrome
import winput
from action_handler import LEGACY_SYSTEM as LEGACY_SYSTEM_IDS
from branding import APP_NAME, APP_VERSION
from config_manager import ConfigManager
from dj_guard import DjSoftwareWatcher
from theme import T, THEMES, apply_theme, stylesheet
from controls import (CONTROLS, CONTROL_TO_MIDI, CONTROL_NAMES, HOTSPOTS, IMAGE_CROP,
                      RELATIVE_CONTROLS, DISPLAY_INVERTED, FX_SWITCH_NOTES,
                      FX_SWITCH_POSITIONS, PAD_MODES, DEFAULT_PAD_MODE, MODE_LABELS,
                      PAD_MODE_BUTTONS, ALL_PAD_IDS, pad_deck, pad_mapping_key)
from midi_listener import MidiListenerThread
from context_tracker import ActiveWindowTracker
from action_handler import ActionHandler

HERE = os.path.dirname(os.path.abspath(__file__))

LED_MODES = [
    ("on_press", "Light while held"),
    ("toggle", "Toggle on each press"),
    ("flash", "Flash when pressed"),
    ("always_on", "Always on"),
    ("off", "Always off"),
]


def describe(mapping):
    """One line naming what a mapping does, for the canvas and the log."""
    if not mapping:
        return None
    t = mapping.get("type")
    if t == "launch_app" or (t == "action" and mapping.get("id") == "custom.app"):
        return f"Opens {mapping.get('command')}" if mapping.get("command") else "Opens an app"
    if t == "script" or (t == "action" and mapping.get("id") == "custom.command"):
        return f"Runs {mapping.get('command')}" if mapping.get("command") else "Runs a command"
    if t == "keystroke" or (t == "action" and mapping.get("id") == "custom.keys"):
        keys = mapping.get("keys", [])
        return "Presses " + " + ".join(k.upper() for k in keys) if keys else "Presses a shortcut"
    if t == "action":
        action = catalog.BY_ID.get(mapping.get("id"))
        return action["name"] if action else None
    if t == "system_action":
        legacy = catalog.BY_ID.get(LEGACY_SYSTEM_IDS.get(mapping.get("action"), ""))
        return legacy["name"] if legacy else mapping.get("action")
    return None


def display_value(cid, value):
    """Where the control sits as you see it, which is not always the value it sends."""
    return 127 - value if cid in DISPLAY_INVERTED else value


def action_kind(cid):
    """Which slice of the action library this control can use."""
    if cid in RELATIVE_CONTROLS:
        return "turn"
    return "range" if CONTROL_TO_MIDI.get(cid, "").startswith("CC") else "press"


def control_kind(cid):
    code = CONTROL_TO_MIDI.get(cid, "")
    if cid.startswith("JOG"):
        return "Jog wheel"
    if cid in RELATIVE_CONTROLS:
        return "Encoder"
    if code.startswith("CC"):
        return "Fader" if HOTSPOTS[cid][0] == "rect" else "Knob"
    return "Button"


def display_font(px, weight=QFont.Weight.Normal):
    f = QFont(T["display"])
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


# ----------------- Controller canvas -----------------
class ControllerCanvas(QWidget):
    control_clicked = pyqtSignal(str)

    LIVE_FADE = 0.5  # seconds a live glow takes to fade out

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(640, 380)
        x0, y0, x1, y1 = IMAGE_CROP
        src = QPixmap(image_path)
        self.pixmap = src.copy(x0, y0, x1 - x0, y1 - y0) if not src.isNull() else QPixmap()
        self.scaled = None
        self.img_rect = QRectF()

        self.hovered = None
        self.selected = None
        self.mouse = QPointF()
        self.show_all = False
        self.summaries = {}   # cid -> text for mapped controls
        self.pulses = {}      # cid -> monotonic time of last event
        self.held = set()     # buttons currently held down
        self.values = {}      # cid -> last absolute 0..127 value

        # Smallest first so the jog hub wins over the platter, and the platter over the ring.
        def area(cid):
            s = HOTSPOTS[cid]
            return s[3] * s[4] if s[0] == "rect" else s[3] ** 2 * math.pi
        self.hit_order = sorted(HOTSPOTS, key=area)

        self.anim = QTimer(self)
        self.anim.setInterval(16)
        self.anim.timeout.connect(self._tick)

    # --- state from the app ---
    def set_summaries(self, summaries):
        self.summaries = summaries
        self.update()

    def select(self, cid):
        self.selected = cid
        self.update()

    def set_show_all(self, on):
        self.show_all = on
        self.update()

    def pulse(self, cid, value, is_note):
        if cid not in HOTSPOTS:
            return
        self.pulses[cid] = time.monotonic()
        if is_note:
            (self.held.add if value > 0 else self.held.discard)(cid)
        elif cid not in RELATIVE_CONTROLS:
            self.values[cid] = display_value(cid, value)
        if not self.anim.isActive():
            self.anim.start()
        self.update()

    def intensity(self, cid, now):
        if cid in self.held:
            return 1.0
        t = self.pulses.get(cid)
        return 0.0 if t is None else max(0.0, 1.0 - (now - t) / self.LIVE_FADE)

    def _tick(self):
        now = time.monotonic()
        if not self.held and all(now - t > self.LIVE_FADE for t in self.pulses.values()):
            self.anim.stop()
        self.update()

    # --- geometry ---
    def resizeEvent(self, event):
        if self.pixmap.isNull():
            return
        pw, ph = self.pixmap.width(), self.pixmap.height()
        scale = min(self.width() / pw, self.height() / ph)
        w, h = pw * scale, ph * scale
        self.img_rect = QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)
        dpr = self.devicePixelRatioF()
        self.scaled = self.pixmap.scaled(int(w * dpr), int(h * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
        self.scaled.setDevicePixelRatio(dpr)

    def _scale(self):
        return self.img_rect.width() / max(1, self.pixmap.width())

    def _pt(self, ix, iy):
        s = self._scale()
        return QPointF(self.img_rect.x() + (ix - IMAGE_CROP[0]) * s, self.img_rect.y() + (iy - IMAGE_CROP[1]) * s)

    def _path(self, cid, grow=0.0):
        shape = HOTSPOTS[cid]
        s = self._scale()
        c = self._pt(shape[1], shape[2])
        path = QPainterPath()
        if shape[0] == "rect":
            w, h = shape[3] * s + grow * 2, shape[4] * s + grow * 2
            radius = min(w, h) * 0.18
            path.addRoundedRect(QRectF(c.x() - w / 2, c.y() - h / 2, w, h), radius, radius)
        else:
            r = shape[3] * s + grow
            path.addEllipse(c, r, r)
            if shape[0] == "ring":
                ri = shape[4] * s - grow
                path.addEllipse(c, ri, ri)  # odd-even fill -> annulus
        return path

    def control_at(self, pos):
        s = self._scale()
        for cid in self.hit_order:
            shape = HOTSPOTS[cid]
            c = self._pt(shape[1], shape[2])
            dx, dy = pos.x() - c.x(), pos.y() - c.y()
            if shape[0] == "rect":
                if abs(dx) <= shape[3] * s / 2 and abs(dy) <= shape[4] * s / 2:
                    return cid
            else:
                d = math.hypot(dx, dy)
                inner = shape[4] * s if shape[0] == "ring" else 0
                if inner <= d <= shape[3] * s:
                    return cid
        return None

    # --- painting ---
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.scaled is None:
            p.setPen(QColor(T['muted']))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "ddj-flx4.webp is missing from the app folder.")
            return
        p.drawPixmap(self.img_rect.topLeft(), self.scaled)

        now = time.monotonic()
        pad = QColor(T['pad'])
        s = self._scale()
        for cid in HOTSPOTS:
            live = self.intensity(cid, now)
            selected = cid == self.selected
            hovered = cid == self.hovered
            path = self._path(cid)

            if live > 0:
                for i, a in ((6, 40), (3, 80)):  # soft outer glow, like a lit LED
                    glow = QColor(pad)
                    glow.setAlpha(int(a * live))
                    p.setPen(QPen(glow, i * max(1.0, s * 1.6)))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawPath(path)
                fill = QColor(pad)
                fill.setAlpha(int(120 * live))
                p.setPen(QPen(pad, 1.5))
                p.setBrush(fill)
                p.drawPath(path)

            # Orange is reserved for live input (like the hardware LEDs); selection is legend white.
            if selected:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(0, 0, 0, 150), 5))
                p.drawPath(self._path(cid, 4))
                p.setPen(QPen(QColor(T['legend']), 2))
                p.drawPath(self._path(cid, 4))
            elif hovered:
                p.setPen(QPen(self._ink(170), 1.5))
                p.setBrush(self._ink(30))
                p.drawPath(self._path(cid, 2))
            elif self.show_all:
                p.setPen(QPen(self._ink(110), 1, Qt.PenStyle.DashLine))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)

            if cid in self.values and (live > 0 or selected):
                self._draw_value(p, cid, self.values[cid])

            if cid in self.summaries:
                self._draw_mapped_dot(p, cid)

        if self.hovered:
            self._draw_chip(p, self.hovered)

    @staticmethod
    def _ink(alpha):
        """The theme's text colour at a given alpha, for outlines drawn over the artwork."""
        c = QColor(T['legend'])
        c.setAlpha(alpha)
        return c

    def _draw_mapped_dot(self, p, cid):
        shape = HOTSPOTS[cid]
        s = self._scale()
        if shape[0] == "rect":
            c = self._pt(shape[1] + shape[3] / 2, shape[2] - shape[4] / 2)
        else:
            r = shape[3] if shape[0] == "circle" else (shape[3] + shape[4]) / 2
            c = self._pt(shape[1] + r * 0.707, shape[2] - r * 0.707)
        radius = max(3.5, 4.5 * s)
        p.setPen(QPen(QColor(T['chassis']), 2))
        p.setBrush(QColor(T['legend']))
        p.drawEllipse(c, radius, radius)

    def _draw_value(self, p, cid, value):
        shape = HOTSPOTS[cid]
        s = self._scale()
        frac = value / 127
        pen = QPen(QColor(T['pad']), max(2.0, 3 * s), cap=Qt.PenCapStyle.RoundCap)
        if shape[0] == "circle":  # knob: 270° arc starting at 7 o'clock
            r = shape[3] * s + max(4.0, 5 * s)
            c = self._pt(shape[1], shape[2])
            rect = QRectF(c.x() - r, c.y() - r, r * 2, r * 2)
            track = QPen(self._ink(50), pen.widthF(), cap=Qt.PenCapStyle.RoundCap)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(track)
            p.drawArc(rect, 225 * 16, -270 * 16)
            p.setPen(pen)
            p.drawArc(rect, 225 * 16, int(-270 * frac * 16))
        elif shape[0] == "rect":  # fader: bar along its long side
            c = self._pt(shape[1], shape[2])
            w, h = shape[3] * s, shape[4] * s
            p.setPen(pen)
            if h > w:
                x = c.x() + w / 2 + max(4.0, 5 * s)
                bottom, top = c.y() + h / 2, c.y() - h / 2
                p.drawLine(QPointF(x, bottom), QPointF(x, bottom - (bottom - top) * frac))
            else:
                y = c.y() + h / 2 + max(4.0, 5 * s)
                left, right = c.x() - w / 2, c.x() + w / 2
                p.drawLine(QPointF(left, y), QPointF(left + (right - left) * frac, y))

    def _draw_chip(self, p, cid):
        name = CONTROL_NAMES[cid]
        detail = self.summaries.get(cid, "Not mapped")
        f1, f2 = display_font(14, QFont.Weight.DemiBold), QFont("Segoe UI")
        f2.setPixelSize(12)
        m1, m2 = QFontMetricsF(f1), QFontMetricsF(f2)
        w = max(m1.horizontalAdvance(name), m2.horizontalAdvance(detail)) + 24
        h = m1.height() + m2.height() + 16
        x = min(max(8, self.mouse.x() + 16), self.width() - w - 8)
        y = self.mouse.y() - h - 12
        if y < 8:
            y = self.mouse.y() + 22
        box = QRectF(x, y, w, h)
        backing = QColor(T['panel'])
        backing.setAlpha(235)
        p.setPen(QPen(QColor(T['line']), 1))
        p.setBrush(backing)
        p.drawRoundedRect(box, T['r_item'], T['r_item'])
        p.setFont(f1)
        p.setPen(QColor(T['legend']))
        p.drawText(QPointF(x + 12, y + 8 + m1.ascent()), name)
        p.setFont(f2)
        p.setPen(QColor(T['pad']) if cid in self.summaries else QColor(T['muted']))
        p.drawText(QPointF(x + 12, y + 8 + m1.height() + m2.ascent()), detail)

    # --- mouse ---
    def mouseMoveEvent(self, event):
        self.mouse = event.position()
        found = self.control_at(self.mouse)
        self.setCursor(Qt.CursorShape.PointingHandCursor if found else Qt.CursorShape.ArrowCursor)
        if found != self.hovered or found:
            self.hovered = found
            self.update()

    def leaveEvent(self, event):
        self.hovered = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.hovered:
            self.select(self.hovered)
            self.control_clicked.emit(self.hovered)


# ----------------- Shortcut capture box -----------------
class KeyCaptureLineEdit(QLineEdit):
    """Records a shortcut via a system-wide low-level hook rather than normal Qt key events.

    Windows claims Win-key combos (Win+V for clipboard history, Win+Tab, Win+L, ...) as shell
    hotkeys and acts on them before a focused window's key events fire at all, so a box built
    on ordinary Qt events could only ever see what the shell didn't already want — in practice,
    a hard ceiling around two keys. The hook in winput.HotkeyCapture sees every key system-wide
    first and blocks the shell's own handling for as long as this box has focus.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Click here, then press the shortcut")
        self.setReadOnly(True)
        self.setProperty("capture", True)
        self.captured_keys = []
        self._capture = winput.HotkeyCapture(self._on_keys)

    def set_keys(self, keys):
        self.captured_keys = list(keys)
        self.setText(" + ".join(k.upper() for k in keys))

    def _on_keys(self, keys):
        self.set_keys(keys)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._capture.start()

    def focusOutEvent(self, event):
        # Every key on the system is blocked while this runs, so it must never outlive focus.
        self._capture.stop()
        super().focusOutEvent(event)


class ActionItemDelegate(QStyledItemDelegate):
    """Two-line rows: the action's name, and the shortcut or command it uses."""

    def sizeHint(self, option, index):
        return QSize(260, 52)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect).adjusted(4, 2, -4, -2)
        selected = option.state & QStyle.StateFlag.State_Selected
        hovered = option.state & QStyle.StateFlag.State_MouseOver
        if selected or hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(T['select']) if selected else QColor(255, 255, 255, 14))
            painter.drawRoundedRect(rect, T['r_item'], T['r_item'])
        painter.setPen(QColor(T['legend']))
        painter.setFont(display_font(15))
        painter.drawText(QRectF(rect.x() + 12, rect.y() + 6, rect.width() - 24, 20),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, index.data())
        painter.setPen(QColor(T['muted']))
        f = QFont("Segoe UI")
        f.setPixelSize(11)
        painter.setFont(f)
        painter.drawText(QRectF(rect.x() + 12, rect.y() + 26, rect.width() - 24, 18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         index.data(Qt.ItemDataRole.UserRole + 1))
        painter.restore()


class ActionPicker(QDialog):
    """The action library: search, categories, and everything a control can be set to do."""

    def __init__(self, kind, control_name, current_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose an action")
        self.setModal(True)
        self.resize(940, 620)
        self.kind = kind
        self.chosen = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(14)

        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(label("Choose an action", "title"))
        head.addWidget(label(f"What should {control_name} do?", "muted"))
        lay.addLayout(head)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search actions, shortcuts and settings pages")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refill)
        lay.addWidget(self.search)

        split = QHBoxLayout()
        split.setSpacing(16)
        self.cats = QListWidget()
        self.cats.setFixedWidth(190)
        self.cats.addItem("All actions")
        for c in catalog.categories(kind):
            self.cats.addItem(c)
        self.cats.setCurrentRow(0)
        self.cats.currentRowChanged.connect(self.refill)
        split.addWidget(self.cats)

        self.list = QListWidget()
        self.list.setItemDelegate(ActionItemDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.itemSelectionChanged.connect(self.on_selection)
        self.list.itemDoubleClicked.connect(lambda _: self.accept_choice())
        split.addWidget(self.list, 1)
        lay.addLayout(split, 1)

        self.detail = label("", "muted")
        self.detail.setWordWrap(True)
        lay.addWidget(self.detail)

        row = QHBoxLayout()
        self.count_lbl = label("", "muted")
        row.addWidget(self.count_lbl)
        row.addStretch()
        cancel = button("Cancel", "ghost")
        cancel.clicked.connect(self.reject)
        self.use_btn = button("Use this action", "primary")
        self.use_btn.clicked.connect(self.accept_choice)
        row.addWidget(cancel)
        row.addWidget(self.use_btn)
        lay.addLayout(row)

        self.refill()
        if current_id:
            self.select_id(current_id)
        self.search.setFocus()

    def refill(self):
        cat_item = self.cats.currentItem()
        category = cat_item.text() if cat_item and self.cats.currentRow() > 0 else None
        query = self.search.text()
        self.list.clear()
        for action in catalog.for_kind(self.kind):
            if category and action["category"] != category:
                continue
            if not catalog.matches(action, query):
                continue
            item = QListWidgetItem(action["name"])
            item.setData(Qt.ItemDataRole.UserRole, action["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, f"{action['category']}   {action['hint']}")
            self.list.addItem(item)
        found = self.list.count()
        self.count_lbl.setText(f"{found} action{'s' if found != 1 else ''}"
                               + (" — try a different word" if not found else ""))
        if found:
            self.list.setCurrentRow(0)
        self.on_selection()

    def select_id(self, action_id):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == action_id:
                self.list.setCurrentRow(i)
                return

    def current_action(self):
        item = self.list.currentItem()
        return catalog.BY_ID.get(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def on_selection(self):
        action = self.current_action()
        self.use_btn.setEnabled(bool(action))
        if not action:
            self.detail.setText("")
            return
        extra = {"custom": "You fill in the details after choosing this.",
                 "uri": "Opens this page in Windows.",
                 "run": "Runs this command.",
                 "keys": "Sends this shortcut to whichever app is in front.",
                 "keypair": "Sends one shortcut each way as you turn.",
                 "native": ""}.get(action["backend"], "")
        self.detail.setText(f"<span style='color:{T['legend']}'>{html.escape(action['hint'])}</span>&nbsp;&nbsp;{extra}")

    def accept_choice(self):
        action = self.current_action()
        if action:
            self.chosen = action
            self.accept()

    def keyPressEvent(self, event):
        # Enter picks the highlighted action; arrows move through the list while typing.
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept_choice()
            return
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self.search.hasFocus():
            row = self.list.currentRow() + (1 if event.key() == Qt.Key.Key_Down else -1)
            self.list.setCurrentRow(max(0, min(self.list.count() - 1, row)))
            return
        super().keyPressEvent(event)


class InstalledAppPicker(QDialog):
    """Everything with a Start Menu entry, so an app can be picked instead of hunted for."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose an installed app")
        self.setModal(True)
        self.resize(560, 640)
        self.chosen = None
        self.icons = QFileIconProvider()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(12)
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(label("Installed apps", "title"))
        head.addWidget(label("Everything with a Start Menu entry on this PC.", "muted"))
        lay.addLayout(head)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search installed apps")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refill)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.setIconSize(QSize(20, 20))
        self.list.itemSelectionChanged.connect(self.on_selection)
        self.list.itemDoubleClicked.connect(lambda _: self.accept_choice())
        lay.addWidget(self.list, 1)

        row = QHBoxLayout()
        self.count_lbl = label("", "muted")
        row.addWidget(self.count_lbl)
        row.addStretch()
        rescan = button("Rescan", "ghost")
        rescan.setToolTip("Look again, after installing something new")
        rescan.clicked.connect(lambda: self.refill(rescan=True))
        cancel = button("Cancel", "ghost")
        cancel.clicked.connect(self.reject)
        self.use_btn = button("Use this app", "primary")
        self.use_btn.clicked.connect(self.accept_choice)
        for b in (rescan, cancel, self.use_btn):
            row.addWidget(b)
        lay.addLayout(row)

        self.refill()
        self.search.setFocus()

    def refill(self, _text=None, rescan=False):
        words = self.search.text().strip().lower().split()
        self.list.clear()
        for name, path in app_scanner.installed(refresh=rescan):
            if not all(w in name.lower() for w in words):
                continue
            item = QListWidgetItem(self.icons.icon(QFileInfo(path)), name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.list.addItem(item)
        found = self.list.count()
        self.count_lbl.setText(f"{found} app{'s' if found != 1 else ''}"
                               + (" — try a different word" if not found else ""))
        if found:
            self.list.setCurrentRow(0)
        self.on_selection()

    def on_selection(self):
        self.use_btn.setEnabled(self.list.currentItem() is not None)

    def accept_choice(self):
        item = self.list.currentItem()
        if item:
            self.chosen = item.data(Qt.ItemDataRole.UserRole)
            self.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept_choice()
            return
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self.search.hasFocus():
            row = self.list.currentRow() + (1 if event.key() == Qt.Key.Key_Down else -1)
            self.list.setCurrentRow(max(0, min(self.list.count() - 1, row)))
            return
        super().keyPressEvent(event)


class AboutDialog(QDialog):
    """Name, version, licence and where to find the project."""

    def __init__(self, icon, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setModal(True)
        self.setFixedWidth(420)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 24, 26, 20)
        lay.setSpacing(4)

        crest = QLabel()
        crest.setPixmap(icon.pixmap(72, 72))
        crest.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(crest)
        lay.addSpacing(10)

        for text, role in ((APP_NAME, "title"), (f"Version {APP_VERSION}", "muted"),
                           (branding.APP_TAGLINE, "muted")):
            lbl = label(text, role)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

        lay.addSpacing(14)
        link = QLabel(
            f"<div style='text-align:center; color:{T['muted']}'>"
            f"{html.escape(branding.APP_COPYRIGHT)}<br>"
            f"Free software under the GNU General Public License v3.<br><br>"
            f"<a style='color:{T['pad']}' href='{branding.APP_URL}'>{branding.APP_URL}</a></div>")
        link.setOpenExternalLinks(True)
        link.setWordWrap(True)
        lay.addWidget(link)

        lay.addSpacing(10)
        detail = label(f"Qt {QT_VERSION_STR} · Python {sys.version.split()[0]}", "muted")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(detail)

        lay.addSpacing(16)
        row = QHBoxLayout()
        row.addStretch()
        copy_btn = button("Copy details", "ghost")
        copy_btn.clicked.connect(self.copy_details)
        close = button("Close", "primary")
        close.clicked.connect(self.accept)
        row.addWidget(copy_btn)
        row.addWidget(close)
        lay.addLayout(row)

    def copy_details(self):
        """Puts the version line on the clipboard, which is what a bug report needs."""
        QApplication.clipboard().setText(
            f"{APP_NAME} {APP_VERSION} · Qt {QT_VERSION_STR} · Python {sys.version.split()[0]} "
            f"· {sys.platform}")


class TitleBar(QFrame):
    """The app's own top bar, in place of the one Windows would draw.

    Dragging and resizing are handed to Windows through startSystemMove/startSystemResize
    rather than moved by hand, so snapping to an edge, the shake gesture and multi-monitor
    DPI all keep working exactly as they do for any other window.
    """

    DRAG_SLOP = 6  # pixels of movement before a press counts as a drag, not a click

    def __init__(self, window, icon):
        super().__init__(window)
        self.setObjectName("titlebar")
        self.win = window
        self.setFixedHeight(40)
        self._press = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 5, 6, 0)
        lay.setSpacing(9)
        self.crest = QLabel()
        self.crest.setPixmap(icon.pixmap(18, 18))
        lay.addWidget(self.crest)
        lay.addWidget(label(APP_NAME, "wordmark"))
        lay.addWidget(label(APP_VERSION, "muted"))
        lay.addStretch()

        self.buttons = {}
        for key, tip, slot in (("minimize", "Minimise to the tray", window.showMinimized),
                               ("maximize", "Maximise", self.toggle_max),
                               ("close", "Close", window.close)):
            b = button("", "chrome")
            b.setToolTip(tip)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(slot)
            if key == "close":
                b.setProperty("danger", "true")
            lay.addWidget(b)
            self.buttons[key] = b
        self.restyle()

    def restyle(self):
        """Redraws the three glyphs, after a theme change or a maximise."""
        for key, b in self.buttons.items():
            shown = "restore" if key == "maximize" and self.win.isMaximized() else key
            b.setIcon(win_chrome.glyph_icon(shown, 11, T["muted"]))
            b.setIconSize(QSize(11, 11))
        self.buttons["maximize"].setToolTip("Restore" if self.win.isMaximized() else "Maximise")

    def toggle_max(self):
        self.win.showNormal() if self.win.isMaximized() else self.win.showMaximized()
        self.restyle()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        # Held and moved, not merely pressed: starting the move on press would swallow the
        # second click of a double-click, which is how a title bar maximises.
        if self._press is None:
            return
        if (event.globalPosition().toPoint() - self._press).manhattanLength() < self.DRAG_SLOP:
            return
        self._press = None
        if self.win.isMaximized():
            self.win.showNormal()  # dragging a maximised window restores it, as Windows does
            self.restyle()
        handle = self.win.windowHandle()
        if handle:
            handle.startSystemMove()

    def mouseReleaseEvent(self, _event):
        self._press = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_max()


# Which way the pointer should look when it is over each edge of the window.
EDGE_CURSORS = {
    Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
    Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
    Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
    Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
    Qt.Edge.LeftEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeBDiagCursor,
    Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
}
EDGE_CURSORS = {k.value: v for k, v in EDGE_CURSORS.items()}


def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def scrollable(inner):
    """Wraps a panel so it scrolls rather than squashing when it outgrows its space."""
    area = QScrollArea()
    area.setObjectName("plain")
    area.setWidget(inner)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.viewport().setAutoFillBackground(False)
    inner.setAutoFillBackground(False)
    return area


def label(text, role=None):
    lbl = QLabel(text)
    if role:
        lbl.setProperty("role", role)
    return lbl


def button(text, kind=None):
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


# ----------------- Main window -----------------
class MidiMapperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1120, 700)
        self.resize(1480, 880)
        # The window draws its own top bar, so Windows is asked not to draw one.
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setMouseTracking(True)

        self.config_manager = ConfigManager()
        self.action_handler = ActionHandler()
        self.action_handler.report = self.log_message  # its notes go to the Activity log
        self.active_profile = "global"
        self.selected_control = None
        self.last_foreign_exe = None
        self.last_foreign_title = ""
        self.pending_action = None
        self.pending_device = (None, None)
        self.fx_notes_on = set()
        self.fx_position = None
        # Pad banks: pad_mode is which bank the hardware is physically sitting in (from the
        # last mode button pressed); pad_edit_mode is which bank the inspector is showing,
        # which follows pad_mode by default but can be changed by hand to program a bank
        # without needing to stand at the controller and switch to it.
        self.pad_mode = {"L": DEFAULT_PAD_MODE, "R": DEFAULT_PAD_MODE}
        self.pad_edit_mode = DEFAULT_PAD_MODE
        self.midi_connected, self.status_message = False, "Starting…"
        self.dj_app = ""  # the DJ software currently holding the controller, if any
        apply_theme(self.config_manager.get_setting("theme", "graphite"))
        self.led_toggled = set()
        self.last_values = {}

        # "auto": profile follows the active window. "static": stays on the chosen profile.
        self.profile_mode = self.config_manager.get_setting("profile_mode", "auto")
        if self.profile_mode == "static":
            saved = self.config_manager.get_setting("static_profile", "global")
            self.active_profile = saved if saved in self.config_manager.get_profiles() else "global"

        # Clicking the taskbar or Alt-Tab briefly focuses explorer.exe; wait for focus to settle.
        # ponytail: fixed 400 ms debounce, raise it if profiles still flicker while switching
        self.switch_timer = QTimer(self)
        self.switch_timer.setSingleShot(True)
        self.switch_timer.setInterval(400)
        self.switch_timer.timeout.connect(self.apply_auto_profile)

        self.closing = False
        self.build_ui()
        for key, act in self.theme_actions.items():
            act.setChecked(key == T["name"])
        self.build_tray()
        self.refresh_profiles()
        self.show_inspector(None)
        self.init_threads()

    # ---------- layout ----------
    def build_ui(self):
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.title_bar = TitleBar(self, self.app_icon())
        shell.addWidget(self.title_bar)

        content = QWidget()
        shell.addWidget(content, 1)
        root = QVBoxLayout(content)
        root.setContentsMargins(18, 8, 18, 18)
        root.setSpacing(12)
        root.addLayout(self.build_header())
        root.addWidget(self.build_context_bar())

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        stage = card()
        stage_lay = QVBoxLayout(stage)
        stage_lay.setContentsMargins(16, 16, 16, 12)
        self.canvas = ControllerCanvas(branding.resource("ddj-flx4.webp"))
        self.canvas.control_clicked.connect(self.on_control_selected)
        stage_lay.addWidget(self.canvas, 1)

        legend = QHBoxLayout()
        legend.setSpacing(18)
        self.mapped_legend = label(f"<span style='color:{T['legend']}'>●</span>&nbsp; Has an action", "muted")
        self.live_legend = label(f"<span style='color:{T['pad']}'>●</span>&nbsp; Live input", "muted")
        legend.addWidget(self.mapped_legend)
        legend.addWidget(self.live_legend)
        legend.addStretch()
        self.pick_from_hw = QCheckBox("Select by pressing")
        self.pick_from_hw.setToolTip("Pressing any control on the DDJ-FLX4 selects it here")
        legend.addWidget(self.pick_from_hw)
        show_all = QCheckBox("Show all hotspots")
        show_all.toggled.connect(self.canvas.set_show_all)
        legend.addWidget(show_all)
        stage_lay.addLayout(legend)
        body.addWidget(stage, 1)

        side = QVBoxLayout()
        side.setSpacing(14)
        side.addWidget(self.build_inspector(), 1)
        side.addWidget(self.build_log())
        side_w = QWidget()
        side_w.setLayout(side)
        side_w.setFixedWidth(400)
        side.setContentsMargins(0, 0, 0, 0)
        body.addWidget(side_w)

    def build_header(self):
        h = QHBoxLayout()
        h.setSpacing(10)
        self.status_dot = QLabel("●")
        self.status_lbl = label("Starting…", "muted")
        h.addWidget(self.status_dot)
        h.addWidget(self.status_lbl)
        h.addStretch()

        h.addWidget(label("Profile", "muted"))
        segment = QFrame()
        segment.setObjectName("segment")
        seg_lay = QHBoxLayout(segment)
        seg_lay.setContentsMargins(3, 3, 3, 3)
        seg_lay.setSpacing(2)
        self.mode_group = QButtonGroup(self)
        for mode, text, tip in (("auto", "Automatic", "Switch to the profile that matches the active window"),
                                ("static", "Static", "Keep the chosen profile whichever window is active")):
            b = button(text, "segment")
            b.setCheckable(True)
            b.setChecked(mode == self.profile_mode)
            b.setToolTip(tip)
            b.setProperty("mode", mode)
            self.mode_group.addButton(b)
            seg_lay.addWidget(b)
        self.mode_group.buttonClicked.connect(lambda b: self.set_profile_mode(b.property("mode")))
        h.addWidget(segment)

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(190)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        self.profile_combo.activated.connect(self.on_profile_picked)  # user picks only
        h.addWidget(self.profile_combo)
        for text, slot in (("New", self.on_add_profile), ("Duplicate", self.on_duplicate_profile)):
            b = button(text)
            b.clicked.connect(slot)
            h.addWidget(b)
        self.del_prof_btn = button("Delete", "ghost")
        self.del_prof_btn.clicked.connect(self.on_delete_profile)
        h.addWidget(self.del_prof_btn)

        more_btn = button("⋯")
        more_btn.setToolTip("Import, export, appearance and about")
        more = QMenu(self)
        glyph = win_chrome.glyph_icon
        # Icons are drawn in the theme's own ink, so set_theme has to redraw them: each one
        # is kept here with the glyph it was made from.
        self.menu_icons = []

        def with_icon(target, name, text, slot=None):
            if slot:
                act = result = target.addAction(glyph(name), text, slot)
            else:
                result = target.addMenu(glyph(name), text)
                act = result.menuAction()  # a submenu wears its icon on the action that opens it
            self.menu_icons.append((act, name))
            return result

        with_icon(more, "import", "Import profiles…", self.on_import_profiles)
        with_icon(more, "export", "Export this profile…", lambda: self.on_export_profiles(False))
        with_icon(more, "export_all", "Export all profiles…", lambda: self.on_export_profiles(True))
        more.addSeparator()
        theme_menu = with_icon(more, "theme", "Theme")
        self.theme_actions = {}
        for key, palette in THEMES.items():
            act = theme_menu.addAction(f"{palette['label']} — {palette['note']}")
            act.setCheckable(True)
            act.triggered.connect(lambda _c, k=key: self.set_theme(k))
            self.theme_actions[key] = act
        more.addSeparator()
        with_icon(more, "about", f"About {APP_NAME}…", self.on_about)
        self.more_menu = more
        # Frosting has to wait for the menu to be about to show: Windows only takes the
        # effect once the native window exists, which it does not until then.
        more.aboutToShow.connect(lambda: win_chrome.frost_menu(more))
        theme_menu.aboutToShow.connect(lambda: win_chrome.frost_menu(theme_menu))
        more_btn.setMenu(more)
        h.addWidget(more_btn)
        return h

    # ---------- appearance ----------
    def set_theme(self, name):
        applied = apply_theme(name)
        self.config_manager.set_setting("theme", applied)
        QApplication.instance().setStyleSheet(stylesheet())
        for key, act in self.theme_actions.items():
            act.setChecked(key == applied)
        # Anything that bakes a colour into its text or its own style has to be rebuilt.
        self.mapped_legend.setText(f"<span style='color:{T['legend']}'>●</span>&nbsp; Has an action")
        self.live_legend.setText(f"<span style='color:{T['pad']}'>●</span>&nbsp; Live input")
        for act, glyph_name in self.menu_icons:
            act.setIcon(win_chrome.glyph_icon(glyph_name))
        self.title_bar.restyle()
        self.restyle_status()
        self.update_context_bar()
        self.canvas.update()
        self.log_message(f"Theme: {THEMES[applied]['label']}")

    def build_context_bar(self):
        bar = QFrame()
        bar.setObjectName("contextbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 6, 8, 6)
        lay.setSpacing(12)
        self.window_lbl = label("", "muted")
        self.window_lbl.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.window_lbl, 1)
        self.mode_lbl = label("", "muted")
        self.mode_lbl.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.mode_lbl)
        self.create_for_app_btn = button("")
        self.create_for_app_btn.clicked.connect(self.on_create_for_active_app)
        lay.addWidget(self.create_for_app_btn)
        return bar

    def build_inspector(self):
        box = card()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(6)

        self.insp_title = label("", "title")
        self.insp_title.setWordWrap(True)
        self.insp_meta = label("", "muted")
        lay.addWidget(self.insp_title)
        lay.addWidget(self.insp_meta)

        # Pad bank picker: only shown for a pad, since only pads have a mode switch changing
        # what they send. Lets you program a bank without standing at the controller to select it.
        self.pad_bank_row = QFrame()
        self.pad_bank_row.setObjectName("segment")
        bank_lay = QHBoxLayout(self.pad_bank_row)
        bank_lay.setContentsMargins(3, 3, 3, 3)
        bank_lay.setSpacing(2)
        self.pad_bank_group = QButtonGroup(self)
        self.pad_bank_buttons = {}
        short = {"HOT_CUE": "Hot Cue", "PAD_FX1": "FX 1", "BEAT_JUMP": "Beat Jump", "SAMPLER": "Sampler"}
        for mode in PAD_MODES:
            b = button(short[mode], "segment")
            b.setCheckable(True)
            b.setToolTip(f"Edit this pad's {MODE_LABELS[mode]} action")
            b.setProperty("mode", mode)
            self.pad_bank_group.addButton(b)
            self.pad_bank_buttons[mode] = b
            bank_lay.addWidget(b)
        self.pad_bank_group.buttonClicked.connect(lambda b: self.on_pad_bank_picked(b.property("mode")))
        self.pad_bank_row.setVisible(False)
        lay.addSpacing(4)
        lay.addWidget(self.pad_bank_row)

        self.value_bar = QProgressBar()
        self.value_bar.setRange(0, 127)
        self.value_bar.setTextVisible(False)
        lay.addSpacing(6)
        lay.addWidget(self.value_bar)
        lay.addSpacing(10)

        self.empty_hint = label("Click any control on the controller to give it an action.\n\n"
                                "Or tick “Select by pressing” and press it on the hardware.", "muted")
        self.empty_hint.setWordWrap(True)
        lay.addWidget(self.empty_hint)

        # Scrollable, because the Action tab grows with the options the chosen action offers.
        # Without this the form is squeezed instead — buttons losing their labels and spin
        # boxes their digits — on a short window or a dense action.
        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_action_tab(), "Action")
        self.tabs.addTab(self.build_led_tab(), "Lighting")
        lay.addWidget(self.tabs, 1)

        self.feedback = label("", "muted")
        lay.addWidget(self.feedback)
        return box

    def build_action_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        # The form scrolls; Save and Remove stay put below it, where they can always be reached.
        form_host = QWidget()
        form = QFormLayout(form_host)
        outer.addWidget(scrollable(form_host), 1)
        form.setContentsMargins(0, 16, 12, 0)  # room on the right for the scrollbar
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.action_label = label("When pressed", "section")
        self.choose_btn = button("Choose an action…")
        self.choose_btn.setMinimumHeight(38)
        self.choose_btn.clicked.connect(self.on_choose_action)
        form.addRow(self.action_label, self.choose_btn)
        self.action_hint = label("", "muted")
        self.action_hint.setWordWrap(True)
        form.addRow(self.action_hint)

        # Only the "Your own" actions need details typed in; the stack shows the right one.
        self.action_stack = QStackedWidget()
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        self.app_path_input = QLineEdit()
        self.app_path_input.setPlaceholderText("notepad, or a path to an .exe")
        pick_installed = button("Installed…")
        pick_installed.setIcon(win_chrome.glyph_icon("app", 14, T["muted"]))
        pick_installed.setToolTip("Pick from the programs installed on this PC")
        pick_installed.clicked.connect(self.on_pick_installed_app)
        browse = button("Browse…")
        browse.setToolTip("Find a program's .exe yourself")
        browse.clicked.connect(self.on_browse_app)
        row.addWidget(self.app_path_input, 1)
        row.addWidget(pick_installed)
        row.addWidget(browse)
        self.action_stack.addWidget(page)

        self.key_input = KeyCaptureLineEdit()
        self.action_stack.addWidget(self.key_input)

        self.script_input = QLineEdit()
        self.script_input.setPlaceholderText("Command line, e.g. python C:/scripts/lights.py")
        self.action_stack.addWidget(self.script_input)

        turn_page = QWidget()
        turn_lay = QVBoxLayout(turn_page)
        turn_lay.setContentsMargins(0, 0, 0, 0)
        turn_lay.setSpacing(6)
        self.key_cw_input = KeyCaptureLineEdit()
        self.key_cw_input.setPlaceholderText("Turning right: click and press the shortcut")
        self.key_ccw_input = KeyCaptureLineEdit()
        self.key_ccw_input.setPlaceholderText("Turning left: click and press the shortcut")
        turn_lay.addWidget(self.key_cw_input)
        turn_lay.addWidget(self.key_ccw_input)
        self.action_stack.addWidget(turn_page)

        device_page = QWidget()
        dev_row = QHBoxLayout(device_page)
        dev_row.setContentsMargins(0, 0, 0, 0)
        self.device_combo = QComboBox()
        refresh_devices = button("Refresh")
        refresh_devices.clicked.connect(lambda: self.load_devices(self.device_combo.currentData()))
        dev_row.addWidget(self.device_combo, 1)
        dev_row.addWidget(refresh_devices)
        self.action_stack.addWidget(device_page)
        self.action_stack.setFixedHeight(40)
        self.details_row_lbl = label("Details", "section")
        form.addRow(self.details_row_lbl, self.action_stack)

        # Per-mapping settings the chosen action supports.
        self.invert_check = QCheckBox("Swap the two directions")
        form.addRow(self.invert_check)
        self.smooth_check = QCheckBox("Smooth scrolling")
        self.smooth_check.setToolTip("Let go and the scrolling carries on, starting at the speed "
                                     "you were spinning and slowing to a stop")
        form.addRow(self.smooth_check)
        sens_row = QHBoxLayout()
        self.sens_spin = QSpinBox()
        self.sens_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)  # the slider is the handle
        self.sens_spin.setFixedWidth(52)
        self.sens_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sens_spin.setRange(1, 30)
        self.sens_spin.setValue(2)
        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setRange(1, 30)
        self.sens_spin.valueChanged.connect(self.sens_slider.setValue)
        self.sens_slider.valueChanged.connect(self.sens_spin.setValue)
        self.sens_slider.setValue(2)
        sens_row.addWidget(self.sens_slider, 1)
        sens_row.addWidget(self.sens_spin)
        self.sens_lbl = label("Sensitivity", "section")
        form.addRow(self.sens_lbl, sens_row)

        accel_row = QHBoxLayout()
        self.accel_spin = QSpinBox()
        self.accel_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.accel_spin.setFixedWidth(52)
        self.accel_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.accel_spin.setRange(0, 10)
        self.accel_slider = QSlider(Qt.Orientation.Horizontal)
        self.accel_slider.setRange(0, 10)
        self.accel_spin.valueChanged.connect(self.accel_slider.setValue)
        self.accel_slider.valueChanged.connect(self.accel_spin.setValue)
        self.accel_slider.valueChanged.connect(self.describe_accel)
        accel_row.addWidget(self.accel_slider, 1)
        accel_row.addWidget(self.accel_spin)
        self.accel_lbl = label("Speed boost", "section")
        form.addRow(self.accel_lbl, accel_row)
        self.accel_hint = label("", "muted")
        self.accel_hint.setWordWrap(True)
        form.addRow(self.accel_hint)

        self.inherited_lbl = label("", "muted")
        self.inherited_lbl.setWordWrap(True)
        form.addRow(self.inherited_lbl)

        btns = QHBoxLayout()
        self.save_action_btn = button("Save action", "primary")
        self.save_action_btn.clicked.connect(self.on_save_action)
        self.remove_action_btn = button("Remove action", "ghost")
        self.remove_action_btn.clicked.connect(self.on_remove_action)
        btns.addWidget(self.save_action_btn)
        btns.addWidget(self.remove_action_btn)
        btns.addStretch()
        outer.addLayout(btns)
        return tab

    def build_led_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        form_host = QWidget()
        form = QFormLayout(form_host)
        outer.addWidget(scrollable(form_host), 1)
        form.setContentsMargins(0, 16, 0, 0)
        form.setVerticalSpacing(12)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.led_mode_combo = QComboBox()
        for key, text in LED_MODES:
            self.led_mode_combo.addItem(text, key)
        form.addRow(label("Button light", "section"), self.led_mode_combo)

        row = QHBoxLayout()
        self.led_val_slider = QSlider(Qt.Orientation.Horizontal)
        self.led_val_slider.setRange(1, 127)
        self.led_val_spin = QSpinBox()
        self.led_val_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.led_val_spin.setFixedWidth(52)
        self.led_val_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.led_val_spin.setRange(1, 127)
        self.led_val_spin.valueChanged.connect(self.led_val_slider.setValue)
        self.led_val_slider.valueChanged.connect(self.led_val_spin.setValue)
        self.led_val_spin.setValue(127)
        row.addWidget(self.led_val_slider, 1)
        row.addWidget(self.led_val_spin)
        form.addRow(label("Brightness", "section"), row)

        self.led_note = label("", "muted")
        self.led_note.setWordWrap(True)
        form.addRow(self.led_note)

        btns = QHBoxLayout()
        self.save_led_btn = button("Save lighting", "primary")
        self.save_led_btn.clicked.connect(self.on_save_led)
        self.test_led_btn = button("Test light")
        self.test_led_btn.clicked.connect(self.on_test_led)
        btns.addWidget(self.save_led_btn)
        btns.addWidget(self.test_led_btn)
        btns.addStretch()
        outer.addLayout(btns)
        return tab

    def build_log(self):
        box = card()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 12, 16, 14)
        lay.addWidget(label("Activity", "section"))
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(500)  # jog wheels spam; keep the log bounded
        self.console.setFixedHeight(150)
        lay.addWidget(self.console)
        return box

    # ---------- tray ----------
    @staticmethod
    def app_icon():
        """The app's own icon, falling back to a drawn jog wheel if the file is missing."""
        for name in ("Spinin2.ico", "Spinin2.png"):
            icon = QIcon(branding.resource(name))
            if not icon.isNull():
                return icon
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T['chassis']))
        p.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14)
        p.setPen(QPen(QColor(T['pad']), 6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(32, 32), 20, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T['legend']))
        p.drawEllipse(QPointF(32, 32), 6, 6)
        p.end()
        return QIcon(pix)

    def build_tray(self):
        icon = self.app_icon()
        self.setWindowIcon(icon)
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)
        menu.addAction("Open Spinin", self.show_from_tray)
        menu.addSeparator()
        self.tray_follow = menu.addAction("Switch profile with the active app")
        self.tray_follow.setCheckable(True)
        self.tray_follow.setChecked(self.profile_mode == "auto")
        self.tray_follow.toggled.connect(lambda on: self.set_profile_mode("auto" if on else "static"))
        self.tray_profiles = menu.addMenu("Profile")
        menu.addSeparator()
        menu.addAction("Quit", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()
        self.update_tray()

    def update_tray(self):
        """Keeps the tray tooltip, mode tick and profile list in step with the window."""
        if not getattr(self, "tray", None):
            return
        status = f"Standing by for {self.dj_app}" if self.dj_app else self.status_lbl.text()
        self.tray.setToolTip(f"{APP_NAME}\n{status}\nProfile: {self.profile_combo.currentText()}")
        self.tray_follow.setChecked(self.profile_mode == "auto")
        self.tray_profiles.clear()
        for i in range(self.profile_combo.count()):
            p_id, name = self.profile_combo.itemData(i), self.profile_combo.itemText(i)
            act = self.tray_profiles.addAction(name)
            act.setCheckable(True)
            act.setChecked(p_id == self.active_profile)
            act.triggered.connect(lambda _checked, idx=i: self.profile_combo.setCurrentIndex(idx))

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_from_tray() if not self.isVisible() else self.hide_to_tray()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self):
        if not self.tray:
            return
        self.hide()
        if not self.config_manager.get_setting("tray_hint_shown"):
            self.config_manager.set_setting("tray_hint_shown", True)
            self.tray.showMessage("Spinin is still running",
                                  "Your controller keeps working. Click the tray icon to reopen.",
                                  self.app_icon(), 4000)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            # Minimising sends it to the tray instead of the taskbar.
            if self.isMinimized() and getattr(self, "tray", None):
                QTimer.singleShot(0, self.hide_to_tray)
            elif getattr(self, "title_bar", None):
                self.title_bar.restyle()  # the maximise glyph becomes restore and back
        super().changeEvent(event)

    # ---------- resizing a window with no frame ----------
    RESIZE_EDGE = 6  # how close to the rim counts as grabbing it

    def edge_at(self, pos):
        """Which edges of the window this point is on, as a Qt.Edge flag."""
        if self.isMaximized():
            return 0
        m = self.RESIZE_EDGE
        edges = 0
        if pos.x() < m:
            edges |= Qt.Edge.LeftEdge.value
        elif pos.x() > self.width() - m:
            edges |= Qt.Edge.RightEdge.value
        if pos.y() < m:
            edges |= Qt.Edge.TopEdge.value
        elif pos.y() > self.height() - m:
            edges |= Qt.Edge.BottomEdge.value
        return edges

    def mouseMoveEvent(self, event):
        self.setCursor(EDGE_CURSORS.get(self.edge_at(event.position().toPoint()),
                                        Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        edges = self.edge_at(event.position().toPoint())
        handle = self.windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and edges and handle:
            handle.startSystemResize(Qt.Edge(edges))  # Windows runs the resize, as for any window
            return
        super().mousePressEvent(event)

    def quit_app(self):
        self.closing = True
        self.close()

    def init_threads(self):
        self.midi_thread = MidiListenerThread(port_name="DDJ-FLX4")
        self.midi_thread.midi_received.connect(self.on_midi_received)
        self.midi_thread.status_changed.connect(self.on_midi_status_changed)

        self.dj_watcher = DjSoftwareWatcher(self.config_manager.get_setting("extra_dj_apps", []))
        self.dj_watcher.changed.connect(self.on_dj_software_changed)
        self.dj_watcher.start()  # settles dj_app before the port has ever been opened
        if not self.dj_app:
            self.midi_thread.start()

        self.window_tracker = ActiveWindowTracker()
        self.window_tracker.process_changed.connect(self.on_active_window_changed)
        self.window_tracker.start()

    # ---------- making way for DJ software ----------
    def on_dj_software_changed(self, dj_name, running):
        """Hands the controller over while DJ software is up, and takes it back afterwards."""
        self.dj_app = dj_name if running else ""
        if running:
            self.log_message(f"{dj_name} is running — released the DDJ-FLX4 to it.")
            self.set_midi_paused(True, f"Standing by for {dj_name}")
        else:
            self.log_message("DJ software closed — taking the DDJ-FLX4 back.")
            self.set_midi_paused(False)
        self.update_context_bar()
        self.update_tray()

    def set_midi_paused(self, paused, message=""):
        """Closes or reopens the MIDI port.

        Nothing less will do: Windows gives a MIDI input to one process at a time, so merely
        ignoring the messages would still leave the controller unusable to the DJ software.
        """
        if paused:
            self.midi_thread.stop()
            self.action_handler.stop_glides()  # nothing should coast on after the handover
            self.on_midi_status_changed(False, message or "Paused")
        else:
            self.midi_thread.resume()

    # ---------- profiles ----------
    def refresh_profiles(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for p_id, p_data in self.config_manager.get_profiles().items():
            self.profile_combo.addItem(p_data.get("name", p_id), p_id)
        idx = self.profile_combo.findData(self.active_profile)
        self.profile_combo.setCurrentIndex(max(0, idx))
        self.profile_combo.blockSignals(False)
        self.del_prof_btn.setEnabled(self.active_profile != "global")
        if self.profile_mode == "static":
            self.config_manager.set_setting("static_profile", self.active_profile)
        self.update_summaries()
        self.update_context_bar()
        self.update_tray()

    def update_summaries(self):
        profile = self.config_manager.get_profile(self.active_profile)
        merged = dict(self.config_manager.get_profile("global").get("mappings", {}))
        merged.update(profile.get("mappings", {}))
        summaries = {}
        for key, m in merged.items():
            text = describe(m)
            if not text:
                continue
            if "@" in key:
                # A pad-bank mapping: only show it on the canvas while that bank is the one
                # the hardware is actually sitting in, so the dot matches what pressing it does.
                cid, mode = key.split("@", 1)
                deck = pad_deck(cid)
                if deck is None or self.pad_mode.get(deck) != mode:
                    continue
                summaries[cid] = text
            else:
                summaries[key] = text
        self.canvas.set_summaries(summaries)

    def on_profile_changed(self, _index):
        p_id = self.profile_combo.currentData()
        if not p_id or p_id == self.active_profile:
            return
        self.active_profile = p_id
        self.del_prof_btn.setEnabled(p_id != "global")
        self.led_toggled.clear()
        if self.profile_mode == "static":
            self.config_manager.set_setting("static_profile", p_id)
        self.log_message(f"Profile: {self.profile_combo.currentText()}")
        self.update_summaries()
        self.update_context_bar()
        self.update_tray()
        self.apply_static_leds()
        if self.selected_control:
            self.on_control_selected(self.selected_control)

    def on_profile_picked(self, _index):
        if self.profile_mode == "auto":
            # Editing another app's profile is fine here (this window is ignored), but warn that
            # Automatic will move away from it as soon as another window becomes active.
            self.mode_lbl.setText(f"<span style='color:{T['legend']}'>Automatic</span> will switch again when "
                                  "another window is active. Choose Static to keep this profile.")

    def set_profile_mode(self, mode):
        self.profile_mode = mode
        self.config_manager.set_setting("profile_mode", mode)
        if mode == "static":
            self.config_manager.set_setting("static_profile", self.active_profile)
            self.log_message(f"Static profile: {self.profile_combo.currentText()}")
        else:
            self.log_message("Automatic profile switching on")
            self.apply_auto_profile()
        self.update_context_bar()
        self.update_tray()

    def apply_auto_profile(self):
        exe = self.last_foreign_exe
        if self.profile_mode != "auto" or not exe:
            return
        target = exe if exe in self.config_manager.get_profiles() else "global"
        idx = self.profile_combo.findData(target)
        if idx >= 0 and target != self.active_profile:
            self.profile_combo.setCurrentIndex(idx)

    def update_context_bar(self):
        exe = self.last_foreign_exe
        profiles = self.config_manager.get_profiles()
        hi = lambda text: f"<span style='color:{T['legend']}'>{html.escape(text)}</span>"
        name = lambda pid: profiles.get(pid, {}).get("name", pid)

        if self.dj_app:
            self.window_lbl.setText(
                f"<span style='color:{T['pad']}'>●</span>&nbsp; Standing by for {hi(self.dj_app)}")
            self.mode_lbl.setText("Close it to take the controller back")
            self.create_for_app_btn.setVisible(False)
            return

        if exe:
            title = self.last_foreign_title
            title = title if len(title) <= 60 else title[:59] + "…"
            self.window_lbl.setText(f"Active window&nbsp;&nbsp;{hi(exe)}&nbsp;&nbsp;{html.escape(title)}")
        else:
            self.window_lbl.setText("Switch to another app and it will show up here.")

        if self.profile_mode == "static":
            self.mode_lbl.setText(f"Static: {hi(name(self.active_profile))} is used for every window")
        elif exe in profiles:
            self.mode_lbl.setText(f"Automatic: using {hi(name(exe))}")
        elif exe:
            self.mode_lbl.setText(f"Automatic: no profile for {html.escape(exe)}, using {hi(name('global'))}")
        else:
            self.mode_lbl.setText(f"Automatic: using {hi(name('global'))}")

        can_create = bool(exe) and exe not in profiles
        self.create_for_app_btn.setVisible(can_create)
        if can_create:
            self.create_for_app_btn.setText(f"Create profile for {exe}")

    def on_create_for_active_app(self):
        exe = self.last_foreign_exe
        if exe:
            ok, res = self.config_manager.add_profile(exe, exe.removesuffix(".exe").title())
            self._after_profile_create(ok, res)

    def ask_profile_exe(self, title):
        exe, ok = QInputDialog.getText(
            self, title,
            "Which app should this profile follow?\nEnter its process name, e.g. photoshop.exe",
            text=self.last_foreign_exe or "")
        exe = exe.strip().lower()
        return exe if ok and exe else None

    def on_add_profile(self):
        exe = self.ask_profile_exe("New profile")
        if exe:
            ok, res = self.config_manager.add_profile(exe, exe.removesuffix(".exe").title())
            self._after_profile_create(ok, res)

    def on_duplicate_profile(self):
        exe = self.ask_profile_exe("Duplicate profile")
        if exe:
            ok, res = self.config_manager.duplicate_profile(
                self.active_profile, exe, exe.removesuffix(".exe").title())
            self._after_profile_create(ok, res)

    def _after_profile_create(self, ok, res):
        if not ok:
            QMessageBox.warning(self, "Profile not created", res)
            return
        self.active_profile = res
        self.refresh_profiles()
        self.log_message(f"Created profile {res}")

    def on_delete_profile(self):
        if self.active_profile == "global":
            return
        name = self.profile_combo.currentText()
        if QMessageBox.question(self, "Delete profile", f"Delete the “{name}” profile and all its mappings?") \
                != QMessageBox.StandardButton.Yes:
            return
        ok, msg = self.config_manager.delete_profile(self.active_profile)
        if ok:
            self.active_profile = "global"
            self.refresh_profiles()
        self.log_message(msg)

    # ---------- sharing profiles ----------
    def on_export_profiles(self, everything):
        profiles = self.config_manager.get_profiles()
        if not everything:
            profiles = {self.active_profile: profiles.get(self.active_profile, {})}
        suggested = "flx4-profiles.json" if everything else f"flx4-{self.active_profile}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export profiles", suggested,
                                              "Profile files (*.json)")
        if not path:
            return
        try:
            profile_io.write_file(path, profiles)
        except OSError as e:
            QMessageBox.warning(self, "Could not export", str(e))
            return
        count = profile_io.count_actions(profiles)
        self.log_message(f"Exported {len(profiles)} profile(s), {count} action(s) to {path}")
        self.flash_feedback(f"Exported {len(profiles)} profile(s).")

    def on_import_profiles(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import profiles", "",
                                              "Profile files (*.json);;All files (*)")
        if not path:
            return
        profiles, problems = profile_io.read_file(path)
        if not profiles:
            QMessageBox.warning(self, "Nothing imported", "\n".join(problems))
            return

        existing = self.config_manager.get_profiles()
        clashes = [p for p in profiles if p in existing]
        lines = [f"{len(profiles)} profile(s), {profile_io.count_actions(profiles)} action(s):", ""]
        lines += [f"  {p['name']} ({pid}) — {len(p['mappings'])} action(s)"
                  for pid, p in profiles.items()]
        risky = profile_io.risky_entries(profiles)
        if risky:
            # Someone else's profile can start programs on this PC, so show exactly what.
            lines += ["", "These will run programs on your PC when you press the control:"]
            lines += [f"  {entry}" for entry in risky[:12]]
            if len(risky) > 12:
                lines.append(f"  …and {len(risky) - 12} more")
        if problems:
            lines += [""] + problems

        box = QMessageBox(self)
        box.setWindowTitle("Import profiles")
        box.setText(f"Import from {os.path.basename(path)}?")
        box.setInformativeText("\n".join(lines))
        box.setIcon(QMessageBox.Icon.Warning if risky else QMessageBox.Icon.Question)
        import_btn = box.addButton("Import", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not import_btn:
            return

        replace = True
        if clashes:
            answer = QMessageBox.question(
                self, "Profiles with the same name",
                f"You already have: {', '.join(clashes)}.\n\nReplace them with the imported "
                f"versions, or keep yours and import only the rest?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel)
            if answer == QMessageBox.StandardButton.Cancel:
                return
            replace = answer == QMessageBox.StandardButton.Yes

        added = 0
        for profile_id, profile in profiles.items():
            if profile_id in existing and not replace:
                continue
            self.config_manager.get_profiles()[profile_id] = profile
            added += 1
        self.config_manager.save()
        self.refresh_profiles()
        self.log_message(f"Imported {added} profile(s) from {path}")
        self.flash_feedback(f"Imported {added} profile(s).")

    # ---------- inspector ----------
    def show_inspector(self, cid):
        has = cid is not None
        self.tabs.setVisible(has)
        self.value_bar.setVisible(has and control_kind(cid) in ("Knob", "Fader"))
        self.empty_hint.setVisible(not has)
        self.feedback.clear()
        if not has:
            self.insp_title.setText("No control selected")
            self.insp_meta.setText("")
            return
        self.insp_title.setText(CONTROL_NAMES.get(cid, cid))
        self.insp_meta.setText(f"{control_kind(cid)}, sends MIDI {CONTROL_TO_MIDI.get(cid, cid)}")
        self.value_bar.setValue(display_value(cid, self.last_values.get(cid, 0)))

        is_note = CONTROL_TO_MIDI.get(cid, "").startswith("NOTE")
        self.tabs.setTabEnabled(1, is_note)
        if not is_note:
            self.tabs.setCurrentIndex(0)

    def mapping_key_for(self, cid):
        """The key a control's mapping is actually stored under: bank-qualified for a pad."""
        return pad_mapping_key(cid, self.pad_edit_mode) if cid in ALL_PAD_IDS else cid

    def show_pad_bank_picker(self):
        self.pad_bank_row.setVisible(True)
        for mode, b in self.pad_bank_buttons.items():
            b.setChecked(mode == self.pad_edit_mode)

    def on_pad_bank_picked(self, mode):
        self.pad_edit_mode = mode
        self.on_control_selected(self.selected_control)  # reload the panel for that bank

    def on_control_selected(self, cid):
        is_new_pad = cid in ALL_PAD_IDS and cid != self.selected_control
        self.selected_control = cid
        self.canvas.select(cid)
        self.show_inspector(cid)

        if cid in ALL_PAD_IDS:
            deck = pad_deck(cid)
            if is_new_pad:
                self.pad_edit_mode = self.pad_mode[deck]  # default to the hardware's own bank
            self.show_pad_bank_picker()
            self.insp_title.setText(f"{CONTROL_NAMES.get(cid, cid)} — {MODE_LABELS[self.pad_edit_mode]} bank")
        else:
            self.pad_bank_row.setVisible(False)

        key = self.mapping_key_for(cid)
        profile_maps = self.config_manager.get_profile(self.active_profile).get("mappings", {})
        mapping = self.config_manager.get_mapping(self.active_profile, key)
        self.app_path_input.clear()
        self.key_input.set_keys([])
        self.key_cw_input.set_keys([])
        self.key_ccw_input.set_keys([])
        self.script_input.clear()

        self.pending_action = self.action_of(mapping) if mapping else None
        if mapping:
            self.app_path_input.setText(mapping.get("command", ""))
            self.script_input.setText(mapping.get("command", ""))
            self.key_input.set_keys(mapping.get("keys", []))
            self.key_cw_input.set_keys(mapping.get("keys_cw", []))
            self.key_ccw_input.set_keys(mapping.get("keys_ccw", []))
            self.pending_device = (mapping.get("device_id"), mapping.get("device_name"))
            if self.pending_device[0]:
                self.load_devices(*self.pending_device)
            options = mapping.get("options", {})
            self.invert_check.setChecked(bool(options.get("invert")))
            self.smooth_check.setChecked(bool(options.get("smooth")))
            self.sens_spin.setValue(int(options.get("sensitivity", 2)))
            self.accel_spin.setValue(int(options.get("acceleration", 0)))
        else:
            self.invert_check.setChecked(False)
            self.smooth_check.setChecked(False)
            self.sens_spin.setValue(2)
            self.accel_spin.setValue(0)
            self.pending_device = (None, None)
        self.sync_action_editor()

        inherited = mapping and self.active_profile != "global" and key not in profile_maps
        self.inherited_lbl.setText("Using the action from the Global profile. Saving here overrides it "
                                   "for this profile only." if inherited else "")
        self.inherited_lbl.setVisible(bool(inherited))
        self.remove_action_btn.setEnabled(key in profile_maps)

        led = self.config_manager.get_led_setting(self.active_profile, cid)
        self.led_mode_combo.setCurrentIndex(max(0, self.led_mode_combo.findData(led.get("mode", "on_press"))))
        self.led_val_spin.setValue(max(1, led.get("value", 127)))
        self.led_note.setText("" if self.midi_thread.outport else "Connect the controller to test lights.")

    @staticmethod
    def action_of(mapping):
        """The catalog action a stored mapping refers to, new format or old."""
        if mapping.get("type") == "action":
            return catalog.BY_ID.get(mapping.get("id"))
        legacy = {"launch_app": "custom.app", "keystroke": "custom.keys", "script": "custom.command"}
        if mapping.get("type") in legacy:
            return catalog.BY_ID[legacy[mapping["type"]]]
        if mapping.get("type") == "system_action":
            return catalog.BY_ID.get(LEGACY_SYSTEM_IDS.get(mapping.get("action"), ""))
        return None

    def on_choose_action(self):
        cid = self.selected_control
        if not cid:
            return
        current = self.pending_action["id"] if self.pending_action else None
        picker = ActionPicker(action_kind(cid), CONTROL_NAMES.get(cid, cid), current, self)
        if picker.exec() and picker.chosen:
            self.pending_action = picker.chosen
            if "invert" in picker.chosen["options"] and cid in DISPLAY_INVERTED:
                self.invert_check.setChecked(True)  # this control reads backwards; start flipped
            self.sync_action_editor()
            self.flash_feedback("Now press Save action to keep it.")

    def sync_action_editor(self):
        """Shows the button's current action, plus only the fields that action needs."""
        kind = action_kind(self.selected_control) if self.selected_control else "press"
        self.action_label.setText({"press": "When pressed", "range": "While you move it",
                                   "turn": "While you turn it"}[kind])
        action = self.pending_action
        self.choose_btn.setText(action["name"] if action else "Choose an action…")
        self.action_hint.setText(f"{action['hint']} ({action['category']})" if action else
                                 "Nothing assigned yet.")

        detail_page = {"custom.app": 0, "custom.keys": 1, "custom.command": 2, "turn.custom": 3,
                       "audio.setdevice": 4}
        page = detail_page.get(action["id"]) if action else None
        self.action_stack.setVisible(page is not None)
        self.details_row_lbl.setVisible(page is not None)
        if page is not None:
            self.action_stack.setCurrentIndex(page)
            self.action_stack.setFixedHeight(76 if page == 3 else 40)
            if page == 4 and self.device_combo.count() == 0:
                self.load_devices(self.pending_device[0], self.pending_device[1])

        options = action["options"] if action else ()
        self.smooth_check.setVisible("smooth" in options)
        self.invert_check.setVisible("invert" in options)
        self.invert_check.setText("Swap the two directions" if kind == "turn" else "Flip it the other way round")
        show_sens = "sensitivity" in options
        self.sens_lbl.setVisible(show_sens)
        self.sens_slider.setVisible(show_sens)
        self.sens_spin.setVisible(show_sens)
        self.sens_lbl.setText("Ticks per step" if kind == "turn" else "Scroll amount")

        show_accel = "acceleration" in options
        for widget in (self.accel_lbl, self.accel_slider, self.accel_spin, self.accel_hint):
            widget.setVisible(show_accel)
        if show_accel:
            self.describe_accel(self.accel_spin.value())

    def describe_accel(self, value):
        """Spells out what the speed boost does, in wheel clicks rather than numbers."""
        if not value:
            self.accel_hint.setText("Off: every turn moves the same amount, fast or slow.")
        else:
            most = round(1 + value * 1.5)
            self.accel_hint.setText(f"A slow turn stays precise. Spin it and each step counts "
                                    f"for up to {most}×.")

    def load_devices(self, device_id=None, name=None):
        """Fills the sound device list, keeping the mapping's device selected if it's still there."""
        self.device_combo.clear()
        for dev_id, dev_name in audio_devices.outputs():
            self.device_combo.addItem(dev_name, dev_id)
        index = self.device_combo.findData(device_id) if device_id else -1
        if index < 0 and name:
            index = self.device_combo.findText(name)
        if index < 0 and device_id:
            self.flash_feedback(f"“{name or device_id}” isn't plugged in; pick another device.")
        self.device_combo.setCurrentIndex(max(0, index))

    def on_browse_app(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose an app", "",
                                              "Programs (*.exe *.bat *.cmd *.lnk);;All files (*)")
        if path:
            self.app_path_input.setText(path)

    def on_pick_installed_app(self):
        picker = InstalledAppPicker(self)
        if picker.exec() and picker.chosen:
            self.app_path_input.setText(picker.chosen)
            self.flash_feedback("Now press Save action to keep it.")

    def on_about(self):
        AboutDialog(self.app_icon(), self).exec()

    def flash_feedback(self, text):
        self.feedback.setText(text)
        QTimer.singleShot(2500, lambda: self.feedback.text() == text and self.feedback.clear())

    def on_save_action(self):
        cid = self.selected_control
        if not cid:
            return
        action = self.pending_action
        if not action:
            self.flash_feedback("Choose an action first.")
            return
        data = {"type": "action", "id": action["id"]}
        missing = ""
        if action["id"] == "custom.app":
            data["command"] = self.app_path_input.text().strip()
            missing = "" if data["command"] else "Type an app name or pick one with Browse."
        elif action["id"] == "custom.command":
            data["command"] = self.script_input.text().strip()
            missing = "" if data["command"] else "Type the command to run."
        elif action["id"] == "custom.keys":
            data["keys"] = self.key_input.captured_keys
            missing = "" if data["keys"] else "Click the box and press the shortcut."
        elif action["id"] == "turn.custom":
            data["keys_cw"] = self.key_cw_input.captured_keys
            data["keys_ccw"] = self.key_ccw_input.captured_keys
            missing = "" if (data["keys_cw"] and data["keys_ccw"]) else "Record a shortcut for each direction."
        elif action["id"] == "audio.setdevice":
            data["device_id"] = self.device_combo.currentData()
            data["device_name"] = self.device_combo.currentText()
            missing = "" if data["device_id"] else "No playback devices found."
        options = {}
        if "invert" in action["options"] and self.invert_check.isChecked():
            options["invert"] = True
        if "smooth" in action["options"] and self.smooth_check.isChecked():
            options["smooth"] = True
        if "sensitivity" in action["options"]:
            options["sensitivity"] = self.sens_spin.value()
        if "acceleration" in action["options"] and self.accel_spin.value():
            options["acceleration"] = self.accel_spin.value()
        if options:
            data["options"] = options
        if missing:
            self.flash_feedback(missing)
            return
        key = self.mapping_key_for(cid)
        self.config_manager.set_mapping(self.active_profile, key, data)
        bank = f" ({MODE_LABELS[self.pad_edit_mode]})" if cid in ALL_PAD_IDS else ""
        self.log_message(f"Saved {CONTROL_NAMES.get(cid, cid)}{bank}: {describe(data)}")
        self.update_summaries()
        self.on_control_selected(cid)
        self.flash_feedback(f"Saved. {describe(data)}.")

    def on_remove_action(self):
        cid = self.selected_control
        if cid:
            self.config_manager.set_mapping(self.active_profile, self.mapping_key_for(cid), None)
            bank = f" ({MODE_LABELS[self.pad_edit_mode]})" if cid in ALL_PAD_IDS else ""
            self.log_message(f"Removed action from {CONTROL_NAMES.get(cid, cid)}{bank}")
            self.update_summaries()
            self.on_control_selected(cid)
            self.flash_feedback("Action removed.")

    # ---------- lights ----------
    def on_save_led(self):
        cid = self.selected_control
        if not cid:
            return
        data = {"mode": self.led_mode_combo.currentData(), "value": self.led_val_spin.value()}
        self.config_manager.set_led_setting(self.active_profile, cid, data)
        self.led_toggled.discard(cid)
        self.apply_static_leds()
        self.log_message(f"Saved lighting for {CONTROL_NAMES.get(cid, cid)}: {self.led_mode_combo.currentText()}")
        self.flash_feedback("Lighting saved.")

    def on_test_led(self):
        cid = self.selected_control
        if not cid:
            return
        code = CONTROL_TO_MIDI.get(cid, cid)
        self.midi_thread.send_led(code, self.led_val_spin.value())
        QTimer.singleShot(900, self.apply_static_leds_or_off(code, cid))

    def apply_static_leds_or_off(self, code, cid):
        def restore():
            mode = self.config_manager.get_led_setting(self.active_profile, cid).get("mode")
            if mode != "always_on":
                self.midi_thread.send_led(code, 0)
        return restore

    def apply_static_leds(self):
        """Pushes 'always on' / 'always off' lights to the controller."""
        for cid, code, _, _ in CONTROLS:
            if not code.startswith("NOTE"):
                continue
            led = self.config_manager.get_led_setting(self.active_profile, cid)
            if led.get("mode") == "always_on":
                self.midi_thread.send_led(code, led.get("value", 127))
            elif led.get("mode") in ("off", "toggle") and cid not in self.led_toggled:
                self.midi_thread.send_led(code, 0)

    def flash_led(self, code, value, times=2, interval=110):
        # Timers, not sleep: sleeping here would freeze the whole window.
        for i in range(times):
            QTimer.singleShot(i * 2 * interval, lambda: self.midi_thread.send_led(code, value))
            QTimer.singleShot(i * 2 * interval + interval, lambda: self.midi_thread.send_led(code, 0))

    def drive_led(self, cid, code, value):
        if not code.startswith("NOTE"):
            return
        led = self.config_manager.get_led_setting(self.active_profile, cid)
        mode, level = led.get("mode", "on_press"), led.get("value", 127)
        pressed = value > 0
        if mode == "on_press":
            self.midi_thread.send_led(code, level if pressed else 0)
        elif mode == "toggle" and pressed:
            if cid in self.led_toggled:
                self.led_toggled.discard(cid)
                self.midi_thread.send_led(code, 0)
            else:
                self.led_toggled.add(cid)
                self.midi_thread.send_led(code, level)
        elif mode == "flash" and pressed:
            self.flash_led(code, level)
        elif mode == "always_on":
            self.midi_thread.send_led(code, level)
        elif mode == "off":
            self.midi_thread.send_led(code, 0)

    # ---------- live input ----------
    def on_midi_received(self, control_id, msg_type, value, raw_code):
        is_note = msg_type != "control_change"
        name = CONTROL_NAMES.get(control_id)
        if name is None:
            # Worth spelling out: an unrecognised code can never trigger an action.
            name = "not a control the app knows, so nothing can be mapped to it"
        self.log_message(f"{raw_code:<11} {value:>3}  {name}")
        self.last_values[control_id] = value

        if raw_code in FX_SWITCH_NOTES:
            self.on_fx_switch(raw_code, value)
            return

        if control_id in PAD_MODE_BUTTONS and value > 0:
            self.on_pad_mode_button(control_id)

        self.canvas.pulse(control_id, value, is_note)

        if self.pick_from_hw.isChecked() and control_id in HOTSPOTS and control_id != self.selected_control \
                and (value > 0 or not is_note):
            self.on_control_selected(control_id)
        elif control_id == self.selected_control:
            self.value_bar.setValue(display_value(control_id, value))

        self.drive_led(control_id, raw_code, value)

        if control_id in ALL_PAD_IDS:
            lookup_id = pad_mapping_key(control_id, self.pad_mode[pad_deck(control_id)])
        else:
            lookup_id = control_id
        mapping = self.config_manager.get_mapping(self.active_profile, lookup_id)
        if mapping and (value > 0 or not is_note):
            self.action_handler.execute(mapping, value=value, control_id=control_id)

    def on_pad_mode_button(self, control_id):
        """A mode button switches which bank the 8 pads below it are currently using."""
        deck, mode = PAD_MODE_BUTTONS[control_id]
        if self.pad_mode[deck] == mode:
            return
        self.pad_mode[deck] = mode
        self.log_message(f"Deck {'1' if deck == 'L' else '2'} pad bank: {MODE_LABELS[mode]}")
        self.update_summaries()
        # If the panel is showing a pad on this deck, follow the switch so it keeps matching
        # what pressing a pad will actually do.
        if self.selected_control in ALL_PAD_IDS and pad_deck(self.selected_control) == deck:
            self.pad_edit_mode = mode
            self.on_control_selected(self.selected_control)

    def on_fx_switch(self, raw_code, value):
        """The Beat FX switch: act on the position it lands in, not on the two notes it sends.

        Sliding it to 1&2 turns both notes on, so the position is worked out from which notes
        are currently on, and each of the three positions carries its own action.
        """
        self.fx_notes_on.add(raw_code) if value > 0 else self.fx_notes_on.discard(raw_code)
        state = tuple(sorted(FX_SWITCH_NOTES[c] for c in self.fx_notes_on))
        position = FX_SWITCH_POSITIONS.get(state)
        if not position or position == self.fx_position:
            return  # mid-slide, or a note repeated for a position we are already in
        self.fx_position = position
        self.canvas.pulse(position, 127, True)
        QTimer.singleShot(400, lambda: self.canvas.pulse(position, 0, True))
        self.log_message(f"Beat FX switch at {CONTROL_NAMES[position].split('at ')[-1]}")

        if self.pick_from_hw.isChecked():
            self.on_control_selected(position)
        mapping = self.config_manager.get_mapping(self.active_profile, position)
        if mapping:
            self.action_handler.execute(mapping, value=127, control_id=position)

    def restyle_status(self):
        """Repaints the status pill in the current theme, without logging it again."""
        # Standing by is not a fault, so it gets the accent rather than the warning colour.
        colour = T["pad"] if self.dj_app else (T["ok"] if self.midi_connected else T["danger"])
        self.status_dot.setStyleSheet(f"color: {colour}; font-size: 14px;")
        self.status_lbl.setText(f"Connected to {self.status_message}" if self.midi_connected
                                else self.status_message)

    def on_midi_status_changed(self, connected, message):
        self.midi_connected, self.status_message = connected, message
        self.restyle_status()
        self.log_message(f"Connected to {message}" if connected else message)
        self.update_tray()
        if connected:
            self.apply_static_leds()

    def on_active_window_changed(self, exe_name, title):
        if exe_name == "global":  # tracker couldn't identify the window; keep the last known one
            return
        changed = exe_name != self.last_foreign_exe
        self.last_foreign_exe, self.last_foreign_title = exe_name, title
        self.update_context_bar()
        if changed and self.profile_mode == "auto":
            self.switch_timer.start()  # restarts the debounce

    def log_message(self, text):
        self.console.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def closeEvent(self, event):
        # Closing the window quits; use minimise to keep it running in the tray.
        if getattr(self, "tray", None):
            self.tray.hide()
        # Belt and braces: a capture box's hook blocks every key on the system, and normally
        # stops on focus-out, but the window can close while one still has focus.
        for box in (self.key_input, self.key_cw_input, self.key_ccw_input):
            box._capture.stop()
        self.dj_watcher.stop()
        self.action_handler.stop_glides()
        self.midi_thread.stop()
        self.window_tracker.stop()
        super().closeEvent(event)


def install_error_guard(window):
    """Keeps the app alive after an unexpected error.

    PyQt aborts the whole process when a Python exception escapes a slot, which is why
    unplugging the controller could take the app down with it. Logging it instead means a
    one-off error costs you a line in the Activity log, not the session.
    """
    def hook(exc_type, exc, tb):
        traceback.print_exception(exc_type, exc, tb)
        try:
            window.log_message(f"Error: {exc_type.__name__}: {exc}")
        except Exception:
            pass
    sys.excepthook = hook


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)
    # Drawing the tick marks by hand is why this wraps Fusion rather than using it directly.
    app.setStyle(win_chrome.SpininStyle("Fusion"))
    app.setQuitOnLastWindowClosed(False)  # hiding to the tray must not quit
    window = MidiMapperApp()  # reads the saved theme before the stylesheet is built
    app.setWindowIcon(window.app_icon())
    app.setStyleSheet(stylesheet())  # on the app, so dialogs are themed too
    install_error_guard(window)
    window.show()
    app.aboutToQuit.connect(window.midi_thread.stop)
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        # Started by double-click there is no console to read, so the error is written down
        # and shown, instead of a window that never appears.
        report = traceback.format_exc()
        # Beside the settings, not the program: an installed app cannot write next to itself.
        log = os.path.join(branding.data_dir(), "startup-error.log")
        try:
            with open(log, "w", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{sys.executable}\n\n{report}")
        except OSError:
            pass
        print(report, file=sys.stderr)
        try:
            QMessageBox.critical(None, "Spinin could not start",
                                 f"{report.strip().splitlines()[-1]}\n\nFull details: {log}")
        except BaseException:
            pass
        sys.exit(1)
