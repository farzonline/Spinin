# Prompt: make an FLX4 Mapper profile for any app

Paste everything below into an AI chat, replacing APP NAME with the program you want
(for example Photoshop, DaVinci Resolve, Ableton Live, Excel). Save the reply as a `.json`
file, then load it with **⋯ → Import profiles…** in FLX4 Mapper.

---

You are writing a profile file for FLX4 Mapper, a Windows app that turns a Pioneer DDJ-FLX4
DJ controller into a control surface for ordinary software. Produce a profile for: **APP NAME**

Return **only** a JSON file, no explanation around it.

## What a profile does

Each control on the DJ controller is given one action. When the app named in the profile id is
the active window, FLX4 Mapper uses that profile.

## File format

```json
{
  "flx4_mapper_profiles": 1,
  "profiles": {
    "app.exe": {
      "name": "Readable name",
      "mappings": {
        "CONTROL_ID": { "type": "action", "id": "ACTION_ID" }
      },
      "led_settings": {
        "CONTROL_ID": { "mode": "on_press", "value": 127 }
      }
    }
  }
}
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
   letters and digits a-z, 0-9; function keys f1-f24; and `backspace`, `caps_lock`, `delete`, `down`, `end`, `enter`, `esc`, `home`, `insert`, `left`, `media_mute`, `media_next`, `media_play_pause`, `media_prev`, `media_stop`, `menu`, `num_lock`, `page_down`, `page_up`, `print_screen`, `right`, `space`, `tab`, `up`, `volume_down`, `volume_up`, `'`, `+`, `,`, `-`, `.`, `/`, `;`, `=`, `[`, `\`, `]`, ```.
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

### Buttons — take a **press** action

`IN_L` (Deck 1 Loop In), `OUT_L` (Deck 1 Loop Out), `BEAT_EXIT_L` (Deck 1 4 Beat / Exit), `LOOP_HALF_L` (Deck 1 Cue/Loop Call ◄), `LOOP_DOUBLE_L` (Deck 1 Cue/Loop Call ►), `SYNC_L` (Deck 1 Beat Sync), `SHIFT_L` (Deck 1 Shift), `CUE_L` (Deck 1 Cue), `PLAY_L` (Deck 1 Play / Pause), `HOT_CUE_L` (Deck 1 Hot Cue mode), `PAD_FX1_L` (Deck 1 Pad FX 1 mode), `BEAT_JUMP_L` (Deck 1 Beat Jump mode), `SAMPLER_L` (Deck 1 Sampler mode), `JOG_TOUCH_L` (Deck 1 Jog Touch), `IN_R` (Deck 2 Loop In), `OUT_R` (Deck 2 Loop Out), `BEAT_EXIT_R` (Deck 2 4 Beat / Exit), `LOOP_HALF_R` (Deck 2 Cue/Loop Call ◄), `LOOP_DOUBLE_R` (Deck 2 Cue/Loop Call ►), `SYNC_R` (Deck 2 Beat Sync), `SHIFT_R` (Deck 2 Shift), `CUE_R` (Deck 2 Cue), `PLAY_R` (Deck 2 Play / Pause), `HOT_CUE_R` (Deck 2 Hot Cue mode), `PAD_FX1_R` (Deck 2 Pad FX 1 mode), `BEAT_JUMP_R` (Deck 2 Beat Jump mode), `SAMPLER_R` (Deck 2 Sampler mode), `JOG_TOUCH_R` (Deck 2 Jog Touch), `BROWSER_LOAD_L` (Load Deck 1), `BROWSER_BACK` (Browse Encoder Push), `BROWSER_LOAD_R` (Load Deck 2), `CH_CUE_L` (Ch 1 Headphone Cue), `CH_CUE_R` (Ch 2 Headphone Cue), `SMART_CFX` (Smart CFX), `SMART_FADER` (Smart Fader), `MASTER_CUE` (Master Cue), `FX_SWITCH_1` (Beat FX Switch at 1), `FX_SWITCH_2` (Beat FX Switch at 2), `FX_SWITCH_BOTH` (Beat FX Switch at 1&2), `FX_SELECT` (Beat FX Select), `BEAT_LEFT` (Beat ◄), `BEAT_RIGHT` (Beat ►), `BEAT_FX_ON_OFF` (Beat FX On / Off)

