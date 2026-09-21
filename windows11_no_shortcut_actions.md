# Windows 11 — useful commands & functions that typically *do not* have a dedicated keyboard shortcut

This is the “stuff users want a gadget for” category: actions that aren’t reliably reachable via one default hotkey, but are very useful.

Implementation mechanisms you can map to your gadget:
- **Settings deep-links** via `ms-settings:` URIs (official list).  
  Source: Microsoft Learn — ms-settings URI scheme reference: https://learn.microsoft.com/en-us/windows/apps/develop/launch/launch-settings#ms-settings-uri-scheme-reference
- **Shell folders** via `shell:` commands (open special folders quickly).  
  References: TenForums shell commands list / SS64 shell folder shortcuts.
- **Classic control panels** (`*.cpl`) and **MMC** consoles (`*.msc`)
- **Built-in executables** and **shutdown/power** commands
- **Core Audio / Win32 APIs** for things like audio device switching

> Notes:
> - Some of these have *third-party* or *OEM* hotkeys, but Windows doesn’t ship a universal default shortcut.
> - If you need “toggle” actions (Wi‑Fi on/off, Bluetooth on/off, DND toggle), you often want a **native API** or **UI automation** fallback because Settings deep-link only opens the page.

---

## 1) Audio & sound (high value, no single universal hotkey)

### Default output device switching (Speakers/Headset/HDMI/Bluetooth)
- **Set default playback device to a specific endpoint** (by friendly name)
- **Toggle last two output devices**
- **Cycle output devices**

Typical implementation:
- Enumerate devices via Core Audio (`IMMDeviceEnumerator`)
- Set default device via PolicyConfig / IPolicyConfig style approach (common in real apps)

Useful supporting pages:
- `ms-settings:sound` (Sound)
- `ms-settings:sound-devices` (All sound devices)
- `ms-settings:apps-volume` (Volume mixer)

### Default input device switching (microphone)
- Set default mic device (same concept as output)
- `ms-settings:sound` (Input selection lives here)

### Per-app volume control
- Set/get volume of a specific app session
- Mute/unmute a specific app
- Route an app to a specific output device (where supported)
- `ms-settings:apps-volume`

---

## 2) Network toggles & connectivity (often no default hotkey)

Actions:
- Toggle **Wi‑Fi on/off**
- Toggle **Bluetooth on/off**
- Toggle **Airplane mode**
- Toggle **Mobile hotspot**
- Connect/disconnect to a known Wi‑Fi network
- Connect/disconnect VPN profile
- Open the “available networks” chooser

Good deep-links:
- `ms-settings:network-status` (Network & internet home)
- `ms-settings:network-wifi`
- `ms-settings:network-wifisettings` (Manage known networks)
- `ms-settings:network-airplanemode`
- `ms-settings:network-mobilehotspot`
- `ms-settings:network-vpn`
- `ms-settings:bluetooth` (Bluetooth & devices)

Source: Microsoft Learn ms-settings reference. 

---

## 3) Power, battery, performance (actions people want one-tap)

Actions:
- Sleep
- Hibernate (if enabled)
- Restart
- Shutdown
- Sign out
- Lock (this one *does* have a shortcut, but belongs here as a “power” intent)
- Toggle Battery Saver / open energy recommendations

Commands / pages:
- Sleep/hibernate/shutdown/restart via `shutdown` command patterns or power APIs
  - `shutdown /s /t 0` (shutdown)
  - `shutdown /r /t 0` (restart)
  - `shutdown /l` (sign out)
  - `shutdown /h` (hibernate)
- `ms-settings:powersleep`
- `ms-settings:batterysaver`
- `ms-settings:batterysaver-settings`
- `ms-settings:energyrecommendations`

Source: Microsoft Learn ms-settings reference.

---

## 4) Display controls (toggles and “open exactly the right page”)

Actions:
- Set brightness (laptops/tablets; no universal shortcut)
- Toggle Night light
- Change scale/resolution/refresh rate
- Choose primary display
- Toggle HDR (there *is* a shortcut on some systems via Game Bar; treat as capability-based)

Deep-links:
- `ms-settings:display`
- `ms-settings:display-advanced`
- `ms-settings:nightlight`
- `ms-settings:display-advancedgraphics`
- `ms-settings:display-advancedgraphics-default`

Source: Microsoft Learn ms-settings reference.

---

## 5) Do Not Disturb / Focus and notifications (toggle is not a default hotkey)

Actions:
- Toggle Do Not Disturb (DND)
- Set Focus/Quiet Hours mode (Priority only / Alarms only)
- Set scheduled quiet hours

Deep-links:
- `ms-settings:notifications`
- `ms-settings:quiethours`
- `ms-settings:quietmomentsscheduled`

Source: Microsoft Learn ms-settings reference.

---

## 6) App and system management (one-tap openers)

Actions:
- Open Installed apps
- Uninstall an app
- Default apps chooser
- Startup apps on/off
- Optional features
- Troubleshooters
- Recovery options

Deep-links:
- `ms-settings:appsfeatures`
- `ms-settings:defaultapps`
- `ms-settings:startupapps`
- `ms-settings:optionalfeatures` (commonly supported)
- `ms-settings:troubleshoot`
- `ms-settings:recovery`

Source: Microsoft Learn ms-settings reference.

---

