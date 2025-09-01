"""
FastMCP Helloworld modified from https://github.com/modelcontextprotocol/python-sdk.
    uv run [this_py_name] fastmcp_quickstart stdio
"""

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("demo")  # corresponding to mcp server name in mcp-servers-config
print("MCP server created.")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    # how to test on cline: 计算1+2的结果，用mcp demo
    # or: calculate the result of 1 + 2 using mcp demo
    print(f"[mcp-tool] add {a} {b}")
    return a - b


@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    # how to test on cline: Get a personalized greeting to "OH" using mcp demo
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="stdio")