### Faders and knobs — take a **range** action

`TEMPO_L` (Deck 1 Tempo), `TEMPO_R` (Deck 2 Tempo), `KNOB_TRIM_L` (Ch 1 Trim), `KNOB_EQ_HI_L` (Ch 1 EQ Hi), `KNOB_EQ_MID_L` (Ch 1 EQ Mid), `KNOB_EQ_LOW_L` (Ch 1 EQ Low), `KNOB_CFX_L` (Ch 1 Color FX), `FADER_L` (Ch 1 Fader), `KNOB_TRIM_R` (Ch 2 Trim), `KNOB_EQ_HI_R` (Ch 2 EQ Hi), `KNOB_EQ_MID_R` (Ch 2 EQ Mid), `KNOB_EQ_LOW_R` (Ch 2 EQ Low), `KNOB_CFX_R` (Ch 2 Color FX), `FADER_R` (Ch 2 Fader), `CROSSFADER` (Crossfader), `KNOB_MIC_LEVEL` (Mic Level), `KNOB_HEADPHONES_MIX` (Headphone Mix), `KNOB_HEADPHONES_LEVEL` (Headphone Level), `KNOB_MASTER_LEVEL` (Master Level), `KNOB_BEAT_FX_LEVEL` (Beat FX Level / Depth)

### Jog wheels and the browse encoder — take a **turn** action

`JOG_SCRATCH_L` (Deck 1 Jog Turn while Touched), `JOG_ROTATE_L` (Deck 1 Jog Ring Turn), `JOG_SCRATCH_R` (Deck 2 Jog Turn while Touched), `JOG_ROTATE_R` (Deck 2 Jog Ring Turn), `BROWSER_ENCODER` (Browse Encoder Turn)

### Pads — take a **press** action, four banks each

Each deck has 8 pads: `PAD_L_1`-`PAD_L_8` on deck 1, `PAD_R_1`-`PAD_R_8` on deck 2. Each pad has **4 separate banks**, one per mode button above the pads: `HOT_CUE`, `PAD_FX1`, `BEAT_JUMP`, `SAMPLER`. A pad's `mappings` key is the pad id plus `@` and the bank, for example `PAD_L_3@HOT_CUE` or `PAD_R_6@SAMPLER`. Use `HOT_CUE` for the one thing APP NAME needs pads for most, since that is the bank active when the controller is switched on; use the other banks for secondary sets of commands if there are more than 8 worth mapping.

## Action ids

### press — for buttons and pads

**Windows & apps**

- `win.start` — Open Start (Win)
- `win.search` — Search (Win+S)
- `win.run` — Run dialog (Win+R)
- `win.settings` — Settings (Win+I)
- `win.explorer` — File Explorer (Win+E)
- `win.quicklink` — Quick Link menu (Win+X)
- `win.taskmanager` — Task Manager (Ctrl+Shift+Esc)
- `win.lock` — Lock the PC (Win+L)
- `win.taskview` — Task View (Win+Tab)
- `win.switch` — Switch window (Alt+Tab)
- `win.close` — Close the window (Alt+F4)
- `win.windowmenu` — Window menu (Alt+Space)
- `win.desktop` — Show the desktop (Win+D)
- `win.peek` — Peek at the desktop (Win+,)
- `win.quicksettings` — Quick Settings (Win+A)
- `win.notifications` — Notifications (Win+N)
- `win.widgets` — Widgets (Win+W)
- `win.cast` — Cast to a device (Win+K)
- `win.minimizeall` — Minimise every window (Win+M)
- `win.restoreall` — Restore minimised windows (Win+Shift+M)
- `win.minimizeothers` — Minimise all but this window (Win+Home)

**Snap & desktops**

