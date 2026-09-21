# SPDX-License-Identifier: GPL-3.0-or-later
# audio_devices.py
# Lists Windows playback devices and changes the default one.
#
# Windows has no public API for setting the default audio device; every tool that does this
# (including the Sound control panel itself) goes through the undocumented IPolicyConfig
# interface, which is what this uses.

import warnings

import comtypes
from comtypes import GUID, COMMETHOD, HRESULT, IUnknown
from ctypes import wintypes, c_wchar_p
from pycaw.utils import AudioUtilities

CLSID_PolicyConfigClient = GUID("{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}")

ROLE_CONSOLE, ROLE_MULTIMEDIA, ROLE_COMMUNICATIONS = 0, 1, 2
RENDER = "eRender"  # what pycaw's GetEndpointDataFlow returns for playback devices


class IPolicyConfig(IUnknown):
    """Only SetDefaultEndpoint is used; the earlier methods are declared to line up the vtable."""
    _iid_ = GUID("{F8679F50-850A-41CF-9C72-430F290290C8}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetMixFormat"),
        COMMETHOD([], HRESULT, "GetDeviceFormat"),
        COMMETHOD([], HRESULT, "ResetDeviceFormat"),
        COMMETHOD([], HRESULT, "SetDeviceFormat"),
        COMMETHOD([], HRESULT, "GetProcessingPeriod"),
        COMMETHOD([], HRESULT, "SetProcessingPeriod"),
        COMMETHOD([], HRESULT, "GetShareMode"),
        COMMETHOD([], HRESULT, "SetShareMode"),
        COMMETHOD([], HRESULT, "GetPropertyValue"),
        COMMETHOD([], HRESULT, "SetPropertyValue"),
        COMMETHOD([], HRESULT, "SetDefaultEndpoint",
                  (["in"], c_wchar_p, "device_id"), (["in"], wintypes.DWORD, "role")),
        COMMETHOD([], HRESULT, "SetEndpointVisibility"),
    ]


def outputs():
    """Active playback devices as a list of (device_id, friendly name)."""
    found = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # pycaw warns about properties some devices lack
        for device in AudioUtilities.GetAllDevices():
            # One awkward device must not empty the whole list, so each is handled on its own.
            try:
                state = getattr(device.state, "value", device.state)
                if state != 1 or not device.id or not device.FriendlyName:  # 1 = Active
                    continue
                if AudioUtilities.GetEndpointDataFlow(device.id) != RENDER:
                    continue
                found.append((device.id, device.FriendlyName))
            except Exception as e:
                print(f"Skipping an audio device: {e}")
    return sorted(found, key=lambda d: d[1].lower())


def current_output():
    """(device_id, name) of the default playback device, or (None, None)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            speakers = AudioUtilities.GetSpeakers()
            device_id = speakers.GetId()
        name = dict(outputs()).get(device_id)
        return device_id, name
    except Exception as e:
        print(f"Error reading default audio device: {e}")
        return None, None


def set_output(device_id):
    """Makes device_id the default for playback, apps and calls alike."""
    try:
        policy = comtypes.CoCreateInstance(CLSID_PolicyConfigClient, IPolicyConfig,
                                           comtypes.CLSCTX_ALL)
        for role in (ROLE_CONSOLE, ROLE_MULTIMEDIA, ROLE_COMMUNICATIONS):
            policy.SetDefaultEndpoint(device_id, role)
        return True
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


if __name__ == "__main__":
    devices = outputs()
    print(f"{len(devices)} active playback device(s):")
    for did, name in devices:
        print(f"  {name}")
    now_id, now_name = current_output()
    print(f"default: {now_name}")
    print(f"next would be: {next_output()[1]}")
    # Re-selecting the device that is already default proves the call works and changes nothing.
    if now_id:
        assert set_output(now_id), "SetDefaultEndpoint failed"
        assert current_output()[0] == now_id, "default device changed unexpectedly"
        print("SetDefaultEndpoint OK (re-applied the current default, nothing changed)")
