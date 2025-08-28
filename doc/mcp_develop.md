# MCP

> <https://github.com/modelcontextprotocol/python-sdk>

```bash
uv run mcp install main.py # install for Claude Desktop
uv run mcp dev main.py # Run a MCP server with the MCP Inspector
uv run mcp --help # show cmd help
```

## Environment Preparation

An example in vscode:

1. mcp[cli]: `uv add "mcp[cli]"` or`uv pip install "mcp[cli]"`, test with `uv run mcp`
2. npx: [nodejs-install](https://nodejs.org/en/download/current), test with `npm -v`
3. mcp-servers-config (Workspace-ver): command+shift+P or F1 -> MCP: Open Workspace Folder MCP Configration -> add mcp servers's config
