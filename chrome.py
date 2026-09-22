# SPDX-License-Identifier: GPL-3.0-or-later
# chrome.py
# The bits of polish around how the app is drawn: proper tick marks, menu icons, and the
# frosted background behind menus.
#
# Everything here degrades quietly. If a platform call is missing or refused the app still
# runs and still looks right, it just loses the effect. The frosted menus are a Windows
# effect and are simply absent on macOS, where the menu stays opaque.

import sys

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QFont, QFontDatabase
from PyQt6.QtWidgets import QProxyStyle, QStyle

from theme import T

IS_MAC = sys.platform == "darwin"

if not IS_MAC:
    import ctypes
    from ctypes import wintypes
else:
    ctypes = wintypes = None

# Windows 11 ships Segoe Fluent Icons; Windows 10 has the same glyphs in Segoe MDL2 Assets.
ICON_FONTS = ("Segoe Fluent Icons", "Segoe MDL2 Assets")

# Glyph names are Microsoft's own, kept here so a swap is obvious.
GLYPH = {
    "import": "",    # OpenFile
    "export": "",    # Save
    "export_all": "",  # Copy
    "theme": "",     # Color
    "about": "",     # Info
    "app": "",       # AllApps
    "minimize": "",  # ChromeMinimize
    "maximize": "",  # ChromeMaximize
    "restore": "",   # ChromeRestore
    "close": "",     # ChromeClose
}

# macOS has no Segoe icon font, and those code points are in a private use area, so they
# would come out as empty boxes. These are ordinary Unicode, present in the system font.
MAC_GLYPH = {
    "import": "↓",      # downwards arrow
    "export": "↑",      # upwards arrow
    "export_all": "⇈",  # upwards paired arrows
    "theme": "◐",       # circle with left half black
    "about": "ⓘ",       # circled latin small letter i
    "app": "☰",         # trigram for heaven, reads as a list
    "minimize": "─",    # box drawings light horizontal
    "maximize": "□",    # white square
    "restore": "❐",     # upper right drop-shadowed white square
    "close": "✕",       # multiplication x
}

_icon_family = None


def icon_family():
    """Whichever Windows icon font this PC has, or None when neither is installed."""
    global _icon_family
    if _icon_family is None:
        if IS_MAC:
            _icon_family = ""  # the Mac glyphs are plain Unicode, drawn in the UI font
        else:
            families = set(QFontDatabase.families())
            _icon_family = next((f for f in ICON_FONTS if f in families), "")
    return _icon_family or None


def glyph_for(name):
    """The character to draw for a named icon, in this platform's icon vocabulary."""
    table = MAC_GLYPH if IS_MAC or not icon_family() else GLYPH
    return table.get(name, GLYPH.get(name, name))


def icon_font(px):
    family = icon_family() or ("SF Pro Text" if IS_MAC else "Segoe UI")
    f = QFont(family)
    f.setPixelSize(px)
    return f


def glyph_icon(name, px=16, colour=None):
    """A menu icon drawn as a glyph, in the theme's own colour."""
    char = glyph_for(name)
    size = px * 2  # drawn at 2x so it stays sharp on a scaled display
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setFont(icon_font(int(size * 0.72)))
    p.setPen(QColor(colour or T["legend"]))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, char)
    p.end()
    return QIcon(pix)


