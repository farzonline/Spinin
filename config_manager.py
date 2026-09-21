# SPDX-License-Identifier: GPL-3.0-or-later
# config_manager.py
import os
import json
import copy

import branding
from controls import ALL_PAD_IDS, DEFAULT_PAD_MODE

# Never the current working directory: launching from elsewhere used to silently create a
# fresh, empty mappings.json there. Beside the source from a checkout, in %APPDATA% once
# installed, since an installed app cannot write to Program Files.
CONFIG_FILE = os.path.join(branding.data_dir(), "mappings.json")

DEFAULT_MAPPINGS = {
    "profiles": {
        "global": {
            "name": "Global Profile",
            "mappings": {
                "PAD_L_1@HOT_CUE": {"type": "launch_app", "command": "notepad"},
                "PAD_L_2@HOT_CUE": {"type": "launch_app", "command": "chrome"},
                "FADER_L": {"type": "system_action", "action": "volume_control"},
                "FADER_R": {"type": "system_action", "action": "volume_control"},
                "CROSSFADER": {"type": "system_action", "action": "volume_control"},
                "PLAY_L": {"type": "system_action", "action": "media_play_pause"},
                "CUE_L": {"type": "system_action", "action": "media_mute"}
            }
        },
        "photoshop.exe": {
            "name": "Adobe Photoshop",
            "mappings": {
                "PAD_L_1@HOT_CUE": {"type": "keystroke", "keys": ["b"]},
                "PAD_L_2@HOT_CUE": {"type": "keystroke", "keys": ["e"]},
                "PAD_L_3@HOT_CUE": {"type": "keystroke", "keys": ["ctrl", "z"]},
                "PAD_L_4@HOT_CUE": {"type": "keystroke", "keys": ["ctrl", "alt", "z"]}
            }
        },
        "vlc.exe": {
            "name": "VLC Media Player",
            "mappings": {
                "PAD_L_1@HOT_CUE": {"type": "keystroke", "keys": ["s"]},
                "PAD_L_2@HOT_CUE": {"type": "keystroke", "keys": ["f"]},
                "PLAY_L": {"type": "system_action", "action": "media_play_pause"}
            }
        }
    }
}

# Actions that have been merged away since; mappings pointing at them are re-pointed on load.
# Without this a button keeps its label and quietly does nothing, which is worse than an error.
RETIRED_ACTIONS = {
    "pow.lock": "win.lock",  # there were two Lock PC actions; the Win+L one never worked
}

# Controls that have been renamed since; old saved files are updated on load.
RENAMED_CONTROLS = {
    "IN_4BEAT_L": "IN_L", "IN_4BEAT_R": "IN_R",
    "FX_SLIDER_1": "FX_SWITCH_1", "FX_SLIDER_2": "FX_SWITCH_2",
    "KNOB_FILTER_L": "KNOB_CFX_L", "KNOB_FILTER_R": "KNOB_CFX_R",
}


