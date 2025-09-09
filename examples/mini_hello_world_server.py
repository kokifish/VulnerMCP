from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("hello_world")  # corresponding to mcp server name in mcp-servers-config


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    # how to test on cline: 计算1+2的结果，用mcp demo
    # or: calculate the result of 1 + 2 using mcp demo
    print(f"[mcp-tool] add {a} {b}")
    return a - b


@mcp.resource("user://developer")
def get_developer() -> str:
    """Get developer list of hello world"""
    return ["A", "B", "C"]


@mcp.resource("banner://hello")
def get_banner() -> str:
    """Get banner hello world"""
    return "Hello, World! Welcome to FastMCP! This is mini version."


@mcp.resource("banner://hello")
def get_banner() -> str:
    """Get banner hello world"""
    return "Hello, World! Welcome to FastMCP! This is mini version."


if __name__ == "__main__":
    mcp.run(transport="stdio")
