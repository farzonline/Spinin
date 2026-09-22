# SPDX-License-Identifier: GPL-3.0-or-later
# audio_devices.py
# Listing playback devices and changing the default one, on whichever platform this is.
#
# Both backends speak the same five functions, and the same shape of device id: an opaque
# string that survives a re-plug. On Windows that is the MMDevice id, on macOS the CoreAudio
# UID. Neither is meaningful to the other, so a mapping that names a device is worth keeping
# per platform.

import sys

if sys.platform == "darwin":
    from macos_system import (current_output, find_output, next_output,  # noqa: F401
                              outputs, set_output)
else:
    from _audio_win import (current_output, find_output, next_output,  # noqa: F401
                            outputs, set_output)


if __name__ == "__main__":
    devices = outputs()
    print(f"{len(devices)} active playback device(s):")
    for did, name in devices:
        print(f"  {name}")
    now_id, now_name = current_output()
    print(f"default: {now_name}")
    print(f"next would be: {next_output()[1]}")
    if now_id:
        assert find_output(now_id)[0] == now_id, "the current device must be findable by id"
        assert set_output(now_id), "re-selecting the current default should succeed"
        assert current_output()[0] == now_id, "default device changed unexpectedly"
        print("set_output OK (re-applied the current default, nothing changed)")