- `snap.left` — Snap window left (Win+Left)
- `snap.right` — Snap window right (Win+Right)
- `snap.maximize` — Maximise window (Win+Up)
- `snap.minimize` — Minimise or restore window (Win+Down)
- `snap.layouts` — Snap Layouts (Win+Z)
- `snap.monitorleft` — Move window to the left monitor (Win+Shift+Left)
- `snap.monitorright` — Move window to the right monitor (Win+Shift+Right)
- `snap.project` — Projection mode (Win+P)
- `desk.new` — New virtual desktop (Win+Ctrl+D)
- `desk.left` — Previous desktop (Win+Ctrl+Left)
- `desk.right` — Next desktop (Win+Ctrl+Right)
- `desk.close` — Close this desktop (Win+Ctrl+F4)

**Capture**

- `cap.region` — Snip a region (Win+Shift+S)
- `cap.fullscreen` — Screenshot to file (Win+PrtScn)
- `cap.window` — Copy this window (Alt+PrtScn)
- `cap.record` — Record a region (Win+Shift+R)
- `cap.gamebar` — Game Bar (Win+G)
- `cap.gamerecord` — Start or stop recording (Win+Alt+R)

**Clipboard & text**

- `clip.history` — Clipboard history (Win+V)
- `clip.emoji` — Emoji panel (Win+.)
- `clip.dictate` — Voice typing (Win+H)
- `clip.language` — Switch keyboard language (Win+Space)
- `edit.copy` — Copy (Ctrl+C)
- `edit.cut` — Cut (Ctrl+X)
- `edit.paste` — Paste (Ctrl+V)
- `edit.undo` — Undo (Ctrl+Z)
- `edit.redo` — Redo (Ctrl+Y)
- `edit.selectall` — Select all (Ctrl+A)
- `edit.find` — Find (Ctrl+F)
- `edit.replace` — Replace (Ctrl+H)
- `edit.save` — Save (Ctrl+S)
- `edit.print` — Print (Ctrl+P)
- `edit.new` — New (Ctrl+N)
- `edit.open` — Open (Ctrl+O)

**Media & audio**

- `media.playpause` — Play or pause (Media key)
- `media.next` — Next track (Media key)
- `media.prev` — Previous track (Media key)
- `media.mute` — Mute or unmute (Media key)
- `media.volup` — Volume up (Media key)
- `media.voldown` — Volume down (Media key)
- `audio.settings` — Sound settings (ms-settings:sound)
- `audio.devices` — All sound devices (ms-settings:sound-devices)
- `audio.mixer` — Volume mixer (ms-settings:apps-volume)
- `audio.classic` — Classic sound panel (mmsys.cpl)
- `audio.nextdevice` — Next sound device (Steps through your playback devices)
- `audio.toggledevice` — Swap the last two sound devices (Back and forth between two outputs)
- `audio.setdevice` — Switch to a chosen sound device (You pick the device) — needs `device_name`

**Settings pages**

- `set.display` — Display settings (ms-settings:display)
- `set.nightlight` — Night light (ms-settings:nightlight)
- `set.graphics` — Graphics settings (ms-settings:display-advancedgraphics)
- `set.bluetooth` — Bluetooth & devices (ms-settings:bluetooth)
- `set.wifi` — Wi-Fi (ms-settings:network-wifi)
- `set.knownnetworks` — Known networks (ms-settings:network-wifisettings)
- `set.airplane` — Aeroplane mode (ms-settings:network-airplanemode)
- `set.hotspot` — Mobile hotspot (ms-settings:network-mobilehotspot)
- `set.vpn` — VPN (ms-settings:network-vpn)
- `set.network` — Network status (ms-settings:network-status)
- `set.powersleep` — Power & sleep (ms-settings:powersleep)
- `set.batterysaver` — Battery saver (ms-settings:batterysaver)
- `set.notifications` — Notifications (ms-settings:notifications)
- `set.focus` — Do not disturb (ms-settings:quiethours)
- `set.apps` — Installed apps (ms-settings:appsfeatures)
- `set.defaultapps` — Default apps (ms-settings:defaultapps)
- `set.startupapps` — Startup apps (ms-settings:startupapps)
- `set.update` — Windows Update (ms-settings:windowsupdate)
- `set.updatehistory` — Update history (ms-settings:windowsupdate-history)
- `set.webcam` — Camera privacy (ms-settings:privacy-webcam)
- `set.mic` — Microphone privacy (ms-settings:privacy-microphone)
- `set.location` — Location privacy (ms-settings:privacy-location)
- `set.security` — Windows Security (ms-settings:windowsdefender)
- `set.storage` — Storage (ms-settings:storagesense)
- `set.disks` — Disks & volumes (ms-settings:disksandvolumes)
- `set.datetime` — Date & time (ms-settings:dateandtime)
- `set.language` — Language & region (ms-settings:regionlanguage)
- `set.keyboard` — Keyboard settings (ms-settings:keyboard)
- `set.developers` — Developer settings (ms-settings:developers)
- `set.recovery` — Recovery (ms-settings:recovery)
- `set.troubleshoot` — Troubleshooters (ms-settings:troubleshoot)
- `set.signin` — Sign-in options (ms-settings:signinoptions)
- `set.findmydevice` — Find my device (ms-settings:findmydevice)

