## Keysight ADS MCP Server（Codex）

### [Date] 7 ，21, 2026

### [Source] From Asenjo.HB.L at Beijing.

### [Author's Email] 3405802009@qq.com

### [Copyright] Copyright Asenjo.HB.L . All rights reserved.

本项目使用 ADS 自带的 Python 和 `keysight.ads` API 连接 Codex 与 ADS 2026。ADS 安装目录由环境变量或 Keysight 注册表自动发现，源码中不固化盘符、用户名或项目绝对路径。

项目提供两种工作模式：

- `ads_headless_*`：在 MCP 进程中打开工作区、读取设计、生成网表和运行仿真。
- `ads_live_*`：通过 ADS Addon 操作当前可见的 ADS GUI 会话。

## 1. 安装环境

在项目目录打开 PowerShell：

```powershell
powershell -[README.md](README.md)ExecutionPolicy Bypass -File .\setup.ps1
```

脚本会从 Keysight 注册表自动找到 ADS，并使用 ADS 自带 Python 创建项目内的 `.venv`。

如果注册表损坏，也可以只在本次安装时传入目录：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -AdsRoot "<ADS安装目录>"
```

## 2. 全局配置 Codex

```powershell
powershell -ExecutionPolicy Bypass -File .\register_codex.ps1
```

注册脚本会更新 `%USERPROFILE%\.codex\config.toml`。配置通过 `%USERPROFILE%` 和项目启动器定位，不写入用户名、盘符或 ADS 安装绝对路径。运行后重启 Codex 或新建任务。

## 3. 安装 ADS 实时插件

打开 ADS 2026 的 Python Console，运行：

```python
from pathlib import Path
exec((Path.home() / "Desktop" / "ADS2026_MCP_Server" / "install_addon_in_ads.py").read_text(encoding="utf-8"))
```

也可以在 `Tools > App Manager` 中选择：

```text
%USERPROFILE%\Desktop\ADS2026_MCP_Server\ads_live_bridge\__init__.py
```

插件只监听本机 `127.0.0.1:8765`。

## 4. 验证

在 Codex 中调用：

```text
ads_detect_tool
ads_live_ping_tool
ads_live_workspace_info_tool
```

本地测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe .\tests\smoke_mcp_stdio.py
```

工作区和输出路径可以使用相对路径，例如：

```text
用 ads_headless_open_workspace_tool 打开 .\demo_wrk。
为 demo_lib:top:schematic 生成网表到 .\demo_wrk\top.net。
```

## 安全说明

`ads_headless_execute_python_tool` 和 `ads_live_execute_python_tool` 可以执行 Python，只应执行用户明确授权的代码。不要将实时桥接监听地址改成 `0.0.0.0`。
