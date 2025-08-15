"""
Run from the repository root:
    uv run python3 tests/mcp_client_test.py
"""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    print("--- Client script started ---")
    try:
        print("Attempting to connect to streamablehttp_client...")
        async with streamablehttp_client("http://localhost:8775/mcp") as (read_stream, write_stream, _):
            print("Connection to streamablehttp_client successful.")

            print("Creating ClientSession...")
            async with ClientSession(read_stream, write_stream) as session:
                print("ClientSession created.")

                print("Initializing session...")
                await session.initialize()
                print("Session initialized.")

                print("Listing available tools...")
                tools = await session.list_tools()
                print(f"Available tools: {[tool.name for tool in tools.tools]}")
        print("--- Client script finished successfully ---")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
