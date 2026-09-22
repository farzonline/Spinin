# SPDX-License-Identifier: GPL-3.0-or-later
# macos_system.py
# The macOS side of everything that is not keystrokes: sound devices and volume, the list of
# installed apps, which app is in front, and locking or sleeping the Mac.
#
# Sound goes through the CoreAudio HAL rather than `osascript`, because a fader sends dozens
# of messages a second and spawning a process for each one would be far too slow. That means
# a block of ctypes against CoreAudio.framework; every call is wrapped so a failure is a
# logged no-op rather than a crash, since none of it has been run on a Mac yet.
#
# NOT YET RUN ON A MAC — see docs/MACOS.md for what still needs checking.

import ctypes
import ctypes.util
import os
import subprocess

APPLICATION_DIRS = ("/Applications", "/Applications/Utilities", "/System/Applications",
                    "/System/Applications/Utilities", os.path.expanduser("~/Applications"))

# Folders of Apple's own bits that clutter the list without being things people launch.
SKIP_APPS = {"Screen Sharing", "Directory Utility", "Storage Management", "Ticket Viewer",
             "Feedback Assistant", "Wireless Diagnostics"}


def _fourcc(code):
    """CoreAudio names its properties with four-character codes packed into a UInt32."""
    return int.from_bytes(code.encode("ascii"), "big")


kAudioObjectSystemObject = 1
kAudioHardwarePropertyDevices = _fourcc("dev#")
kAudioHardwarePropertyDefaultOutputDevice = _fourcc("dOut")
kAudioObjectPropertyScopeGlobal = _fourcc("glob")
kAudioObjectPropertyScopeOutput = _fourcc("outp")
kAudioObjectPropertyName = _fourcc("lnam")
kAudioDevicePropertyStreamConfiguration = _fourcc("slay")
kAudioDevicePropertyDeviceUID = _fourcc("uid ")
kAudioHardwareServiceDeviceProperty_VirtualMainVolume = _fourcc("vmvc")
kAudioDevicePropertyVolumeScalar = _fourcc("volm")
kAudioDevicePropertyMute = _fourcc("mute")
kAudioObjectPropertyElementMain = 0


class _PropertyAddress(ctypes.Structure):
    _fields_ = [("mSelector", ctypes.c_uint32), ("mScope", ctypes.c_uint32),
                ("mElement", ctypes.c_uint32)]


def _load(name):
    path = ctypes.util.find_library(name)
    return ctypes.CDLL(path) if path else None


_core_audio = _load("CoreAudio")
_core_foundation = _load("CoreFoundation")
AVAILABLE = bool(_core_audio and _core_foundation)

if AVAILABLE:
    _core_foundation.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                    ctypes.c_long, ctypes.c_uint32]
    _core_foundation.CFStringGetCString.restype = ctypes.c_bool
    _core_foundation.CFRelease.argtypes = [ctypes.c_void_p]


def _cfstring(ref):
    """A CFStringRef as a Python str. Releases the reference; CoreAudio hands us ownership."""
    if not ref:
        return ""
    buffer = ctypes.create_string_buffer(1024)
    ok = _core_foundation.CFStringGetCString(ref, buffer, len(buffer), 0x08000100)  # UTF-8
    _core_foundation.CFRelease(ref)
    return buffer.value.decode("utf-8", "replace") if ok else ""


def _address(selector, scope=kAudioObjectPropertyScopeGlobal, element=kAudioObjectPropertyElementMain):
    return _PropertyAddress(selector, scope, element)


def _get_property(object_id, address, ctype):
    """Reads one fixed-size property. Returns None if CoreAudio refuses."""
    if not AVAILABLE:
        return None
    value = ctype()
    size = ctypes.c_uint32(ctypes.sizeof(ctype))
    status = _core_audio.AudioObjectGetPropertyData(
        ctypes.c_uint32(object_id), ctypes.byref(address), 0, None,
        ctypes.byref(size), ctypes.byref(value))
    return value if status == 0 else None


def _set_property(object_id, address, value):
    if not AVAILABLE:
        return False
    status = _core_audio.AudioObjectSetPropertyData(
        ctypes.c_uint32(object_id), ctypes.byref(address), 0, None,
        ctypes.sizeof(value), ctypes.byref(value))
    return status == 0


def _device_ids():
    if not AVAILABLE:
        return []
    address = _address(kAudioHardwarePropertyDevices)
    size = ctypes.c_uint32(0)
    if _core_audio.AudioObjectGetPropertyDataSize(
            ctypes.c_uint32(kAudioObjectSystemObject), ctypes.byref(address), 0, None,
            ctypes.byref(size)) != 0:
        return []
    count = size.value // ctypes.sizeof(ctypes.c_uint32)
    if not count:
        return []
    buffer = (ctypes.c_uint32 * count)()
    if _core_audio.AudioObjectGetPropertyData(
            ctypes.c_uint32(kAudioObjectSystemObject), ctypes.byref(address), 0, None,
            ctypes.byref(size), buffer) != 0:
        return []
    return list(buffer)


