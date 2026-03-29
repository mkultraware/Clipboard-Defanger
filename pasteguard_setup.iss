#define MyAppName "Sekura PasteGuard"
#define MyAppVersion "2.0"
#define MyAppPublisher "Sekura"
#define MyAppURL "https://sekura.se"
#define MyAppExeName "PasteGuard.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\Sekura\PasteGuard
DefaultGroupName={#MyAppName}
OutputDir=.\installer_output
OutputBaseFilename=SekuraPasteGuard_Setup_v2.0
SetupIconFile=clipboard-x.512.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startupentry"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Windows Startup:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "clipboard-x.512.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\clipboard-x.512.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\clipboard-x.512.ico"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden

[Code]
var
  LicensePage: TInputOptionWizardPage;
procedure InitializeWizard;
begin
  LicensePage := CreateInputOptionPage(wpLicense,
    'License Selection', 'Please select how you will use this software.',
    'Commercial use requires a valid license.', True, False);
  LicensePage.Add('Personal Use (Free for individuals)');
  LicensePage.Add('Business / Commercial Use (Contact for Pricing)');
  LicensePage.Values[0] := True;
end;