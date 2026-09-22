# SPDX-License-Identifier: GPL-3.0-or-later
# action_spec.py
# The shape of an action, shared by every platform's catalog.
#
# Its own module so actions_win.py and actions_mac.py can both build entries without either
# importing actions.py, which imports them.
#
# kind      "press"  buttons and pads
#           "range"  faders and knobs (absolute 0-127 position)
#           "turn"   jog wheels and the browse encoder (relative ticks)
# backend   "keys"   tap a keyboard shortcut          payload: list of key names
#           "uri"    open a URI or a settings page    payload: "ms-settings:…" / "x-apple…"
#           "run"    run a command line               payload: command
#           "native" handled in action_handler.py     payload: handler name
#           "keypair" one shortcut each way on a turn payload: {"cw": [...], "ccw": [...]}
#           "custom" the user fills in the details    payload: legacy mapping type
# options   per-mapping settings the app offers for this action ("invert", "sensitivity")

TURN_OPTIONS = ("sensitivity", "acceleration", "invert")
# Only the wheel-driven scrolling actions can glide on after you let go; a jog wheel that
# kept skipping tracks or stepping frames on its own would be a nuisance, not a feature.
SCROLL_TURN_OPTIONS = TURN_OPTIONS + ("smooth",)
RANGE_OPTIONS = ("invert",)


def _a(id, kind, category, name, hint, backend, payload, options=()):
    return {"id": id, "kind": kind, "category": category, "name": name, "hint": hint,
            "backend": backend, "payload": payload, "options": tuple(options)}