def _is_output(device_id):
    """True when the device has at least one output channel."""
    address = _address(kAudioDevicePropertyStreamConfiguration, kAudioObjectPropertyScopeOutput)
    size = ctypes.c_uint32(0)
    if _core_audio.AudioObjectGetPropertyDataSize(
            ctypes.c_uint32(device_id), ctypes.byref(address), 0, None,
            ctypes.byref(size)) != 0 or size.value == 0:
        return False
    buffer = (ctypes.c_byte * size.value)()
    if _core_audio.AudioObjectGetPropertyData(
            ctypes.c_uint32(device_id), ctypes.byref(address), 0, None,
            ctypes.byref(size), buffer) != 0:
        return False
    # AudioBufferList: UInt32 mNumberBuffers, then the buffers themselves. Any buffer at all
    # means the device can play something.
    return int.from_bytes(bytes(buffer[:4]), "little") > 0


def _device_name(device_id):
    address = _address(kAudioObjectPropertyName, kAudioObjectPropertyScopeOutput)
    ref = _get_property(device_id, address, ctypes.c_void_p)
    return _cfstring(ref.value) if ref else ""


def _device_uid(device_id):
    """The stable id for a device, which survives a re-plug where the numeric id does not."""
    address = _address(kAudioDevicePropertyDeviceUID, kAudioObjectPropertyScopeOutput)
    ref = _get_property(device_id, address, ctypes.c_void_p)
    return _cfstring(ref.value) if ref else ""


def _by_uid():
    return {uid: device_id for device_id, uid in
            ((d, _device_uid(d)) for d in _device_ids() if _is_output(d)) if uid}


# ---------- the audio_devices interface ----------
def outputs():
    """Active playback devices as a list of (device_id, friendly name)."""
    found = []
    try:
        for device_id in _device_ids():
            if not _is_output(device_id):
                continue
            uid, name = _device_uid(device_id), _device_name(device_id)
            if uid and name:
                found.append((uid, name))
    except Exception as e:
        print(f"Error listing audio devices: {e}")
    return sorted(found, key=lambda d: d[1].lower())


def current_output():
    """(device_id, name) of the default playback device, or (None, None)."""
    try:
        address = _address(kAudioHardwarePropertyDefaultOutputDevice)
        value = _get_property(kAudioObjectSystemObject, address, ctypes.c_uint32)
        if not value:
            return None, None
        return _device_uid(value.value) or None, _device_name(value.value) or None
    except Exception as e:
        print(f"Error reading default audio device: {e}")
        return None, None


def set_output(device_id):
    """Makes device_id (a CoreAudio UID) the default output."""
    try:
        numeric = _by_uid().get(device_id)
        if numeric is None:
            return False
        address = _address(kAudioHardwarePropertyDefaultOutputDevice)
        return _set_property(kAudioObjectSystemObject, address, ctypes.c_uint32(numeric))
    except Exception as e:
        print(f"Error switching audio device: {e}")
        return False


def find_output(device_id=None, name=None):
    """Matches by id first, then by name, so a re-plugged device is still found."""
    devices = outputs()
    by_id = dict(devices)
    if device_id and device_id in by_id:
        return device_id, by_id[device_id]
    if name:
        for did, dname in devices:
            if dname == name:
                return did, dname
    return None, None


def next_output(step=1):
    """The device after the current default, wrapping around."""
    devices = outputs()
    if len(devices) < 2:
        return None, None
    ids = [d[0] for d in devices]
    current = current_output()[0]
    index = ids.index(current) if current in ids else -1
    return devices[(index + step) % len(devices)]


# ---------- system volume ----------
def _default_output_id():
    address = _address(kAudioHardwarePropertyDefaultOutputDevice)
    value = _get_property(kAudioObjectSystemObject, address, ctypes.c_uint32)
    return value.value if value else None


def set_volume(level):
    """Sets the output volume, 0.0 to 1.0."""
    device_id = _default_output_id()
    if device_id is None:
        return False
    level = max(0.0, min(1.0, float(level)))
    # The virtual main volume is the one the menu bar slider moves. Some devices do not
    # publish it, and those take a per-channel write instead.
    address = _address(kAudioHardwareServiceDeviceProperty_VirtualMainVolume,
                       kAudioObjectPropertyScopeOutput)
    if _set_property(device_id, address, ctypes.c_float(level)):
        return True
    ok = False
    for channel in (1, 2):
        per_channel = _address(kAudioDevicePropertyVolumeScalar,
                               kAudioObjectPropertyScopeOutput, channel)
        ok = _set_property(device_id, per_channel, ctypes.c_float(level)) or ok
    return ok


