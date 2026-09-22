# SPDX-License-Identifier: GPL-3.0-or-later
# actions_mac.py
# The macOS action catalog.
#
# Where an action means the same thing on both platforms it deliberately keeps the Windows
# id (win.lock, snap.maximize, turn.desktops), so a profile written on one platform still
# largely works on the other even though the keys underneath are different. actions.py has a
# check that any shared id agrees on kind and options.
#
# Dropped from the Windows catalog, because macOS has no counterpart:
#   PowerToys            not a Mac product
#   range.appvolume      macOS has no public per-application volume API
#   range.balance        no supported way to set master channel balance
#   win.quicklink, win.widgets, snap.layouts, cap.printscreen, and the Windows-only
#   settings pages and system tools
#
# NOT YET RUN ON A MAC. The shortcuts are macOS defaults as documented by Apple, but no
# entry here has been pressed on real hardware — see docs/MACOS.md.

from action_spec import _a, RANGE_OPTIONS, SCROLL_TURN_OPTIONS, TURN_OPTIONS

# System Settings panes. Ventura renamed the app, but these URLs still resolve.
_PREF = "x-apple.systempreferences:com.apple."


def _app(name):
    """Opens a bundled application by name."""
    return f'open -a "{name}"'


PRESS_ACTIONS = [
    # --- System & apps ---
    _a("win.search", "press", "System & apps", "Spotlight search", "Cmd+Space", "keys", ["cmd", "space"]),
    _a("mac.spotlightfinder", "press", "System & apps", "Search in Finder", "Cmd+Option+Space", "keys",
       ["cmd", "alt", "space"]),
    _a("win.settings", "press", "System & apps", "System Settings", "Opens System Settings", "run",
       _app("System Settings")),
    _a("win.explorer", "press", "System & apps", "Finder", "Opens a Finder window", "run", _app("Finder")),
    _a("win.taskmanager", "press", "System & apps", "Activity Monitor", "Opens Activity Monitor", "run",
       _app("Activity Monitor")),
    _a("win.lock", "press", "System & apps", "Lock the screen", "Locks the Mac", "native", "lock"),
    _a("win.taskview", "press", "System & apps", "Mission Control", "Ctrl+Up", "keys", ["ctrl", "up"]),
    _a("mac.appexpose", "press", "System & apps", "App Exposé", "Ctrl+Down", "keys", ["ctrl", "down"]),
    _a("mac.launchpad", "press", "System & apps", "Launchpad", "Opens Launchpad", "run", _app("Launchpad")),
    _a("win.switch", "press", "System & apps", "Switch app", "Cmd+Tab", "keys", ["cmd", "tab"]),
    _a("mac.switchwindow", "press", "System & apps", "Next window of this app", "Cmd+`", "keys", ["cmd", "`"]),
    _a("win.close", "press", "System & apps", "Close the window", "Cmd+W", "keys", ["cmd", "w"]),
    _a("mac.quit", "press", "System & apps", "Quit the app", "Cmd+Q", "keys", ["cmd", "q"]),
    _a("mac.hide", "press", "System & apps", "Hide the app", "Cmd+H", "keys", ["cmd", "h"]),
    _a("win.minimizeothers", "press", "System & apps", "Hide all other apps", "Cmd+Option+H", "keys",
       ["cmd", "alt", "h"]),
    _a("snap.minimize", "press", "System & apps", "Minimise the window", "Cmd+M", "keys", ["cmd", "m"]),
    _a("win.minimizeall", "press", "System & apps", "Minimise every window of this app", "Cmd+Option+M", "keys",
       ["cmd", "alt", "m"]),
    _a("mac.forcequit", "press", "System & apps", "Force Quit dialog", "Cmd+Option+Esc", "keys",
       ["cmd", "alt", "esc"]),
    _a("mac.newwindow", "press", "System & apps", "New window", "Cmd+N", "keys", ["cmd", "n"]),
    _a("win.desktop", "press", "System & apps", "Show the desktop", "Fn+F11", "keys", ["fn", "f11"]),
    _a("mac.emoji", "press", "System & apps", "Emoji and symbols", "Cmd+Ctrl+Space", "keys",
       ["cmd", "ctrl", "space"]),

    # --- Spaces & windows ---
    _a("snap.maximize", "press", "Spaces & windows", "Full screen on or off", "Ctrl+Cmd+F", "keys",
       ["ctrl", "cmd", "f"]),
    _a("desk.left", "press", "Spaces & windows", "Previous space", "Ctrl+Left", "keys", ["ctrl", "left"]),
    _a("desk.right", "press", "Spaces & windows", "Next space", "Ctrl+Right", "keys", ["ctrl", "right"]),
    _a("mac.tileleft", "press", "Spaces & windows", "Tile window left", "Fn+Ctrl+Left (macOS 15+)", "keys",
       ["fn", "ctrl", "left"]),
    _a("mac.tileright", "press", "Spaces & windows", "Tile window right", "Fn+Ctrl+Right (macOS 15+)", "keys",
       ["fn", "ctrl", "right"]),
    _a("mac.tilefill", "press", "Spaces & windows", "Fill the screen", "Fn+Ctrl+F (macOS 15+)", "keys",
       ["fn", "ctrl", "f"]),
    _a("mac.zoomwindow", "press", "Spaces & windows", "Zoom the window", "Ctrl+Cmd+= ", "keys",
       ["ctrl", "cmd", "="]),

    # --- Capture ---
    _a("cap.screen", "press", "Capture", "Screenshot to a file", "Cmd+Shift+3", "keys", ["cmd", "shift", "3"]),
    _a("cap.region", "press", "Capture", "Snip a region", "Cmd+Shift+4", "keys", ["cmd", "shift", "4"]),
    _a("cap.toolbar", "press", "Capture", "Screenshot toolbar", "Cmd+Shift+5", "keys", ["cmd", "shift", "5"]),
    _a("cap.screenclip", "press", "Capture", "Screenshot to the clipboard", "Cmd+Ctrl+Shift+3", "keys",
       ["cmd", "ctrl", "shift", "3"]),
    _a("cap.regionclip", "press", "Capture", "Snip a region to the clipboard", "Cmd+Ctrl+Shift+4", "keys",
       ["cmd", "ctrl", "shift", "4"]),
    _a("cap.record", "press", "Capture", "Record the screen", "Opens the screenshot toolbar", "keys",
       ["cmd", "shift", "5"]),

    # --- Clipboard & text ---
    _a("txt.copy", "press", "Clipboard & text", "Copy", "Cmd+C", "keys", ["cmd", "c"]),
    _a("txt.cut", "press", "Clipboard & text", "Cut", "Cmd+X", "keys", ["cmd", "x"]),
    _a("txt.paste", "press", "Clipboard & text", "Paste", "Cmd+V", "keys", ["cmd", "v"]),
    _a("txt.pasteplain", "press", "Clipboard & text", "Paste and match style", "Cmd+Option+Shift+V", "keys",
       ["cmd", "alt", "shift", "v"]),
    _a("txt.selectall", "press", "Clipboard & text", "Select all", "Cmd+A", "keys", ["cmd", "a"]),
    _a("txt.undo", "press", "Clipboard & text", "Undo", "Cmd+Z", "keys", ["cmd", "z"]),
    _a("txt.redo", "press", "Clipboard & text", "Redo", "Cmd+Shift+Z", "keys", ["cmd", "shift", "z"]),
    _a("txt.find", "press", "Clipboard & text", "Find", "Cmd+F", "keys", ["cmd", "f"]),
    _a("txt.findnext", "press", "Clipboard & text", "Find next", "Cmd+G", "keys", ["cmd", "g"]),
    _a("txt.save", "press", "Clipboard & text", "Save", "Cmd+S", "keys", ["cmd", "s"]),
    _a("txt.saveas", "press", "Clipboard & text", "Save as", "Cmd+Shift+S", "keys", ["cmd", "shift", "s"]),
    _a("txt.open", "press", "Clipboard & text", "Open", "Cmd+O", "keys", ["cmd", "o"]),
    _a("txt.print", "press", "Clipboard & text", "Print", "Cmd+P", "keys", ["cmd", "p"]),
    _a("txt.bold", "press", "Clipboard & text", "Bold", "Cmd+B", "keys", ["cmd", "b"]),
    _a("txt.italic", "press", "Clipboard & text", "Italic", "Cmd+I", "keys", ["cmd", "i"]),
    _a("txt.underline", "press", "Clipboard & text", "Underline", "Cmd+U", "keys", ["cmd", "u"]),
    _a("txt.newtab", "press", "Clipboard & text", "New tab", "Cmd+T", "keys", ["cmd", "t"]),
    _a("txt.closetab", "press", "Clipboard & text", "Close tab", "Cmd+W", "keys", ["cmd", "w"]),
    _a("txt.reopentab", "press", "Clipboard & text", "Reopen the last tab", "Cmd+Shift+T", "keys",
       ["cmd", "shift", "t"]),

    # --- Media & audio ---
    _a("media.playpause", "press", "Media & audio", "Play or pause", "Media key", "native", "media_play_pause"),
    _a("media.next", "press", "Media & audio", "Next track", "Media key", "native", "media_next"),
    _a("media.prev", "press", "Media & audio", "Previous track", "Media key", "native", "media_prev"),
    _a("media.mute", "press", "Media & audio", "Mute or unmute", "Mute key", "native", "media_mute"),
    _a("media.volup", "press", "Media & audio", "Volume up", "Volume key", "native", "volume_up"),
    _a("media.voldown", "press", "Media & audio", "Volume down", "Volume key", "native", "volume_down"),
    _a("audio.nextdevice", "press", "Media & audio", "Next sound device", "Steps through outputs", "native",
       "next_output"),
    _a("audio.toggledevice", "press", "Media & audio", "Swap the last two sound devices", "Back and forth",
       "native", "toggle_output"),
    _a("audio.setdevice", "press", "Media & audio", "Use a particular sound device", "You choose the device",
       "custom", "device"),
    _a("mac.sounddevices", "press", "Media & audio", "Sound settings", "Opens the Sound pane", "uri",
       _PREF + "preference.sound"),

    # --- Settings panes ---
    _a("set.display", "press", "Settings panes", "Displays", "System Settings", "uri", _PREF + "preference.displays"),
    _a("set.network", "press", "Settings panes", "Network", "System Settings", "uri", _PREF + "preference.network"),
    _a("set.bluetooth", "press", "Settings panes", "Bluetooth", "System Settings", "uri",
       _PREF + "preference.bluetooth"),
    _a("set.keyboard", "press", "Settings panes", "Keyboard", "System Settings", "uri",
       _PREF + "preference.keyboard"),
    _a("mac.trackpad", "press", "Settings panes", "Trackpad", "System Settings", "uri",
       _PREF + "preference.trackpad"),
    _a("set.notifications", "press", "Settings panes", "Notifications", "System Settings", "uri",
       _PREF + "preference.notifications"),
    _a("set.privacy", "press", "Settings panes", "Privacy & Security", "System Settings", "uri",
       _PREF + "preference.security"),
    _a("set.power", "press", "Settings panes", "Battery", "System Settings", "uri", _PREF + "preference.battery"),
    _a("set.update", "press", "Settings panes", "Software Update", "System Settings", "uri",
       _PREF + "preferences.softwareupdate"),
    _a("set.printers", "press", "Settings panes", "Printers & Scanners", "System Settings", "uri",
       _PREF + "preference.printfax"),
    _a("set.datetime", "press", "Settings panes", "Date & Time", "System Settings", "uri",
       _PREF + "preference.datetime"),
    _a("set.users", "press", "Settings panes", "Users & Groups", "System Settings", "uri",
       _PREF + "preferences.users"),
    _a("set.desktop", "press", "Settings panes", "Wallpaper", "System Settings", "uri",
       _PREF + "preference.desktopscreeneffect"),
    _a("acc.settings", "press", "Settings panes", "Accessibility", "System Settings", "uri",
       _PREF + "preference.universalaccess"),

    # --- Folders ---
    _a("fold.home", "press", "Folders", "Home", "Opens your home folder", "run", "open ~"),
    _a("fold.downloads", "press", "Folders", "Downloads", "Opens Downloads", "run", "open ~/Downloads"),
    _a("fold.documents", "press", "Folders", "Documents", "Opens Documents", "run", "open ~/Documents"),
    _a("fold.desktop", "press", "Folders", "Desktop", "Opens Desktop", "run", "open ~/Desktop"),
    _a("fold.pictures", "press", "Folders", "Pictures", "Opens Pictures", "run", "open ~/Pictures"),
    _a("fold.music", "press", "Folders", "Music", "Opens Music", "run", "open ~/Music"),
    _a("fold.videos", "press", "Folders", "Movies", "Opens Movies", "run", "open ~/Movies"),
    _a("fold.apps", "press", "Folders", "Applications", "Opens Applications", "run", "open /Applications"),
    _a("mac.utilities", "press", "Folders", "Utilities", "Opens Utilities", "run",
       "open /Applications/Utilities"),
    _a("mac.icloud", "press", "Folders", "iCloud Drive", "Opens iCloud Drive", "run",
       'open ~/Library/Mobile\\ Documents/com~apple~CloudDocs'),
    _a("fold.recycle", "press", "Folders", "Trash", "Opens the Trash", "run", "open ~/.Trash"),

    # --- System tools ---
    _a("sys.terminal", "press", "System tools", "Terminal", "Opens Terminal", "run", _app("Terminal")),
    _a("sys.calc", "press", "System tools", "Calculator", "Opens Calculator", "run", _app("Calculator")),
    _a("mac.diskutility", "press", "System tools", "Disk Utility", "Opens Disk Utility", "run",
       _app("Disk Utility")),
    _a("mac.console", "press", "System tools", "Console", "Opens Console", "run", _app("Console")),
    _a("mac.systeminfo", "press", "System tools", "System Information", "Opens System Information", "run",
       _app("System Information")),
    _a("mac.keychain", "press", "System tools", "Keychain Access", "Opens Keychain Access", "run",
       _app("Keychain Access")),
    _a("mac.preview", "press", "System tools", "Preview", "Opens Preview", "run", _app("Preview")),
    _a("mac.fontbook", "press", "System tools", "Font Book", "Opens Font Book", "run", _app("Font Book")),
    _a("mac.timemachine", "press", "System tools", "Time Machine", "Opens Time Machine", "run",
       _app("Time Machine")),
    _a("mac.textedit", "press", "System tools", "TextEdit", "Opens TextEdit", "run", _app("TextEdit")),
    _a("mac.notes", "press", "System tools", "Notes", "Opens Notes", "run", _app("Notes")),
    _a("mac.emptytrash", "press", "System tools", "Empty the Trash", "Cmd+Shift+Delete", "keys",
       ["cmd", "shift", "delete"]),

    # --- Power ---
    _a("pow.sleep", "press", "Power", "Sleep", "Puts the Mac to sleep", "native", "sleep"),
    _a("mac.displaysleep", "press", "Power", "Turn the display off", "pmset displaysleepnow", "run",
       "pmset displaysleepnow"),
    _a("mac.screensaver", "press", "Power", "Start the screen saver", "Opens the screen saver", "run",
       "open -a ScreenSaverEngine"),
    _a("pow.signout", "press", "Power", "Log out", "Cmd+Shift+Q", "keys", ["cmd", "shift", "q"]),
    _a("pow.restart", "press", "Power", "Restart", "Asks System Events to restart", "run",
       "osascript -e 'tell application \"System Events\" to restart'"),
    _a("pow.shutdown", "press", "Power", "Shut down", "Asks System Events to shut down", "run",
       "osascript -e 'tell application \"System Events\" to shut down'"),

    # --- Meetings (each app's own default) ---
    _a("meet.teamsmute", "press", "Meetings", "Teams mute", "Cmd+Shift+M", "keys", ["cmd", "shift", "m"]),
    _a("meet.teamsvideo", "press", "Meetings", "Teams camera", "Cmd+Shift+O", "keys", ["cmd", "shift", "o"]),
    _a("meet.zoommute", "press", "Meetings", "Zoom mute", "Cmd+Shift+A", "keys", ["cmd", "shift", "a"]),
    _a("meet.zoomvideo", "press", "Meetings", "Zoom camera", "Cmd+Shift+V", "keys", ["cmd", "shift", "v"]),
    _a("meet.zoomshare", "press", "Meetings", "Zoom share screen", "Cmd+Shift+S", "keys", ["cmd", "shift", "s"]),

    # --- Accessibility ---
    _a("acc.magnifyin", "press", "Accessibility", "Zoom in", "Option+Cmd+=", "keys", ["alt", "cmd", "="]),
    _a("acc.magnifyout", "press", "Accessibility", "Zoom out", "Option+Cmd+-", "keys", ["alt", "cmd", "-"]),
    _a("acc.narrator", "press", "Accessibility", "VoiceOver on or off", "Cmd+F5", "keys", ["cmd", "f5"]),
    _a("acc.colorfilters", "press", "Accessibility", "Invert colours", "Ctrl+Option+Cmd+8", "keys",
       ["ctrl", "alt", "cmd", "8"]),
    _a("mac.accshortcuts", "press", "Accessibility", "Accessibility shortcuts", "Option+Cmd+F5", "keys",
       ["alt", "cmd", "f5"]),

    # --- Your own ---
    _a("custom.app", "press", "Your own", "Open an app", "You choose the app", "custom", "launch_app"),
    _a("custom.keys", "press", "Your own", "Press a keyboard shortcut", "You record the keys", "custom", "keystroke"),
    _a("custom.command", "press", "Your own", "Run a command", "You type the command", "custom", "script"),
]