class ConfigManager:
    def __init__(self, filepath=None):
        # Resolved here rather than as the default value, so tests can point CONFIG_FILE at
        # an isolated file before construction without it being baked in at import time.
        self.filepath = filepath or CONFIG_FILE
        self.config = copy.deepcopy(DEFAULT_MAPPINGS)
        self.load()

    def load(self):
        """Loads configuration from JSON file. Creates one if it doesn't exist."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                # Don't overwrite the broken file on next save: keep a copy the user can recover.
                print(f"Error loading config file: {e}. Reverting to defaults.")
                os.replace(self.filepath, self.filepath + ".broken")
                self.config = copy.deepcopy(DEFAULT_MAPPINGS)
            self.migrate()
        else:
            self.save()

    def migrate(self):
        """Renames controls that changed name, so older mappings keep working."""
        changed = False
        for profile in self.config.get("profiles", {}).values():
            for section in ("mappings", "led_settings"):
                entries = profile.get(section, {})
                for old, new in RENAMED_CONTROLS.items():
                    if old in entries:
                        entries.setdefault(new, entries.pop(old))
                        changed = True
            # Pads gained per-mode banks; a plain pad id from before was always the bank the
            # hardware defaults to (Hot Cue), since that was the only bank the app could see.
            mappings = profile.get("mappings", {})
            for pad_id in [k for k in mappings if k in ALL_PAD_IDS]:
                mappings.setdefault(f"{pad_id}@{DEFAULT_PAD_MODE}", mappings.pop(pad_id))
                changed = True
            for mapping in mappings.values():
                replacement = RETIRED_ACTIONS.get(mapping.get("id")) if isinstance(mapping, dict) else None
                if replacement and mapping.get("type") == "action":
                    mapping["id"] = replacement
                    changed = True
        if changed:
            self.save()

    def save(self):
        """Saves current configuration to JSON file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config file: {e}")

    def get_setting(self, key, default=None):
        return self.config.get("settings", {}).get(key, default)

    def set_setting(self, key, value):
        if self.get_setting(key) != value:
            self.config.setdefault("settings", {})[key] = value
            self.save()

    def get_profiles(self):
        """Returns a dict of all profiles."""
        return self.config.get("profiles", {})

    def get_profile(self, profile_id):
        """Returns a specific profile. Falls back to global if not found."""
        profiles = self.get_profiles()
        if profile_id in profiles:
            return profiles[profile_id]
        return profiles.get("global", {"name": "Global", "mappings": {}})

    def add_profile(self, profile_id, name):
        """Creates a new empty profile."""
        profile_id = profile_id.lower().strip()
        if not profile_id.endswith(".exe") and profile_id != "global":
            profile_id += ".exe"
        
        if profile_id not in self.config["profiles"]:
            self.config["profiles"][profile_id] = {
                "name": name,
                "mappings": {}
            }
            self.save()
            return True, profile_id
        return False, "Profile already exists."

    def delete_profile(self, profile_id):
        """Deletes a profile. Cannot delete 'global'."""
        if profile_id == "global":
            return False, "Cannot delete the Global profile."
        
        if profile_id in self.config["profiles"]:
            del self.config["profiles"][profile_id]
            self.save()
            return True, f"Profile '{profile_id}' deleted."
        return False, "Profile not found."

    def set_mapping(self, profile_id, control_id, mapping_data):
        """Sets a mapping for a control under a profile."""
        profiles = self.get_profiles()
        if profile_id not in profiles:
            return False, "Profile does not exist."
        
        if "mappings" not in profiles[profile_id]:
            profiles[profile_id]["mappings"] = {}

        if mapping_data is None:
            if control_id in profiles[profile_id]["mappings"]:
                del profiles[profile_id]["mappings"][control_id]
        else:
            profiles[profile_id]["mappings"][control_id] = mapping_data
            
        self.save()
        return True, "Mapping saved."

    def get_mapping(self, profile_id, control_id):
        """Gets a mapping for a control under a profile. Checks global if not in profile."""
        profile = self.get_profile(profile_id)
        mappings = profile.get("mappings", {})
        if control_id in mappings:
            return mappings[control_id]
        
        global_profile = self.get_profile("global")
        return global_profile.get("mappings", {}).get(control_id, None)

    def set_led_setting(self, profile_id, control_id, led_data):
        """Sets LED light behavior for a control under a profile."""
        profiles = self.get_profiles()
        if profile_id not in profiles:
            return False, "Profile does not exist."

        if "led_settings" not in profiles[profile_id]:
            profiles[profile_id]["led_settings"] = {}

        if led_data is None:
            if control_id in profiles[profile_id]["led_settings"]:
                del profiles[profile_id]["led_settings"][control_id]
        else:
            profiles[profile_id]["led_settings"][control_id] = led_data

        self.save()
        return True, "LED setting saved."

    def get_led_setting(self, profile_id, control_id):
        """Gets LED setting for a control. Checks profile first, then global."""
        profile = self.get_profile(profile_id)
        leds = profile.get("led_settings", {})
        if control_id in leds:
            return leds[control_id]

        global_profile = self.get_profile("global")
        global_leds = global_profile.get("led_settings", {})
        return global_leds.get(control_id, {"mode": "on_press", "value": 127})

    def duplicate_profile(self, source_id, new_id, new_name):
        """Duplicates an existing profile into a new one."""
        profiles = self.get_profiles()
        if source_id not in profiles:
            return False, "Source profile does not exist."
        
        new_id = new_id.lower().strip()
        if not new_id.endswith(".exe") and new_id != "global":
            new_id += ".exe"
            
        if new_id in profiles:
            return False, "New profile ID already exists."
            
        source = profiles[source_id]
        profiles[new_id] = {
            "name": new_name,
            "mappings": copy.deepcopy(source.get("mappings", {})),
            "led_settings": copy.deepcopy(source.get("led_settings", {}))
        }
        self.save()
        return True, new_id


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mappings.json")
        c = ConfigManager(path)
        assert os.path.exists(path), "a missing config file is created"
        assert c.get_profile("global")["mappings"], "and seeded with the defaults"

        c.set_mapping("global", "PLAY_R", {"type": "action", "id": "win.lock"})
        c.set_setting("theme", "voltage")
        assert ConfigManager(path).get_mapping("global", "PLAY_R")["id"] == "win.lock", "saved"
        assert ConfigManager(path).get_setting("theme") == "voltage"
        c.set_mapping("global", "PLAY_R", None)
        assert ConfigManager(path).get_mapping("global", "PLAY_R") is None, "removed"

        # A pad saved before the banks existed was always in the bank the hardware starts in.
        old = os.path.join(tmp, "old.json")
        with open(old, "w", encoding="utf-8") as f:
            json.dump({"profiles": {"global": {"name": "G", "mappings": {
                "PAD_L_5": {"type": "keystroke", "keys": ["a"]},
                "IN_4BEAT_L": {"type": "keystroke", "keys": ["b"]}}}}}, f)
        moved = ConfigManager(old).get_profile("global")["mappings"]
        assert f"PAD_L_5@{DEFAULT_PAD_MODE}" in moved and "PAD_L_5" not in moved, moved
        assert "IN_L" in moved and "IN_4BEAT_L" not in moved, "renamed controls follow too"

        # A retired action is re-pointed, so the button keeps working instead of going quiet.
        retired = os.path.join(tmp, "retired.json")
        with open(retired, "w", encoding="utf-8") as f:
            json.dump({"profiles": {"global": {"name": "G", "mappings": {
                "IN_R": {"type": "action", "id": "pow.lock"},
                "IN_L": {"type": "action", "id": "win.search"}}}}}, f)
        fixed = ConfigManager(retired).get_profile("global")["mappings"]
        assert fixed["IN_R"]["id"] == "win.lock", fixed
        assert fixed["IN_L"]["id"] == "win.search", "actions still in the catalog are left alone"
        import actions as _catalog
        for old_id, new_id in RETIRED_ACTIONS.items():
            assert old_id not in _catalog.BY_ID, f"{old_id} is still in the catalog"
            assert new_id in _catalog.BY_ID, f"{new_id} is not an action"

        # A broken file is kept aside rather than silently overwritten.
        bad = os.path.join(tmp, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{not json")
        ConfigManager(bad)
        assert os.path.exists(bad + ".broken"), "the unreadable file must be recoverable"

    print(f"config_manager OK — settings live in {CONFIG_FILE}")

