import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from urllib.parse import quote, unquote

import arkts_api
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ResourceError
from mcp.server.fastmcp.server import Context
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import AnyUrl, BaseModel, Field, FileUrl

VULMCP_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr
)
log_name = "ArkTS_MCP"
log_file = os.path.join(VULMCP_ROOT_PATH, log_name + ".log")
Log = logging.getLogger(log_name)
handle = RotatingFileHandler(log_file, mode="a", maxBytes=50 * 1024 * 1024,
                             backupCount=10, encoding="utf-8", delay=0)
handle.setLevel(logging.INFO)
handle.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
Log.addHandler(handle)
Log.setLevel(logging.DEBUG)

# Create an MCP server
mcp = FastMCP("ArkTS_Assembly_Analysis")  # corresponding to mcp server name in mcp-servers-config


@mcp.resource("panda://{module_method_name}")
def get_panda_assembly_resource(module_method_name: str) -> str:
    """Read the decompiled assembly code with Panda Assembly format of a module's method with ArkTS.

    Args:
        module_method_name: module name and method name, combined with {module_name}.{method_name}
    Returns:
        str: Assembly code with Panda Assembly format.
    """
    module_methd_name_l = arkts_api.get_all_module_method()
    decoded_module_method_name = unquote(module_method_name)
    Log.info(f"resource: {module_method_name} -> {decoded_module_method_name}")
    if f"{decoded_module_method_name}" not in module_methd_name_l:
        raise ResourceError(f"Unknown module.method name: {decoded_module_method_name}")
    return arkts_api.get_module_method_panda_assembly_code(decoded_module_method_name)


if __name__ == "__main__":
    # debug with inspector: uv run mcp dev ArkTS/mcp_server_fast.py --with-editable .
    asyncio.run(mcp.run(transport="stdio"))
