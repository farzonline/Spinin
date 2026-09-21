# Changelog

All notable changes to Spinin are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-09-20

First public release, under the name Spinin.

### Added
- **Stands down for DJ software.** When rekordbox, Serato, Traktor, VirtualDJ, djay,
  Mixxx, Engine DJ or DJUCED is running, Spinin closes the MIDI port and hands the
  DDJ-FLX4 over. Windows only lets one program hold a MIDI input, so merely ignoring
  the messages would still have left the controller unusable to them. It takes the
  controller back by itself when the DJ software closes.
- **Smooth scrolling.** A jog wheel set to scroll now carries on after you let go and
  slows to a stop, starting from the speed you were actually spinning. Per-mapping
  option on the two scrolling actions.
- **Installed apps list.** "Open an app" can be picked from everything on the Start
  Menu, with each program's own icon, instead of hunting for an `.exe`.
- **Its own title bar**, in the app's colours rather than the Windows one, with native
  dragging, snapping and resizing.
- **Frosted menus** with icons, using the Windows acrylic backdrop.
- **About window** with the version, licence and a link to the project.
- Installer and a signed-off `.exe` build; no batch files or PowerShell launchers.

### Changed
- **Voltage is now the default theme** — near black with electric lime.
- New app icon.
- Check boxes and menu ticks are drawn as real tick marks.
- The inspector panel scrolls instead of squashing its contents on a short window.
- Settings live in `%APPDATA%\Spinin\` for installed copies, so the app works without
  write access to its own folder. Running from a source checkout is unchanged.

### Removed
- The **Test** button. Its countdown-then-fire behaviour was more confusing than useful;
  map the control and press it instead.

### Fixed
- **Lock PC** now calls `LockWorkStation()`. Windows blocks a synthetic Win+L, so the
  old keystroke version silently did nothing.
- The retired duplicate "Lock PC" action is re-pointed to the working one on load, so a
  button mapped to it keeps working instead of going quiet.

[0.1.0]: https://github.com/farzonline/Spinin/releases/tag/v0.1.0
