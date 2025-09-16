import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from urllib.parse import quote, unquote

import arkts_api
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool, ToolAnnotations
from pydantic import AnyUrl, BaseModel, Field, FileUrl

VULMCP_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log_name = "ArkTS_MCP"
log_file = os.path.join(VULMCP_ROOT_PATH, log_name + ".log")
Log = logging.getLogger(log_name)
handle = RotatingFileHandler(log_file, mode="a", maxBytes=50 * 1024 * 1024, backupCount=10, encoding="utf-8", delay=0)
handle.setLevel(logging.INFO)
handle.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
Log.addHandler(handle)


if os.path.exists(arkts_api.LOCAL_DEFAULT_PANDARE_PKL):
    os.remove(arkts_api.LOCAL_DEFAULT_PANDARE_PKL)
api_py = os.path.join(VULMCP_ROOT_PATH, "ArkTS", "arkts_api.py")
os.system(f"python {api_py}")

module_method_name_l = arkts_api.get_all_module_method()


# Create an MCP server with high-level FastMCP
mcp = FastMCP("ArkTS_Assembly_Analysis")  # corresponding to mcp server name in mcp-servers-config

for module_method_name in module_method_name_l:
    @mcp.resource(f"panda://{quote(module_method_name)}", name=module_method_name,
                  title=f"ArkTS Assembly code of {module_method_name}",
                  description=f"The ArkTS assembly code (Panda Assembly format) of {module_method_name}.",
                  mime_type="text/plain")
    async def read_panda_assembly() -> str:
        return await arkts_api.get_module_method_panda_assembly_code(module_method_name)


@mcp.resource("panda://{module_method_name}", name="ArkTS Panda Assembly code",
              title=f"ArkTS Assembly code of the giving module method name with URL encoding",
              description=f"The ArkTS assembly code (Panda Assembly format) of the giving module method name with URL encoding. Valid resource URL example: panda://Index%26.%23%2A%23 (for specific match of Index&.#*# using URL encoding), panda://*module_name* (for wildcard matching of all methods in module/class named `module_name`). Check URL encoding or use wildcard matching if it still failed.",
              mime_type="text/plain")
async def read_panda_assembly_template(module_method_name: str) -> str:
    contents: list[str] = await arkts_api.read_pa_by_url(AnyUrl(f"panda://{module_method_name}"))
    return "\n".join(contents)


@mcp.tool("get_resource_related", title="get resource related including assmebly code or raw file",
          description="Provide relevant resource(e.g. ArkTS assembly code) based on the ArkTS/panda assembly code or module method name. The assembly code snippets provided should be as complete as possible. If provide a module method name like `module_A.method_B`, it's better to provide a wildcard matching pattern like `module_A.*`",
          annotations=ToolAnnotations(
              title="get resource related including assmebly code or raw file", readOnlyHint=True))
async def get_resource_related(code_or_name: str) -> list[str]:
    Log.info(f"get_resource_related: arg={code_or_name}")
    contents: list = []
    if "(any:" not in code_or_name:  # resource url or module method name
        if not code_or_name.startswith("panda://"):
            code_or_name = "panda://" + code_or_name

        contents: list[str] = await arkts_api.read_pa_by_url(AnyUrl(code_or_name))
        Log.info(f"get_resource_related: return len={len(contents)}, {type(contents)}")
        return contents
    else:  # code with Panda Assembly format (lifted)
        return get_resource_related(
            AnyUrl(f"panda://&vulwebview.src.main.ets.pages.Index&.#~@0>#aboutToAppear"))


if __name__ == "__main__":
    # debug with inspector: uv run mcp dev ArkTS/mcp_server_fast.py --with-editable .
    # python ArkTS/mcp_server_fast.py
    # cmdline used in cline: uv --directory /Users/koki/git_space/MCP/VulnerMCP/ArkTS run mcp_server_fast.py
    asyncio.run(mcp.run(transport="stdio"))
