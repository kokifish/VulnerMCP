from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ResourceError, ToolError

# Create an MCP server
mcp = FastMCP("hello_world")  # corresponding to mcp server name in mcp-servers-config


@mcp.tool("get_location", title="get location", description="get location of the giving user name")
def get_location_of_user(user_name: str) -> str:
    if user_name == "CoreA" or user_name == "MainA":
        return "SZ"
    if user_name == "CoreB" or user_name == "MainB":
        return "GZ"
    raise ToolError("user name invalid. Check valid user names by resource protocol user://")


@mcp.resource("user://{group}", name="developers",
              description="developer list of specific group in project hello world")
def get_developer(group: str) -> list[str]:
    if group == "core":
        return ["CoreA", "CoreB"]
    elif group == "main":
        return ["MainA", "MainB"]
    raise ResourceError("group invalid. valid groups: core, main")


@mcp.resource("banner://hello", name="hello world banner", description="banner of project hello world")
def get_banner() -> str:
    return "Hello, World! Welcome to FastMCP! This is mini version."


if __name__ == "__main__":
    mcp.run(transport="stdio")
