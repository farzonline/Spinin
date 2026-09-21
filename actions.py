# SPDX-License-Identifier: GPL-3.0-or-later
# actions.py
# The action library: everything a control can be set to do, in one table.
#
# kind      "press"  buttons and pads
#           "range"  faders and knobs (absolute 0-127 position)
#           "turn"   jog wheels and the browse encoder (relative ticks)
# backend   "keys"   tap a keyboard shortcut          payload: list of key names
#           "uri"    open a Windows URI               payload: "ms-settings:…" / "shell:…"
#           "run"    run a command line               payload: command
#           "native" handled in action_handler.py     payload: handler name
#           "custom" the user fills in the details    payload: legacy mapping type
# options   per-mapping settings the app offers for this action ("invert", "sensitivity")
#
# Shortcuts come from windows11_keyboard_shortcuts.md; URIs and commands from
# windows11_no_shortcut_actions.md. PowerToys shortcuts are that app's defaults and
# can be changed in PowerToys itself.

TURN_OPTIONS = ("sensitivity", "acceleration", "invert")
# Only the wheel-driven scrolling actions can glide on after you let go; a jog wheel that
# kept skipping tracks or stepping frames on its own would be a nuisance, not a feature.
SCROLL_TURN_OPTIONS = TURN_OPTIONS + ("smooth",)
RANGE_OPTIONS = ("invert",)


def _a(id, kind, category, name, hint, backend, payload, options=()):
    return {"id": id, "kind": kind, "category": category, "name": name, "hint": hint,
            "backend": backend, "payload": payload, "options": tuple(options)}


