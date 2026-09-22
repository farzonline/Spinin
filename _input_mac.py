# SPDX-License-Identifier: GPL-3.0-or-later
# _input_mac.py
# Sends keystrokes and scroll events on macOS through Quartz Event Services.
#
# The macOS counterpart of _input_win.py: same names, same signatures, so userinput.py can
# hand either one to the rest of the app without anything else knowing which it got.
#
# Two things work differently here from Windows, and both shape the code below:
#
#   1. Modifiers are flags on an event, not events of their own. Sending Cmd+C means one
#      "c" event carrying the Command flag, not a Cmd-down / c / Cmd-up sequence. key_down()
#      and key_up() still exist for held modifiers (Ctrl held across a scroll), so held
#      modifier state is tracked here and folded into whatever is sent next.
#
#   2. Play/pause, next and previous are not ordinary keys. They are NSSystemDefined events
#      with their own numbering, so they take a separate path from everything else. Volume
#      up/down/mute do have real key codes and go the normal way.
#
# NOT YET RUN ON A MAC. Written against the Quartz and AppKit APIs but unverified on real
# hardware — see docs/MACOS.md for what still needs checking.

import time

try:
    import Quartz
    from AppKit import NSEvent, NSSystemDefined
    AVAILABLE = True
except ImportError:  # pyobjc missing, or being imported on a non-Mac for a self-check
    Quartz = None
    NSEvent = NSSystemDefined = None
    AVAILABLE = False

# Carbon virtual key codes (HIToolbox Events.h). These are positions on the keyboard, not
# letters: 0x00 is the key where a US layout puts "A", whatever the current layout prints.
KEYS = {
    "a": 0x00, "s": 0x01, "d": 0x02, "f": 0x03, "h": 0x04, "g": 0x05, "z": 0x06, "x": 0x07,
    "c": 0x08, "v": 0x09, "b": 0x0B, "q": 0x0C, "w": 0x0D, "e": 0x0E, "r": 0x0F, "y": 0x10,
    "t": 0x11, "1": 0x12, "2": 0x13, "3": 0x14, "4": 0x15, "6": 0x16, "5": 0x17,
    "=": 0x18, "9": 0x19, "7": 0x1A, "-": 0x1B, "8": 0x1C, "0": 0x1D, "]": 0x1E, "o": 0x1F,
    "u": 0x20, "[": 0x21, "i": 0x22, "p": 0x23, "l": 0x25, "j": 0x26, "'": 0x27, "k": 0x28,
    ";": 0x29, "\\": 0x2A, ",": 0x2B, "/": 0x2C, "n": 0x2D, "m": 0x2E, ".": 0x2F, "`": 0x32,
    "enter": 0x24, "tab": 0x30, "space": 0x31, "backspace": 0x33, "esc": 0x35,
    "caps_lock": 0x39, "delete": 0x75, "insert": 0x72, "help": 0x72,
    "home": 0x73, "page_up": 0x74, "end": 0x77, "page_down": 0x79,
    "left": 0x7B, "right": 0x7C, "down": 0x7D, "up": 0x7E,
    "volume_up": 0x48, "volume_down": 0x49, "media_mute": 0x4A,
    # Modifiers, for the rare case one is sent as a key in its own right.
    "cmd": 0x37, "shift": 0x38, "alt": 0x3A, "ctrl": 0x3B,
    "rshift": 0x3C, "ralt": 0x3D, "rctrl": 0x3E, "fn": 0x3F,
}
KEYS.update({f"f{n}": code for n, code in zip(
    range(1, 21),
    (0x7A, 0x78, 0x63, 0x76, 0x60, 0x61, 0x62, 0x64, 0x65, 0x6D,
     0x67, 0x6F, 0x69, 0x6B, 0x71, 0x6A, 0x40, 0x4F, 0x50, 0x5A))})

# "win" is what the stored mappings call the Windows key; on a Mac that role is Command.
# Both names resolve so a profile written on either platform still means something here.
ALIASES = {"win": "cmd", "super": "cmd", "meta": "cmd", "option": "alt", "opt": "alt",
           "command": "cmd", "control": "ctrl", "return": "enter", "escape": "esc",
           "pgup": "page_up", "pgdn": "page_down", "del": "delete"}

MODIFIER_FLAGS = {
    "shift": 1 << 17, "ctrl": 1 << 18, "alt": 1 << 19, "cmd": 1 << 20, "fn": 1 << 23,
}
MODIFIERS = set(MODIFIER_FLAGS)