def set_muted(muted):
    device_id = _default_output_id()
    if device_id is None:
        return False
    address = _address(kAudioDevicePropertyMute, kAudioObjectPropertyScopeOutput)
    return _set_property(device_id, address, ctypes.c_uint32(1 if muted else 0))


def get_muted():
    device_id = _default_output_id()
    if device_id is None:
        return False
    address = _address(kAudioDevicePropertyMute, kAudioObjectPropertyScopeOutput)
    value = _get_property(device_id, address, ctypes.c_uint32)
    return bool(value.value) if value else False


# ---------- installed applications ----------
def scan_apps(roots=None):
    """[(display name, path)] for the .app bundles on this Mac, sorted by name."""
    found = {}
    for root in (roots if roots is not None else APPLICATION_DIRS):
        if not root or not os.path.isdir(root):
            continue
        try:
            entries = os.listdir(root)
        except OSError:
            continue
        for entry in entries:
            if not entry.endswith(".app"):
                continue
            name = entry[:-4]
            if name in SKIP_APPS:
                continue
            found.setdefault(name, os.path.join(root, entry))  # first root wins
    return sorted(found.items(), key=lambda pair: pair[0].lower())


# ---------- the app in front ----------
def frontmost_app():
    """(identifier, window title). The identifier is the bundle id, which is what a macOS
    profile is keyed on — the counterpart of an .exe name on Windows."""
    try:
        from AppKit import NSWorkspace
    except ImportError:
        return "global", ""
    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not app:
            return "global", ""
        identifier = app.bundleIdentifier() or (app.localizedName() or "").lower()
        return identifier or "global", _window_title(app.processIdentifier())
    except Exception as e:
        print(f"Error reading the front app: {e}")
        return "global", ""


def _window_title(pid):
    """Best-effort window title. Needs Screen Recording permission on Catalina and later,
    so an empty string here is normal rather than a fault."""
    try:
        import Quartz
        options = (Quartz.kCGWindowListOptionOnScreenOnly
                   | Quartz.kCGWindowListExcludeDesktopElements)
        for window in Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []:
            if window.get("kCGWindowOwnerPID") == pid:
                title = window.get("kCGWindowName")
                if title:
                    return str(title)
    except Exception:
        pass
    return ""


def own_identifier():
    """What frontmost_app() calls this app, so it can tell when it is itself in front."""
    try:
        from AppKit import NSBundle
        return NSBundle.mainBundle().bundleIdentifier() or "org.spinin.Spinin"
    except Exception:
        return "org.spinin.Spinin"


# ---------- power and launching ----------
def _run(command):
    try:
        subprocess.Popen(command)
        return True
    except Exception as e:
        print(f"Error running {command}: {e}")
        return False


def lock_screen():
    """Locks the Mac. CGSession is what the Fast User Switching menu calls."""
    return _run(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/"
                 "CGSession", "-suspend"])


def sleep_now():
    return _run(["pmset", "sleepnow"])


def launch(name_or_path):
    """Opens an app by name or by path to its .app bundle."""
    if not name_or_path:
        return False
    if os.path.exists(name_or_path):
        return _run(["open", name_or_path])
    return _run(["open", "-a", name_or_path])


def open_uri(uri):
    return _run(["open", uri])


if __name__ == "__main__":
    import tempfile

    # The app scan is pure filesystem work, so it can be checked from any platform.
    with tempfile.TemporaryDirectory() as tmp:
        for entry in ("Safari.app", "Mail.app", "Screen Sharing.app", "notes.txt"):
            os.makedirs(os.path.join(tmp, entry), exist_ok=True)
        names = [n for n, _ in scan_apps([tmp])]
        assert names == ["Mail", "Safari"], names
        assert scan_apps([tmp]) == scan_apps([tmp, tmp]), "the same root twice must not duplicate"
        assert scan_apps([tmp])[0][1].endswith("Mail.app")
    assert scan_apps(["/does/not/exist"]) == []

    assert _fourcc("dev#") == 0x64657623, hex(_fourcc("dev#"))
    assert _fourcc("dOut") == 0x644F7574
    assert _fourcc("glob") == 0x676C6F62
    assert ctypes.sizeof(_PropertyAddress) == 12, "three UInt32s, no padding"

    if AVAILABLE:
        devices = outputs()
        print(f"{len(devices)} output device(s): " + ", ".join(n for _, n in devices))
        print(f"default: {current_output()[1]}")
    else:
        print("CoreAudio not present (not a Mac) — sound paths untested")
    print("macos_system OK")
