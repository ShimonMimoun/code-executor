import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def run():
    url = "http://127.0.0.1:8000/api/v1/mcp/sse"
    print(f"Connecting to {url}...")
    
    async with sse_client(url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            print("Successfully initialized MCP session.")
            
            # List tools
            tools = await session.list_tools()
            print("Available tools:")
            for t in tools.tools:
                print(f" - {t.name}")
                
            # Call tool
            print("\nExecuting code via MCP...")
            result = await session.call_tool(
                "execute_code",
                {
                    "language": "python",
                    "version": "3.12",
                    "code": "print('Hello directly from MCP execution!')",
                }
            )
            
            print("\nExecution Output:")
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(run())
