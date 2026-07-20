@echo off
setlocal
if not defined ADS_INSTALL_ROOT if defined HPEESOF_DIR set "ADS_INSTALL_ROOT=%HPEESOF_DIR%"
if not defined ADS_INSTALL_ROOT for /f "tokens=2,*" %%A in ('reg query "HKLM\SOFTWARE\Keysight\ADS" /s /v HPEESOF_DIR 2^>nul ^| findstr /I "HPEESOF_DIR"') do if not defined ADS_INSTALL_ROOT set "ADS_INSTALL_ROOT=%%B"
if not defined ADS_INSTALL_ROOT (
  echo ADS 2026 was not found. Repair the Keysight registry entry or set ADS_INSTALL_ROOT. 1>&2
  exit /b 1
)
set "HPEESOF_DIR=%ADS_INSTALL_ROOT%"
set "PATH=%ADS_INSTALL_ROOT%\bin;%PATH%"
"%~dp0.venv\Scripts\python.exe" "%~dp0mcp_server.py"
