# SPDX-License-Identifier: GPL-3.0-or-later
# userinput.py
# Sending keystrokes and scroll events, on whichever platform this is.
#
# The rest of the app imports this and never learns which backend answered. Each backend
# offers the same names: tap, key_down, key_up, scroll, vk_for, last_error, HotkeyCapture
# and KEYS.

import sys

IS_MAC = sys.platform == "darwin"

if IS_MAC:
    from _input_mac import (KEYS, HotkeyCapture, key_down, key_up, last_error,  # noqa: F401
                            scroll, tap, vk_for)
else:
    from _input_win import (VK as KEYS, HotkeyCapture, key_down, key_up,  # noqa: F401
                            last_error, scroll, tap, vk_for)


if __name__ == "__main__":
    assert callable(tap) and callable(scroll) and callable(vk_for)
    assert isinstance(last_error(), str), "last_error is a function on both backends"
    assert KEYS and vk_for("a") is not None and vk_for("nonsense") is None
    assert hasattr(HotkeyCapture, "start") and hasattr(HotkeyCapture, "stop")
    print(f"userinput OK — {'macOS' if IS_MAC else 'Windows'} backend, {len(KEYS)} keys")
