#define AppName "SpatialForge"
#define AppVersion "0.1.0"
#define AppPublisher "SpatialForge"
#define AppExeName "SpatialForge.exe"

[Setup]
AppId={{2A3D653D-D61C-46CA-9A41-A27F81121F49}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\SpatialForge
DefaultGroupName=SpatialForge
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\artifacts\installer
OutputBaseFilename=SpatialForge-{#AppVersion}-win-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
SetupLogging=yes
LicenseFile=..\..\LICENSE.txt

[Files]
Source: "..\..\artifacts\publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\DEPENDENCY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SpatialForge"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\SpatialForge"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch SpatialForge"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := IsWin64;
  if not Result then
    MsgBox('SpatialForge requires 64-bit Windows 11.', mbError, MB_OK);
end;
