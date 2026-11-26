"""Smoke test: start the gmail-calendar server, list its tools, call list_events.

Run with GOOGLE_PRIVATE_DIR set to your private folder:

    GOOGLE_PRIVATE_DIR=/path/to/private-folder uv run test_server.py
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
EXPECTED_TOOLS = {
    "search_emails",
    "read_email",
    "create_draft",
    "list_events",
    "find_free_slots",
    "create_event",
}


async def main() -> int:
    private_dir = os.environ.get("GOOGLE_PRIVATE_DIR", "")
    if not private_dir or not Path(private_dir).expanduser().is_dir():
        print("FAIL: set GOOGLE_PRIVATE_DIR to the existing folder that holds token.json.", file=sys.stderr)
        return 1
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(HERE / "server.py")],
        env={**os.environ, "GOOGLE_PRIVATE_DIR": private_dir},
        cwd=str(HERE),
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Server started and initialized.\n")

            tools = (await session.list_tools()).tools
            print(f"Tools ({len(tools)}):")
            for tool in tools:
                summary = (tool.description or "").strip().splitlines()[0]
                print(f"  - {tool.name}: {summary}")
            names = {tool.name for tool in tools}
            tools_ok = names == EXPECTED_TOOLS
            print(f"Tool list matches the expected 6: {tools_ok}\n")

            result = await session.call_tool("list_events", {"days_ahead": 1})
            print(f"list_events(days_ahead=1) -> isError={result.isError}")
            for block in result.content:
                print(getattr(block, "text", block))

            passed = tools_ok and not result.isError
            print(f"\n{'PASS' if passed else 'FAIL'}")
            return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
