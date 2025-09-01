# README of ex0

- meta/llama-4-scout-17b-16e-instruct: 测试mcp demo的时候会有很多问题
  - resource greeting经常调用不成功，会尝试找外部的mcp，调用方式也有问题，经常用的是tool的调用方式
  - Tool add 经常尝试自己调python算或者用别的mcp
- deepseek-ai/deepseek-r1：基本都会按照指令调用map demo，有时会发现add计算错误，然后调用别的mcp tools尝试修改源文件

## Cline MCP Config

```json
{
  "mcpServers": {
    "demo": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/koki/git_space/VulnerMCP/examples",
        "run",
        "ex0.py"
      ],
      "autoApprove": [
        "add",
        "greeting"
      ]
    }
  }
}
```
