# SPDX-License-Identifier: GPL-3.0-or-later
# action_handler.py
import ctypes
import math
import os
import sys
import subprocess
import threading
import time

from AppOpener import open as open_app
from pycaw.pycaw import AudioUtilities

import actions as catalog
import audio_devices
import winput

OWN_PROCESS = os.path.basename(sys.executable).lower()

# Jog ticks per second: below SLOW_TURN nothing is added, at FAST_TURN the boost is in full.
# ponytail: set by feel on a DDJ-FLX4, lower them if acceleration kicks in too late.
SLOW_TURN, FAST_TURN = 30.0, 110.0

# Smooth scrolling: let the wheel go and the scroll runs on, starting at the speed you were
# actually turning it and slowing to a stop, the way a phone list does.
# ponytail: tuned by feel; GLIDE_DECAY is the one to change if it coasts too long or too little.
GLIDE_HOLD = 0.13     # quiet time after the last tick before the glide takes over
GLIDE_DECAY = 2.6     # e-folds a second — how quickly the glide runs down
GLIDE_MIN = 1.2       # clicks a second at which it stops altogether
GLIDE_MAX = 45.0      # clicks a second cap, so a hard spin stays readable
GLIDE_FRAME = 0.016   # how often the glide adds up what it owes, ~60 a second

# Legacy "system_action" values -> catalog ids, so old mappings.json files keep working.
LEGACY_SYSTEM = {
    "volume_control": "range.volume", "volume_up": "media.volup", "volume_down": "media.voldown",
    "media_play_pause": "media.playpause", "media_mute": "media.mute",
    "media_next": "media.next", "media_prev": "media.prev",
}


def foreground_pid():
    import win32gui
    import win32process
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return pid or None


def foreground_name():
    """Process name of the window that will receive a keystroke, for the Activity log."""
    try:
        import psutil
        pid = foreground_pid()
        return psutil.Process(pid).name().lower() if pid else "no window"
    except Exception:
        return "unknown"


