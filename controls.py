# SPDX-License-Identifier: GPL-3.0-or-later
# controls.py
# Single source of truth for every DDJ-FLX4 control: MIDI code, display name and
# hotspot on ddj-flx4.webp. MIDI codes come from the annotated Presentation1.pptx.
#
# Hotspot coordinates are in SOURCE IMAGE PIXELS (ddj-flx4.webp is 1320x1320):
#   ("circle", cx, cy, r)          knobs, round buttons
#   ("ring",   cx, cy, r_out, r_in) jog wheel outer ring
#   ("rect",   cx, cy, w, h)        pads, square buttons, faders
# ponytail: hand-calibrated against the image; nudge numbers here if a hotspot looks off
# (tick "Show all hotspots" in the app to check them).

DECK_R_DX = 784  # right deck is the left deck shifted this many pixels

# Controller body inside the transparent webp (x0, y0, x1, y1) -> the canvas crops to this.
IMAGE_CROP = (50, 312, 1270, 1008)


def _deck(side, ch, pad_ch, dx):
    s, n = side, "Deck 1" if side == "L" else "Deck 2"
    pads = []
    for i in range(8):
        row, col = divmod(i, 4)
        pads.append((f"PAD_{s}_{i + 1}", f"NOTE_{pad_ch}_{48 + i}", f"{n} Pad {i + 1}",
                     ("rect", 185 + col * 55.5 + dx, 880 + row * 56, 46, 46)))
    return [
        (f"IN_{s}", f"NOTE_{ch}_16", f"{n} Loop In", ("circle", 116 + dx, 401, 20)),
        (f"OUT_{s}", f"NOTE_{ch}_17", f"{n} Loop Out", ("circle", 180 + dx, 401, 20)),
        (f"BEAT_EXIT_{s}", f"NOTE_{ch}_77", f"{n} 4 Beat / Exit", ("circle", 242 + dx, 401, 14)),
        (f"LOOP_HALF_{s}", f"NOTE_{ch}_81", f"{n} Cue/Loop Call ◄", ("circle", 306 + dx, 401, 12)),
        (f"LOOP_DOUBLE_{s}", f"NOTE_{ch}_83", f"{n} Cue/Loop Call ►", ("circle", 358 + dx, 401, 12)),
        (f"SYNC_{s}", f"NOTE_{ch}_88", f"{n} Beat Sync", ("circle", 420 + dx, 401, 16)),
        (f"SHIFT_{s}", f"NOTE_{ch}_63", f"{n} Shift", ("rect", 116 + dx, 786, 24, 22)),
        (f"CUE_{s}", f"NOTE_{ch}_12", f"{n} Cue", ("circle", 116 + dx, 853, 31)),
        (f"PLAY_{s}", f"NOTE_{ch}_11", f"{n} Play / Pause", ("circle", 116 + dx, 923, 31)),
        (f"HOT_CUE_{s}", f"NOTE_{ch}_27", f"{n} Hot Cue mode", ("rect", 185 + dx, 824, 44, 15)),
        (f"PAD_FX1_{s}", f"NOTE_{ch}_30", f"{n} Pad FX 1 mode", ("rect", 240.5 + dx, 824, 44, 15)),
        (f"BEAT_JUMP_{s}", f"NOTE_{ch}_32", f"{n} Beat Jump mode", ("rect", 296 + dx, 824, 44, 15)),
        (f"SAMPLER_{s}", f"NOTE_{ch}_34", f"{n} Sampler mode", ("rect", 351.5 + dx, 824, 44, 15)),
        *pads,
        (f"TEMPO_{s}", f"CC_{ch}_0", f"{n} Tempo", ("rect", 419 + dx, 858, 44, 164)),
        (f"JOG_TOUCH_{s}", f"NOTE_{ch}_54", f"{n} Jog Touch", ("circle", 267 + dx, 612, 62)),
        (f"JOG_SCRATCH_{s}", f"CC_{ch}_34", f"{n} Jog Turn while Touched", ("circle", 267 + dx, 612, 140)),
        (f"JOG_ROTATE_{s}", f"CC_{ch}_33", f"{n} Jog Ring Turn", ("ring", 267 + dx, 612, 176, 140)),
    ]