def draw_tick(painter, rect, colour, weight=2.0):
    """The tick itself: a two-stroke check, sized to the box it sits in."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    path = QPainterPath()
    path.moveTo(x + w * 0.24, y + h * 0.52)
    path.lineTo(x + w * 0.42, y + h * 0.70)
    path.lineTo(x + w * 0.77, y + h * 0.30)
    pen = QPen(QColor(colour), weight)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


class SpininStyle(QProxyStyle):
    """Draws the check boxes and menu ticks by hand, so they are a tick and not a filled square.

    Qt's own indicator is a square block once a stylesheet touches it, which is why the
    stylesheet deliberately leaves QCheckBox::indicator alone and lets this run instead.
    """

    def pixelMetric(self, metric, option=None, widget=None):
        # Fusion's 13px box is too small next to 13px text once the tick is a tick.
        pm = QStyle.PixelMetric
        if metric in (pm.PM_IndicatorWidth, pm.PM_IndicatorHeight):
            return 18
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        pe = QStyle.PrimitiveElement
        if element == pe.PE_IndicatorCheckBox:
            self._checkbox(option, painter)
            return
        if element == pe.PE_IndicatorMenuCheckMark:
            rect = QRectF(option.rect)
            if option.state & QStyle.StateFlag.State_On:
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                draw_tick(painter, rect, T["pad"], 1.8)
                painter.restore()
            return
        super().drawPrimitive(element, option, painter, widget)

    @staticmethod
    def _checkbox(option, painter):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(option.rect.width(), option.rect.height())
        box = QRectF(option.rect.x(), option.rect.y() + (option.rect.height() - side) / 2,
                     side, side).adjusted(0.75, 0.75, -0.75, -0.75)
        state = option.state
        on = bool(state & QStyle.StateFlag.State_On)
        hover = bool(state & QStyle.StateFlag.State_MouseOver)
        radius = max(3.0, side * 0.28)

        if on:
            painter.setPen(QPen(QColor(T["pad"]), 1.2))
            painter.setBrush(QColor(T["pad"]))
        else:
            painter.setPen(QPen(QColor(T["legend"] if hover else T["muted"]), 1.2))
            painter.setBrush(QColor(T["raised"]))
        painter.drawRoundedRect(box, radius, radius)
        if on:
            draw_tick(painter, box, T["on_pad"], max(1.6, side * 0.13))
        painter.restore()


# ---------------- frosted backgrounds ----------------
class _ACCENTPOLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_uint), ("AccentFlags", ctypes.c_uint),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_uint)]


class _WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(_ACCENTPOLICY)),
                ("SizeOfData", ctypes.c_size_t)]


ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
DWMWCP_ROUNDSMALL = 3


def _hwnd(widget):
    if IS_MAC:
        return None
    try:
        return wintypes.HWND(int(widget.winId()))
    except Exception:
        return None


def round_corners(widget, small=False):
    """Asks Windows 11 for its own rounded corners on this window."""
    handle = _hwnd(widget)
    if not handle:
        return False
    try:
        value = ctypes.c_int(DWMWCP_ROUNDSMALL if small else DWMWCP_ROUND)
        return ctypes.windll.dwmapi.DwmSetWindowAttribute(
            handle, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(value),
            ctypes.sizeof(value)) == 0
    except Exception:
        return False  # Windows 10 and earlier have no such attribute


def acrylic(widget, colour=None, alpha=0xAE):
    """Frosts whatever is behind this window, tinted with the theme's panel colour."""
    handle = _hwnd(widget)
    if not handle:
        return False
    try:
        set_attr = ctypes.windll.user32.SetWindowCompositionAttribute
    except AttributeError:
        return False  # only exists from Windows 10 onwards
    c = QColor(colour or T["panel"])
    # The gradient colour is packed the other way round from the usual: 0xAABBGGRR.
    packed = (alpha << 24) | (c.blue() << 16) | (c.green() << 8) | c.red()
    policy = _ACCENTPOLICY(ACCENT_ENABLE_ACRYLICBLURBEHIND, 2, packed, 0)
    data = _WINCOMPATTRDATA(WCA_ACCENT_POLICY, ctypes.pointer(policy), ctypes.sizeof(policy))
    try:
        return bool(set_attr(handle, ctypes.byref(data)))
    except Exception:
        return False


def frost_menu(menu, opacity=0.26):
    """Makes a QMenu a frosted panel, and says whether Windows agreed to frost it.

    The see-through stylesheet is only applied once the blur is actually in place. Without
    that check a PC that refuses the effect would get a transparent menu over bare desktop,
    which is worse than the plain one it started with.
    """
    if IS_MAC:
        # macOS draws its own menu shadow and rounding. Stripping those to fake a frost we
        # cannot produce here would leave the menu looking worse than the plain one.
        return False
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    menu.winId()  # the native window has to exist before Windows is asked about it
    blurred = acrylic(menu)
    round_corners(menu, small=True)
    if blurred:
        from theme import menu_qss
        menu.setStyleSheet(menu_qss(opacity))
    else:
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    return blurred


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QCheckBox, QMenu

    app = QApplication(sys.argv)
    app.setStyle(SpininStyle("Fusion"))

    assert icon_family() in (*ICON_FONTS, None)
    icon = glyph_icon("about", 16)
    assert not icon.isNull() and not icon.pixmap(32, 32).isNull()

    # The tick must actually put ink inside the box, in both states.
    def ink(checked):
        box = QCheckBox("x")
        box.setChecked(checked)
        pix = QPixmap(20, 20)
        pix.fill(Qt.GlobalColor.black)
        p = QPainter(pix)
        from PyQt6.QtWidgets import QStyleOptionButton
        o = QStyleOptionButton()
        o.rect = pix.rect()
        o.state = (QStyle.StateFlag.State_On if checked else QStyle.StateFlag.State_Off)
        SpininStyle("Fusion").drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, o, p)
        p.end()
        img = pix.toImage()
        return len({img.pixel(x, y) for x in range(20) for y in range(20)})

    assert ink(False) > 1, "an empty box still needs an outline"
    assert ink(True) > ink(False), "a ticked box must have more in it than an empty one"

    menu = QMenu()
    menu.addAction(glyph_icon("theme"), "Theme")
    frost_menu(menu)  # must not raise, whatever Windows makes of it
    print(f"chrome OK — icon font: {icon_family() or 'none installed'}")
