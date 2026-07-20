from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    server_path = root / "mcp_server.py"
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(root)})
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        cwd=str(root),
        env=env,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("initialize OK", flush=True)
            tools = await session.list_tools()
            print("list_tools OK", flush=True)
            names = sorted(tool.name for tool in tools.tools)
            expected = "ads_detect_tool"
            assert expected in names
            print(f"calling {expected}", flush=True)
            detected = await session.call_tool(expected, {})
            assert detected.isError is not True
            if os.environ.get("ADS_TEST_LIVE") == "1":
                live_result = await session.call_tool("ads_live_ping_tool", {})
                assert live_result.isError is not True
                print("ads_live_ping_tool call OK")
            print(f"stdio MCP handshake OK; {len(names)} tools")
            print(f"{expected} call OK")


if __name__ == "__main__":
    asyncio.run(main())
