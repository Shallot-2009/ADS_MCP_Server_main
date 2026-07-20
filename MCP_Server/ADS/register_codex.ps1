$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$ConfigDir = Join-Path $HOME '.codex'
$ConfigPath = Join-Path $ConfigDir 'config.toml'
$Begin = '# BEGIN ADS2026 MCP (managed by ADS2026_MCP_Server)'
$End = '# END ADS2026 MCP'

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment is missing. Run setup.ps1 first."
}

$HomeFull = (Resolve-Path -LiteralPath $HOME).Path.TrimEnd('\')
$ProjectFull = (Resolve-Path -LiteralPath $ProjectRoot).Path.TrimEnd('\')
if (-not $ProjectFull.StartsWith($HomeFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'For a path-free global configuration, place ADS2026_MCP_Server under your user profile.'
}
$ProjectRelative = $ProjectFull.Substring($HomeFull.Length).TrimStart('\')
$Launcher = '%USERPROFILE%\' + $ProjectRelative + '\start_mcp.bat'

New-Item -ItemType Directory -Force $ConfigDir | Out-Null
$Existing = if (Test-Path -LiteralPath $ConfigPath) { Get-Content -Raw $ConfigPath } else { '' }
$Pattern = '(?ms)^' + [regex]::Escape($Begin) + '.*?^' + [regex]::Escape($End) + '\r?\n?'
$Existing = [regex]::Replace($Existing, $Pattern, '').TrimEnd()

function TomlLiteral([string]$Value) {
    return "'" + $Value.Replace("'", "''") + "'"
}

$Block = @"
$Begin
[mcp_servers.ads2026]
command = 'cmd.exe'
args = ['/d', '/s', '/c', $(TomlLiteral $Launcher)]
startup_timeout_sec = 60
tool_timeout_sec = 900
$End
"@

$NewContent = if ($Existing) { $Existing + "`r`n`r`n" + $Block } else { $Block }
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ConfigPath, $NewContent + [Environment]::NewLine, $Utf8NoBom)

Write-Host "Registered MCP server 'ads2026' in $ConfigPath" -ForegroundColor Green
Write-Host 'Restart Codex (or start a new task) so it reloads MCP configuration.'
