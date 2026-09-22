# SPDX-License-Identifier: GPL-3.0-or-later
# actions.py
# The action library: everything a control can be set to do, for whichever platform this is.
#
# The entries themselves live in actions_win.py and actions_mac.py, because a Windows
# shortcut and a macOS one rarely agree on more than the idea. This module picks one and is
# the only thing the rest of the app talks to.
#
# Action ids are stored inside mappings.json, so they are a compatibility surface: renaming
# one silently breaks somebody's mapping. Where the same idea exists on both platforms the
# id is deliberately kept the same, so a profile carries across as far as it sensibly can.

import sys

from action_spec import _a, RANGE_OPTIONS, SCROLL_TURN_OPTIONS, TURN_OPTIONS  # noqa: F401

IS_MAC = sys.platform == "darwin"
PLATFORM = "mac" if IS_MAC else "win"

if IS_MAC:
    from actions_mac import PRESS_ACTIONS, RANGE_ACTIONS, TURN_ACTIONS
else:
    from actions_win import PRESS_ACTIONS, RANGE_ACTIONS, TURN_ACTIONS

ACTIONS = PRESS_ACTIONS + TURN_ACTIONS + RANGE_ACTIONS
BY_ID = {a["id"]: a for a in ACTIONS}


# Which kind of action a control accepts, from its MIDI code and hotspot.
def kind_for_control(cid, midi_code, is_relative, shape_kind):
    if is_relative:
        return "turn"
    if midi_code.startswith("CC"):
        return "range"
    return "press"


def for_kind(kind):
    return [a for a in ACTIONS if a["kind"] == kind]


def categories(kind):
    seen = []
    for a in ACTIONS:
        if a["kind"] == kind and a["category"] not in seen:
            seen.append(a["category"])
    return seen


def matches(action, query):
    q = query.strip().lower()
    if not q:
        return True
    return all(word in f"{action['name']} {action['hint']} {action['category']}".lower() for word in q.split())


def decode_delta(value):
    """DDJ-FLX4 relative encodings: jogs send 65/63 (offset 64), the browse encoder 1/127."""
    if 56 <= value <= 72:          # jog wheels sit around 64
        return value - 64
    return value if value < 64 else value - 128


def _check(actions, press, turn, ranged, label):
    """Shared checks, run against either platform's catalog."""
    by_id = {a["id"]: a for a in actions}
    assert len(by_id) == len(actions), f"{label}: duplicate action id"
    for a in actions:
        assert a["backend"] in ("keys", "uri", "run", "native", "keypair", "custom"), a
        assert a["kind"] in ("press", "turn", "range"), a
        assert a["name"] and a["hint"] and a["category"], a
        if a["backend"] == "keypair":
            assert set(a["payload"]) == {"cw", "ccw"}, a
    # Gliding only makes sense where a wheel drives a scroll bar.
    smooth = {a["id"] for a in actions if "smooth" in a["options"]}
    assert smooth == {"turn.scroll", "turn.scrollh"}, f"{label}: {smooth}"
    for a in actions:
        if a["id"] in smooth:
            assert a["backend"] == "native" and a["payload"].startswith("scroll_"), a
        if a["kind"] == "turn":
            assert "sensitivity" in a["options"], f"{label}: a turn needs sensitivity: {a}"
    # Every platform must offer the four "your own" actions: the UI has a page for each.
    for required in ("custom.app", "custom.keys", "custom.command", "turn.custom"):
        assert required in by_id, f"{label}: missing {required}"
    print(f"{label}: {len(actions)} actions OK "
          f"({len(press)} press, {len(turn)} turn, {len(ranged)} range)")
    return by_id


if __name__ == "__main__":
    assert decode_delta(65) == 1 and decode_delta(63) == -1, "jog"
    assert decode_delta(1) == 1 and decode_delta(127) == -1, "encoder"

    # Both catalogs are checked from either platform, so a Windows CI run still proves the
    # macOS one is well formed.
    import actions_mac
    import actions_win
    win_ids = _check(actions_win.PRESS_ACTIONS + actions_win.TURN_ACTIONS + actions_win.RANGE_ACTIONS,
                     actions_win.PRESS_ACTIONS, actions_win.TURN_ACTIONS, actions_win.RANGE_ACTIONS,
                     "windows")
    mac_ids = _check(actions_mac.PRESS_ACTIONS + actions_mac.TURN_ACTIONS + actions_mac.RANGE_ACTIONS,
                     actions_mac.PRESS_ACTIONS, actions_mac.TURN_ACTIONS, actions_mac.RANGE_ACTIONS,
                     "macos")

    # An id that exists on both must mean the same thing, or a profile would change meaning
    # when it crossed platforms.
    for action_id in set(win_ids) & set(mac_ids):
        w, m = win_ids[action_id], mac_ids[action_id]
        assert w["kind"] == m["kind"], f"{action_id} is {w['kind']} on Windows, {m['kind']} on macOS"
        assert w["options"] == m["options"], f"{action_id} offers different options per platform"
    shared = len(set(win_ids) & set(mac_ids))
    print(f"{shared} action ids shared between the two, consistent in kind and options")
    print(f"active catalog: {PLATFORM} ({len(ACTIONS)} actions)")
