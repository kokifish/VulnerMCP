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

1. mcp[cli]: `uv add "mcp[cli]"` or`uv pip install "mcp[cli]"`, test with `uv run mcp`
2. npx: [nodejs-install](https://nodejs.org/en/download/current), test with `npm -v`
3. [opt] mcp-servers-config in vscode (Workspace-ver): command+shift+P or F1 -> MCP: Open Workspace Folder MCP Configration -> add mcp servers's config
4. mcp-servers-config in cline: cline -> mcp-servers -> Installed -> Configure MCP Servers -> copy same config from vscode

> If a wrong LLM used in adding a new mcp server with cline task chat window, mcp servers maybe installed failed. XD
>

## MCP HelloWorld

## MCP Concepts and Corresponding Development

## MCP All-in-One demo
