# SPDX-License-Identifier: GPL-3.0-or-later
# make_profile_prompt.py
# Writes PROFILE_PROMPT.md: the prompt you paste into an AI chat, together with the name of an
# app, to get a ready-made Spinin profile back.
#
# It is generated rather than written by hand so the control and action ids always match the
# app. Re-run it after adding actions:  python make_profile_prompt.py

import os
import re
from collections import defaultdict

import actions as catalog
import userinput
from controls import (CONTROLS, CONTROL_NAMES, CONTROL_TO_MIDI, RELATIVE_CONTROLS,
                      ALL_PAD_IDS, PAD_MODES)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "PROFILE_PROMPT.md")


def control_kind(cid):
    if cid in RELATIVE_CONTROLS:
        return "turn"
    return "range" if CONTROL_TO_MIDI[cid].startswith("CC") else "press"


def control_table():
    by_kind = defaultdict(list)
    for cid, _, name, _ in CONTROLS:
        if cid in ALL_PAD_IDS:
            continue  # pads are listed separately below: they need a bank suffix
        by_kind[control_kind(cid)].append(f"`{cid}` ({name})")
    lines = []
    for kind, heading in (("press", "Buttons — take a **press** action"),
                          ("range", "Faders and knobs — take a **range** action"),
                          ("turn", "Jog wheels and the browse encoder — take a **turn** action")):
        lines.append(f"\n### {heading}\n")
        lines.append(", ".join(by_kind[kind]))
    lines.append("\n### Pads — take a **press** action, four banks each\n")
    lines.append(
        "Each deck has 8 pads: `PAD_L_1`-`PAD_L_8` on deck 1, `PAD_R_1`-`PAD_R_8` on deck 2. "
        "Each pad has **4 separate banks**, one per mode button above the pads: "
        + ", ".join(f"`{m}`" for m in PAD_MODES) + ". A pad's `mappings` key is the pad id "
        "plus `@` and the bank, for example `PAD_L_3@HOT_CUE` or `PAD_R_6@SAMPLER`. Use "
        "`HOT_CUE` for the one thing APP NAME needs pads for most, since that is the bank "
        "active when the controller is switched on; use the other banks for secondary sets "
        "of commands if there are more than 8 worth mapping."
    )
    return "\n".join(lines)


def action_table(kind):
    by_category = defaultdict(list)
    for action in catalog.for_kind(kind):
        by_category[action["category"]].append(action)
    lines = []
    for category, items in by_category.items():
        lines.append(f"\n**{category}**\n")
        for a in items:
            extra = ""
            if a["backend"] == "custom":
                needs = {"custom.app": "needs `command`", "custom.keys": "needs `keys`",
                         "custom.command": "needs `command`",
                         "turn_keys": "needs `keys_cw` and `keys_ccw`",
                         "device": "needs `device_name`"}
                extra = f" — {needs.get(a['payload'], needs.get(a['id'], ''))}"
            lines.append(f"- `{a['id']}` — {a['name']} ({a['hint']}){extra}")
    return "\n".join(lines)


def key_names():
    """The named keys, minus the modifiers and f-keys already described in the sentence."""
    modifiers = {"ctrl", "alt", "shift", "win", "rctrl", "ralt", "rshift"}
    specials = sorted(k for k in userinput.KEYS
                      if len(k) > 1 and k not in modifiers and not re.fullmatch(r"f\d+", k))
    punctuation = sorted(k for k in userinput.KEYS if len(k) == 1 and not k.isalnum())
    return ("a-z, 0-9", "f1-f24",
            ", ".join(f"`{s}`" for s in specials + punctuation))


