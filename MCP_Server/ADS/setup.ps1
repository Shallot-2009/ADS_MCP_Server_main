param([string]$AdsRoot = '')

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-AdsRoot([string]$RequestedRoot) {
    $Candidates = @($RequestedRoot, $env:ADS_INSTALL_ROOT, $env:HPEESOF_DIR) | Where-Object { $_ }
    $RegistryBase = 'HKLM:\SOFTWARE\Keysight\ADS'
    if (Test-Path -LiteralPath $RegistryBase) {
        $Candidates += Get-ChildItem -LiteralPath $RegistryBase -ErrorAction SilentlyContinue |
            Sort-Object PSChildName -Descending |
            ForEach-Object { (Get-ItemProperty -LiteralPath (Join-Path $_.PSPath 'eeenv') -ErrorAction SilentlyContinue).HPEESOF_DIR }
    }
    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path -LiteralPath (Join-Path $Candidate 'tools\python\python.exe'))) {
            return (Resolve-Path -LiteralPath $Candidate).Path
        }
    }
    throw 'ADS 2026 was not found. Repair the Keysight registry entry or pass -AdsRoot once.'
}

$AdsRoot = Resolve-AdsRoot $AdsRoot
$AdsPython = Join-Path $AdsRoot 'tools\python\python.exe'
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $AdsPython)) {
    throw "ADS bundled Python was not found: $AdsPython"
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    & $AdsPython -m venv --system-site-packages (Join-Path $ProjectRoot '.venv')
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "$ProjectRoot[dev]"

$env:HPEESOF_DIR = $AdsRoot
$env:ADS_INSTALL_ROOT = $AdsRoot
$env:PATH = "$(Join-Path $AdsRoot 'bin');$env:PATH"
& $VenvPython -c "from ads_runtime import ADSRuntime; import json; print(json.dumps(ADSRuntime().detect(), ensure_ascii=False, indent=2))"

Write-Host ''
Write-Host 'Setup completed.' -ForegroundColor Green
Write-Host "MCP Python: $VenvPython"
Write-Host "Next: run .\register_codex.ps1, then restart Codex."
