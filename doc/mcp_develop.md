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

### Resources: Expose Data

> they provide data but shouldn't perform significant computation or have side effects

- `Resources`向LLM暴露数据。类似REST API的GET
- 不应有大量计算或有副作用。

### Tools: Take Action

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

Classes without type hints cannot be serialized for structured output. Only classes with properly annotated attributes will be converted to `Pydantic` models for schema generation and validation. 没有类型注释的类无法被序列化为结构化输出。只有正确注释属性的类才会被转换为Pydantic模型进行schema生成和验证。

Structured results are automatically validated against the output schema generated from the annotation. 结构化结果会用注解生成的输出模式做自动验证。 This ensures the tool returns well-typed, validated data that clients can easily process. 

> In cases where a tool function's return type annotation causes the tool to be classified as structured *and this is undesirable*, the classification can be suppressed by passing `structured_output=False` to the `@tool` decorator. 如果`tool`函数的返回类型注解导致`tool`被分类为结构化的 是非预期的，可以传递`structured_output=False`给`@tool`装饰器来抑制分类

- https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/snippets/servers/structured_output.py

### Prompts

Prompts are reusable templates that help LLMs interact with your server effectively. `Prompts`是帮助LLM与你的服务器高效交互的可重用模版。

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP(name="Prompt Example")


@mcp.prompt(title="Code Review")
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"


@mcp.prompt(title="Debug Assistant")
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]
```

### Images: Handle Image

FastMCP provides an `Image` class that automatically handles image data:

```python
"""Example showing image handling with FastMCP."""

from PIL import Image as PILImage
from mcp.server.fastmcp import FastMCP, Image

mcp = FastMCP("Image Example")

@mcp.tool() # 这个案例在tool里面用 fastmcp.Image
def create_thumbnail(image_path: str) -> Image:
    """Create a thumbnail from an image"""
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png") # 这里用mcp的Image返回
```



### Context

- `tool`, `resource`中用`Context`只需传递一个`Context`注解的参数（参数名字无要求）

```python
from mcp.server.fastmcp import Context, FastMCP
mcp = FastMCP(name="Context Example")

@mcp.tool()
async def my_tool(x: int, ctx: Context) -> str:
    """Tool that uses context capabilities."""
    # The context parameter can have any name as long as it's type-annotated
    return await process_with_context(x, ctx)
```



#### Context Properties and Methods

- `ctx.request_id` - Unique ID for the current request
- `ctx.client_id` - Client ID if available
- `ctx.fastmcp` - Access to the FastMCP server instance (see [FastMCP Properties](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#fastmcp-properties))
- `ctx.session` - Access to the underlying session for advanced communication (see [Session Properties and Methods](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#session-properties-and-methods))
- `ctx.request_context` - Access to request-specific data and lifespan resources (see [Request Context Properties](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#request-context-properties))
- `await ctx.debug(message)` - Send debug log message
- `await ctx.info(message)` - Send info log message
- `await ctx.warning(message)` - Send warning log message
- `await ctx.error(message)` - Send error log message
- `await ctx.log(level, message, logger_name=None)` - Send log with custom level
- `await ctx.report_progress(progress, total=None, message=None)` - Report operation progress
- `await ctx.read_resource(uri)` - Read a resource by URI
- `await ctx.elicit(message, schema)` - Request additional information from user with validation





### Completions: Completion Suggestions

MCP supports providing completion suggestions for prompt arguments and resource template parameters. 为prompt参数/资源模版参数 提供补全建议。With the context parameter, servers can provide completions based on previously resolved values:

Server side: https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/snippets/servers/completion.py

Client usage: https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/snippets/clients/completion_client.py

```python
"""
cd to the `examples/snippets` directory and run:
    uv run completion-client
"""

import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import PromptReference, ResourceTemplateReference

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="uv",  # Using uv to run the server
    args=["run", "server", "completion", "stdio"],  # Server with completion support
    env={"UV_INDEX": os.environ.get("UV_INDEX", "")},
)