## 7) Privacy & security quick jumps

Actions:
- Open Camera/Microphone permissions
- Toggle location services (needs API/UI automation to truly toggle)
- Windows Security dashboard
- Device encryption
- Find my device

Deep-links:
- `ms-settings:privacy-location`
- `ms-settings:privacy-webcam`
- `ms-settings:privacy-microphone`
- `ms-settings:windowsdefender`
- `ms-settings:deviceencryption`
- `ms-settings:findmydevice`

Source: Microsoft Learn ms-settings reference.

---

## 8) Accounts, sign-in, backup-ish

Actions:
- Manage sign-in options
- Set up Windows Hello face/fingerprint enrollment
- Access work or school

Deep-links:
- `ms-settings:signinoptions`
- `ms-settings:signinoptions-launchfaceenrollment`
- `ms-settings:signinoptions-launchfingerprintenrollment`
- `ms-settings:workplace`

Source: Microsoft Learn ms-settings reference.

---

## 9) Time, language, input, speech

Actions:
- Change language/region
- Change keyboard options
- Speech settings

Deep-links:
- `ms-settings:dateandtime`
- `ms-settings:regionlanguage`
- `ms-settings:keyboard`
- `ms-settings:keyboard-advanced`
- `ms-settings:speech`

Source: Microsoft Learn ms-settings reference.

---

## 10) Storage and disks (super useful for a “gadget”)

Actions:
- Open storage usage
- Run Storage Sense
- Manage disks/volumes
- Choose default save locations

Deep-links:
- `ms-settings:storagesense`
- `ms-settings:storagepolicies`
- `ms-settings:storagerecommendations`
- `ms-settings:disksandvolumes`
- `ms-settings:savelocations`

Source: Microsoft Learn ms-settings reference.

---

## 11) Shell folders (`shell:`) — open special locations instantly

These are great because they’re stable and don’t depend on UI layout.

Examples (popular, practical targets):
- `shell:Downloads`
- `shell:Desktop`
- `shell:Documents`
- `shell:Pictures`
- `shell:Music`
- `shell:Videos`
- `shell:AppData` (Roaming)
- `shell:Local AppData`
- `shell:Startup` (current user Startup folder)
- `shell:Common Startup` (all users)
- `shell:Start Menu`
- `shell:Common Start Menu`
- `shell:Programs`
- `shell:Common Programs`
- `shell:Recent` (recent items)
- `shell:SendTo`
- `shell:Fonts`
- `shell:ConnectionsFolder` (classic network connections)
- `shell:RecycleBinFolder`

References:
- TenForums shell commands list: https://www.tenforums.com/tutorials/3109-shell-commands-list-windows-10-a.html
- SS64 shell shortcuts: https://ss64.com/nt/shell.html

---

## 12) Classic Control Panel / MMC entries (still very useful)

These typically don’t have a default hotkey, but are perfect gadget targets.

**Control Panel applets (`.cpl`)**
- `appwiz.cpl` — Programs and Features
- `ncpa.cpl` — Network Connections
- `mmsys.cpl` — Sound (classic)
- `sysdm.cpl` — System Properties
- `firewall.cpl` — Windows Defender Firewall (varies by build)

**MMC consoles (`.msc`)**
- `devmgmt.msc` — Device Manager
- `diskmgmt.msc` — Disk Management
- `services.msc` — Services
- `eventvwr.msc` — Event Viewer
- `taskschd.msc` — Task Scheduler

---

## 13) “Openers” for built-in tools (Run targets)

Actions:
- Open Command Prompt / PowerShell / Terminal
- Open Registry Editor
- Open System Information
- Open DirectX Diagnostic

Targets:
- `cmd`
- `powershell`
- `wt`
- `regedit`
- `msinfo32`
- `dxdiag`

---

## 14) Window management beyond built-in shortcuts (API-level)

Actions (no single default hotkey; better as gadget intents):
- Move active window to an exact monitor + exact region (not just Snap presets)
- Set window Always-on-top (Windows has PowerToys toggle, not default)
- Save/restore window layouts
- Focus a window by title/process

Implementation hint:
- Win32 window APIs (EnumWindows, SetForegroundWindow, MoveWindow, SetWindowPos, etc.)

---

## 15) File operations beyond basic shortcuts

Actions:
- Empty Recycle Bin
- Create new file with template in current folder
- Toggle file extensions / hidden files (Settings/Explorer options)
- Batch rename
- Open with… (specific app)

Implementation hint:
- Shell APIs (IFileOperation), `shell:` folders, or launching Explorer with verbs.

---

## 16) Update & developer actions

Actions:
- Check for updates
- Open update history
- Optional updates
- Developer settings

Deep-links:
- `ms-settings:windowsupdate`
- `ms-settings:windowsupdate-history`
- `ms-settings:windowsupdate-optionalupdates`
- `ms-settings:developers`

Source: Microsoft Learn ms-settings reference.

---

## 17) A practical way to encode these in your app

If your gadget maps “custom input → perfect Windows action”, you’ll want each action to have:
- **Intent name** (e.g., `audio.setDefaultOutput`, `network.toggleWifi`, `settings.openPage`)
- **Parameters** (device name, boolean, page URI, etc.)
- **Preferred backend** (Keystroke / URI launch / shell / command / native API / UIA fallback)

