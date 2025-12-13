{
  "mcpServers": {
    "local-llama-stdio": {
      "command": "/usr/bin/env",
      "args": [
        "python3.11",
        "/media/waqasm86/External1/Project-Python/Project-Windsurf/windsurf-local-llm-mcp/mcp-server/server_stdio.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "LLAMA_COMPLETION_URL": "http://127.0.0.1:8090/completion",
        "LLAMA_TIMEOUT_S": "120"
      },
      "disabled": false
    }
  }
}