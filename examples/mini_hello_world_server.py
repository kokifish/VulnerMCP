import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ResourceError, ToolError
from mcp.server.fastmcp.prompts import base
from pydantic import BaseModel, Field

GIT_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log_name = "hello_world"
log_file = os.path.join(GIT_ROOT_PATH, log_name + ".log")
Log = logging.getLogger(log_name)
handle = RotatingFileHandler(log_file, mode="a", maxBytes=50 * 1024 * 1024, backupCount=10, encoding="utf-8", delay=0)
Log.addHandler(handle)

# Create an MCP server
mcp = FastMCP("hello_world")  # corresponding to mcp server name in mcp-servers-config


@mcp.tool("get_location", title="get location",  # tool
          description="get location of the giving user name")
def get_location_of_user(user_name: str = Field(description="developer name of project"), ctx: Context = None) -> str:
    Log.info(f"tool: user_name {user_name} {ctx.model_config} {ctx.fastmcp.name} | {ctx.session.client_params}")
    if user_name == "CoreA" or user_name == "MainA":
        return "SZ"
    if user_name == "CoreB" or user_name == "MainB":
        return "GZ"
    raise ToolError("user name invalid. Check valid user names by resource protocol user://")


@mcp.resource("user://{group}", name="developers",  # resource template
              title="developer groups", description="developer list of specific group in project hello world")
def get_developer(group: str) -> list[str]:
    if group == "core":
        return ["CoreA", "CoreB"]
    elif group == "main":
        return ["MainA", "MainB"]
    raise ResourceError("group invalid. valid groups: core, main")


@mcp.resource("banner://hello", name="hello world banner",  # direct resource
              description="banner of project hello world")
def get_banner() -> str:
    return "Hello, World! Welcome to FastMCP! This is mini version."


@mcp.prompt("get_developers_info", title="get developer's info",
            description="get information of developers in project hello world")
def get_developers_info(group: str) -> list[base.Message]:
    return [
        base.UserMessage(f"I wanna get infomation of developers in project hello world. You should:"),
        base.UserMessage(f"1. get {group} developers by resource user://{group}"),
        base.UserMessage(f"2. get location of each user by tool get_location."),
        base.UserMessage("Combine the response and make a conclusion."),
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")
