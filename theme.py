# SPDX-License-Identifier: GPL-3.0-or-later
# theme.py
# The palettes and the stylesheet built from whichever one is active.
#
# Every colour the app draws comes from T, so switching a theme re-styles the window and the
# controller view together. Themes are named after where you would use them.
#
# A theme may also set the shape and type tokens in SHAPE below (corner radii, the heading
# font, button padding), so a theme can change the app's silhouette and not only its colours.
# Leave them out and the theme gets the app's original look.

SHAPE = {
    "display": "Bahnschrift",   # headings, values, the controller legend
    "r_card": 14,               # cards
    "r_btn": 8,                 # buttons
    "r_input": 8,               # combo boxes, text fields, spin boxes, menus
    "r_box": 10,                # list views, the log, the context bar
    "r_item": 7,                # rows inside lists and menus
    "btn_pad": "7px 14px",
}

THEMES = {
    "graphite": {
        "label": "Graphite", "note": "The controller's own colours",
        "chassis": "#1f2023", "panel": "#292a2e", "raised": "#34363b", "line": "#43454b",
        "legend": "#ebe7e0", "muted": "#9d9a93", "pad": "#ff8c1a", "on_pad": "#1a1206",
        "danger": "#ff6b5e", "ok": "#8fd694", "select": "#50525a", "dark": True,
    },
    "booth": {
        "label": "Dark Booth", "note": "Near black, for a dim room",
        "chassis": "#0d0e10", "panel": "#161719", "raised": "#212226", "line": "#303237",
        "legend": "#e8e8ea", "muted": "#8b8d93", "pad": "#ff5a2b", "on_pad": "#1a0a04",
        "danger": "#ff6b5e", "ok": "#7fd18a", "select": "#3a3c42", "dark": True,
    },
    "club": {
        "label": "Club Blue", "note": "Deep blue with a cyan accent",
        "chassis": "#101726", "panel": "#182136", "raised": "#212d47", "line": "#2e3c5c",
        "legend": "#e6edfb", "muted": "#8fa0c0", "pad": "#35d6f0", "on_pad": "#04202a",
        "danger": "#ff7a7a", "ok": "#7ee0b0", "select": "#2c3c5e", "dark": True,
    },
    "neon": {
        "label": "Neon Night", "note": "Violet with a magenta accent",
        "chassis": "#16111f", "panel": "#1f1830", "raised": "#2b2142", "line": "#3d2f5c",
        "legend": "#efe8fb", "muted": "#a294c0", "pad": "#ff4fd8", "on_pad": "#260420",
        "danger": "#ff7a92", "ok": "#8ce0c0", "select": "#3a2c58", "dark": True,
    },
    "voltage": {
        "label": "Voltage", "note": "Near black and electric lime, big soft corners",
        "chassis": "#0b0b0d", "chassis2": "#141418",
        "panel": "#171719", "panel2": "#101012",
        "raised": "#212126", "line": "#2b2b31",
        "legend": "#f3f4f1", "muted": "#83848b",
        "pad": "#cdf94a", "pad2": "#a7d92c", "on_pad": "#0e1204",
        "danger": "#ff6f60", "ok": "#8fd694", "select": "#2f3038", "dark": True,
        "display": "Segoe UI Variable Display", "r_card": 22, "r_btn": 16,
        "r_input": 13, "r_box": 16, "r_item": 10, "btn_pad": "9px 18px",
    },
    "daylight": {
        "label": "Daylight", "note": "Light, for a bright room",
        "chassis": "#eceae5", "panel": "#f7f5f1", "raised": "#e4e1da", "line": "#cfcbc2",
        "legend": "#23242a", "muted": "#6d6a64", "pad": "#d2660a", "on_pad": "#fff6ec",
        "danger": "#c23b2e", "ok": "#2f7d44", "select": "#d7d3ca", "dark": False,
    },
}

DEFAULT_THEME = "voltage"
T = {}


def apply_theme(name):
    """Switches the active palette. Returns the name actually applied."""
    name = name if name in THEMES else DEFAULT_THEME
    T.clear()
    T.update(SHAPE)          # shape and type first, so a theme can override any of it
    T.update(THEMES[name])
    T["name"] = name
    return name


apply_theme(DEFAULT_THEME)


def fill(a, b):
    """Flat colour, or a soft top-to-bottom gradient when the theme gives a second stop."""
    return a if not b else f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {a}, stop:1 {b})"