CONTROLS = _deck("L", 0, 7, 0) + _deck("R", 1, 9, DECK_R_DX) + [
    # Browser
    ("BROWSER_LOAD_L", "NOTE_6_70", "Load Deck 1", ("rect", 579, 376, 38, 18)),
    ("BROWSER_BACK", "NOTE_6_65", "Browse Encoder Push", ("circle", 660, 368, 13)),
    ("BROWSER_ENCODER", "CC_6_64", "Browse Encoder Turn", ("ring", 660, 368, 22, 13)),
    ("BROWSER_LOAD_R", "NOTE_6_71", "Load Deck 2", ("rect", 741, 376, 38, 18)),
    # Channel strips
    ("KNOB_TRIM_L", "CC_0_4", "Ch 1 Trim", ("circle", 610, 428, 17)),
    ("KNOB_EQ_HI_L", "CC_0_7", "Ch 1 EQ Hi", ("circle", 610, 489, 22)),
    ("KNOB_EQ_MID_L", "CC_0_11", "Ch 1 EQ Mid", ("circle", 610, 550, 22)),
    ("KNOB_EQ_LOW_L", "CC_0_15", "Ch 1 EQ Low", ("circle", 610, 611, 22)),
    ("KNOB_CFX_L", "CC_6_23", "Ch 1 Color FX", ("circle", 610, 672, 22)),
    ("CH_CUE_L", "NOTE_0_84", "Ch 1 Headphone Cue", ("rect", 610, 734, 34, 15)),
    ("FADER_L", "CC_0_19", "Ch 1 Fader", ("rect", 610, 834, 40, 110)),
    ("KNOB_TRIM_R", "CC_1_4", "Ch 2 Trim", ("circle", 710, 428, 17)),
    ("KNOB_EQ_HI_R", "CC_1_7", "Ch 2 EQ Hi", ("circle", 710, 489, 22)),
    ("KNOB_EQ_MID_R", "CC_1_11", "Ch 2 EQ Mid", ("circle", 710, 550, 22)),
    ("KNOB_EQ_LOW_R", "CC_1_15", "Ch 2 EQ Low", ("circle", 710, 611, 22)),
    ("KNOB_CFX_R", "CC_6_24", "Ch 2 Color FX", ("circle", 710, 672, 22)),
    ("CH_CUE_R", "NOTE_1_84", "Ch 2 Headphone Cue", ("rect", 710, 734, 34, 15)),
    ("FADER_R", "CC_1_19", "Ch 2 Fader", ("rect", 710, 834, 40, 110)),
    ("CROSSFADER", "CC_6_31", "Crossfader", ("rect", 660, 953, 118, 38)),
    # Left mixer column
    ("KNOB_MIC_LEVEL", "CC_6_5", "Mic Level", ("circle", 517, 549, 17)),
    ("SMART_CFX", "NOTE_6_0", "Smart CFX", ("circle", 517, 672, 14)),
    ("KNOB_HEADPHONES_MIX", "CC_6_12", "Headphone Mix", ("circle", 517, 745, 17)),
    ("KNOB_HEADPHONES_LEVEL", "CC_6_13", "Headphone Level", ("circle", 517, 812, 17)),
    ("SMART_FADER", "NOTE_6_1", "Smart Fader", ("circle", 517, 883, 14)),
    # Master / Beat FX column
    ("KNOB_MASTER_LEVEL", "CC_6_8", "Master Level", ("circle", 802, 428, 22)),
    ("MASTER_CUE", "NOTE_6_99", "Master Cue", ("rect", 802, 489, 34, 15)),
    # The Beat FX channel switch has three positions. Two of them send a note of their own;
    # the third sends both at once, so it gets a virtual code and is worked out in the app.
    ("FX_SWITCH_1", "NOTE_4_16", "Beat FX Switch at 1", ("rect", 790, 610, 14, 18)),
    ("FX_SWITCH_2", "NOTE_5_17", "Beat FX Switch at 2", ("rect", 804, 610, 14, 18)),
    ("FX_SWITCH_BOTH", "VIRTUAL_FX_BOTH", "Beat FX Switch at 1&2", ("rect", 818, 610, 14, 18)),
    ("FX_SELECT", "NOTE_4_99", "Beat FX Select", ("rect", 802, 672, 38, 17)),
    ("BEAT_LEFT", "NOTE_4_74", "Beat ◄", ("rect", 784, 734, 27, 16)),
    ("BEAT_RIGHT", "NOTE_4_75", "Beat ►", ("rect", 820, 734, 27, 16)),
    ("KNOB_BEAT_FX_LEVEL", "CC_4_2", "Beat FX Level / Depth", ("circle", 802, 811, 22)),
    ("BEAT_FX_ON_OFF", "NOTE_4_71", "Beat FX On / Off", ("circle", 802, 883, 17)),
]

MIDI_TO_CONTROL = {code: cid for cid, code, _, _ in CONTROLS}
CONTROL_TO_MIDI = {cid: code for cid, code, _, _ in CONTROLS}
CONTROL_NAMES = {cid: name for cid, _, name, _ in CONTROLS}
HOTSPOTS = {cid: shape for cid, _, _, shape in CONTROLS}