async def run():
    """Run the completion client example."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session: # 创建 mcp client session（一次对话？）
            # Initialize the connection
            await session.initialize()

            # List available resource templates
            templates = await session.list_resource_templates() # mcp server的资源模版
            print("Available resource templates:")
            for template in templates.resourceTemplates:
                print(f"  - {template.uriTemplate}")

            # List available prompts
            prompts = await session.list_prompts() # mcp server的prompts
            print("\nAvailable prompts:")
            for prompt in prompts.prompts:
                print(f"  - {prompt.name}")

            # Complete resource template arguments
            if templates.resourceTemplates:
                template = templates.resourceTemplates[0]
                print(f"\nCompleting arguments for resource template: {template.uriTemplate}")

                # Complete without context # 会调用到 mcp server 的 @mcp.completion()
                result = await session.complete(
                    ref=ResourceTemplateReference(type="ref/resource", uri=template.uriTemplate),
                    argument={"name": "owner", "value": "model"},
                )
                print(f"Completions for 'owner' starting with 'model': {result.completion.values}")

                # Complete with context - repo suggestions based on owner
                result = await session.complete(
                    ref=ResourceTemplateReference(type="ref/resource", uri=template.uriTemplate),
                    argument={"name": "repo", "value": ""},
                    context_arguments={"owner": "modelcontextprotocol"},
                )
                print(f"Completions for 'repo' with owner='modelcontextprotocol': {result.completion.values}")

            # Complete prompt arguments
            if prompts.prompts:
                prompt_name = prompts.prompts[0].name
                print(f"\nCompleting arguments for prompt: {prompt_name}")

                result = await session.complete(
                    ref=PromptReference(type="ref/prompt", name=prompt_name),
                    argument={"name": "style", "value": ""},
                )
                print(f"Completions for 'style' argument: {result.completion.values}")


def main():
    """Entry point for the completion client."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
```



### Elicitation: Request Info from User

> 启发功能 https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation

Elicitation通过让用户输入嵌套在其它mcp server feature中来实现可交互的工作流。mcp-protocol本身不限定Elicitation出现的位置，也不要求使用任何用户交互模型

Request additional information from users. 向用户请求更多info/action. This example shows an Elicitation during a Tool Call:

```python
from pydantic import BaseModel, Field

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

mcp = FastMCP(name="Elicitation Example")


class BookingPreferences(BaseModel):
    """Schema for collecting user preferences."""

    checkAlternative: bool = Field(description="Would you like to check another date?")
    alternativeDate: str = Field(
        default="2024-12-26",
        description="Alternative date (YYYY-MM-DD)",
    )


@mcp.tool()
async def book_table(date: str, time: str, party_size: int, ctx: Context[ServerSession, None]) -> str:
    """Book a table with date availability check."""
    # Check if date is available
    if date == "2024-12-25":
        # Date unavailable - ask user for alternative
        result = await ctx.elicit(
            message=(f"No tables available for {party_size} on {date}. Would you like to try another date?"),
            schema=BookingPreferences,
        )

        if result.action == "accept" and result.data:
            if result.data.checkAlternative:
                return f"[SUCCESS] Booked for {result.data.alternativeDate}"
            return "[CANCELLED] No booking made"
        return "[CANCELLED] Booking cancelled"

    # Date available
    return f"[SUCCESS] Booked for {date} at {time}"
```



The `elicit()` method returns an `ElicitationResult` with:

- `action`: "accept", "decline", or "cancel" 三种状态：接受、拒绝、取消
- `data`: The validated response (only when accepted)
- `validation_error`: Any validation error message

### Sampling

> 原义为采样，功能是mcp server接收到某个参数的请求时，将这个参数包装成prompt，再向LLM提问。这里sampling的含义代表的是啥？
>
> https://modelcontextprotocol.io/specification/2025-06-18/client/sampling

`tool`可以通过`sampling`(generating text)和LLM交互。Tools can interact with LLMs through sampling (generating text):

```python
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.types import SamplingMessage, TextContent

mcp = FastMCP(name="Sampling Example")


@mcp.tool()
async def generate_poem(topic: str, ctx: Context[ServerSession, None]) -> str:
    """Generate a poem using LLM sampling."""
    prompt = f"Write a short poem about {topic}" # LLM调mcp server后，mcp server将参数组合成prompt，再向LLM发送消息

    result = await ctx.session.create_message( # 这里会和LLM交互
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        max_tokens=100,
    )

    if result.content.type == "text":
        return result.content.text
    return str(result.content)
```





### Logging and Notifications

使用`Context`做logging和notify。logging是与LLM无关的？notify应该也和LLM无关？

Tools can send logs and notifications through the context:

```python
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

mcp = FastMCP(name="Notifications Example")