**Folders**

- `fold.downloads` — Downloads (shell:Downloads)
- `fold.desktop` — Desktop folder (shell:Desktop)
- `fold.documents` — Documents (shell:Documents)
- `fold.pictures` — Pictures (shell:Pictures)
- `fold.music` — Music (shell:Music)
- `fold.videos` — Videos (shell:Videos)
- `fold.appdata` — AppData (Roaming) (shell:AppData)
- `fold.localappdata` — AppData (Local) (shell:Local AppData)
- `fold.startup` — Startup folder (shell:Startup)
- `fold.recent` — Recent items (shell:Recent)
- `fold.fonts` — Fonts (shell:Fonts)
- `fold.recyclebin` — Recycle Bin (shell:RecycleBinFolder)
- `fold.connections` — Network connections (shell:ConnectionsFolder)
- `fold.programs` — Start menu programs (shell:Programs)

**System tools**

- `tool.devmgmt` — Device Manager (devmgmt.msc)
- `tool.diskmgmt` — Disk Management (diskmgmt.msc)
- `tool.services` — Services (services.msc)
- `tool.eventvwr` — Event Viewer (eventvwr.msc)
- `tool.taskschd` — Task Scheduler (taskschd.msc)
- `tool.appwiz` — Programs & Features (appwiz.cpl)
- `tool.ncpa` — Network Connections (ncpa.cpl)
- `tool.sysdm` — System Properties (sysdm.cpl)
- `tool.firewall` — Firewall (firewall.cpl)
- `tool.cmd` — Command Prompt (cmd)
- `tool.powershell` — PowerShell (powershell)
- `tool.terminal` — Windows Terminal (wt)
- `tool.regedit` — Registry Editor (regedit)
- `tool.msinfo` — System Information (msinfo32)
- `tool.dxdiag` — DirectX Diagnostics (dxdiag)
- `tool.controlpanel` — Control Panel (control)

**Power**

- `pow.sleep` — Sleep (Suspends the PC)
- `pow.hibernate` — Hibernate (shutdown /h)
- `pow.restart` — Restart (shutdown /r /t 0)
- `pow.shutdown` — Shut down (shutdown /s /t 0)
- `pow.signout` — Sign out (shutdown /l)
- `pow.lock` — Lock the PC (Win+L)

**PowerToys**

- `pt.run` — PowerToys Run (Alt+Space)
- `pt.alwaysontop` — Pin window on top (Win+Ctrl+T)
- `pt.colorpicker` — Colour Picker (Win+Shift+C)
- `pt.textextractor` — Text Extractor (Win+Shift+T)
- `pt.ruler` — Screen Ruler (Win+Shift+M)
- `pt.croplock` — Crop & Lock (Win+Ctrl+Shift+T)
- `pt.peek` — Peek at a file (Ctrl+Space)
- `pt.pasteplain` — Paste as plain text (Win+Ctrl+Alt+V)
- `pt.advancedpaste` — Advanced Paste (Win+Shift+V)
- `pt.highlighter` — Mouse highlighter (Win+Shift+H)
- `pt.mutemic` — Mute the microphone (Win+Shift+A)
- `pt.mutecam` — Mute the camera (Win+Shift+O)
- `pt.muteboth` — Mute mic and camera (Win+Shift+Q)