PRESS_ACTIONS = [
    # --- Windows & apps ---
    _a("win.start", "press", "Windows & apps", "Open Start", "Win", "keys", ["win"]),
    _a("win.search", "press", "Windows & apps", "Search", "Win+S", "keys", ["win", "s"]),
    _a("win.run", "press", "Windows & apps", "Run dialog", "Win+R", "keys", ["win", "r"]),
    _a("win.settings", "press", "Windows & apps", "Settings", "Win+I", "keys", ["win", "i"]),
    _a("win.explorer", "press", "Windows & apps", "File Explorer", "Win+E", "keys", ["win", "e"]),
    _a("win.quicklink", "press", "Windows & apps", "Quick Link menu", "Win+X", "keys", ["win", "x"]),
    _a("win.taskmanager", "press", "Windows & apps", "Task Manager", "Ctrl+Shift+Esc", "keys", ["ctrl", "shift", "esc"]),
    _a("win.lock", "press", "Windows & apps", "Lock the PC", "Win+L", "native", "lock"),
    _a("win.taskview", "press", "Windows & apps", "Task View", "Win+Tab", "keys", ["win", "tab"]),
    _a("win.switch", "press", "Windows & apps", "Switch window", "Alt+Tab", "keys", ["alt", "tab"]),
    _a("win.close", "press", "Windows & apps", "Close the window", "Alt+F4", "keys", ["alt", "f4"]),
    _a("win.windowmenu", "press", "Windows & apps", "Window menu", "Alt+Space", "keys", ["alt", "space"]),
    _a("win.desktop", "press", "Windows & apps", "Show the desktop", "Win+D", "keys", ["win", "d"]),
    _a("win.peek", "press", "Windows & apps", "Peek at the desktop", "Win+,", "keys", ["win", ","]),
    _a("win.quicksettings", "press", "Windows & apps", "Quick Settings", "Win+A", "keys", ["win", "a"]),
    _a("win.notifications", "press", "Windows & apps", "Notifications", "Win+N", "keys", ["win", "n"]),
    _a("win.widgets", "press", "Windows & apps", "Widgets", "Win+W", "keys", ["win", "w"]),
    _a("win.cast", "press", "Windows & apps", "Cast to a device", "Win+K", "keys", ["win", "k"]),
    _a("win.minimizeall", "press", "Windows & apps", "Minimise every window", "Win+M", "keys", ["win", "m"]),
    _a("win.restoreall", "press", "Windows & apps", "Restore minimised windows", "Win+Shift+M", "keys",
       ["win", "shift", "m"]),
    _a("win.minimizeothers", "press", "Windows & apps", "Minimise all but this window", "Win+Home", "keys",
       ["win", "home"]),

    # --- Snap & desktops ---
    _a("snap.left", "press", "Snap & desktops", "Snap window left", "Win+Left", "keys", ["win", "left"]),
    _a("snap.right", "press", "Snap & desktops", "Snap window right", "Win+Right", "keys", ["win", "right"]),
    _a("snap.maximize", "press", "Snap & desktops", "Maximise window", "Win+Up", "keys", ["win", "up"]),
    _a("snap.minimize", "press", "Snap & desktops", "Minimise or restore window", "Win+Down", "keys", ["win", "down"]),
    _a("snap.layouts", "press", "Snap & desktops", "Snap Layouts", "Win+Z", "keys", ["win", "z"]),
    _a("snap.monitorleft", "press", "Snap & desktops", "Move window to the left monitor", "Win+Shift+Left", "keys",
       ["win", "shift", "left"]),
    _a("snap.monitorright", "press", "Snap & desktops", "Move window to the right monitor", "Win+Shift+Right", "keys",
       ["win", "shift", "right"]),
    _a("snap.project", "press", "Snap & desktops", "Projection mode", "Win+P", "keys", ["win", "p"]),
    _a("desk.new", "press", "Snap & desktops", "New virtual desktop", "Win+Ctrl+D", "keys", ["win", "ctrl", "d"]),
    _a("desk.left", "press", "Snap & desktops", "Previous desktop", "Win+Ctrl+Left", "keys", ["win", "ctrl", "left"]),
    _a("desk.right", "press", "Snap & desktops", "Next desktop", "Win+Ctrl+Right", "keys", ["win", "ctrl", "right"]),
    _a("desk.close", "press", "Snap & desktops", "Close this desktop", "Win+Ctrl+F4", "keys", ["win", "ctrl", "f4"]),

    # --- Capture ---
    _a("cap.region", "press", "Capture", "Snip a region", "Win+Shift+S", "keys", ["win", "shift", "s"]),
    _a("cap.fullscreen", "press", "Capture", "Screenshot to file", "Win+PrtScn", "keys", ["win", "print_screen"]),
    _a("cap.window", "press", "Capture", "Copy this window", "Alt+PrtScn", "keys", ["alt", "print_screen"]),
    _a("cap.record", "press", "Capture", "Record a region", "Win+Shift+R", "keys", ["win", "shift", "r"]),
    _a("cap.gamebar", "press", "Capture", "Game Bar", "Win+G", "keys", ["win", "g"]),
    _a("cap.gamerecord", "press", "Capture", "Start or stop recording", "Win+Alt+R", "keys", ["win", "alt", "r"]),

    # --- Clipboard & text ---
    _a("clip.history", "press", "Clipboard & text", "Clipboard history", "Win+V", "keys", ["win", "v"]),
    _a("clip.emoji", "press", "Clipboard & text", "Emoji panel", "Win+.", "keys", ["win", "."]),
    _a("clip.dictate", "press", "Clipboard & text", "Voice typing", "Win+H", "keys", ["win", "h"]),
    _a("clip.language", "press", "Clipboard & text", "Switch keyboard language", "Win+Space", "keys", ["win", "space"]),
    _a("edit.copy", "press", "Clipboard & text", "Copy", "Ctrl+C", "keys", ["ctrl", "c"]),
    _a("edit.cut", "press", "Clipboard & text", "Cut", "Ctrl+X", "keys", ["ctrl", "x"]),
    _a("edit.paste", "press", "Clipboard & text", "Paste", "Ctrl+V", "keys", ["ctrl", "v"]),
    _a("edit.undo", "press", "Clipboard & text", "Undo", "Ctrl+Z", "keys", ["ctrl", "z"]),
    _a("edit.redo", "press", "Clipboard & text", "Redo", "Ctrl+Y", "keys", ["ctrl", "y"]),
    _a("edit.selectall", "press", "Clipboard & text", "Select all", "Ctrl+A", "keys", ["ctrl", "a"]),
    _a("edit.find", "press", "Clipboard & text", "Find", "Ctrl+F", "keys", ["ctrl", "f"]),
    _a("edit.replace", "press", "Clipboard & text", "Replace", "Ctrl+H", "keys", ["ctrl", "h"]),
    _a("edit.save", "press", "Clipboard & text", "Save", "Ctrl+S", "keys", ["ctrl", "s"]),
    _a("edit.print", "press", "Clipboard & text", "Print", "Ctrl+P", "keys", ["ctrl", "p"]),
    _a("edit.new", "press", "Clipboard & text", "New", "Ctrl+N", "keys", ["ctrl", "n"]),
    _a("edit.open", "press", "Clipboard & text", "Open", "Ctrl+O", "keys", ["ctrl", "o"]),

    # --- Media & audio ---
    _a("media.playpause", "press", "Media & audio", "Play or pause", "Media key", "native", "media_play_pause"),
    _a("media.next", "press", "Media & audio", "Next track", "Media key", "native", "media_next"),
    _a("media.prev", "press", "Media & audio", "Previous track", "Media key", "native", "media_prev"),
    _a("media.mute", "press", "Media & audio", "Mute or unmute", "Media key", "native", "media_mute"),
    _a("media.volup", "press", "Media & audio", "Volume up", "Media key", "native", "volume_up"),
    _a("media.voldown", "press", "Media & audio", "Volume down", "Media key", "native", "volume_down"),
    _a("audio.settings", "press", "Media & audio", "Sound settings", "ms-settings:sound", "uri", "ms-settings:sound"),
    _a("audio.devices", "press", "Media & audio", "All sound devices", "ms-settings:sound-devices", "uri",
       "ms-settings:sound-devices"),
    _a("audio.mixer", "press", "Media & audio", "Volume mixer", "ms-settings:apps-volume", "uri",
       "ms-settings:apps-volume"),
    _a("audio.classic", "press", "Media & audio", "Classic sound panel", "mmsys.cpl", "run", "mmsys.cpl"),
    _a("audio.nextdevice", "press", "Media & audio", "Next sound device",
       "Steps through your playback devices", "native", "next_output"),
    _a("audio.toggledevice", "press", "Media & audio", "Swap the last two sound devices",
       "Back and forth between two outputs", "native", "toggle_output"),
    _a("audio.setdevice", "press", "Media & audio", "Switch to a chosen sound device",
       "You pick the device", "custom", "device"),

    # --- Settings pages ---
    _a("set.display", "press", "Settings pages", "Display settings", "ms-settings:display", "uri", "ms-settings:display"),
    _a("set.nightlight", "press", "Settings pages", "Night light", "ms-settings:nightlight", "uri",
       "ms-settings:nightlight"),
    _a("set.graphics", "press", "Settings pages", "Graphics settings", "ms-settings:display-advancedgraphics", "uri",
       "ms-settings:display-advancedgraphics"),
    _a("set.bluetooth", "press", "Settings pages", "Bluetooth & devices", "ms-settings:bluetooth", "uri",
       "ms-settings:bluetooth"),
    _a("set.wifi", "press", "Settings pages", "Wi-Fi", "ms-settings:network-wifi", "uri", "ms-settings:network-wifi"),
    _a("set.knownnetworks", "press", "Settings pages", "Known networks", "ms-settings:network-wifisettings", "uri",
       "ms-settings:network-wifisettings"),
    _a("set.airplane", "press", "Settings pages", "Aeroplane mode", "ms-settings:network-airplanemode", "uri",
       "ms-settings:network-airplanemode"),
    _a("set.hotspot", "press", "Settings pages", "Mobile hotspot", "ms-settings:network-mobilehotspot", "uri",
       "ms-settings:network-mobilehotspot"),
    _a("set.vpn", "press", "Settings pages", "VPN", "ms-settings:network-vpn", "uri", "ms-settings:network-vpn"),
    _a("set.network", "press", "Settings pages", "Network status", "ms-settings:network-status", "uri",
       "ms-settings:network-status"),
    _a("set.powersleep", "press", "Settings pages", "Power & sleep", "ms-settings:powersleep", "uri",
       "ms-settings:powersleep"),
    _a("set.batterysaver", "press", "Settings pages", "Battery saver", "ms-settings:batterysaver", "uri",
       "ms-settings:batterysaver"),
    _a("set.notifications", "press", "Settings pages", "Notifications", "ms-settings:notifications", "uri",
       "ms-settings:notifications"),
    _a("set.focus", "press", "Settings pages", "Do not disturb", "ms-settings:quiethours", "uri",
       "ms-settings:quiethours"),
    _a("set.apps", "press", "Settings pages", "Installed apps", "ms-settings:appsfeatures", "uri",
       "ms-settings:appsfeatures"),
    _a("set.defaultapps", "press", "Settings pages", "Default apps", "ms-settings:defaultapps", "uri",
       "ms-settings:defaultapps"),
    _a("set.startupapps", "press", "Settings pages", "Startup apps", "ms-settings:startupapps", "uri",
       "ms-settings:startupapps"),
    _a("set.update", "press", "Settings pages", "Windows Update", "ms-settings:windowsupdate", "uri",
       "ms-settings:windowsupdate"),
    _a("set.updatehistory", "press", "Settings pages", "Update history", "ms-settings:windowsupdate-history", "uri",
       "ms-settings:windowsupdate-history"),
    _a("set.webcam", "press", "Settings pages", "Camera privacy", "ms-settings:privacy-webcam", "uri",
       "ms-settings:privacy-webcam"),
    _a("set.mic", "press", "Settings pages", "Microphone privacy", "ms-settings:privacy-microphone", "uri",
       "ms-settings:privacy-microphone"),
    _a("set.location", "press", "Settings pages", "Location privacy", "ms-settings:privacy-location", "uri",
       "ms-settings:privacy-location"),
    _a("set.security", "press", "Settings pages", "Windows Security", "ms-settings:windowsdefender", "uri",
       "ms-settings:windowsdefender"),
    _a("set.storage", "press", "Settings pages", "Storage", "ms-settings:storagesense", "uri", "ms-settings:storagesense"),
    _a("set.disks", "press", "Settings pages", "Disks & volumes", "ms-settings:disksandvolumes", "uri",
       "ms-settings:disksandvolumes"),
    _a("set.datetime", "press", "Settings pages", "Date & time", "ms-settings:dateandtime", "uri",
       "ms-settings:dateandtime"),
    _a("set.language", "press", "Settings pages", "Language & region", "ms-settings:regionlanguage", "uri",
       "ms-settings:regionlanguage"),
    _a("set.keyboard", "press", "Settings pages", "Keyboard settings", "ms-settings:keyboard", "uri",
       "ms-settings:keyboard"),
    _a("set.developers", "press", "Settings pages", "Developer settings", "ms-settings:developers", "uri",
       "ms-settings:developers"),
    _a("set.recovery", "press", "Settings pages", "Recovery", "ms-settings:recovery", "uri", "ms-settings:recovery"),
    _a("set.troubleshoot", "press", "Settings pages", "Troubleshooters", "ms-settings:troubleshoot", "uri",
       "ms-settings:troubleshoot"),
    _a("set.signin", "press", "Settings pages", "Sign-in options", "ms-settings:signinoptions", "uri",
       "ms-settings:signinoptions"),
    _a("set.findmydevice", "press", "Settings pages", "Find my device", "ms-settings:findmydevice", "uri",
       "ms-settings:findmydevice"),

    # --- Folders ---
    _a("fold.downloads", "press", "Folders", "Downloads", "shell:Downloads", "uri", "shell:Downloads"),
    _a("fold.desktop", "press", "Folders", "Desktop folder", "shell:Desktop", "uri", "shell:Desktop"),
    _a("fold.documents", "press", "Folders", "Documents", "shell:Documents", "uri", "shell:Documents"),
    _a("fold.pictures", "press", "Folders", "Pictures", "shell:Pictures", "uri", "shell:Pictures"),
    _a("fold.music", "press", "Folders", "Music", "shell:Music", "uri", "shell:Music"),
    _a("fold.videos", "press", "Folders", "Videos", "shell:Videos", "uri", "shell:Videos"),
    _a("fold.appdata", "press", "Folders", "AppData (Roaming)", "shell:AppData", "uri", "shell:AppData"),
    _a("fold.localappdata", "press", "Folders", "AppData (Local)", "shell:Local AppData", "uri", "shell:Local AppData"),
    _a("fold.startup", "press", "Folders", "Startup folder", "shell:Startup", "uri", "shell:Startup"),
    _a("fold.recent", "press", "Folders", "Recent items", "shell:Recent", "uri", "shell:Recent"),
    _a("fold.fonts", "press", "Folders", "Fonts", "shell:Fonts", "uri", "shell:Fonts"),
    _a("fold.recyclebin", "press", "Folders", "Recycle Bin", "shell:RecycleBinFolder", "uri", "shell:RecycleBinFolder"),
    _a("fold.connections", "press", "Folders", "Network connections", "shell:ConnectionsFolder", "uri",
       "shell:ConnectionsFolder"),
    _a("fold.programs", "press", "Folders", "Start menu programs", "shell:Programs", "uri", "shell:Programs"),

    # --- System tools ---
    _a("tool.devmgmt", "press", "System tools", "Device Manager", "devmgmt.msc", "run", "devmgmt.msc"),
    _a("tool.diskmgmt", "press", "System tools", "Disk Management", "diskmgmt.msc", "run", "diskmgmt.msc"),
    _a("tool.services", "press", "System tools", "Services", "services.msc", "run", "services.msc"),
    _a("tool.eventvwr", "press", "System tools", "Event Viewer", "eventvwr.msc", "run", "eventvwr.msc"),
    _a("tool.taskschd", "press", "System tools", "Task Scheduler", "taskschd.msc", "run", "taskschd.msc"),
    _a("tool.appwiz", "press", "System tools", "Programs & Features", "appwiz.cpl", "run", "appwiz.cpl"),
    _a("tool.ncpa", "press", "System tools", "Network Connections", "ncpa.cpl", "run", "ncpa.cpl"),
    _a("tool.sysdm", "press", "System tools", "System Properties", "sysdm.cpl", "run", "sysdm.cpl"),
    _a("tool.firewall", "press", "System tools", "Firewall", "firewall.cpl", "run", "firewall.cpl"),
    _a("tool.cmd", "press", "System tools", "Command Prompt", "cmd", "run", "cmd"),
    _a("tool.powershell", "press", "System tools", "PowerShell", "powershell", "run", "powershell"),
    _a("tool.terminal", "press", "System tools", "Windows Terminal", "wt", "run", "wt"),
    _a("tool.regedit", "press", "System tools", "Registry Editor", "regedit", "run", "regedit"),
    _a("tool.msinfo", "press", "System tools", "System Information", "msinfo32", "run", "msinfo32"),
    _a("tool.dxdiag", "press", "System tools", "DirectX Diagnostics", "dxdiag", "run", "dxdiag"),
    _a("tool.controlpanel", "press", "System tools", "Control Panel", "control", "run", "control"),

    # --- Power ---
    _a("pow.sleep", "press", "Power", "Sleep", "Suspends the PC", "native", "sleep"),
    _a("pow.hibernate", "press", "Power", "Hibernate", "shutdown /h", "run", "shutdown /h"),
    _a("pow.restart", "press", "Power", "Restart", "shutdown /r /t 0", "run", "shutdown /r /t 0"),
    _a("pow.shutdown", "press", "Power", "Shut down", "shutdown /s /t 0", "run", "shutdown /s /t 0"),
    _a("pow.signout", "press", "Power", "Sign out", "shutdown /l", "run", "shutdown /l"),

    # --- PowerToys (these are PowerToys' default shortcuts) ---
    _a("pt.run", "press", "PowerToys", "PowerToys Run", "Alt+Space", "keys", ["alt", "space"]),
    _a("pt.alwaysontop", "press", "PowerToys", "Pin window on top", "Win+Ctrl+T", "keys", ["win", "ctrl", "t"]),
    _a("pt.colorpicker", "press", "PowerToys", "Colour Picker", "Win+Shift+C", "keys", ["win", "shift", "c"]),
    _a("pt.textextractor", "press", "PowerToys", "Text Extractor", "Win+Shift+T", "keys", ["win", "shift", "t"]),
    _a("pt.ruler", "press", "PowerToys", "Screen Ruler", "Win+Shift+M", "keys", ["win", "shift", "m"]),
    _a("pt.croplock", "press", "PowerToys", "Crop & Lock", "Win+Ctrl+Shift+T", "keys", ["win", "ctrl", "shift", "t"]),
    _a("pt.peek", "press", "PowerToys", "Peek at a file", "Ctrl+Space", "keys", ["ctrl", "space"]),
    _a("pt.pasteplain", "press", "PowerToys", "Paste as plain text", "Win+Ctrl+Alt+V", "keys",
       ["win", "ctrl", "alt", "v"]),
    _a("pt.advancedpaste", "press", "PowerToys", "Advanced Paste", "Win+Shift+V", "keys", ["win", "shift", "v"]),
    _a("pt.highlighter", "press", "PowerToys", "Mouse highlighter", "Win+Shift+H", "keys", ["win", "shift", "h"]),
    _a("pt.mutemic", "press", "PowerToys", "Mute the microphone", "Win+Shift+A", "keys", ["win", "shift", "a"]),
    _a("pt.mutecam", "press", "PowerToys", "Mute the camera", "Win+Shift+O", "keys", ["win", "shift", "o"]),
    _a("pt.muteboth", "press", "PowerToys", "Mute mic and camera", "Win+Shift+Q", "keys", ["win", "shift", "q"]),

    # --- Meetings (each app's own default) ---
    _a("meet.teamsmute", "press", "Meetings", "Teams mute", "Ctrl+Shift+M", "keys", ["ctrl", "shift", "m"]),
    _a("meet.teamsvideo", "press", "Meetings", "Teams camera", "Ctrl+Shift+O", "keys", ["ctrl", "shift", "o"]),
    _a("meet.zoommute", "press", "Meetings", "Zoom mute", "Alt+A", "keys", ["alt", "a"]),
    _a("meet.zoomvideo", "press", "Meetings", "Zoom camera", "Alt+V", "keys", ["alt", "v"]),
    _a("meet.zoomshare", "press", "Meetings", "Zoom share screen", "Alt+S", "keys", ["alt", "s"]),

    # --- Accessibility ---
    _a("acc.settings", "press", "Accessibility", "Accessibility settings", "Win+U", "keys", ["win", "u"]),
    _a("acc.magnifyin", "press", "Accessibility", "Magnifier in", "Win++", "keys", ["win", "+"]),
    _a("acc.magnifyout", "press", "Accessibility", "Magnifier out", "Win+-", "keys", ["win", "-"]),
    _a("acc.magnifyexit", "press", "Accessibility", "Close Magnifier", "Win+Esc", "keys", ["win", "esc"]),
    _a("acc.narrator", "press", "Accessibility", "Narrator on or off", "Win+Ctrl+Enter", "keys",
       ["win", "ctrl", "enter"]),
    _a("acc.colorfilters", "press", "Accessibility", "Colour filters", "Win+Ctrl+C", "keys", ["win", "ctrl", "c"]),

    # --- Your own ---
    _a("custom.app", "press", "Your own", "Open an app", "You choose the app", "custom", "launch_app"),
    _a("custom.keys", "press", "Your own", "Press a keyboard shortcut", "You record the keys", "custom", "keystroke"),
    _a("custom.command", "press", "Your own", "Run a command", "You type the command", "custom", "script"),
]

