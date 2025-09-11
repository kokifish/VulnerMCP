import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import arkts_api
import mcp.types as types
from mcp.server import Server
from mcp.server.fastmcp.server import Context
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.fastmcp.exceptions import ResourceError
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import AnyUrl, FileUrl, BaseModel, Field


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


class PandaAssemblyModulePath(BaseModel):
    pa_file_path: str = Field(
        ...,
        description="The path to the Panda Assembly format file which is endwith .pa, .dis or .pandasm.",)
    module_path: str = Field(
        ...,
        description="The module name in the Panda Assembly format file.",)

# 获取MCP/VulnerMCP/Vulwebview.abc.dis文件的ABC模块的Panda Assembly格式


async def serve() -> None:
    server = Server("ArkTS_Assembly_Analysis")
    Log.info(f"Starting ArkTS Assembly Analysis MCP server...")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """reponse of Client->Server tools/list request"""
        Log.info(f"tools/list called")
        return [
            Tool(
                name="get_panda_assembly",  # type: str, the function name of this tool
                # actually it just is a display name if you already implemented the call_tool method
                description="Get the decompiled Panda Assembly format assembly code of a module in a file.",
                # the most important field for LLM to understand what this tool is doing
                inputSchema=PandaAssemblyModulePath.model_json_schema()
                # dict[str, Any] # set input schema using pydantic model
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """reponse of Client->Server tools/call request"""
        Log.info(f"tools/call called")
        try:
            match name:
                case "get_panda_assembly":  # case里面的要和 list_tools 里的一一对应
                    pa_file_path = arguments.get("pa_file_path")
                    module_path = arguments.get("module_path")
                    if not pa_file_path:
                        raise ValueError("Missing required argument: pa_file_path")
                    if not module_path:
                        raise ValueError("Missing required argument: module_path")

                    result = "mov a,b; add a,1; ret"

                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=f"{result}")]

        except Exception as e:
            raise ValueError(f"Error processing mcp-server-time query: {str(e)}")

    # @server.list_resources
    # def list_resources() -> list:
    #     module_methd_name_l = arkts_api.get_all_module_method()
    #     return [f"pa://{ele}" for ele in module_methd_name_l]
    # @server.list_resource_templates

    # @server.read_resource("pa://{module_name}/{method_name}")
    @server.read_resource()
    async def get_panda_assembly_resource(uri: AnyUrl):

    def get_panda_assembly_resource(module_name: str, method_name: str, ctx: Context) -> str:
        module_methd_name_l = arkts_api.get_all_module_method()

        if f"{module_name}/{method_name}" not in module_methd_name_l:
            raise ResourceError(f"Unknown module/method name: {module_name}/{method_name}")
        return "mov a,b; add a,1; ret"

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    # debug run: uv run mcp dev ArkTS/mcp_server.py --with-editable .
    asyncio.run(serve())