PROMPT = """# Prompt: make a Spinin profile for any app

Paste everything below into an AI chat, replacing APP NAME with the program you want
(for example Photoshop, DaVinci Resolve, Ableton Live, Excel). Save the reply as a `.json`
file, then load it with **⋯ → Import profiles…** in Spinin.

---

You are writing a profile file for Spinin, a Windows app that turns a Pioneer DDJ-FLX4
DJ controller into a control surface for ordinary software. Produce a profile for: **APP NAME**

Return **only** a JSON file, no explanation around it.

## What a profile does

Each control on the DJ controller is given one action. When the app named in the profile id is
the active window, Spinin uses that profile.

## File format

```json
{{
  "flx4_mapper_profiles": 1,
  "profiles": {{
    "app.exe": {{
      "name": "Readable name",
      "mappings": {{
        "CONTROL_ID": {{ "type": "action", "id": "ACTION_ID" }}
      }},
      "led_settings": {{
        "CONTROL_ID": {{ "mode": "on_press", "value": 127 }}
      }}
    }}
  }}
}}
```

- The profile id must be the program's **process name in lower case**, ending in `.exe`
  (`photoshop.exe`, `resolve.exe`, `ableton live 11 suite.exe`). This is how the app is
  recognised, so get it right; it is what Task Manager shows under Details.
- `led_settings` is optional. `mode` is one of `on_press`, `toggle`, `flash`, `always_on`,
  `off`, and only works on buttons and pads.

## Rules

1. Use only the control ids and action ids listed below. Never invent one.
2. Match the kind: **press** actions on buttons and pads, **range** actions on faders and
   knobs, **turn** actions on jog wheels and the encoder.
3. Most actions need nothing else. These need extra fields in the same object:
   - `custom.keys` — `"keys": ["ctrl", "s"]`, the shortcut to press.
   - `turn.custom` — `"keys_cw"` and `"keys_ccw"`, one shortcut per direction.
   - `custom.app` — `"command": "notepad"` or a full path to an .exe.
   - `custom.command` — `"command": "..."` a command line.
   - `audio.setdevice` — `"device_name": "Speakers (Realtek(R) Audio)"`.
4. **`custom.keys` is the one you will use most**: give each pad a real keyboard shortcut of
   APP NAME. Prefer the app's genuine defaults over guesses, and skip anything you are unsure
   of rather than inventing it.
5. Key names for `keys`, `keys_cw` and `keys_ccw`: modifiers `ctrl`, `alt`, `shift`, `win`;
   letters and digits {letters}; function keys {fkeys}; and {specials}.
   Write a combination as a list in press order, modifiers first: `["ctrl", "shift", "s"]`.
6. Optional `options` on turn and range actions:
   - `"sensitivity"`: 1-30. For a jog this is wheel ticks per step; 2-3 feels natural.
   - `"acceleration"`: 0-10, turn actions only. A fast spin then travels further. 0 is off.
   - `"invert"`: true, to swap the two directions or flip a fader.
7. A pad's `mappings` key needs its bank: `PAD_L_1@HOT_CUE`, never bare `PAD_L_1`. A
   `led_settings` key for a pad stays **without** a bank (`PAD_L_1`) — lighting isn't split
   by bank, only the action is.
8. Leave a control out rather than filling every one. A profile of 10-20 well-chosen controls
   beats one that maps everything, and it's fine to only use the `HOT_CUE` bank if the app
   doesn't need more than 8 pad commands.

## Sensible layout

The pads are the fastest thing to hit, so put the most-used commands there. The jog wheels
suit anything continuous — scrubbing a timeline, zooming, stepping through frames or history.
The faders and knobs suit volume. Keep Play/Cue for transport-like actions where the app has
them. Give a short profile `name` that a person would recognise.

## Control ids
{controls}

## Action ids

### press — for buttons and pads
{press}

### range — for faders and knobs
{range}

### turn — for jog wheels and the browse encoder
{turn}

## Example

```json
{{
  "flx4_mapper_profiles": 1,
  "profiles": {{
    "photoshop.exe": {{
      "name": "Photoshop",
      "mappings": {{
        "PAD_L_1@HOT_CUE": {{ "type": "action", "id": "custom.keys", "keys": ["b"] }},
        "PAD_L_2@HOT_CUE": {{ "type": "action", "id": "custom.keys", "keys": ["e"] }},
        "PAD_L_3@HOT_CUE": {{ "type": "action", "id": "custom.keys", "keys": ["ctrl", "z"] }},
        "PAD_L_4@HOT_CUE": {{ "type": "action", "id": "custom.keys", "keys": ["ctrl", "s"] }},
        "PAD_L_1@SAMPLER": {{ "type": "action", "id": "custom.keys", "keys": ["shift", "b"] }},
        "JOG_ROTATE_L": {{ "type": "action", "id": "turn.brush",
                           "options": {{ "sensitivity": 3, "acceleration": 4 }} }},
        "JOG_ROTATE_R": {{ "type": "action", "id": "turn.zoom",
                           "options": {{ "sensitivity": 2 }} }},
        "FADER_L": {{ "type": "action", "id": "range.volume" }},
        "PLAY_L": {{ "type": "action", "id": "custom.keys", "keys": ["ctrl", "0"] }}
      }},
      "led_settings": {{
        "PAD_L_1": {{ "mode": "toggle", "value": 127 }}
      }}
    }}
  }}
}}
```
"""


def build():
    letters, fkeys, specials = key_names()
    return PROMPT.format(controls=control_table(), press=action_table("press"),
                         range=action_table("range"), turn=action_table("turn"),
                         letters=letters, fkeys=fkeys, specials=specials)


if __name__ == "__main__":
    text = build()
    # Every id the prompt hands out must be one the app will accept.
    for action_id in set(re.findall(r"`([a-z]+\.[a-z]+)`", text)):
        if action_id.endswith(".exe"):  # profile ids in the examples, not actions
            continue
        assert action_id in catalog.BY_ID, f"prompt names an action that doesn't exist: {action_id}"
    for cid in set(re.findall(r"`([A-Z][A-Z0-9_]+)`", text)):
        if cid in PAD_MODES:  # a bank name mentioned on its own, not a control id
            continue
        assert cid in CONTROL_NAMES, f"prompt names a control that doesn't exist: {cid}"
    for compound in set(re.findall(r"`(PAD_[LR]_\d@[A-Z0-9_]+)`", text)):
        pad_id, mode = compound.split("@")
        assert pad_id in ALL_PAD_IDS and mode in PAD_MODES, f"bad pad bank example: {compound}"
    # The worked example has to survive the importer, or the prompt is teaching the wrong shape.
    import json
    import tempfile
    import profile_io
    example = text.split("## Example")[1].split("```json")[1].split("```")[0]
    sample = os.path.join(tempfile.gettempdir(), "flx4-prompt-example.json")
    with open(sample, "w", encoding="utf-8") as f:
        f.write(example)
    loaded, problems = profile_io.read_file(sample)
    assert loaded and not problems, (loaded, problems)
    assert len(loaded["photoshop.exe"]["mappings"]) == json.loads(example)["profiles"][
        "photoshop.exe"]["mappings"].__len__(), "the importer dropped part of the example"
    os.remove(sample)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {OUT} ({len(text.splitlines())} lines, {len(CONTROLS)} controls, "
          f"{len(catalog.ACTIONS)} actions)")
