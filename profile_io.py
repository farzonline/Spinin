# SPDX-License-Identifier: GPL-3.0-or-later
# profile_io.py
# Shares profiles between apps, machines and people as .flx4.json files.
#
# An imported file comes from somewhere else, so nothing in it is trusted: every profile,
# mapping and option is checked against the action library before it is let in, and anything
# unknown is dropped. Profiles can contain "Run a command" and "Open an app" actions, so
# `risky_entries` lists those for the user to see before they accept the file.

import json
import os
import re
from datetime import date

import actions as catalog

FORMAT_KEY = "flx4_mapper_profiles"
FORMAT_VERSION = 1
MAX_FILE_BYTES = 2_000_000
MAX_PROFILES = 100
SAFE_ID = re.compile(r"^[a-z0-9._+-]{1,64}$")
LEGACY_TYPES = {"launch_app", "keystroke", "system_action", "script"}
RISKY_ACTIONS = {"custom.command", "custom.app"}


def export_data(profiles, source="Spinin"):
    return {FORMAT_KEY: FORMAT_VERSION, "exported": date.today().isoformat(),
            "source": source, "profiles": profiles}


def write_file(path, profiles):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_data(profiles), f, indent=2)
    return path


def _clean_mapping(mapping):
    """Returns a mapping stripped to known fields, or None if it isn't usable."""
    if not isinstance(mapping, dict):
        return None
    m_type = mapping.get("type")
    if m_type in LEGACY_TYPES:
        return mapping  # the app already translates these
    if m_type != "action":
        return None
    action = catalog.BY_ID.get(mapping.get("id"))
    if not action:
        return None  # an action this version doesn't have
    clean = {"type": "action", "id": action["id"]}
    for field in ("command", "device_id", "device_name"):
        if isinstance(mapping.get(field), str):
            clean[field] = mapping[field][:500]
    for field in ("keys", "keys_cw", "keys_ccw"):
        value = mapping.get(field)
        if isinstance(value, list) and all(isinstance(k, str) for k in value):
            clean[field] = value[:8]
    options = mapping.get("options")
    if isinstance(options, dict):
        kept = {}
        for key in action["options"]:
            if key == "invert" and options.get("invert"):
                kept["invert"] = True
            elif key in ("sensitivity", "acceleration") and isinstance(options.get(key), int):
                kept[key] = max(0, min(30, options[key]))
        if kept:
            clean["options"] = kept
    return clean


def read_file(path):
    """Loads and checks a profile file. Returns (profiles, problems)."""
    problems = []
    if os.path.getsize(path) > MAX_FILE_BYTES:
        return {}, ["That file is too big to be a profile file."]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {}, [f"This isn't a readable profile file: {e}"]
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        return {}, ["This file doesn't contain any Spinin profiles."]
    if FORMAT_KEY not in data:
        problems.append("The file doesn't say it came from Spinin; importing anyway.")

    profiles, dropped = {}, 0
    for profile_id, profile in list(data["profiles"].items())[:MAX_PROFILES]:
        if not isinstance(profile_id, str) or not SAFE_ID.match(profile_id.lower()):
            problems.append(f"Skipped a profile with an odd name: {str(profile_id)[:40]}")
            continue
        if not isinstance(profile, dict):
            continue
        mappings = {}
        for cid, mapping in (profile.get("mappings") or {}).items():
            clean = _clean_mapping(mapping) if isinstance(cid, str) else None
            if clean:
                mappings[cid] = clean
            else:
                dropped += 1
        leds = {}
        for cid, led in (profile.get("led_settings") or {}).items():
            if isinstance(led, dict) and isinstance(led.get("mode"), str):
                leds[cid] = {"mode": led["mode"], "value": int(led.get("value", 127)) % 128}
        name = profile.get("name") if isinstance(profile.get("name"), str) else profile_id
        profiles[profile_id.lower()] = {"name": name[:60], "mappings": mappings,
                                        "led_settings": leds}
    if dropped:
        problems.append(f"{dropped} action(s) were left out because this version doesn't have them.")
    if not profiles:
        problems.append("Nothing in the file could be imported.")
    return profiles, problems


def risky_entries(profiles):
    """Commands and apps the file would run, so they can be shown before importing."""
    risky = []
    for profile in profiles.values():
        for mapping in profile.get("mappings", {}).values():
            is_legacy = mapping.get("type") in ("script", "launch_app")
            if mapping.get("id") in RISKY_ACTIONS or is_legacy:
                command = mapping.get("command", "").strip()
                if command:
                    risky.append(f"{profile['name']}: {command}")
    return risky


def count_actions(profiles):
    return sum(len(p.get("mappings", {})) for p in profiles.values())


if __name__ == "__main__":
    import tempfile
    good = {"vlc.exe": {"name": "VLC", "led_settings": {},
                        "mappings": {"PAD_L_1": {"type": "action", "id": "media.playpause"},
                                     "PAD_L_2": {"type": "action", "id": "custom.command",
                                                 "command": "calc.exe"}}}}
    path = os.path.join(tempfile.gettempdir(), "flx4-selfcheck.json")
    write_file(path, good)
    loaded, problems = read_file(path)
    assert loaded["vlc.exe"]["mappings"]["PAD_L_1"]["id"] == "media.playpause", loaded
    assert not problems, problems
    assert risky_entries(loaded) == ["VLC: calc.exe"], risky_entries(loaded)

    # Anything unknown or malformed is dropped rather than trusted.
    nasty = {FORMAT_KEY: 1, "profiles": {
        "ok.exe": {"name": "Fine", "mappings": {
            "PAD_L_1": {"type": "action", "id": "no.such.action"},
            "PAD_L_2": {"type": "action", "id": "win.start", "options": {"sensitivity": 9999},
                        "surprise": "ignored"},
            "PAD_L_3": "not even a mapping"}},
        "../../evil": {"name": "Escape", "mappings": {}},
        "big.exe": {"name": "x" * 500, "mappings": {}}}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nasty, f)
    loaded, problems = read_file(path)
    assert "../../evil" not in loaded and "ok.exe" in loaded
    assert list(loaded["ok.exe"]["mappings"]) == ["PAD_L_2"], loaded["ok.exe"]["mappings"]
    assert "surprise" not in loaded["ok.exe"]["mappings"]["PAD_L_2"]
    assert "options" not in loaded["ok.exe"]["mappings"]["PAD_L_2"], "win.start takes no options"
    assert len(loaded["big.exe"]["name"]) == 60
    assert any("left out" in p for p in problems), problems

    with open(path, "w", encoding="utf-8") as f:
        f.write("this is not json")
    assert read_file(path) == ({}, ["This isn't a readable profile file: " +
                                    read_file(path)[1][0].split(": ", 1)[1]])
    os.remove(path)
    print("profile_io self-check OK")
