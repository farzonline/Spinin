# The macOS port

**Status: builds and runs headless on macOS; never used interactively.** Written on a
Windows machine, then run on Apple's macOS 14 runners (Apple Silicon) through the
`macOS build` workflow, which passes.

**Proven on real macOS by CI:**

- Every module imports, pyobjc (Quartz, AppKit) loads, and `check_portable.py` passes
- The whole UI constructs offscreen: the window, every dialog, all six themes, and the
  editor for each of the 138 Mac actions (`smoke_test.py`)
- **CoreAudio device enumeration works**: lists the runner's output devices, reads the
  default, and switches the default successfully. This was written blind in ctypes and was
  the part most likely to be wrong; it is not.
- The app scanner finds real `.app` bundles with the right names
- The Mac catalog's key names all resolve to key codes
- The `.app` bundle builds, carries the right bundle id, and gets an `.icns` made from the
  PNG

**Not proven, because CI has no display, keyboard, speakers or controller:** that a
keystroke actually lands in another app, that the permission prompts work, that volume
changes anything audible, and that the DDJ-FLX4 is found over CoreMIDI.

Do not ship a macOS release until the checklist at the bottom has been worked through on
real hardware. An unsigned build of each passing commit is kept for 14 days as a workflow
artifact (`Spinin-macos-unsigned`) if you want something to try.

## How the platform split works

The app talks to three modules that each pick a backend at import time:

| Shared module | Windows backend | macOS backend |
|---|---|---|
| `userinput.py` — keystrokes, scroll, shortcut recording | `_input_win.py` (Win32 `SendInput`, `WH_KEYBOARD_LL` hook) | `_input_mac.py` (Quartz event services, `CGEventTap`) |
| `audio_devices.py` — output devices | `_audio_win.py` (`IPolicyConfig`, pycaw) | `macos_system.py` (CoreAudio HAL via ctypes) |
| `actions.py` — the action catalog | `actions_win.py` (184 actions) | `actions_mac.py` (138 actions) |

Three more dispatch inline, because only one function differs: `app_scanner.py` (Start Menu
shortcuts vs `.app` bundles), `context_tracker.py` (`win32gui` vs `NSWorkspace`), and
`action_handler.py` (lock, sleep, launching, volume).

`check_portable.py` fails the build if a shared module imports a Windows-only or
macOS-only package at module scope. That check is the main thing keeping the port alive
while nobody can run it, so leave it in CI.

## What differs on macOS, and why

**Modifiers are flags, not keys.** Quartz attaches modifiers to the event they modify rather
than sending them as separate presses. `_input_mac.tap()` folds them into flags, and also
sends them as real key events, because some apps watch for the physical press.

**`win` means Command.** A mapping recorded on Windows stores `"win"`. On macOS that resolves
to Command, so a profile crossing platforms does roughly the right thing.

**Media keys are not keys.** Play/pause, next and previous travel as `NSSystemDefined`
events with their own numbering. Volume and mute do have real key codes and go the ordinary
way.

**Zoom uses Command, not Control.** Ctrl+scroll on macOS is the accessibility screen zoom, so
`ZOOM_MODIFIER` in `action_handler.py` is `cmd` there.

**Profiles are keyed on bundle id**, not an `.exe` name — `com.adobe.Photoshop` rather than
`photoshop.exe`. Mac and Windows profiles are therefore not interchangeable, even though the
action ids largely are (75 are shared).

**DJ software handover is a courtesy, not a necessity.** CoreMIDI lets several apps read one
port, unlike Windows. Spinin still stands down, because two programs acting on the same jog
wheel is its own kind of mess.

**No per-app volume and no balance.** macOS has no public API for either, so
`range.appvolume` and `range.balance` are absent from the Mac catalog. A Windows profile
using them degrades to doing nothing rather than crashing.

## Permissions

macOS will refuse everything important until the user grants these in
**System Settings → Privacy & Security**:

- **Accessibility** — required to send keystrokes at all, and for `CGEventTapCreate` to
  record a shortcut. Without it `HotkeyCapture` sets `permission_needed` and silently
  records nothing; the UI should say so rather than look broken.
