; Xdrop Windows Installer Script (Inno Setup 6)
; Universal Social Media & Web Asset Importer for DaVinci Resolve, Premiere Pro & After Effects

#define MyAppName "Xdrop"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Xdrop Team"
#define MyAppURL "https://github.com/Code-Xceed/Xdrop"
#define MyAppExeName "Xdrop.exe"

[Setup]
AppId={{5D9A948C-BF16-438B-B61E-C653139360A2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=dist-installer
OutputBaseFilename=Xdrop-Installer-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "resolvescript"; Description: "Register Xdrop script in DaVinci Resolve (Workspace -> Scripts -> Utility -> Xdrop)"; GroupDescription: "NLE Integrations:"
Name: "adobescript"; Description: "Install Xdrop panel in Adobe Premiere Pro & After Effects (Window -> Extensions -> Xdrop)"; GroupDescription: "NLE Integrations:"

[Files]
; Dist build and python services
Source: "..\dist\Xdrop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\apps\premiere-plugin\*"; DestDir: "{app}\apps\premiere-plugin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs

; Integration helper scripts
Source: "..\scripts\install-resolve-script.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\scripts\install-premiere-plugin.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Auto-install DaVinci Resolve script
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{tmp}\install-resolve-script.ps1"""; Tasks: resolvescript; Flags: runhidden
; Auto-install Premiere Pro & After Effects CEP extension
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{tmp}\install-premiere-plugin.ps1"""; Tasks: adobescript; Flags: runhidden
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\Xdrop.py"
Type: filesandordirs; Name: "{userappdata}\Adobe\CEP\extensions\com.xdrop.panel"
Type: filesandordirs; Name: "{localappdata}\Xdrop\logs"
Type: filesandordirs; Name: "{commonappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\ResolveFetch.py"
Type: filesandordirs; Name: "{userappdata}\Adobe\CEP\extensions\com.resolvefetch.premiere"
Type: filesandordirs; Name: "{localappdata}\ResolveFetch\logs"
