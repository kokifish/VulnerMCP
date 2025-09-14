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
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool, ReadResourceResult
from pydantic import AnyUrl, FileUrl, BaseModel, Field
from urllib.parse import unquote, quote
from mcp.server.lowlevel.helper_types import ReadResourceContents
import re

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


class PandaAssemblyModuleMethodName(BaseModel):
    module_method_name: str = Field(
        ...,
        description="The module and method name of the Panda Assembly format file. e.g. A.B means module A method B",)

# 获取MCP/VulnerMCP/Vulwebview.abc.dis文件的ABC模块的Panda Assembly格式


async def serve() -> None:
    server = Server("ArkTS_Assembly_Analysis")  # low-level mcp server
    Log.info(f"Starting ArkTS Assembly Analysis MCP server...")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """reponse of Client->Server tools/list request"""
        Log.info(f"tools/list called")
        return [
            # Tool(
            #     name="get_resource_url_related",  # type: str, the function name of this tool
            #     # actually it just is a display name if you already implemented the call_tool method
            #     description="Provide all possible relevant resource url based on the panda assembly code. The assembly code snippets provided should be as complete as possible.",
            #     # the most important field for LLM to understand what this tool is doing
            #     inputSchema={
            #         "type": "object",
            #         "properties": {"panda_assembly_code": {"type": "string", "description": "The given panda assembly code snippets"}},
            #         "required": ["panda_assembly_code"],
            #     },
            # dict[str, Any] # set input schema using pydantic model
            Tool(
                name="get_resource_related",  # type: str, the function name of this tool
                # actually it just is a display name if you already implemented the call_tool method
                description="Provide all possible relevant resource(e.g. ArkTS assembly code) based on the ArkTS/panda assembly code or moudle method name. The assembly code snippets provided should be as complete as possible.",
                # the most important field for LLM to understand what this tool is doing
                inputSchema={
                    "type": "object",
                    "properties": {"code_or_name": {"type": "string", "description": "panda assembly code snippets or module method name"}},
                    "required": ["code_or_name"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """reponse of Client->Server tools/call request"""
        Log.info(f"tools/call called")
        try:
            match name:
                # case "get_resource_url_related":  # should match the str-id in tools/list
                #     panda_assembly_code = arguments.get("panda_assembly_code")
                #     if not panda_assembly_code:
                #         raise ValueError("Missing required argument: panda_assembly_code")

                #     result = r"panda://%26vulwebview.src.main.ets.pages.Index%26.%23~%400%3E%23aboutToAppear"
                #     return [TextContent(type="text", text=f"{result}")]
                case "get_resource_related":
                    code_or_name = arguments.get("code_or_name")
                    if not code_or_name:
                        raise ValueError("Missing required argument: code_or_name")
                    return await get_resource_related(code_or_name)
                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=f"{result}")]

        except Exception as e:
            raise ValueError(f"Error processing mcp-server-time query: {str(e)}")

    @server.list_resources()
    async def get_all_resources() -> list[types.Resource]:
        module_methd_name_l = arkts_api.get_all_module_method()
        Log.info(f"resource: list. module_methd_name_l len = {len(module_methd_name_l)}")
        pa_resources = [
            types.Resource(
                uri=AnyUrl(f"panda://{quote(module_method_name)}"),
                name=module_method_name,
                title="Panda Assembly of " + module_method_name,
                description="The decompiled assembly code with Panda Assembly format of module.method = "
                + module_method_name,
                mimeType="text/plain",
            )
            for module_method_name in module_methd_name_l
        ]
        return pa_resources

    @server.read_resource()
    async def read_resource_impl(uri: AnyUrl) -> list[ReadResourceContents]:
        Log.info(f"resource: read: {uri} | host:{uri.host} path:{uri.path}")
        if uri.host is None:
            raise ValueError(f"Invalid resource path: {uri}")

        resource_pattern = uri.host
        all_resources = arkts_api.get_all_module_method()

        matched_resources = []
        if "*" in resource_pattern:  # * match mode
            pattern = resource_pattern.replace(".", r"\.").replace("*", ".*")
            regex = re.compile(f"^{pattern}$")
            matched_resources = [quote(res) for res in all_resources if regex.match(quote(res))]
        elif unquote(resource_pattern) in all_resources:
            matched_resources = [unquote(resource_pattern)]
        else:
            matched_resources = [s for s in all_resources if unquote(resource_pattern) in s]
            if len(matched_resources) == 0:
                raise ResourceError(f"Unknown module.method name: {resource_pattern}")

        contents: list[ReadResourceContents] = []
        for resource in matched_resources:
            decoded_name = unquote(resource)
            asm_txt = arkts_api.get_module_method_panda_assembly_code(decoded_name)
            if len(asm_txt) > 0:
                contents.append(ReadResourceContents(content=asm_txt, mime_type="text/plain"))
        return contents

    async def get_resource_related(code_or_name: str) -> list:
        Log.info(f"get_resource_related: read: {code_or_name}")
        contents: list = []
        if "(any:" not in code_or_name:  # resource url or module method name
            code_or_name = code_or_name.lstrip("panda://")
            resource_content = await server.read_resource(AnyUrl(f"panda://{code_or_name}"))
        else:  # code with Panda Assembly format (lifted)
            resource_content = await server.read_resource(
                AnyUrl(f"panda://&vulwebview.src.main.ets.pages.Index&.#~@0>#aboutToAppear"))
        for item in resource_content:
            contents.append(TextContent(type="text", text=item.content))
        return contents

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    # debug run: npx @modelcontextprotocol/inspector uv --directory /Users/koki/git_space/MCP/VulnerMCP/ArkTS/ run mcp_server.py
    # debug run: uv run mcp dev ArkTS/mcp_server.py --with-editable .
    asyncio.run(serve())