- **Input Monitoring** — may also be required for the event tap, depending on the release.
- **Screen Recording** — only to read a window's *title*. The app name still works without
  it, so this one is optional and the code treats a missing title as normal.

An unsigned build gets a Gatekeeper warning, and TCC permission grants are keyed to the
signature — meaning **each new unsigned build is treated as a different app and has to be
granted permission again**. That alone makes signing worth doing early.

## Checklist for the first real Mac

Work down this list; each item is something CI cannot reach.

- [ ] App launches from Finder without a Gatekeeper dead end
- [ ] Accessibility prompt appears, and keystrokes work once granted
- [ ] `userinput.tap(["cmd", "c"])` actually copies in another app
- [ ] Shifted punctuation (`+`, `?`, `~`) produces the right character
- [ ] Media keys control the actual playing app — the `NSSystemDefined` path is the least
      certain code in the port
- [ ] Recording a shortcut works, including one with Command in it
- [ ] Scroll direction matches Windows (dy positive scrolls up); check "natural scrolling"
      both on and off
- [ ] Smooth scrolling coasts and decays the way it does on Windows
- [ ] `macos_system.outputs()` lists real devices; switching the default works
- [ ] Volume fader moves the actual output level, and lifts a mute coming up from zero
- [ ] Profile switching follows the front app, by bundle id
- [ ] Installed-apps picker lists `/Applications` with the right names
- [ ] Lock and sleep work (`CGSession -suspend`, `pmset sleepnow`)
- [ ] Title bar buttons are on the **left** and in macOS order; dragging, zooming and
      resizing behave
- [ ] Menu icons render as real glyphs, not empty boxes
- [ ] The DDJ-FLX4 is found over CoreMIDI, and LEDs light

## Things most likely to be wrong

In rough order of how much I would bet against them:

1. **The `NSSystemDefined` media-key path** — fiddly, and the constants are folklore more
   than documentation.
2. **`CGEventTap` lifetime** — it is attached to `CFRunLoopGetCurrent()`, which assumes Qt's
   event loop is running that run loop on the main thread. Probably right, unverified.
3. **CoreAudio volume** — device listing and switching are now proven by CI, but setting the
   volume level uses a different property (`vmvc`, falling back to per-channel `volm`) that
   CI never exercises. Check the fader actually moves the output level.
4. **The Sequoia tiling shortcuts** (`mac.tileleft` and friends) — these are version
   specific and will simply do nothing on older macOS.
5. **System Settings pane URLs** — Ventura renamed the panes; the old
   `x-apple.systempreferences:` URLs mostly still redirect, but some may not.

## Bugs the macOS CI has already caught

Worth knowing, because each would have shipped otherwise:

- `chrome.py` nulled out `ctypes` on macOS, but defines structures from it at import time —
  the app would have crashed on launch.
- `dj_guard.py` appended `.exe` to every process name, so it could never have recognised
  rekordbox on a Mac and would never have stood down.
- Two self-checks used Windows-only fixtures and failed for the wrong reason on macOS.

## Building it

```bash
python3 -m pip install -r requirements-dev.txt
# The icon is assembled from the PNG with Apple's own tools:
mkdir -p Spinin2.iconset
for size in 16 32 64 128 256 512; do
  sips -z $size $size Spinin2.png --out "Spinin2.iconset/icon_${size}x${size}.png"
  sips -z $((size*2)) $((size*2)) Spinin2.png --out "Spinin2.iconset/icon_${size}x${size}@2x.png"
done
iconutil -c icns Spinin2.iconset -o Spinin2.icns
pyinstaller --noconfirm Spinin-mac.spec        # -> dist/Spinin.app
```

For a build other people can run without a Gatekeeper fight, you need an Apple Developer
Program membership, then `codesign` with a Developer ID and `notarytool` to notarise.

## Settings location

| Running from | Settings file |
|---|---|
| The `.app` | `~/Library/Application Support/Spinin/mappings.json` |
| A source checkout | `mappings.json`, beside the source |