class ActionHandler:
    def __init__(self):
        self.volume_interface = None
        self.previous_output = None  # for "swap the last two sound devices"
        self.turn_accum = {}     # control_id -> unspent jog ticks
        self.turn_speed = {}     # control_id -> (last tick time, smoothed ticks per second)
        self.move_accum = {}     # control_id -> (last position, unspent scroll)
        self.glide = {}          # control_id -> a scroll still coasting to a stop
        self._glide_lock = threading.Lock()
        self._pump = None
        self._session_cache = (0, {})
        self._last_level = -1.0
        self.init_audio()

    def init_audio(self):
        """Initialises the pycaw audio endpoint for system volume control."""
        try:
            device = AudioUtilities.GetSpeakers()
            if hasattr(device, "EndpointVolume"):  # pycaw >= 20240316
                self.volume_interface = device.EndpointVolume
            elif device:  # older pycaw returns the raw IMMDevice
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import IAudioEndpointVolume
                iface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume_interface = cast(iface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            print(f"Failed to initialise pycaw volume control: {e}")

    # ---------- entry point ----------
    def execute(self, mapping, value=None, control_id=None):
        """Runs a mapping. `value` is the raw 0-127 MIDI value; `control_id` identifies the
        physical control, which turn and movement actions need to track their own state."""
        if not mapping:
            return False
        action, payload = self.resolve(mapping)
        if not action:
            return False
        options = mapping.get("options", {})
        try:
            if action["kind"] == "press":
                return self.run_press(action, payload)
            if action["kind"] == "turn":
                return self.run_turn(action, payload, value, options, control_id)
            return self.run_range(action, payload, value, options, control_id)
        except Exception as e:
            print(f"Error running {action['id']}: {e}")
            return False

    def resolve(self, mapping):
        """Returns (catalog action, payload) for both new and legacy mappings."""
        m_type = mapping.get("type")
        if m_type == "action":
            action = catalog.BY_ID.get(mapping.get("id"))
            if not action:
                return None, None
            if action["backend"] != "custom":
                return action, action["payload"]
            if action["payload"] == "turn_keys":
                return action, {"cw": mapping.get("keys_cw", []), "ccw": mapping.get("keys_ccw", [])}
            if action["payload"] == "device":
                return action, (mapping.get("device_id"), mapping.get("device_name"))
            return action, mapping.get("keys") or mapping.get("command", "")
        # Legacy formats
        if m_type == "launch_app":
            return catalog.BY_ID["custom.app"], mapping.get("command", "")
        if m_type == "script":
            return catalog.BY_ID["custom.command"], mapping.get("command", "")
        if m_type == "keystroke":
            return catalog.BY_ID["custom.keys"], mapping.get("keys", [])
        if m_type == "system_action":
            action = catalog.BY_ID.get(LEGACY_SYSTEM.get(mapping.get("action"), ""))
            return (action, action["payload"]) if action else (None, None)
        return None, None

    # ---------- press ----------
    def run_press(self, action, payload):
        backend = action["backend"]
        if backend == "keys":
            return self.tap(payload)
        if backend == "uri":
            return self.launch_uri(payload)
        if backend == "run":
            return self.spawn(payload)
        if backend == "native":
            return self.NATIVE_PRESS[payload](self)
        if backend == "custom":
            if action["id"] == "custom.keys":
                return self.tap(payload)
            if action["id"] == "custom.app":
                return self.launch_app(payload)
            if action["id"] == "audio.setdevice":
                return self.choose_output(*payload)
            return self.spawn(payload)
        return False

    def tap(self, keys):
        """Sends a shortcut and reports where it went, so a dead shortcut can be diagnosed."""
        if not keys:
            return False
        target = foreground_name()
        ok = winput.tap(keys)
        combo = " + ".join(k.upper() for k in keys)
        if not ok:
            self.report(f"{combo} was not sent. {winput.last_error}")
        elif target == OWN_PROCESS:
            self.report(f"Sent {combo}, but Spinin itself was in front, so it went nowhere. "
                        "Click the app you want it in first.")
        else:
            self.report(f"Sent {combo} to {target}")
        return ok

    def report(self, text):
        """Overridden by the window so messages land in the Activity log."""
        print(text)

    @staticmethod
    def scroll(dx=0, dy=0, with_ctrl=False):
        if not with_ctrl:
            return winput.scroll(dx, dy)
        winput.key_down("ctrl")  # Ctrl + wheel is how apps zoom
        try:
            return winput.scroll(dx, dy)
        finally:
            winput.key_up("ctrl")

    @staticmethod
    def _background(fn, *args):
        # AppOpener scans installed apps and Explorer can be slow; never block the UI thread.
        threading.Thread(target=fn, args=args, daemon=True).start()
        return True

    def launch_uri(self, uri):
        def run():
            try:
                if uri.startswith("shell:"):
                    subprocess.Popen(["explorer.exe", uri])
                else:
                    os.startfile(uri)
            except Exception as e:
                print(f"Error opening {uri}: {e}")
        return self._background(run)

    def spawn(self, command):
        if not command:
            return False

        def run():
            try:
                subprocess.Popen(command, shell=True)
            except Exception as e:
                print(f"Error running {command}: {e}")
        return self._background(run)

    def launch_app(self, name):
        if not name:
            return False

        def run():
            try:
                if os.path.exists(name):
                    # Covers the Start Menu shortcuts the app list offers: opening the .lnk
                    # keeps the working directory and arguments the installer put in it,
                    # which resolving it down to the bare .exe would throw away.
                    os.startfile(name)
                elif any(c in name for c in "\\/ "):
                    subprocess.Popen(name, shell=True)
                else:
                    open_app(name, match_closest=True)
            except Exception as e:
                print(f"Error launching {name}: {e}")
        return self._background(run)

    def sleep_pc(self):
        return bool(ctypes.windll.powrprof.SetSuspendState(0, 1, 0))

    def lock_pc(self):
        # Windows ignores a synthetic Win+L (SendInput can't touch the secure desktop) -
        # LockWorkStation() is the actual API third-party code has to call.
        return bool(ctypes.windll.user32.LockWorkStation())

    # ---------- sound device switching ----------
    def switch_output(self, device_id, name=None):
        """Makes a device the default, remembering the one it replaced."""
        if not device_id:
            return False
        was = audio_devices.current_output()[0]
        if not audio_devices.set_output(device_id):
            return False
        if was and was != device_id:
            self.previous_output = was
        self.volume_interface = None
        self.init_audio()  # the old endpoint belongs to the device we just left
        self._last_level = -1.0
        print(f"Sound device: {name or device_id}")
        return True

    def choose_output(self, device_id, name):
        found_id, found_name = audio_devices.find_output(device_id, name)
        if not found_id:
            print(f"Sound device not available: {name or device_id}")
            return False
        return self.switch_output(found_id, found_name)

    def step_output(self, step=1):
        device_id, name = audio_devices.next_output(step)
        return self.switch_output(device_id, name)

    def toggle_output(self):
        if self.previous_output:
            device_id, name = audio_devices.find_output(self.previous_output)
            if device_id:
                return self.switch_output(device_id, name)
        return self.step_output(1)  # nothing to go back to yet

    NATIVE_PRESS = {
        "media_play_pause": lambda s: s.tap(["media_play_pause"]),  # media keys are system-wide
        "media_mute": lambda s: s.tap(["media_mute"]),
        "media_next": lambda s: s.tap(["media_next"]),
        "media_prev": lambda s: s.tap(["media_prev"]),
        "volume_up": lambda s: s.tap(["volume_up"]),
        "volume_down": lambda s: s.tap(["volume_down"]),
        "sleep": lambda s: s.sleep_pc(),
        "lock": lambda s: s.lock_pc(),
        "next_output": lambda s: s.step_output(1),
        "toggle_output": lambda s: s.toggle_output(),
    }

    # ---------- turn (jog wheels, browse encoder) ----------
    def run_turn(self, action, payload, value, options, control_id):
        delta = catalog.decode_delta(value or 0)
        if options.get("invert"):
            delta = -delta
        rate = self.note_turn(control_id)
        step = max(1, int(options.get("sensitivity", 2)))  # ticks of the wheel per action
        total = self.turn_accum.get(control_id, 0) + delta
        fired = int(total / step)
        self.turn_accum[control_id] = total - fired * step
        multiplier = self.boost(control_id, options)
        if fired:
            for _ in range(abs(fired) * multiplier):
                self.turn_once(action, payload, 1 if fired > 0 else -1)
        # The action has to allow it too: "smooth" left over on a mapping that has since been
        # pointed at "skip tracks" must not set that skipping away on its own.
        if delta and options.get("smooth") and "smooth" in action["options"]:
            self.arm_glide(action, payload, control_id, 1 if delta > 0 else -1,
                           rate / step * multiplier)
        return bool(fired)

    def note_turn(self, control_id):
        """Records that the wheel moved, and returns how fast it is turning in ticks a second."""
        now = time.monotonic()
        last, rate = self.turn_speed.get(control_id, (0.0, 0.0))
        gap = now - last
        self.turn_speed[control_id] = (now, 0.0 if gap > 0.25 else  # a pause starts over
                                       (rate * 0.7 + (1 / gap) * 0.3 if gap > 0 else rate))
        return self.turn_speed[control_id][1]

    def boost(self, control_id, options):
        """How many times over to repeat each step, from how fast the wheel is turning.

        A slow turn stays 1:1 for precision; spin it and each step counts for more, the way a
        mouse wheel accelerates. 'acceleration' 0 turns it off.
        """
        strength = float(options.get("acceleration", 0) or 0)
        if strength <= 0:
            return 1
        speed = self.turn_speed.get(control_id, (0.0, 0.0))[1]
        fraction = min(max(speed - SLOW_TURN, 0.0) / (FAST_TURN - SLOW_TURN), 1.5)
        return max(1, round(1 + strength * fraction))

    # ---------- smooth scrolling ----------
    def arm_glide(self, action, payload, control_id, direction, clicks_per_sec):
        """Keeps a glide ready for this control, at the speed the wheel is turning right now.

        Called on every tick while you turn it. Each call pushes 'touched' forward, so the
        glide sits waiting and only takes over once the ticks stop — which also means putting
        a hand back on the wheel catches a scroll already coasting.
        """
        with self._glide_lock:
            self.glide[control_id] = {"v": min(float(clicks_per_sec), GLIDE_MAX),
                                      "dir": direction, "touched": time.monotonic(),
                                      "carry": 0.0, "action": action, "payload": payload}
            if self._pump is None or not self._pump.is_alive():
                self._pump = threading.Thread(target=self._run_glides, daemon=True)
                self._pump.start()

    def stop_glides(self, control_id=None):
        """Drops one coasting scroll, or every one of them."""
        with self._glide_lock:
            self.glide.pop(control_id, None) if control_id else self.glide.clear()

    def _run_glides(self):
        """Pays out the coasting scrolls, then exits once none are left."""
        last = time.monotonic()
        while True:
            time.sleep(GLIDE_FRAME)
            now = time.monotonic()
            elapsed, last = now - last, now
            with self._glide_lock:
                live = list(self.glide.items())
            if not live:
                return
            for control_id, g in live:
                if now - g["touched"] < GLIDE_HOLD:
                    continue  # still being turned by hand; nothing to coast yet
                g["v"] *= math.exp(-GLIDE_DECAY * elapsed)
                if g["v"] < GLIDE_MIN:
                    self.stop_glides(control_id)
                    continue
                g["carry"] += g["v"] * elapsed
                clicks = int(g["carry"])
                if clicks:
                    g["carry"] -= clicks
                    for _ in range(clicks):
                        self.turn_once(g["action"], g["payload"], g["dir"])

    def turn_once(self, action, payload, direction):
        if action["backend"] == "native":
            handler = payload
            if handler == "scroll_v":
                self.scroll(0, direction)
            elif handler == "scroll_h":
                self.scroll(direction, 0)
            elif handler == "zoom_wheel":
                self.scroll(0, direction, with_ctrl=True)
            elif handler == "audio_device":
                self.step_output(direction)
            return
        keys = payload.get("cw" if direction > 0 else "ccw", [])
        self.tap(keys)

    # ---------- range (faders, knobs) ----------
    def run_range(self, action, payload, value, options, control_id):
        if value is None:
            return False
        level = max(0.0, min(1.0, value / 127))
        if options.get("invert"):
            level = 1.0 - level
        if payload == "sys_volume":
            return self.set_volume(level)
        if payload == "app_volume":
            return self.set_app_volume(level)
        if payload == "balance":
            return self.set_balance(level)
        if payload == "scroll_move":
            return self.scroll_by_move(level, options, control_id)
        return False

    def set_volume(self, level):
        for attempt in (1, 2):
            if not self.volume_interface:
                return False
            try:
                self.volume_interface.SetMasterVolumeLevelScalar(level, None)
                # Coming back up from silence should also lift a mute, however it was set.
                if level > 0 and self._last_level <= 0 and self.volume_interface.GetMute():
                    self.volume_interface.SetMute(0, None)
                self._last_level = level
                return True
            except Exception as e:
                print(f"Error setting volume (attempt {attempt}): {e}")
                self.init_audio()  # the endpoint dies when the default audio device changes
        return False

    def app_session(self):
        """SimpleAudioVolume of the app in front, cached: enumerating sessions is slow
        and a fader sends dozens of messages a second."""
        pid = foreground_pid()
        if not pid:
            return None
        cached_at, by_pid = self._session_cache
        if time.monotonic() - cached_at > 2.0 or pid not in by_pid:
            by_pid = {}
            try:
                for session in AudioUtilities.GetAllSessions():
                    if session.Process:
                        by_pid[session.Process.pid] = session.SimpleAudioVolume
            except Exception as e:
                print(f"Error reading audio sessions: {e}")
            self._session_cache = (time.monotonic(), by_pid)
        return by_pid.get(pid)

    def set_app_volume(self, level):
        session = self.app_session()
        if not session:
            return False
        session.SetMasterVolume(level, None)
        return True

    def set_balance(self, level):
        """0 = hard left, 0.5 = centred, 1 = hard right."""
        if not self.volume_interface:
            return False
        try:
            channels = self.volume_interface.GetChannelCount()
            if channels < 2:
                return False
            left, right = min(1.0, 2 - 2 * level), min(1.0, 2 * level)
            self.volume_interface.SetChannelVolumeLevelScalar(0, left, None)
            self.volume_interface.SetChannelVolumeLevelScalar(1, right, None)
            return True
        except Exception as e:
            print(f"Error setting balance: {e}")
            return False

    def scroll_by_move(self, level, options, control_id):
        last, spare = self.move_accum.get(control_id, (level, 0.0))
        gain = max(1, int(options.get("sensitivity", 5)))
        spare += (level - last) * gain * 10
        clicks = int(spare)
        self.move_accum[control_id] = (level, spare - clicks)
        if clicks:
            self.scroll(0, clicks)
        return bool(clicks)


if __name__ == "__main__":
    # Checks the routing only: no keys are pressed and nothing is launched.
    h = ActionHandler.__new__(ActionHandler)
    h.turn_accum, h.move_accum, h.turn_speed = {}, {}, {}
    h.glide, h._glide_lock, h._pump = {}, threading.Lock(), None
    fired = []
    h.turn_once = lambda action, payload, d: fired.append(d)
    turn = {"type": "action", "id": "turn.scroll", "options": {"sensitivity": 2}}
    action, payload = h.resolve(turn)
    for raw in (65, 65, 65, 65):  # four clockwise jog ticks at 2 ticks per action
        h.run_turn(action, payload, raw, turn["options"], "JOG_ROTATE_L")
    assert fired == [1, 1], fired
    h.run_turn(action, payload, 63, {"sensitivity": 1, "invert": True}, "JOG_ROTATE_L")
    assert fired[-1] == 1, "inverted anticlockwise should go the other way"

    legacy = {"type": "system_action", "action": "volume_control"}
    assert h.resolve(legacy)[0]["id"] == "range.volume"
    assert h.resolve({"type": "keystroke", "keys": ["ctrl", "z"]})[1] == ["ctrl", "z"]
    assert h.resolve({"type": "action", "id": "win.start"})[1] == ["win"]

    moved = []
    h.scroll = lambda dx=0, dy=0, with_ctrl=False: moved.append(dy)
    h.scroll_by_move(0.0, {"sensitivity": 5}, "FADER_L")
    h.scroll_by_move(0.5, {"sensitivity": 5}, "FADER_L")
    assert moved == [25], moved

    assert h.resolve({"type": "action", "id": "audio.setdevice", "device_id": "x",
                      "device_name": "Speakers"})[1] == ("x", "Speakers")
    assert catalog.BY_ID["audio.nextdevice"]["payload"] in ActionHandler.NATIVE_PRESS

    # Acceleration: a slow turn stays 1:1, a fast one multiplies.
    h.turn_speed = {}
    slow = []
    for _ in range(6):
        h.turn_speed["J"] = (time.monotonic() - 0.10, 10.0)  # ~10 ticks a second
        slow.append(h.boost("J", {"acceleration": 5}))
    assert set(slow) == {1}, slow
    h.turn_speed["J"] = (time.monotonic() - 0.005, 150.0)    # spinning it
    fast = h.boost("J", {"acceleration": 5})
    assert fast >= 6, fast
    assert h.boost("J", {"acceleration": 0}) == 1, "acceleration off means 1:1"
    print(f"turn acceleration OK (slow {slow[0]}x, fast {fast}x)")

    # Smooth scrolling: the scroll runs on after the wheel stops, then winds down by itself.
    h.turn_accum, h.turn_speed, h.glide = {}, {}, {}
    smooth = {"sensitivity": 1, "smooth": True}
    for _ in range(6):
        h.run_turn(action, payload, 65, smooth, "JOG_ROTATE_R")
        time.sleep(0.02)
    assert "JOG_ROTATE_R" in h.glide, "a smooth scroll must leave something to coast"
    coasted = len(fired)
    time.sleep(0.45)
    assert len(fired) > coasted, "the glide must keep scrolling once the wheel stops"
    assert all(d == 1 for d in fired[coasted:]), "it must coast the way it was turned"
    time.sleep(1.5)
    assert "JOG_ROTATE_R" not in h.glide, "the glide must run down and stop on its own"

    # Without the option, and on an action that does not offer it, nothing coasts.
    h.turn_speed, h.glide = {}, {}
    h.run_turn(action, payload, 65, {"sensitivity": 1}, "JOG_ROTATE_L")
    assert not h.glide, "smooth scrolling is off unless it is asked for"
    skip, skip_payload = h.resolve({"type": "action", "id": "turn.track"})
    h.run_turn(skip, skip_payload, 65, smooth, "JOG_ROTATE_L")
    assert not h.glide, "only the scrolling actions may coast"
    print("smooth scrolling OK")
    print("action_handler self-check OK")
