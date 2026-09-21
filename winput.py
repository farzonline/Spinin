# SPDX-License-Identifier: GPL-3.0-or-later
# winput.py
# Sends keystrokes and mouse wheel events through Win32 SendInput.
#
# Why not pynput: on Windows it sends printable characters as Unicode text events
# (KEYEVENTF_UNICODE) rather than key presses, and apps do not treat those as shortcuts —
# Ctrl+W did nothing in Chromium-based browsers. Real virtual-key codes work everywhere,
# and this drops the dependency.

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
INPUT_KEYBOARD, INPUT_MOUSE = 1, 0
MOUSEEVENTF_WHEEL, MOUSEEVENTF_HWHEEL = 0x0800, 0x01000
WHEEL_DELTA = 120

VK = {
    # The left-hand modifier codes are what a physical keyboard sends. The generic ones
    # (VK_CONTROL 0x11 etc.) are a state Windows derives, and some apps ignore them.
    "ctrl": 0xA2, "alt": 0xA4, "shift": 0xA0, "win": 0x5B,
    "rctrl": 0xA3, "ralt": 0xA5, "rshift": 0xA1,
    "enter": 0x0D, "space": 0x20, "tab": 0x09, "esc": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "insert": 0x2D,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23, "page_up": 0x21, "page_down": 0x22,
    "print_screen": 0x2C, "caps_lock": 0x14, "menu": 0x5D, "num_lock": 0x90,
    # Media and volume keys
    "media_play_pause": 0xB3, "media_mute": 0xAD, "media_stop": 0xB2,
    "media_next": 0xB0, "media_prev": 0xB1, "volume_up": 0xAF, "volume_down": 0xAE,
    # Punctuation, by physical key
    ",": 0xBC, ".": 0xBE, ";": 0xBA, "/": 0xBF, "'": 0xDE, "`": 0xC0,
    "[": 0xDB, "]": 0xDD, "\\": 0xDC, "-": 0xBD, "=": 0xBB, "+": 0xBB,
}
VK.update({chr(c): c for c in range(ord("A"), ord("Z") + 1)})          # "A".."Z"
VK.update({chr(c).lower(): c for c in range(ord("A"), ord("Z") + 1)})  # "a".."z"
VK.update({str(d): 0x30 + d for d in range(10)})
VK.update({f"f{i}": 0x70 + i - 1 for i in range(1, 25)})

# Keys that need the extended-key flag or Windows may read them as their numpad twins.
EXTENDED = {0x26, 0x28, 0x25, 0x27, 0x24, 0x23, 0x21, 0x22, 0x2D, 0x2E, 0x2C, 0x90,
            0xA3, 0xA5, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3, 0x5B, 0x5C}

# "+" on the main row needs Shift on a US layout ("=" key), so Win++ still zooms Magnifier.
NEEDS_SHIFT = {"+"}


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


def _key_event(vk, keyup):
    flags = KEYEVENTF_KEYUP if keyup else 0
    if vk in EXTENDED:
        flags |= KEYEVENTF_EXTENDEDKEY
    scan = user32.MapVirtualKeyW(vk, 0)
    return _INPUT(type=INPUT_KEYBOARD,
                  union=_INPUTUNION(ki=_KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags)))


last_error = ""  # why the most recent send failed, for the Activity log


def _send(events):
    global last_error
    if not events:
        return False
    array = (_INPUT * len(events))(*events)
    sent = user32.SendInput(len(events), array, ctypes.sizeof(_INPUT))
    if sent == len(events):
        last_error = ""
        return True
    code = ctypes.get_last_error() if hasattr(ctypes, "get_last_error") else 0
    if code == 5:  # ERROR_ACCESS_DENIED
        last_error = ("Windows blocked the keystroke. The app in front is running as "
                      "administrator, so Spinin has to be started as administrator too.")
    else:
        last_error = f"Windows rejected the keystroke (error {code})."
    print(last_error)
    return False


def vk_for(name):
    """Virtual-key code for a key name, or None if it isn't one we can send."""
    return VK.get(str(name).lower().strip())


def tap(keys):
    """Presses a shortcut: every key down in order, then up in reverse."""
    codes = []
    for name in keys:
        vk = vk_for(name)
        if vk is None:
            print(f"Unknown key: {name!r}")
            return False
        if str(name) in NEEDS_SHIFT and VK["shift"] not in codes:
            codes.append(VK["shift"])
        codes.append(vk)
    events = [_key_event(vk, False) for vk in codes]
    events += [_key_event(vk, True) for vk in reversed(codes)]
    return _send(events)


def key_down(name):
    vk = vk_for(name)
    return _send([_key_event(vk, False)]) if vk is not None else False


def key_up(name):
    vk = vk_for(name)
    return _send([_key_event(vk, True)]) if vk is not None else False


# --- Recording a shortcut that includes the Windows key ---
# Windows itself claims Win-key combos (Win+V for clipboard history, Win+Tab, Win+L, ...) as
# shell hotkeys and acts on them before a normal window's keyboard events ever fire, so a
# shortcut-recording box built on ordinary Qt key events can only ever see what the shell
# doesn't already want — which is why Ctrl+Win+V behaved as if only two keys were supported.
# A WH_KEYBOARD_LL hook sees every key system-wide before the shell does, and returning a
# non-zero value here stops that action for as long as the hook is installed, which the
# recorder only does while its own box has keyboard focus.
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0100, 0x0101, 0x0104, 0x0105


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)]


_HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

# ctypes defaults an unprototyped function's return value to a 32-bit c_int, which truncates
# every pointer-sized handle below on 64-bit Windows (SetWindowsHookExW would then fail with
# ERROR_MOD_NOT_FOUND from a garbled module handle). These four calls need the real widths.
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, _HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]