@mcp.tool()
async def process_data(data: str, ctx: Context[ServerSession, None]) -> str:
    """Process data with logging."""
    # Different log levels
    await ctx.debug(f"Debug: Processing '{data}'")
    await ctx.info("Info: Starting processing")
    await ctx.warning("Warning: This is experimental")
    await ctx.error("Error: (This is just a demo)")

    # Notify about resource changes
    await ctx.session.send_resource_list_changed()

    return f"Processed: {data}"
```



### Authentication

Authentication can be used by servers that want to expose tools accessing protected resources.

**Architecture:**

- **Authorization Server (AS)**: Handles OAuth flows, user authentication, and token issuance
- **Resource Server (RS)**: Your MCP server that validates tokens and serves protected resources
- **Client**: Discovers AS through RFC 9728, obtains tokens, and uses them with the MCP server

### FastMCP Properties: ctx.fastmcp

可以通过`ctx.fastmcp`读写`FastMCP` server 实例的属性/元数据。The FastMCP server instance accessible via `ctx.fastmcp` provides access to server configuration and metadata:

- `ctx.fastmcp.name` - The server's name as defined during initialization
- `ctx.fastmcp.instructions` - Server instructions/description provided to clients
- `ctx.fastmcp.settings` - Complete server configuration object containing:
  - `debug` - Debug mode flag
  - `log_level` - Current logging level
  - `host` and `port` - Server network configuration
  - `mount_path`, `sse_path`, `streamable_http_path` - Transport paths
  - `stateless_http` - Whether the server operates in stateless mode
  - And other configuration options



### Session Properties and Methods: ctx.session

 `ctx.session` 提供client通信的高级控制。The session object accessible via `ctx.session` provides advanced control over client communication:

- `ctx.session.client_params` - Client initialization parameters and declared capabilities
- `await ctx.session.send_log_message(level, data, logger)` - Send log messages with full control
- `await ctx.session.create_message(messages, max_tokens)` - Request LLM sampling/completion 除了这个，貌似都属于logging功能或read方法
- `await ctx.session.send_progress_notification(token, progress, total, message)` - Direct progress updates
- `await ctx.session.send_resource_updated(uri)` - Notify clients that a specific resource changed
- `await ctx.session.send_resource_list_changed()` - Notify clients that the resource list changed
- `await ctx.session.send_tool_list_changed()` - Notify clients that the tool list changed
- `await ctx.session.send_prompt_list_changed()` - Notify clients that the prompt list changed



### Request Context Properties: ctx.request_context

The request context accessible via `ctx.request_context` contains request-specific information and resources:

- `ctx.request_context.lifespan_context` - Access to resources initialized during server startup
  - Database connections, configuration objects, shared services
  - Type-safe access to resources defined in your server's lifespan function
- `ctx.request_context.meta` - Request metadata from the client including:
  - `progressToken` - Token for progress notifications
  - Other client-provided metadata
- `ctx.request_context.request` - The original MCP request object for advanced processing
- `ctx.request_context.request_id` - Unique identifier for this request

## Running MCP Server

> 大致分为这几种：
>
> - Claude Install: `uv run mcp install server.py`
> - MCP Inspector: `uv run mcp dev server.py [--with pandas --with numpy] [--with-editable .]`
> - Direct Execution: `python server.py` or `uv run mcp run server.py` 不支持low-level server variant，只支持`FastMCP`
> - HTTP

### Develop Mode: Inspector

The fastest way to test and debug your server is with the MCP Inspector:

```bash
uv run mcp dev server.py

# Add dependencies
uv run mcp dev server.py --with pandas --with numpy

# Mount local code
uv run mcp dev server.py --with-editable .
```

## Advanced Usage

### Low-Level Server

> Caution: The `uv run mcp run` and `uv run mcp dev` tool doesn't support low-level server.

#### Structured Output Support

```python
"""
Run from the repository root:
    uv run examples/snippets/servers/lowlevel/structured_output.py
"""

import asyncio
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

server = Server("example-server")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools with structured output schemas."""
    return [ # List of Tool
        types.Tool(
            name="get_weather",  # tool的函数名
            description="Get current weather for a city",
            inputSchema={  # LLM调MCP Server tool的入参
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name"}},
                "required": ["city"],  # 必选参数
            },
            outputSchema={
                "type": "object",  # 指定 Structured data only
                "properties": {
                    "temperature": {"type": "number", "description": "Temperature in Celsius"},
                    "condition": {"type": "string", "description": "Weather condition"},
                    "humidity": {"type": "number", "description": "Humidity percentage"},
                    "city": {"type": "string", "description": "City name"},
                },
                "required": ["temperature", "condition", "humidity", "city"],  # 必选字段
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle tool calls with structured output."""
    if name == "get_weather":  # 这个name对应FastMCP @mcp.tool()的函数名
        city = arguments["city"]

        # Simulated weather data - in production, call a weather API
        weather_data = {
            "temperature": 22.5,
            "condition": "partly cloudy",
            "humidity": 65,
            "city": city,  # Include the requested city
        }

        # low-level server will validate structured output against the tool's
        # output schema, and additionally serialize it into a TextContent block
        # for backwards compatibility with pre-2025-06-18 clients.
        return weather_data
    else:
        raise ValueError(f"Unknown tool: {name}")