**Meetings**

- `meet.teamsmute` — Teams mute (Ctrl+Shift+M)
- `meet.teamsvideo` — Teams camera (Ctrl+Shift+O)
- `meet.zoommute` — Zoom mute (Alt+A)
- `meet.zoomvideo` — Zoom camera (Alt+V)
- `meet.zoomshare` — Zoom share screen (Alt+S)

**Accessibility**

- `acc.settings` — Accessibility settings (Win+U)
- `acc.magnifyin` — Magnifier in (Win++)
- `acc.magnifyout` — Magnifier out (Win+-)
- `acc.magnifyexit` — Close Magnifier (Win+Esc)
- `acc.narrator` — Narrator on or off (Win+Ctrl+Enter)
- `acc.colorfilters` — Colour filters (Win+Ctrl+C)

**Your own**

- `custom.app` — Open an app (You choose the app) — needs `command`
- `custom.keys` — Press a keyboard shortcut (You record the keys) — needs `keys`
- `custom.command` — Run a command (You type the command) — needs `command`

### range — for faders and knobs

**Audio**

- `range.volume` — System volume (Windows master volume)
- `range.appvolume` — Volume of the app in front (Per-app volume mixer)
- `range.balance` — Speaker balance left to right (Master channel balance)

**Scrolling**

- `range.scroll` — Scroll by how far you move it (Mouse wheel)

### turn — for jog wheels and the browse encoder

**Scrolling**

- `turn.scroll` — Scroll up and down (Mouse wheel)
- `turn.scrollh` — Scroll sideways (Shift + wheel)
- `turn.zoom` — Zoom in and out (Ctrl + wheel)
- `turn.zoomkeys` — Zoom with Ctrl and +/- (Ctrl+Plus / Ctrl+Minus)

**Media**

- `turn.volume` — Nudge the volume (Volume keys)
- `turn.track` — Skip tracks (Next / previous track)
- `turn.seek` — Seek in the track (Right / left arrow)
- `turn.frame` — Step frame by frame (Comma / full stop)
- `turn.audiodevice` — Step through sound devices (Playback device)

**Editing**

- `turn.undo` — Undo and redo (Ctrl+Z / Ctrl+Y)
- `turn.brush` — Brush size ([ and ])
- `turn.arrows` — Move up and down (Up / down arrow)
- `turn.pages` — Page up and down (PageUp / PageDown)

**Windows**

- `turn.tabs` — Switch tabs (Ctrl+Tab)
- `turn.desktops` — Switch virtual desktops (Win+Ctrl+Left / Right)
- `turn.history` — Back and forward (Alt+Left / Alt+Right)

**Your own**

- `turn.custom` — Two shortcuts, one each way (You record both) — needs `keys_cw` and `keys_ccw`

## Example

```json
{
  "flx4_mapper_profiles": 1,
  "profiles": {
    "photoshop.exe": {
      "name": "Photoshop",
      "mappings": {
        "PAD_L_1@HOT_CUE": { "type": "action", "id": "custom.keys", "keys": ["b"] },
        "PAD_L_2@HOT_CUE": { "type": "action", "id": "custom.keys", "keys": ["e"] },
        "PAD_L_3@HOT_CUE": { "type": "action", "id": "custom.keys", "keys": ["ctrl", "z"] },
        "PAD_L_4@HOT_CUE": { "type": "action", "id": "custom.keys", "keys": ["ctrl", "s"] },
        "PAD_L_1@SAMPLER": { "type": "action", "id": "custom.keys", "keys": ["shift", "b"] },
        "JOG_ROTATE_L": { "type": "action", "id": "turn.brush",
                           "options": { "sensitivity": 3, "acceleration": 4 } },
        "JOG_ROTATE_R": { "type": "action", "id": "turn.zoom",
                           "options": { "sensitivity": 2 } },
        "FADER_L": { "type": "action", "id": "range.volume" },
        "PLAY_L": { "type": "action", "id": "custom.keys", "keys": ["ctrl", "0"] }
      },
      "led_settings": {
        "PAD_L_1": { "mode": "toggle", "value": 127 }
      }
    }
  }
}
```