# Left and right variants of a modifier both count as that modifier for recording purposes;
# tap() always sends the left-hand code regardless of which one was physically held.
_MODIFIER_NAMES = {0xA0: "shift", 0xA1: "shift", 0xA2: "ctrl", 0xA3: "ctrl",
                   0xA4: "alt", 0xA5: "alt", 0x5B: "win", 0x5C: "win"}
_CODE_TO_NAME = {code: name for name, code in VK.items() if code not in _MODIFIER_NAMES}


class HotkeyCapture:
    """Captures one keyboard shortcut via a system-wide hook, so combinations the shell would
    otherwise swallow (anything with the Windows key) can still be recorded.

    Only meant to run while a single UI element has focus: start() on focus-in, stop() on
    focus-out. While active it blocks every key system-wide, matching how a "press the new
    shortcut key" box works in other apps — the reason to always stop it the moment focus
    moves away.
    """

    def __init__(self, on_change):
        self.on_change = on_change  # called with the combo so far (list[str]) as it changes
        self._held = []
        self._hook_id = None
        self._proc = _HOOKPROC(self._raw_hook)  # kept alive: ctypes won't hold a ref for us

    def start(self):
        if self._hook_id:
            return
        self._held = []
        h_mod = kernel32.GetModuleHandleW(None)
        self._hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, h_mod, 0)

    def stop(self):
        if self._hook_id:
            user32.UnhookWindowsHookEx(self._hook_id)
            self._hook_id = None
        self._held = []

    def _raw_hook(self, code, wparam, lparam):
        # A hook callback must never let a Python exception escape into ctypes' C trampoline.
        try:
            if code >= 0:
                self._handle(wparam, lparam)
        except Exception as e:
            print(f"Hotkey capture error: {e}")
        if code < 0:
            return user32.CallNextHookEx(None, code, wparam, lparam)
        return 1  # swallow it: nothing else should react while we're recording

    def _handle(self, wparam, lparam):
        vk = ctypes.cast(lparam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents.vkCode
        if wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            modifier = _MODIFIER_NAMES.get(vk)
            if modifier:
                if modifier not in self._held:
                    self._held.append(modifier)
                    self.on_change(list(self._held))
            else:
                name = _CODE_TO_NAME.get(vk)
                if name:
                    self.on_change(self._held + [name])
        elif wparam in (WM_KEYUP, WM_SYSKEYUP):
            modifier = _MODIFIER_NAMES.get(vk)
            if modifier and modifier in self._held:
                self._held.remove(modifier)


def scroll(dx=0, dy=0):
    """Mouse wheel: dy positive scrolls up, dx positive scrolls right."""
    events = []
    if dy:
        events.append(_INPUT(type=INPUT_MOUSE, union=_INPUTUNION(
            mi=_MOUSEINPUT(mouseData=int(dy * WHEEL_DELTA), dwFlags=MOUSEEVENTF_WHEEL))))
    if dx:
        events.append(_INPUT(type=INPUT_MOUSE, union=_INPUTUNION(
            mi=_MOUSEINPUT(mouseData=int(dx * WHEEL_DELTA), dwFlags=MOUSEEVENTF_HWHEEL))))
    return _send(events)


def _pump_briefly(seconds):
    """Runs a native Windows message loop for a moment. A WH_KEYBOARD_LL callback only fires
    while the thread that installed it is pumping messages — Qt's own event loop already does
    this for the real app, so this helper exists only for testing outside of Qt."""
    msg = wintypes.MSG()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):  # PM_REMOVE
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.005)


if __name__ == "__main__":
    # Resolves keys without sending anything: pressing real keys here would hit the terminal.
    assert vk_for("w") == 0x57 and vk_for("W") == 0x57, "letters map to their own key"
    assert vk_for("ctrl") == 0xA2 and vk_for("win") == 0x5B, "modifiers use the physical keys"
    assert vk_for("f12") == 0x7B and vk_for("7") == 0x37
    assert vk_for("volume_up") == 0xAF and vk_for("[") == 0xDB
    assert vk_for("nonsense") is None
    for action_keys in (["ctrl", "w"], ["win", "shift", "s"], ["alt", "tab"], ["win", "."]):
        assert all(vk_for(k) is not None for k in action_keys), action_keys
    print("winput key table OK")

    # End to end, with real injected input through the real Win32 hook: Ctrl+Win+V is exactly
    # the combo the shell claims first (Clipboard History), so this is the actual bug fixed.
    seen = []
    capture = HotkeyCapture(lambda keys: seen.append(list(keys)))
    capture.start()
    try:
        key_down("ctrl"); _pump_briefly(0.05)
        key_down("win"); _pump_briefly(0.05)
        key_down("v"); _pump_briefly(0.05)
        key_up("v"); key_up("win"); key_up("ctrl")
        _pump_briefly(0.05)
    finally:
        capture.stop()
    assert seen and seen[-1] == ["ctrl", "win", "v"], seen
    print("HotkeyCapture recorded Ctrl+Win+V through the low-level hook OK "
          f"(shell hotkey suppressed, {len(seen)} update(s) seen)")

    # Four modifiers plus a key: the case the fix was actually asked for.
    seen.clear()
    capture.start()
    try:
        for name in ("ctrl", "alt", "shift", "win", "f1"):
            key_down(name)
            _pump_briefly(0.05)
        for name in ("f1", "win", "shift", "alt", "ctrl"):
            key_up(name)
        _pump_briefly(0.05)
    finally:
        capture.stop()
    assert seen[-1] == ["ctrl", "alt", "shift", "win", "f1"], seen
    print("HotkeyCapture recorded all four modifiers plus a key OK")