def rgba(hex_colour, alpha):
    """#rrggbb plus an opacity of 0..1, as the rgba() a stylesheet wants."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def menu_qss(opacity=1.0):
    """The QMenu rules on their own, so a frosted menu can restate them see-through.

    Deliberately says nothing about QMenu::indicator: leaving that alone is what lets the
    app's own style draw a real tick there instead of Qt's filled square.
    """
    t = T
    return f"""
QMenu {{ background: {rgba(t['panel'], opacity)}; border: 1px solid {t['line']};
    border-radius: {t['r_input']}px; padding: 6px; }}
QMenu::item {{ padding: 8px 30px 8px 38px; border-radius: {t['r_item'] - 1}px; color: {t['legend']}; }}
QMenu::item:selected {{ background: {rgba(t['raised'], min(1.0, opacity + 0.25))}; }}
QMenu::item:disabled {{ color: {t['muted']}; }}
QMenu::icon {{ left: 13px; }}
QMenu::separator {{ height: 1px; background: {t['line']}; margin: 5px 10px; }}
QMenu::right-arrow {{ width: 10px; height: 10px; right: 12px; }}
"""


def stylesheet():
    t = T
    # A light theme needs darker hovers than a dark one.
    hover = "rgba(0,0,0,0.05)" if not t["dark"] else "rgba(255,255,255,0.05)"
    return f"""
* {{ font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; font-size: 13px; color: {t['legend']}; }}
QWidget#root {{ background: {fill(t['chassis'], t.get('chassis2'))}; }}
QFrame#card {{ background: {fill(t['panel'], t.get('panel2'))}; border: 1px solid {t['line']};
    border-radius: {t['r_card']}px; }}
QFrame#header {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel[role="muted"] {{ color: {t['muted']}; }}
QLabel[role="title"] {{ font-family: '{t['display']}'; font-size: 20px; font-weight: 600; }}
QLabel[role="brand"] {{ font-family: '{t['display']}'; font-size: 17px; font-weight: 600; letter-spacing: 0.5px; }}
QLabel[role="section"] {{ font-family: '{t['display']}'; font-size: 14px; color: {t['muted']}; }}

QPushButton {{ background: {t['raised']}; border: 1px solid {t['line']}; border-radius: {t['r_btn']}px;
    padding: {t['btn_pad']}; }}
QPushButton:hover {{ border-color: {t['muted']}; }}
QPushButton:pressed {{ background: {t['select']}; }}
QPushButton:disabled {{ color: {t['muted']}; border-color: {t['line']}; }}
QPushButton:focus {{ border-color: {t['pad']}; }}
QPushButton[kind="primary"] {{ background: {fill(t['pad'], t.get('pad2'))}; color: {t['on_pad']};
    border: 1px solid {t['pad']}; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: {t['pad']}; border-color: {t['legend']}; }}
QPushButton[kind="primary"]:disabled {{ background: {t['raised']}; color: {t['muted']}; border-color: {t['line']}; }}
QPushButton[kind="ghost"] {{ background: transparent; border-color: transparent; color: {t['muted']}; }}
QPushButton[kind="ghost"]:hover {{ color: {t['legend']}; background: {t['raised']}; }}
QFrame#segment {{ background: {t['raised']}; border: 1px solid {t['line']}; border-radius: {t['r_input'] + 1}px; }}
QPushButton[kind="segment"] {{ background: transparent; border: none; border-radius: {t['r_input'] - 2}px;
    padding: 5px 12px; color: {t['muted']}; }}
QPushButton[kind="segment"]:hover {{ color: {t['legend']}; }}
QPushButton[kind="segment"]:checked {{ background: {t['select']}; color: {t['legend']}; }}
QFrame#contextbar {{ background: {t['panel']}; border: 1px solid {t['line']}; border-radius: {t['r_box']}px; }}

QComboBox, QLineEdit, QSpinBox {{ background: {t['raised']}; border: 1px solid {t['line']};
    border-radius: {t['r_input']}px; padding: 6px 10px;
    selection-background-color: {t['pad']}; selection-color: {t['on_pad']}; }}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover {{ border-color: {t['muted']}; }}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border-color: {t['pad']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {t['raised']}; border: 1px solid {t['line']}; outline: none;
    selection-background-color: {t['select']}; selection-color: {t['legend']}; padding: 4px; }}
QLineEdit[capture="true"] {{ font-family: '{t['display']}'; font-size: 15px; letter-spacing: 1px; }}

QTabWidget::pane {{ border: none; border-top: 1px solid {t['line']}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {t['muted']}; padding: 8px 2px; margin-right: 18px;
    border-bottom: 2px solid transparent; font-family: '{t['display']}'; font-size: 14px; }}
