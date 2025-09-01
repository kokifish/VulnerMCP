# MCP

> [MCP-python-sdk](https://github.com/modelcontextprotocol/python-sdk)
>
> [Quick Start Video on X](https://x.com/sdrzn/status/1867271665086074969) use cline on UI and config for mcp servers

```bash
uv run mcp install main.py # install for Claude Desktop
uv run mcp dev main.py # Run a MCP server with the MCP Inspector
uv run mcp --help # show cmd help
```

## Environment Preparation

An example in vscode and cline:

1. mcp[cli]: `uv add "mcp[cli]"` or `uv pip install "mcp[cli]"`, test with `uv run mcp`
2. npx: [nodejs-install](https://nodejs.org/en/download/current), test with `npm -v`
3. [opt] mcp-servers-config in vscode (Workspace-ver): command+shift+P or F1 -> MCP: Open Workspace Folder MCP Configuration -> add mcp servers's config
4. mcp-servers-config in cline: cline -> mcp-servers -> Installed -> Configure MCP Servers -> copy same config from vscode

> If a wrong LLM used in adding a new mcp server with cline task chat window, mcp servers maybe installed failed. XD
>

## HelloWorld

## Concepts and Development

### Server

- `FastMCP`是MCP的核心介面
- connection management: 连接管理。
- protocol compliance: 协议遵守，协议规范。
- message routing: 消息路由。

### Resources

> they provide data but shouldn't perform significant computation or have side effects

- `Resources`向LLM暴露数据。类似REST API的GET
- 不应有大量计算或有副作用。

### Tools

- `Tools`是LLM通过MCP server操作的接口
- 通常会进行计算、产生副作用
- Tools can optionally receive a Context object by including a parameter with the `Context` type annotation. This context is automatically injected by the FastMCP framework and provides access to MCP capabilities.

```python
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

mcp = FastMCP(name="Progress Example")


@mcp.tool()
async def long_running_task(task_name: str, ctx: Context[ServerSession, None], steps: int = 5) -> str:
    """Execute a task with progress updates."""
    await ctx.info(f"Starting: {task_name}")

    for i in range(steps):
        progress = (i + 1) / steps
        await ctx.report_progress(
            progress=progress,
            total=1.0,
            message=f"Step {i + 1}/{steps}",
        )
        await ctx.debug(f"Completed step {i + 1}")

    return f"Task '{task_name}' completed"
```

### Structured Output

有返回类型注解时`Tools`默认返回结构化数据，否则返回非结构化数据

Structured output supports these return types:

- Pydantic models (BaseModel subclasses)
- TypedDicts
- Dataclasses and other classes with type hints
- `dict[str, T]` (where T is any JSON-serializable type)
- Primitive types (str, int, float, bool, bytes, None) - wrapped in `{"result": value}`
- Generic types (list, tuple, Union, Optional, etc.) - wrapped in `{"result": value}`

Classes without type hints cannot be serialized for structured output. Only classes with properly annotated attributes will be converted to Pydantic models for schema generation and validation. Structured results are automatically validated against the output schema generated from the annotation. This ensures the tool returns well-typed, validated data that clients can easily process.

## An All-in-One demo
