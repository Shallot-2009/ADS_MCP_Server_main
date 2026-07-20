## Keysight ADS 2026 MCP Server (Codex)

### [Date] 7 ，21, 2026

### [Source] From Asenjo.HB.L at Beijing.

### [Author's Email] 3405802009@qq.com

### [Copyright] Copyright Asenjo.HB.L . All rights reserved.

This project connects Codex with ADS 2026 using the Python runtime bundled with ADS and the official `keysight.ads` API. The ADS installation directory is automatically discovered through environment variables or the Keysight Windows registry. No drive letter, user name, or absolute project path is hardcoded in the source code.

The project provides two operating modes:

- `ads_headless_*`: Opens workspaces, reads designs, generates netlists, and runs simulations inside the MCP process.
- `ads_live_*`: Controls the currently visible ADS GUI session through an ADS Addon.

## 1. Install the Environment

Open PowerShell in the project directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The script automatically locates ADS through the Keysight registry and uses the Python runtime bundled with ADS to create the project-local `.venv`.

If the registry entry is damaged, you can provide the installation directory for this setup run only:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -AdsRoot "<ADS installation directory>"
```

## 2. Configure Codex Globally

```powershell
powershell -ExecutionPolicy Bypass -File .\register_codex.ps1
```

The registration script updates `%USERPROFILE%\.codex\config.toml`. It locates the project through `%USERPROFILE%` and the project launcher without writing a user name, drive letter, or absolute ADS installation path. Restart Codex or create a new task after running the script.

## 3. Install the ADS Live Addon

Open the Python Console in ADS 2026 and run:

```python
from pathlib import Path
exec((Path.home() / "Desktop" / "ADS2026_MCP_Server" / "install_addon_in_ads.py").read_text(encoding="utf-8"))
```

Alternatively, select the following file in `Tools > App Manager`:

```text
%USERPROFILE%\Desktop\ADS2026_MCP_Server\ads_live_bridge\__init__.py
```

The Addon listens only on the local address `127.0.0.1:8765`.

## 4. Verification

Call the following tools in Codex:

```text
ads_detect_tool
ads_live_ping_tool
ads_live_workspace_info_tool
```

Run the local tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe .\tests\smoke_mcp_stdio.py
```

Workspace and output locations may use relative paths. For example:

```text
Use ads_headless_open_workspace_tool to open .\demo_wrk.
Generate the netlist for demo_lib:top:schematic at .\demo_wrk\top.net.
```

## Security

`ads_headless_execute_python_tool` and `ads_live_execute_python_tool` can execute Python code. Use them only for code explicitly authorized by the user. Do not change the live bridge listening address to `0.0.0.0`.