QTabBar::tab:hover {{ color: {t['legend']}; }}
QTabBar::tab:selected {{ color: {t['legend']}; border-bottom: 2px solid {t['pad']}; }}

QCheckBox {{ spacing: 9px; color: {t['muted']}; }}
QCheckBox:hover {{ color: {t['legend']}; }}
QCheckBox:checked {{ color: {t['legend']}; }}

QSlider::groove:horizontal {{ height: 4px; background: {t['line']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {t['pad']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 14px; margin: -6px 0; border-radius: 7px; background: {t['legend']}; }}

QProgressBar {{ background: {t['raised']}; border: none; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: {t['pad']}; border-radius: 3px; }}

QPlainTextEdit {{ background: {t['chassis']}; border: 1px solid {t['line']}; border-radius: {t['r_box']}px;
    padding: 6px; font-family: 'Cascadia Mono', Consolas, monospace; font-size: 11px; color: {t['muted']}; }}
QScrollArea#plain, QScrollArea#plain > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {t['line']}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QToolTip {{ background: {t['raised']}; color: {t['legend']}; border: 1px solid {t['line']};
    border-radius: {t['r_item']}px; padding: 4px; }}
QDialog {{ background: {fill(t['chassis'], t.get('chassis2'))}; }}
QListWidget {{ background: {t['panel']}; border: 1px solid {t['line']}; border-radius: {t['r_box']}px;
    outline: none; padding: 5px; }}
QListWidget::item {{ padding: 7px 10px; border-radius: {t['r_item']}px; color: {t['muted']}; }}
QListWidget::item:hover {{ color: {t['legend']}; background: {hover}; }}
QListWidget::item:selected {{ background: {t['select']}; color: {t['legend']}; }}
QMessageBox, QInputDialog {{ background: {t['panel']}; }}

QFrame#titlebar {{ background: transparent; }}
QLabel[role="wordmark"] {{ font-family: '{t['display']}'; font-size: 15px; font-weight: 600;
    letter-spacing: 0.6px; }}
QPushButton[kind="chrome"] {{ background: transparent; border: none; border-radius: {t['r_btn'] - 6}px;
    color: {t['muted']}; padding: 0; min-width: 40px; max-width: 40px; min-height: 30px; max-height: 30px; }}
QPushButton[kind="chrome"]:hover {{ background: {t['raised']}; color: {t['legend']}; }}
QPushButton[kind="chrome"]:pressed {{ background: {t['select']}; }}
QPushButton[kind="chrome"][danger="true"]:hover {{ background: {t['danger']}; color: #ffffff; }}
""" + menu_qss()


if __name__ == "__main__":
    import re
    for name, palette in THEMES.items():
        apply_theme(name)
        css = stylesheet()
        assert "None" not in css and "{'" not in css, name
        for key in ("chassis", "panel", "raised", "line", "legend", "muted", "pad", "on_pad",
                    "danger", "ok", "select"):
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", palette[key]), (name, key, palette[key])
        for key, extra in (("chassis2", None), ("panel2", None), ("pad2", None)):
            if key in palette:
                assert re.fullmatch(r"#[0-9a-fA-F]{6}", palette[key]), (name, key, palette[key])
        for key in SHAPE:  # every token the stylesheet reads must resolve, defaulted or set
            assert key in T, (name, key)
        assert f"border-radius: {T['r_card']}px" in css, name

    # A theme that sets a second stop paints a gradient; one that does not stays flat.
    apply_theme("voltage")
    assert "qlineargradient" in stylesheet() and T["display"] == "Segoe UI Variable Display"
    apply_theme("graphite")
    assert "qlineargradient" not in stylesheet(), "themes without a second stop stay flat"
    assert T["r_card"] == SHAPE["r_card"] and T["display"] == SHAPE["display"], "defaults apply"

    assert apply_theme("nonsense") == DEFAULT_THEME, "an unknown theme falls back"
    assert DEFAULT_THEME == "voltage", "Voltage is what a new install opens in"

    assert rgba("#cdf94a", 1) == "rgba(205, 249, 74, 1.000)"
    assert rgba("ffffff", 0.5) == "rgba(255, 255, 255, 0.500)", "a missing # is still a colour"
    # Ticks are drawn by the app's own style, so the stylesheet must not claim the indicators.
    assert "QCheckBox::indicator" not in stylesheet() and "QMenu::indicator" not in menu_qss()
    assert "rgba(" in menu_qss(0.6) and menu_qss(1.0) in stylesheet(), "one set of menu rules"

    apply_theme(DEFAULT_THEME)
    print(f"{len(THEMES)} themes OK: " + ", ".join(t['label'] for t in THEMES.values()))