# The performance pads send a different note block for each pad mode (Hot Cue, Pad FX, Beat
# Jump, Sampler and the shifted modes), all on the deck's own pad channel. Rather than listing
# every block, any note on a pad channel is taken as a pad, so a mapping works whatever mode
# the pads happen to be in. Note 48 is pad 1 in Hot Cue mode, 49 is pad 2, and each other mode
# starts its own run of eight.
# Channels 8 and 10 are included because the shifted pad modes (Keyboard, Pad FX 2, Beat Loop,
# Key Shift) send on the next channel up on Pioneer gear. ponytail: if a pad ever lights up the
# wrong square in the app, its channel belongs somewhere else in this table.
PAD_CHANNELS = {7: "L", 8: "L", 9: "R", 10: "R"}


def control_for_code(raw_code):
    """The control a MIDI code belongs to, including pads in any pad mode."""
    known = MIDI_TO_CONTROL.get(raw_code)
    if known:
        return known
    parts = raw_code.split("_")
    if len(parts) == 3 and parts[0] == "NOTE":
        channel, note = int(parts[1]), int(parts[2])
        if channel in PAD_CHANNELS:
            return f"PAD_{PAD_CHANNELS[channel]}_{note % 8 + 1}"
    return raw_code

# Controls that send 0 at the end that looks "full" on the hardware, so the app draws their
# position upside down unless it is flipped here.
# ponytail: add a control id here if its reading runs backwards on your unit
DISPLAY_INVERTED = {"TEMPO_L", "TEMPO_R"}

# The Beat FX switch: which note is on tells you which position it is in.
FX_SWITCH_NOTES = {"NOTE_4_16": "one", "NOTE_5_17": "two"}
FX_SWITCH_POSITIONS = {("one",): "FX_SWITCH_1", ("two",): "FX_SWITCH_2",
                       ("one", "two"): "FX_SWITCH_BOTH"}

# Controls that send a relative +/- tick instead of an absolute position.
RELATIVE_CONTROLS = {"JOG_ROTATE_L", "JOG_ROTATE_R", "JOG_SCRATCH_L", "JOG_SCRATCH_R", "BROWSER_ENCODER"}

# Pad banks: each of the four mode buttons above the pads switches what the 8 pads underneath
# do, so one physical pad can hold up to 4 separate mappings (32 per deck across both decks).
# The button's own control id doubles as the bank's key; MODE_LABELS is just for display.
PAD_MODES = ["HOT_CUE", "PAD_FX1", "BEAT_JUMP", "SAMPLER"]
DEFAULT_PAD_MODE = "HOT_CUE"
MODE_LABELS = {"HOT_CUE": "Hot Cue", "PAD_FX1": "Pad FX 1", "BEAT_JUMP": "Beat Jump",
              "SAMPLER": "Sampler"}
# mode-button control id -> (deck, mode key)
PAD_MODE_BUTTONS = {f"{mode}_{deck}": (deck, mode) for mode in PAD_MODES for deck in "LR"}
ALL_PAD_IDS = {f"PAD_{deck}_{i}" for deck in "LR" for i in range(1, 9)}


def pad_deck(cid):
    """'L' or 'R' for a pad control id, else None."""
    return cid.split("_")[1] if cid in ALL_PAD_IDS else None


def pad_mapping_key(cid, mode):
    """The key mappings/led_settings are actually stored under for a pad in a given bank.

    Every other control uses its own id unchanged; only pads are split into banks, because
    only pads have a physical mode switch changing what they send.
    """
    return f"{cid}@{mode}" if cid in ALL_PAD_IDS else cid

if __name__ == "__main__":
    assert len(MIDI_TO_CONTROL) == len(CONTROLS), "duplicate MIDI code"
    assert len(CONTROL_TO_MIDI) == len(CONTROLS), "duplicate control id"
    assert control_for_code("NOTE_0_11") == "PLAY_L"
    # Pads keep their identity in every pad mode: Hot Cue, and the other note blocks.
    for block in (0, 8, 16, 24, 32, 40, 48, 56, 64, 96, 112):
        assert control_for_code(f"NOTE_7_{block}") == "PAD_L_1", block
        assert control_for_code(f"NOTE_9_{block + 6}") == "PAD_R_7", block
    assert control_for_code("NOTE_7_55") == "PAD_L_8" and control_for_code("NOTE_9_48") == "PAD_R_1"
    assert control_for_code("CC_6_99") == "CC_6_99", "an unknown code stays as itself"
    print(f"{len(CONTROLS)} controls OK, pads recognised in every pad mode")