TURN_ACTIONS = [
    _a("turn.scroll", "turn", "Scrolling", "Scroll up and down", "Mouse wheel", "native", "scroll_v",
       SCROLL_TURN_OPTIONS),
    _a("turn.scrollh", "turn", "Scrolling", "Scroll sideways", "Shift + wheel", "native", "scroll_h",
       SCROLL_TURN_OPTIONS),
    _a("turn.zoom", "turn", "Scrolling", "Zoom in and out", "Ctrl + wheel", "native", "zoom_wheel", TURN_OPTIONS),
    _a("turn.zoomkeys", "turn", "Scrolling", "Zoom with Ctrl and +/-", "Ctrl+Plus / Ctrl+Minus", "keypair",
       {"cw": ["ctrl", "+"], "ccw": ["ctrl", "-"]}, TURN_OPTIONS),
    _a("turn.volume", "turn", "Media", "Nudge the volume", "Volume keys", "keypair",
       {"cw": ["volume_up"], "ccw": ["volume_down"]}, TURN_OPTIONS),
    _a("turn.track", "turn", "Media", "Skip tracks", "Next / previous track", "keypair",
       {"cw": ["media_next"], "ccw": ["media_prev"]}, TURN_OPTIONS),
    _a("turn.seek", "turn", "Media", "Seek in the track", "Right / left arrow", "keypair",
       {"cw": ["right"], "ccw": ["left"]}, TURN_OPTIONS),
    _a("turn.frame", "turn", "Media", "Step frame by frame", "Comma / full stop", "keypair",
       {"cw": ["."], "ccw": [","]}, TURN_OPTIONS),
    _a("turn.undo", "turn", "Editing", "Undo and redo", "Ctrl+Z / Ctrl+Y", "keypair",
       {"cw": ["ctrl", "y"], "ccw": ["ctrl", "z"]}, TURN_OPTIONS),
    _a("turn.brush", "turn", "Editing", "Brush size", "[ and ]", "keypair",
       {"cw": ["]"], "ccw": ["["]}, TURN_OPTIONS),
    _a("turn.arrows", "turn", "Editing", "Move up and down", "Up / down arrow", "keypair",
       {"cw": ["down"], "ccw": ["up"]}, TURN_OPTIONS),
    _a("turn.pages", "turn", "Editing", "Page up and down", "PageUp / PageDown", "keypair",
       {"cw": ["page_down"], "ccw": ["page_up"]}, TURN_OPTIONS),
    _a("turn.tabs", "turn", "Windows", "Switch tabs", "Ctrl+Tab", "keypair",
       {"cw": ["ctrl", "tab"], "ccw": ["ctrl", "shift", "tab"]}, TURN_OPTIONS),
    _a("turn.desktops", "turn", "Windows", "Switch virtual desktops", "Win+Ctrl+Left / Right", "keypair",
       {"cw": ["win", "ctrl", "right"], "ccw": ["win", "ctrl", "left"]}, TURN_OPTIONS),
    _a("turn.history", "turn", "Windows", "Back and forward", "Alt+Left / Alt+Right", "keypair",
       {"cw": ["alt", "right"], "ccw": ["alt", "left"]}, TURN_OPTIONS),
    _a("turn.audiodevice", "turn", "Media", "Step through sound devices", "Playback device",
       "native", "audio_device", TURN_OPTIONS),
    _a("turn.custom", "turn", "Your own", "Two shortcuts, one each way", "You record both", "custom", "turn_keys",
       TURN_OPTIONS),
]