# NSSystemDefined key numbers for the transport keys, which have no virtual key code.
MEDIA_KEYS = {"media_play_pause": 16, "media_next": 17, "media_prev": 18,
              "media_fast": 19, "media_rewind": 20}

# Keys a US layout only produces with Shift held.
NEEDS_SHIFT = {"+": "=", "_": "-", "{": "[", "}": "]", ":": ";", '"': "'", "|": "\\",
               "<": ",", ">": ".", "?": "/", "~": "`"}

_last_error = ""
_held = set()  # modifiers currently held down by key_down(), folded into later events


def last_error():
    """Why the most recent send failed, for the Activity log."""
    return _last_error


def _fail(message):
    global _last_error
    _last_error = message
    print(message)
    return False


def canonical(name):
    """The name this backend knows a key by, after following the aliases."""
    key = str(name).lower().strip()
    return ALIASES.get(key, key)


def vk_for(name):
    """Virtual key code for a key name, or None if it isn't one we can send."""
    key = canonical(name)
    if key in NEEDS_SHIFT:
        key = NEEDS_SHIFT[key]
    return KEYS.get(key)


def _flags_for(modifiers):
    flags = 0
    for modifier in modifiers:
        flags |= MODIFIER_FLAGS.get(modifier, 0)
    return flags


def _post_key(code, down, flags):
    event = Quartz.CGEventCreateKeyboardEvent(None, code, down)
    if flags:
        Quartz.CGEventSetFlags(event, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def _post_media(number, down):
    """Transport keys travel as NSSystemDefined events, not as key codes."""
    data1 = (number << 16) | ((0xA if down else 0xB) << 8)
    event = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
        NSSystemDefined, (0, 0), 0xA00, 0, 0, None, 8, data1, -1)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event.CGEvent())


def tap(keys):
    """Presses a shortcut. Modifiers become flags on the key they modify."""
    if not AVAILABLE:
        return _fail("Cannot send keystrokes: pyobjc is not installed.")
    if not keys:
        return False

    modifiers, plain = [], []
    for name in keys:
        key = canonical(name)
        if key in MODIFIERS:
            modifiers.append(key)
        else:
            plain.append(key)
            if key in NEEDS_SHIFT and "shift" not in modifiers:
                modifiers.append("shift")

    media = [k for k in plain if k in MEDIA_KEYS]
    ordinary = [k for k in plain if k not in MEDIA_KEYS]
    for key in ordinary:
        if vk_for(key) is None:
            return _fail(f"Unknown key: {key!r}")

    flags = _flags_for(set(modifiers) | _held)
    try:
        for key in media:
            _post_media(MEDIA_KEYS[key], True)
            _post_media(MEDIA_KEYS[key], False)
        if ordinary:
            # Modifiers first as real key events too: some apps watch for the physical press
            # rather than reading the flags off the event they are handed.
            for modifier in modifiers:
                _post_key(KEYS[modifier], True, flags)
            for key in ordinary:
                _post_key(vk_for(key), True, flags)
                _post_key(vk_for(key), False, flags)
            for modifier in reversed(modifiers):
                _post_key(KEYS[modifier], False, _flags_for(_held))
        elif not media:
            return False
    except Exception as e:
        return _fail(f"macOS rejected the keystroke ({e}). Grant Spinin Accessibility "
                     "permission in System Settings > Privacy & Security.")
    global _last_error
    _last_error = ""
    return True


def key_down(name):
    """Holds a key. Used for the modifier held across a scroll, so it is remembered."""
    if not AVAILABLE:
        return _fail("Cannot send keystrokes: pyobjc is not installed.")
    key = canonical(name)
    code = vk_for(key)
    if code is None:
        return False
    if key in MODIFIERS:
        _held.add(key)
    _post_key(code, True, _flags_for(_held))
    return True


def key_up(name):
    if not AVAILABLE:
        return False
    key = canonical(name)
    code = vk_for(key)
    if code is None:
        return False
    _held.discard(key)
    _post_key(code, False, _flags_for(_held))
    return True


def scroll(dx=0, dy=0):
    """Scroll wheel: dy positive scrolls up, dx positive scrolls right, as on Windows."""
    if not AVAILABLE:
        return _fail("Cannot scroll: pyobjc is not installed.")
    try:
        event = Quartz.CGEventCreateScrollWheelEvent(
            None, Quartz.kCGScrollEventUnitLine, 2, int(dy), int(dx))
        if _held:
            Quartz.CGEventSetFlags(event, _flags_for(_held))
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        return True
    except Exception as e:
        return _fail(f"macOS rejected the scroll ({e}).")


