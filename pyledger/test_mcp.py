import asyncio
import json
from pyledger.mcp_server import PyLedgerMCPServer

async def test_mcp_server():
    """Test the MCP server functionality."""
    server = PyLedgerMCPServer()
    
    # Test listing tools
    from mcp.types import ListToolsRequest
    tools_result = await server.handle_list_tools(ListToolsRequest(method="tools/list"))
    print("Available tools:")
    for tool in tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # Test listing accounts
    from mcp.types import CallToolRequest, CallToolResult
    request = CallToolRequest(
        method="tools/call", 
        params={"name": "list_accounts", "arguments": {}}
    )
    result = await server.handle_call_tool(request)
    
    print("\nAccounts in the system:")
    print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 