RANGE_ACTIONS = [
    _a("range.volume", "range", "Audio", "System volume", "Windows master volume", "native", "sys_volume",
       RANGE_OPTIONS),
    _a("range.appvolume", "range", "Audio", "Volume of the app in front", "Per-app volume mixer", "native",
       "app_volume", RANGE_OPTIONS),
    _a("range.balance", "range", "Audio", "Speaker balance left to right", "Master channel balance", "native",
       "balance", RANGE_OPTIONS),
    _a("range.scroll", "range", "Scrolling", "Scroll by how far you move it", "Mouse wheel", "native", "scroll_move",
       ("invert", "sensitivity")),
]

ACTIONS = PRESS_ACTIONS + TURN_ACTIONS + RANGE_ACTIONS
BY_ID = {a["id"]: a for a in ACTIONS}

# Which kind of action a control accepts, from its MIDI code and hotspot.
def kind_for_control(cid, midi_code, is_relative, shape_kind):
    if is_relative:
        return "turn"
    if midi_code.startswith("CC"):
        return "range"
    return "press"


def for_kind(kind):
    return [a for a in ACTIONS if a["kind"] == kind]


def categories(kind):
    seen = []
    for a in ACTIONS:
        if a["kind"] == kind and a["category"] not in seen:
            seen.append(a["category"])
    return seen


