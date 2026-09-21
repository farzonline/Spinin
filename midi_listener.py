# SPDX-License-Identifier: GPL-3.0-or-later
# midi_listener.py
import time
import mido
from PyQt6.QtCore import QThread, pyqtSignal

from controls import MIDI_TO_CONTROL, CONTROL_TO_MIDI, control_for_code  # noqa: F401

# 14-bit knobs/faders send a coarse CC (x) then a fine CC (y); value = 128*x + y.
DUAL_CC_PAIRS = {
    "CC_6_8": "CC_6_40",
    "CC_0_4": "CC_0_36",
    "CC_1_4": "CC_1_36",
    "CC_0_7": "CC_0_39",
    "CC_1_7": "CC_1_39",
    "CC_6_5": "CC_6_37",
    "CC_0_11": "CC_0_43",
    "CC_1_11": "CC_1_43",
    "CC_0_15": "CC_0_47",
    "CC_1_15": "CC_1_47",
    "CC_6_23": "CC_6_55",
    "CC_6_24": "CC_6_56",
    "CC_6_12": "CC_6_44",
    "CC_6_13": "CC_6_45",
    "CC_4_2": "CC_4_34",
    "CC_1_0": "CC_1_32",
    "CC_0_0": "CC_0_32",
    "CC_6_31": "CC_6_63",
    "CC_0_19": "CC_0_51",
    "CC_1_19": "CC_1_51",
}
FINE_TO_COARSE = {fine: coarse for coarse, fine in DUAL_CC_PAIRS.items()}

STARTUP_LIGHTS = [CONTROL_TO_MIDI[f"PAD_{s}_{i}"] for s in "LR" for i in range(1, 9)] + [
    CONTROL_TO_MIDI[c] for c in ("CUE_L", "PLAY_L", "CUE_R", "PLAY_R")
]


