; installer.iss — builds the Spinin installer with Inno Setup 6.
;
; Build the app first:   pyinstaller --noconfirm Spinin.spec
; Then this:             iscc installer.iss
;
; Installs per-user into Local AppData rather than Program Files, so no administrator
; prompt is needed. Spinin only ever touches its own settings, so there is nothing an
; install for all users would buy.

#define AppName     "Spinin"
#define AppPublisher "farzonline"
#define AppURL      "https://github.com/farzonline/Spinin"
#define AppExe      "Spinin.exe"

; Written by Spinin.spec from branding.py during the PyInstaller build, so this can never
; disagree with the version the app itself reports. Not read from the built exe's own file
; version: GetVersionNumbersString() there is a padded four-part number (0.1.0.0), not the
; three-part version used everywhere else.
#define AppVersion  Trim(FileRead(FileOpen("VERSION.txt")))

[Setup]
AppId={{8E2F4A17-6B5C-4D93-9E1A-5C7B2D0F8A34}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=dist\installer
OutputBaseFilename={#AppName}-{#AppVersion}-Setup
SetupIconFile=Spinin2.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user: no UAC prompt, and {autopf} resolves to Local AppData\Programs.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
AppCopyright=Copyright (C) 2026 farzonline. GPL-3.0-or-later.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup";     Description: "Start {#AppName} when I sign in"; \
                     GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\Spinin\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Spinin\*";         DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}";    Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The build's own leftovers only. Settings in {userappdata}\Spinin are deliberately kept,
; so reinstalling does not throw away the mappings someone spent time on.
Type: filesandordirs; Name: "{app}"