def matches(action, query):
    q = query.strip().lower()
    if not q:
        return True
    return all(word in f"{action['name']} {action['hint']} {action['category']}".lower() for word in q.split())


def decode_delta(value):
    """DDJ-FLX4 relative encodings: jogs send 65/63 (offset 64), the browse encoder 1/127."""
    if 56 <= value <= 72:          # jog wheels sit around 64
        return value - 64
    return value if value < 64 else value - 128


if __name__ == "__main__":
    assert len(BY_ID) == len(ACTIONS), "duplicate action id"
    assert decode_delta(65) == 1 and decode_delta(63) == -1, "jog"
    assert decode_delta(1) == 1 and decode_delta(127) == -1, "encoder"
    for a in ACTIONS:
        assert a["backend"] in ("keys", "uri", "run", "native", "keypair", "custom"), a
        assert a["kind"] in ("press", "turn", "range"), a
    # Gliding only makes sense where a wheel drives a scroll bar.
    smooth = {a["id"] for a in ACTIONS if "smooth" in a["options"]}
    assert smooth == {"turn.scroll", "turn.scrollh"}, smooth
    for a in ACTIONS:
        if a["id"] in smooth:
            assert a["backend"] == "native" and a["payload"].startswith("scroll_"), a
    print(f"{len(ACTIONS)} actions OK "
          f"({len(PRESS_ACTIONS)} press, {len(TURN_ACTIONS)} turn, {len(RANGE_ACTIONS)} range)")