class MidiListenerThread(QThread):
    # midi_received: (control_id, msg_type, value, raw_midi_code)
    midi_received = pyqtSignal(str, str, int, str)
    status_changed = pyqtSignal(bool, str)

    def __init__(self, port_name="DDJ-FLX4"):
        super().__init__()
        self.port_name = port_name
        self.running = True
        self.outport = None
        self.cc_coarse_values = {}
        self.cc_fine_values = {}
        self.cc_last_sent = {}

    def _find(self, names):
        return next((p for p in names if self.port_name.lower() in p.lower()), None)

    def run(self):
        self.status_changed.emit(False, "Looking for DDJ-FLX4…")
        while self.running:
            try:
                # No fallback to "first available port": on Windows that is usually the
                # GS Wavetable synth, which would play the LED messages as audible notes.
                target_in = self._find(mido.get_input_names())
                if not target_in:
                    self.status_changed.emit(False, "DDJ-FLX4 not found. Plug it in via USB.")
                    self._sleep(2.0)
                    continue

                target_out = self._find(mido.get_output_names())
                self.outport = mido.open_output(target_out) if target_out else None
                with mido.open_input(target_in) as inport:
                    self.cc_coarse_values.clear()
                    self.cc_fine_values.clear()
                    self.cc_last_sent.clear()
                    if self.outport:
                        self.play_startup_light_show()
                    self.status_changed.emit(True, target_in)

                    last_check = time.monotonic()
                    while self.running:
                        msg = inport.poll()
                        if msg:
                            control_id, raw_code, val = self.parse_message(msg)
                            if control_id:
                                self.midi_received.emit(control_id, msg.type, val, raw_code)
                            continue
                        # rtmidi never errors on unplug, so poll the port list instead. Checking
                        # often keeps the window short in which LEDs go to a dead port.
                        if time.monotonic() - last_check > 0.7:
                            last_check = time.monotonic()
                            if target_in not in mido.get_input_names():
                                self._close_out()
                                self.status_changed.emit(
                                    False, "DDJ-FLX4 unplugged. It will reconnect by itself.")
                                break
                        time.sleep(0.003)
            except Exception as e:
                # Never let this thread die: the app must survive an unplug and reconnect.
                print(f"MIDI listener error: {e}")
                self.status_changed.emit(False, f"MIDI problem: {e}. Retrying…")
                self._sleep(2.0)
            finally:
                self._close_out()

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while self.running and time.monotonic() < end:
            time.sleep(0.05)

    def _close_out(self):
        # Clear the reference first: the UI thread sends LEDs through this port and must not
        # touch one that is being closed, which is a native crash rather than an exception.
        port, self.outport = self.outport, None
        if port:
            try:
                port.close()
            except Exception as e:
                print(f"Error closing MIDI output: {e}")

    def parse_message(self, msg):
        """Returns (control_id, raw_code, value) or (None, '', 0) for messages to ignore."""
        if msg.type == "control_change":
            raw_code = f"CC_{msg.channel}_{msg.control}"
            val = msg.value
            # 14-bit controls send a coarse (MSB) and a fine (LSB) half. Which half a control
            # resends while you move it varies, so recalculate on whichever one arrives and
            # emit only when the 0-127 result actually changes (no double events).
            coarse = fine = None
            if raw_code in DUAL_CC_PAIRS:
                coarse, fine = raw_code, DUAL_CC_PAIRS[raw_code]
                self.cc_coarse_values[coarse] = msg.value
            elif raw_code in FINE_TO_COARSE:
                coarse, fine = FINE_TO_COARSE[raw_code], raw_code
                self.cc_fine_values[fine] = msg.value
            if coarse:
                if coarse not in self.cc_coarse_values:
                    return None, "", 0  # fine half first: the position isn't known yet
                if fine in self.cc_fine_values:
                    full = 128 * self.cc_coarse_values[coarse] + self.cc_fine_values[fine]
                    val = round(full / 16383 * 127)
                else:
                    val = self.cc_coarse_values[coarse]  # 7-bit until a fine half shows up
                raw_code = coarse
                if self.cc_last_sent.get(coarse) == val:
                    return None, "", 0
                self.cc_last_sent[coarse] = val
        elif msg.type in ("note_on", "note_off"):
            raw_code = f"NOTE_{msg.channel}_{msg.note}"
            val = 0 if msg.type == "note_off" else msg.velocity
        else:
            return None, "", 0
        return control_for_code(raw_code), raw_code, val

    def send_led(self, raw_code: str, value: int = 127):
        """Lights an LED: note_on/CC back to the controller on the control's own code."""
        if not self.outport:
            return
        try:
            kind, channel, num = raw_code.split("_")
            value = max(0, min(127, int(value)))
            if kind == "NOTE":
                msg = mido.Message("note_on", channel=int(channel), note=int(num), velocity=value)
            elif kind == "CC":
                msg = mido.Message("control_change", channel=int(channel), control=int(num), value=value)
            else:
                return
            self.outport.send(msg)
        except Exception as e:
            print(f"Error sending LED message ({raw_code}): {e}")

    def play_startup_light_show(self):
        for code in STARTUP_LIGHTS:
            self.send_led(code, 127)
            time.sleep(0.03)
        time.sleep(0.15)
        for code in STARTUP_LIGHTS:
            self.send_led(code, 0)

    def stop(self):
        # The poll loop notices within a few ms; closing the port from this thread could crash rtmidi.
        self.running = False
        self.wait(3000)

    def resume(self):
        """Opens the port again after stop(), for when DJ software has finished with it."""
        if self.isRunning():
            return False
        self.running = True
        self.start()
        return True


if __name__ == "__main__":
    t = MidiListenerThread.__new__(MidiListenerThread)
    t.cc_coarse_values, t.cc_fine_values, t.cc_last_sent = {}, {}, {}
    cc = lambda c, n, v: mido.Message("control_change", channel=c, control=n, value=v)
    assert t.parse_message(cc(0, 51, 127)) == (None, "", 0), "fine half alone: position unknown"
    assert t.parse_message(cc(0, 19, 127)) == ("FADER_L", "CC_0_19", 127), "coarse half must emit"
    assert t.parse_message(cc(0, 51, 127)) == (None, "", 0), "unchanged value must not repeat"
    assert t.parse_message(cc(0, 51, 0)) == ("FADER_L", "CC_0_19", 126), "fine half must emit too"
    assert t.parse_message(cc(0, 19, 0)) == ("FADER_L", "CC_0_19", 0)
    # A fader that only resends its coarse half still moves through the whole range.
    sweep = [t.parse_message(cc(1, 0, x))[2] for x in (0, 32, 64, 96, 127)]
    assert sweep == [0, 32, 64, 96, 127], sweep
    assert t.parse_message(cc(6, 64, 1)) == ("BROWSER_ENCODER", "CC_6_64", 1)
    assert t.parse_message(mido.Message("note_on", channel=7, note=48, velocity=127)) == ("PAD_L_1", "NOTE_7_48", 127)
    print("midi_listener self-check OK")
