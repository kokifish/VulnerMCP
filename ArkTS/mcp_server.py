import asyncio
import fnmatch
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from urllib.parse import quote, unquote

import arkts_api
import mcp.types as types
from mcp.server import Server

from mcp.shared.context import RequestContext
from mcp.server.fastmcp.server import Context
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    ReadResourceResult,
    TextContent,
    Tool,
)
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


class PandaAssemblyModuleMethodName(BaseModel):
    module_method_name: str = Field(
        ...,
        description="The module and method name of the Panda Assembly format file. e.g. A.B means module A method B",)


async def get_resource_related(code_or_name: str) -> list[TextContent]:
    Log.info(f"get_resource_related: read: {code_or_name}")
    contents: list = []
    if "(any:" not in code_or_name:  # resource url or module method name
        if not code_or_name.startswith("panda://"):
            code_or_name = "panda://" + code_or_name

        contents = await arkts_api.read_pa_by_url(AnyUrl(code_or_name))

        if len(contents):
            return [TextContent(type="text", text=asm_txt) for asm_txt in contents]
        else:
            return []
    else:  # code with Panda Assembly format (lifted)
        return get_resource_related(
            AnyUrl(f"panda://&vulwebview.src.main.ets.pages.Index&.#~@0>#aboutToAppear"))


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
            #     inputSchema={
            #         "type": "object",
            #         "properties": {"panda_assembly_code": {"type": "string", "description": "The given panda assembly code snippets"}},
            #     },
            Tool(
                name="get_resource_related",  # type: str, the function name of this tool
                # actually it just is a display name if you already implemented the call_tool method
                description="Provide relevant resource(e.g. ArkTS assembly code) based on the ArkTS/panda assembly code or module method name. The assembly code snippets provided should be as complete as possible. If provide a module method name like `module_A.method_B`, it's better to provide a wildcard matching pattern like `module_A.*`",
                # the most important field for LLM to understand what this tool is doing
                inputSchema={
                    "type": "object",
                    "properties": {"code_or_name": {"type": "string", "description": "Panda assembly code snippets or module method name."}},
                    "required": ["code_or_name"],
                },  # dict[str, Any] # set input schema using pydantic model
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """reponse of Client->Server tools/call request"""
        Log.info(f"tools/call called")
        match name:
            # case "get_resource_url_related":  # should match the str-id in tools/list
            #     panda_assembly_code = arguments.get("panda_assembly_code")
            #     if not panda_assembly_code:
            #         raise ValueError("Missing required argument: panda_assembly_code")
            #     return [TextContent(type="text", text=r"panda://%26vulwebview.src.main.ets.pages.Index%26.%23~%400%3E%23aboutToAppear")]
            case "get_resource_related":
                code_or_name = arguments.get("code_or_name")
                if not code_or_name:
                    raise ValueError("Missing required argument: code_or_name")
                return await get_resource_related(code_or_name)
            case _:
                raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=f"{result}")]

    @server.list_resources()
    async def list_all_resources() -> list[types.Resource]:
        module_methd_name_l = await arkts_api.get_all_module_method()
        Log.info(f"resource: list. module_methd_name_l len = {len(module_methd_name_l)}")
        pa_resources = [
            types.Resource(
                uri=AnyUrl(f"panda://{quote(module_method_name)}"),  # quote(module_method_name)
                name=module_method_name,
                title="Panda Assembly of " + module_method_name,
                description=f"The ArkTS decompiled assembly code with Panda Assembly format of {module_method_name}",
                mimeType="text/plain",
            )
            for module_method_name in module_methd_name_l
        ]
        return pa_resources

    @server.read_resource()
    async def read_resource_impl(uri: AnyUrl) -> list[ReadResourceContents]:
        contents = await arkts_api.read_pa_by_url(uri)
        return [ReadResourceContents(content=asm_txt, mime_type="text/plain") for asm_txt in contents]

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        """reponse of Client->Server prompts/list request"""
        return [
            types.Prompt(
                name="example-prompt",
                description="An example prompt template",
                arguments=[types.PromptArgument(name="arg1", description="Example argument", required=True)],
            )
        ]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    # debug run: npx @modelcontextprotocol/inspector uv --directory /Users/koki/git_space/MCP/VulnerMCP/ArkTS/ run mcp_server.py
    # debug run: uv run mcp dev ArkTS/mcp_server.py --with-editable .
    asyncio.run(serve())
