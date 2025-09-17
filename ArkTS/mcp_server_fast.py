import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from urllib.parse import quote, unquote

import arkts_api
from mcp.server.fastmcp import Context, FastMCP, Image
from mcp.server.models import InitializationOptions
from mcp.types import Tool, ToolAnnotations
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
os.system(f"python {api_py}")  # Initialization of ArkTS reverse API


# Create an MCP server with high-level FastMCP
mcp = FastMCP("ArkTS_Assembly_Analysis")  # corresponding to mcp server name in mcp-servers-config


def create_panda_resource_function(name):
    @mcp.resource(f"panda://{quote(name)}", name=name,
                  title=f"ArkTS Assembly code of {name}",
                  description=f"The ArkTS assembly code (Panda Assembly format) of {name}",
                  mime_type="text/plain")
    def read_panda_assembly() -> str:
        pa_code_str = arkts_api.get_module_method_panda_assembly_code(name)
        Log.info(f"mcp resource read: panda {name} | {quote(name)} | {len(pa_code_str)}")
        return pa_code_str
    return read_panda_assembly


module_method_name_l = arkts_api.get_all_module_method()
Log.info(f"MCP ini: module_method_name_l {len(module_method_name_l)} {module_method_name_l}")
for module_method_name in module_method_name_l:
    # NOTE: 由于 Python 闭包捕获变量引用而非变量值，这里不可以把工厂函数的内容复制过来展开写，否则所有url指向的内容都会是最后注册的内容
    # 所以这里可以用这种简单的写法“倒一手”，让创建的函数用的参数值是module_method_name的值而非其本身。或者可以用 functools.partial
    create_panda_resource_function(module_method_name)


@mcp.resource("panda://{module_method_name}", name="ArkTS Panda Assembly code",
              title=f"ArkTS Assembly code of {module_method_name}",
              description=f"The ArkTS assembly code (Panda Assembly format) of {module_method_name}. Valid resource URL example: panda://Index%26.%23%2A%23 (for specific match of Index&.#*# using URL encoding), panda://*module_name* (for wildcard matching of all methods in module/class named `module_name`). Check URL encoding or use wildcard matching if it still failed.")
def read_panda_assembly_template(module_method_name: str) -> str:
    Log.info(f"mcp resource template read: {module_method_name}")
    try:
        contents: list[str] = arkts_api.read_pa_by_url(AnyUrl(f"panda://{module_method_name}"))
        Log.info(f"mcp resource template read: return len={len(contents)}")
    except Exception as e:
        contents: list[str] = arkts_api.read_pa_by_url(AnyUrl(f"panda://{unquote(module_method_name)}"))
        Log.info(f"mcp resource template read: unquote return len={len(contents)}")
    return "\n".join(contents)


def create_external_resource_function(name):
    @mcp.resource(f"file://{name}", name=name,
                  title=f"Raw content of file {name}",
                  description=f"Raw content of file {name} in the HarmonyOS hap/app package",
                  mime_type="text/plain")
    async def read_external_resource() -> str:
        raw_content = await arkts_api.get_external_file_content(name)
        Log.info(f"mcp resource read: file {name} | {len(raw_content)}")
        return raw_content
    return read_external_resource


external_res_path_l = arkts_api.get_external_text_file_list()
Log.info(f"MCP ini: external_res_path_l {len(external_res_path_l)} {external_res_path_l}")
for res_path in external_res_path_l:
    create_external_resource_function(res_path)


@mcp.tool("get_resource_related", title="get resource related including assmebly code or raw file",
          description="Provide relevant resource(e.g. ArkTS assembly code) based on the ArkTS/panda assembly code or module method name. The assembly code snippets provided should be as complete as possible. If provide a module method name like `module_A.method_B`, it's better to provide a wildcard matching pattern like `module_A.*`",
          annotations=ToolAnnotations(title="get resource related", readOnlyHint=True, openWorldHint=False),
          structured_output=True)
def get_resource_related(code_or_name: str) -> list[str]:
    Log.info(f"get_resource_related: arg={code_or_name}")
    contents: list = []
    if "(any:" not in code_or_name:  # resource url or module method name
        if not code_or_name.startswith("panda://"):
            code_or_name = "panda://" + code_or_name
        try:
            contents: list[str] = arkts_api.read_pa_by_url(AnyUrl(code_or_name))
            Log.info(f"get_resource_related: return len={len(contents)}")
        except Exception as e:
            contents: list[str] = arkts_api.read_pa_by_url(AnyUrl(unquote(code_or_name)))
            Log.info(f"get_resource_related-unquote: return len={len(contents)}")
        return contents
    else:  # code with Panda Assembly format (lifted)
        return get_resource_related(
            AnyUrl(f"panda://&vulwebview.src.main.ets.pages.Index&.#~@0>#aboutToAppear"))


if __name__ == "__main__":
    # debug with inspector: uv run mcp dev ArkTS/mcp_server_fast.py --with-editable .
    # python ArkTS/mcp_server_fast.py
    # cmdline used in cline: uv --directory /Users/koki/git_space/MCP/VulnerMCP/ArkTS run mcp_server_fast.py
    mcp.run(transport="stdio")