async def run():
    """Run the structured output server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="structured-output-example",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())
```

Tools can return data in three ways:

1. **Content only**: Return a list of content blocks (default behavior before spec revision 2025-06-18)
2. **Structured data only**: Return a dictionary that will be serialized to JSON (Introduced in spec revision 2025-06-18)
3. **Both**: Return a tuple of (content, structured_data) preferred option to use for backwards compatibility

When an `outputSchema` is defined, the server automatically validates the structured output against the schema. This ensures type safety and helps catch errors early. 如果定义了`outputSchema`，server会用schema自动验证结构化输出，以确保类型安全。

### MCP Clients

### Parsing Tool Results

When calling tools through MCP, the `CallToolResult` object contains the tool's response in a structured format. Understanding how to parse this result is essential for properly handling tool outputs.

```python
"""examples/snippets/clients/parsing_tool_results.py"""

import asyncio

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client


async def parse_tool_results():
    """Demonstrates how to parse different types of content in CallToolResult."""
    server_params = StdioServerParameters(
        command="python", args=["path/to/mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Example 1: Parsing text content
            result = await session.call_tool("get_data", {"format": "text"})
            for content in result.content:
                if isinstance(content, types.TextContent):  # 非结构化输出
                    print(f"Text: {content.text}")

            # Example 2: Parsing structured content from JSON tools
            result = await session.call_tool("get_user", {"id": "123"})
            if hasattr(result, "structuredContent") and result.structuredContent:  # 结构化输出
                # Access structured data directly
                user_data = result.structuredContent
                print(f"User: {user_data.get('name')}, Age: {user_data.get('age')}")

            # Example 3: Parsing embedded resources
            result = await session.call_tool("read_config", {})
            for content in result.content:
                if isinstance(content, types.EmbeddedResource):  # 嵌套资源的server对应代码是什么？
                    resource = content.resource
                    if isinstance(resource, types.TextResourceContents):
                        print(f"Config from {resource.uri}: {resource.text}")
                    elif isinstance(resource, types.BlobResourceContents):
                        print(f"Binary data from {resource.uri}")

            # Example 4: Parsing image content
            result = await session.call_tool("generate_chart", {"data": [1, 2, 3]})
            for content in result.content:
                if isinstance(content, types.ImageContent):  # 前面提到的mcp的Image组件
                    print(f"Image ({content.mimeType}): {len(content.data)} bytes")

            # Example 5: Handling errors
            result = await session.call_tool("failing_tool", {})
            if result.isError:
                print("Tool execution failed!")
                for content in result.content:
                    if isinstance(content, types.TextContent):
                        print(f"Error: {content.text}")


async def main():
    await parse_tool_results()


if __name__ == "__main__":
    asyncio.run(main())
```

### MCP Primitives

The MCP protocol defines three core primitives that servers can implement:

| Primitive | Control                | Description                                       | Example Use                  |
| --------- | ---------------------- | ------------------------------------------------- | ---------------------------- |
| Prompts   | User-controlled        | Interactive templates invoked by user choice      | Slash commands, menu options |
| Resources | Application-controlled | Contextual data managed by the client application | File contents, API responses |
| Tools     | Model-controlled       | Functions exposed to the LLM to take actions      | API calls, data updates      |

- Prompts: 用户控制，用户选择的交互模板

### Server Capabilities

MCP服务器功能

MCP servers declare capabilities during initialization:

| Capability    | Feature Flag              | Description                     |
| ------------- | ------------------------- | ------------------------------- |
| `prompts`     | `listChanged`             | Prompt template management      |
| `resources`   | `subscribe` `listChanged` | Resource exposure and updates   |
| `tools`       | `listChanged`             | Tool discovery and execution    |
| `logging`     | -                         | Server logging configuration    |
| `completions` | -                         | Argument completion suggestions |



## An All-in-One demo

### Stdio MCP Server