TURN_ACTIONS = [
    _a("turn.scroll", "turn", "Scrolling", "Scroll up and down", "Scroll wheel", "native", "scroll_v",
       SCROLL_TURN_OPTIONS),
    _a("turn.scrollh", "turn", "Scrolling", "Scroll sideways", "Sideways scroll", "native", "scroll_h",
       SCROLL_TURN_OPTIONS),
    _a("turn.zoom", "turn", "Scrolling", "Zoom in and out", "Cmd + scroll", "native", "zoom_wheel", TURN_OPTIONS),
    _a("turn.zoomkeys", "turn", "Scrolling", "Zoom with Cmd and +/-", "Cmd+Plus / Cmd+Minus", "keypair",
       {"cw": ["cmd", "="], "ccw": ["cmd", "-"]}, TURN_OPTIONS),
    _a("turn.volume", "turn", "Media", "Nudge the volume", "Volume keys", "keypair",
       {"cw": ["volume_up"], "ccw": ["volume_down"]}, TURN_OPTIONS),
    _a("turn.track", "turn", "Media", "Skip tracks", "Next / previous track", "keypair",
       {"cw": ["media_next"], "ccw": ["media_prev"]}, TURN_OPTIONS),
    _a("turn.seek", "turn", "Media", "Seek in the track", "Right / left arrow", "keypair",
       {"cw": ["right"], "ccw": ["left"]}, TURN_OPTIONS),
    _a("turn.frame", "turn", "Media", "Step frame by frame", "Comma / full stop", "keypair",
       {"cw": ["."], "ccw": [","]}, TURN_OPTIONS),
    _a("turn.undo", "turn", "Editing", "Undo and redo", "Cmd+Z / Cmd+Shift+Z", "keypair",
       {"cw": ["cmd", "shift", "z"], "ccw": ["cmd", "z"]}, TURN_OPTIONS),
    _a("turn.brush", "turn", "Editing", "Brush size", "[ and ]", "keypair",
       {"cw": ["]"], "ccw": ["["]}, TURN_OPTIONS),
    _a("turn.arrows", "turn", "Editing", "Move up and down", "Up / down arrow", "keypair",
       {"cw": ["down"], "ccw": ["up"]}, TURN_OPTIONS),
    _a("turn.pages", "turn", "Editing", "Page up and down", "Page up / page down", "keypair",
       {"cw": ["page_down"], "ccw": ["page_up"]}, TURN_OPTIONS),
    _a("turn.tabs", "turn", "Windows", "Switch tabs", "Ctrl+Tab", "keypair",
       {"cw": ["ctrl", "tab"], "ccw": ["ctrl", "shift", "tab"]}, TURN_OPTIONS),
    _a("turn.desktops", "turn", "Windows", "Switch spaces", "Ctrl+Left / Ctrl+Right", "keypair",
       {"cw": ["ctrl", "right"], "ccw": ["ctrl", "left"]}, TURN_OPTIONS),
    _a("turn.history", "turn", "Windows", "Back and forward", "Cmd+[ / Cmd+]", "keypair",
       {"cw": ["cmd", "]"], "ccw": ["cmd", "["]}, TURN_OPTIONS),
    _a("turn.audiodevice", "turn", "Media", "Step through sound devices", "Playback device",
       "native", "audio_device", TURN_OPTIONS),
    _a("turn.custom", "turn", "Your own", "Two shortcuts, one each way", "You record both", "custom", "turn_keys",
       TURN_OPTIONS),
]

RANGE_ACTIONS = [
    _a("range.volume", "range", "Audio", "System volume", "macOS output volume", "native", "sys_volume",
       RANGE_OPTIONS),
    _a("range.scroll", "range", "Scrolling", "Scroll by how far you move it", "Scroll wheel", "native",
       "scroll_move", ("invert", "sensitivity")),
]
