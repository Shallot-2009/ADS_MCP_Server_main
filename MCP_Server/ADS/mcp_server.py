from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ads_runtime import ADSLiveClient, ADSRuntime


INSTRUCTIONS = """Control Keysight ADS 2026 through native Python APIs.

There are two modes:
1. ads_headless_* tools run in the MCP process using ADS's bundled Python.
2. ads_live_* tools call the addon inside the visible ADS GUI.

Prefer native ADS database operations over mouse/keyboard automation. Inspect
the workspace and design before modifying it. Save designs before simulation.
Use ads_live_execute_python_tool only for code the user has authorized.
"""

mcp = FastMCP("keysight-ads2026-mcp", instructions=INSTRUCTIONS)
runtime = ADSRuntime()
runtime.preload()
live = ADSLiveClient()


@mcp.tool()
async def ads_detect_tool() -> dict[str, Any]:
    """Detect ADS 2026, bundled Python, simulator, and Python API availability."""
    return runtime.detect()


@mcp.tool()
async def ads_launch_gui_tool(workspace_path: str | None = None, extra_args: list[str] | None = None) -> dict[str, Any]:
    """Launch the ADS GUI, optionally passing a workspace path."""
    return runtime.launch_gui(workspace_path=workspace_path, extra_args=extra_args)


@mcp.tool()
async def ads_headless_workspace_info_tool() -> dict[str, Any]:
    """Return the workspace open in the MCP's headless ADS automation session."""
    return runtime.workspace_info()


@mcp.tool()
async def ads_headless_open_workspace_tool(path: str, force: bool = False) -> dict[str, Any]:
    """Open an existing ADS workspace in the headless automation session."""
    return runtime.open_workspace(path=path, force=force)


@mcp.tool()
async def ads_headless_create_workspace_tool(path: str, open_after_create: bool = True) -> dict[str, Any]:
    """Create a new ADS workspace and optionally open it."""
    return runtime.create_workspace(path=path, open_after_create=open_after_create)


@mcp.tool()
async def ads_headless_close_workspace_tool() -> dict[str, Any]:
    """Close the headless ADS workspace. Unsaved changes are discarded by ADS."""
    return runtime.close_workspace()


@mcp.tool()
async def ads_headless_list_designs_tool(include_read_only: bool = False) -> dict[str, Any]:
    """List library/cell/view designs in the headless ADS workspace."""
    return runtime.list_designs(include_read_only=include_read_only)


@mcp.tool()
async def ads_headless_design_summary_tool(design_name: str, max_instances: int = 500) -> dict[str, Any]:
    """Summarize an ADS design such as 'my_lib:cell1:schematic'."""
    return runtime.design_summary(design_name=design_name, max_instances=max_instances)


@mcp.tool()
async def ads_headless_generate_netlist_tool(design_name: str, output_path: str | None = None) -> dict[str, Any]:
    """Generate an ADS netlist from a schematic and optionally save it."""
    return runtime.generate_netlist(design_name=design_name, output_path=output_path)


@mcp.tool()
async def ads_headless_run_simulation_tool(
    netlist_path: str,
    cwd: str | None = None,
    extra_args: list[str] | None = None,
    timeout_seconds: float = 600.0,
) -> dict[str, Any]:
    """Run hpeesofsim.exe on an ADS netlist and return stdout/stderr."""
    return runtime.run_simulation(
        netlist_path=netlist_path,
        cwd=cwd,
        extra_args=extra_args,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
async def ads_headless_execute_python_tool(code: str) -> dict[str, Any]:
    """Execute Python in the headless ADS session.

    Available variables: de, runtime, Path. Assign `result` to return data.
    """
    return runtime.run_python(code)


@mcp.tool()
async def ads_live_ping_tool() -> dict[str, Any]:
    """Check whether the ADS GUI live-bridge addon is running."""
    return live.ping()


@mcp.tool()
async def ads_live_status_tool() -> dict[str, Any]:
    """Diagnose ADS GUI process, addon files, port, and live-bridge connectivity."""
    return live.status()


@mcp.tool()
async def ads_live_ensure_tool(
    launch_if_needed: bool = True,
    wait_seconds: float = 60.0,
    poll_seconds: float = 1.0,
) -> dict[str, Any]:
    """Ensure the ADS GUI live bridge is ready, launching ADS when it is not running."""
    return live.ensure_ready(
        runtime=runtime,
        launch_if_needed=launch_if_needed,
        wait_seconds=wait_seconds,
        poll_seconds=poll_seconds,
    )


@mcp.tool()
async def ads_live_workspace_info_tool() -> dict[str, Any]:
    """Read workspace information from the visible ADS GUI."""
    return live.workspace_info()


@mcp.tool()
async def ads_live_list_designs_tool() -> dict[str, Any]:
    """List writable designs in the workspace open in the ADS GUI."""
    return live.list_designs()


@mcp.tool()
async def ads_live_open_workspace_tool(path: str, force: bool = False) -> dict[str, Any]:
    """Open an ADS workspace in the visible ADS GUI."""
    return live.open_workspace(path=path, force=force)


@mcp.tool()
async def ads_live_zoom_all_tool() -> dict[str, Any]:
    """Run ADS View All in the active schematic/layout window."""
    return live.zoom_all()


@mcp.tool()
async def ads_live_execute_python_tool(code: str) -> dict[str, Any]:
    """Execute authorized Python on ADS's GUI main thread.

    Available variables: de, ael, app, Path. Assign `result` to return data.
    """
    return live.execute_python(code)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
