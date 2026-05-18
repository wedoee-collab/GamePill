; GamePill - script d'installation Inno Setup
; Compilation : ISCC.exe gamepill.iss  ->  dist\GamePillSetup.exe
; Prerequis : dist\GamePill.exe doit exister (pyinstaller gamepill.spec)

#define MyAppName "GamePill"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "sm0ke"
#define MyAppURL "https://wedoee-collab.github.io/GamePill/"
#define MyAppExeName "GamePill.exe"

[Setup]
AppId={{7B3A9C1E-5D42-4F8A-B6E1-9C2D8F4A1E03}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=GamePillSetup
SetupIconFile=assets\gamepill.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