class HotkeyCapture:
    """Records one shortcut, using a Quartz event tap to see keys before other apps do.

    The counterpart of the Windows low-level keyboard hook. Needs Accessibility permission;
    without it CGEventTapCreate returns None and capture silently does nothing, so
    `permission_needed` says which it was so the UI can explain rather than look broken.
    """

    def __init__(self, on_change):
        self.on_change = on_change
        self.permission_needed = False
        self._held = []
        self._tap = None
        self._source = None

    def start(self):
        if self._tap or not AVAILABLE:
            self.permission_needed = not AVAILABLE
            return
        self._held = []
        mask = ((1 << Quartz.kCGEventKeyDown) | (1 << Quartz.kCGEventKeyUp)
                | (1 << Quartz.kCGEventFlagsChanged))
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault, mask, self._callback, None)
        if not self._tap:
            self.permission_needed = True  # almost always a missing Accessibility grant
            return
        self.permission_needed = False
        self._source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), self._source,
                                  Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self._tap, True)

    def stop(self):
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)
            if self._source:
                Quartz.CFRunLoopRemoveSource(Quartz.CFRunLoopGetCurrent(), self._source,
                                             Quartz.kCFRunLoopCommonModes)
            self._tap = self._source = None
        self._held = []

    def _callback(self, proxy, event_type, event, refcon):
        # A tap callback must never let a Python exception escape into the C trampoline.
        try:
            self._handle(event_type, event)
        except Exception as e:
            print(f"Hotkey capture error: {e}")
        return None  # swallow it: nothing should act while we are recording

    def _handle(self, event_type, event):
        if event_type == Quartz.kCGEventFlagsChanged:
            flags = Quartz.CGEventGetFlags(event)
            now = [m for m, bit in MODIFIER_FLAGS.items() if flags & bit and m != "fn"]
            if now != self._held:
                self._held = now
                self.on_change(list(self._held))
            return
        if event_type != Quartz.kCGEventKeyDown:
            return
        code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        name = _CODE_TO_NAME.get(code)
        if name:
            self.on_change(self._held + [name])


_CODE_TO_NAME = {code: name for name, code in KEYS.items() if name not in MODIFIERS}


def _pump_briefly(seconds):
    """Runs the macOS run loop for a moment, so a tap callback can fire outside Qt."""
    if AVAILABLE:
        Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, seconds, False)
    else:
        time.sleep(seconds)


if __name__ == "__main__":
    # Resolves keys without sending anything, and runs on any platform so the table can be
    # checked from CI on Windows or Linux as well as on a Mac.
    assert vk_for("w") == 0x0D and vk_for("W") == 0x0D, "letters are case-insensitive"
    assert vk_for("cmd") == 0x37 and vk_for("win") == 0x37, "win maps to Command here"
    assert vk_for("f12") == 0x6F and vk_for("7") == 0x1A
    assert vk_for("[") == 0x21 and vk_for("volume_up") == 0x48
    assert vk_for("+") == KEYS["="], "shifted punctuation resolves to its unshifted key"
    assert vk_for("nonsense") is None
    assert canonical("Option") == "alt" and canonical("Return") == "enter"

    # Every key the macOS catalog asks for must resolve here, or be a media key. Checked
    # against actions_mac directly rather than actions, so this holds when run from Windows CI.
    import actions_mac
    missing = set()
    for action in actions_mac.PRESS_ACTIONS + actions_mac.TURN_ACTIONS + actions_mac.RANGE_ACTIONS:
        names = []
        if action["backend"] == "keys":
            names = list(action["payload"])
        elif action["backend"] == "keypair":
            names = list(action["payload"]["cw"]) + list(action["payload"]["ccw"])
        for name in names:
            key = canonical(name)
            if key not in MEDIA_KEYS and vk_for(key) is None:
                missing.add(name)
    assert not missing, f"no macOS key code for: {sorted(missing)}"

    assert _flags_for(["cmd", "shift"]) == (1 << 20) | (1 << 17)
    print(f"_input_mac key table OK ({len(KEYS)} keys, pyobjc "
          f"{'available' if AVAILABLE else 'not installed — send paths untested'})")
