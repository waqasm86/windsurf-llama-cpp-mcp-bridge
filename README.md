# Windsurf llama.cpp MCP Bridge

A small Python **MCP stdio server** that lets **Windsurf** call a local `llama.cpp` `llama-server` through the `/completion` endpoint.

```text
Windsurf  ->  MCP over stdio  ->  Python bridge  ->  llama.cpp llama-server  ->  local GGUF model
```

This project is designed for reproducible local AI-developer-tooling experiments, low-VRAM machines, and customer-engineering style debugging.

## What works

- MCP stdio integration for Windsurf.
- Local `llama.cpp` `/completion` calls.
- `complete` tool for general completions.
- `review_code` tool for code review prompts.
- `llama_health` tool for endpoint reachability checks.
- Safe logging: all logs go to `stderr`; JSON-RPC responses stay on `stdout`.
- Low-VRAM `llama-server` startup script.

## Requirements

- Python 3.11+
- `requests`
- A built `llama.cpp` `llama-server` binary
- A local GGUF model
- Windsurf with MCP support

## Install

```bash
git clone https://github.com/waqasm86/windsurf-llama-cpp-mcp-bridge.git
cd windsurf-llama-cpp-mcp-bridge

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r mcp-server/requirements.txt
```

## Start llama.cpp

Copy the example config and edit paths:

```bash
cp llama/config.example.env llama/config.env
nano llama/config.env
```

Then start the local model server:

```bash
./llama/start_llama_server.sh
```

The default endpoint is:

```text
http://127.0.0.1:8090/completion
```

Quick manual test:

```bash
curl -s http://127.0.0.1:8090/completion \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Say hello in one line.","n_predict":32,"temperature":0.2,"stream":false}'
```

## Configure Windsurf

Copy `windsurf-config/mcp.json` into your Windsurf MCP configuration location, then replace this placeholder with your real absolute path:

```text
/ABSOLUTE/PATH/TO/windsurf-llama-cpp-mcp-bridge/mcp-server/server_stdio.py
```

Example config:

```json
{
  "mcpServers": {
    "local-llama-stdio": {
      "command": "/usr/bin/env",
      "args": [
        "python3.11",
        "-u",
        "/ABSOLUTE/PATH/TO/windsurf-llama-cpp-mcp-bridge/mcp-server/server_stdio.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "LLAMA_COMPLETION_URL": "http://127.0.0.1:8090/completion",
        "LLAMA_TIMEOUT_S": "120"
      },
      "autoRestart": true,
      "disabled": false
    }
  }
}
```

Restart Windsurf after editing the MCP config.

## Smoke test without Windsurf

Test initialization and tool discovery:

```bash
./mcp-server/smoke_test_stdio.sh
```

Test a real completion after `llama-server` is running:

```bash
cd mcp-server
printf '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"complete","arguments":{"prompt":"Say hello in one line.","max_tokens":64,"temperature":0.2}}}\n' \
  | LLAMA_COMPLETION_URL="http://127.0.0.1:8090/completion" python3.11 -u server_stdio.py
```

## Available tools

### `complete`

Input:

```json
{
  "prompt": "Explain MCP in one paragraph.",
  "max_tokens": 256,
  "temperature": 0.7
}
```

### `review_code`

Input:

```json
{
  "language": "python",
  "code": "def add(a,b): return a+b",
  "max_tokens": 512
}
```

### `llama_health`

Checks whether the configured `/completion` endpoint is reachable.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Windsurf shows no tools | Wrong path in `mcp.json` | Use an absolute path to `server_stdio.py` |
| MCP process starts then exits | Python dependency missing | Run `pip install -r mcp-server/requirements.txt` |
| Tool call says llama.cpp is unreachable | `llama-server` is not running or port mismatch | Start `./llama/start_llama_server.sh` and keep port `8090` aligned |
| Broken JSON / no response | Logs printed to stdout | Keep all logs on `stderr` only |
| CUDA out-of-memory | Too many GPU layers or large context | Reduce `GPU_LAYERS`, `CTX_SIZE`, or `BATCH_SIZE` in `llama/config.env` |
| Slow generation | CPU fallback or low-end GPU | Reduce model size, use smaller quantization, or lower context/batch size |

## Notes for customer-engineering demos

This repo intentionally favors debuggability over complexity. It demonstrates the full deployment path for an AI coding tool integration:

1. Start a local model runtime.
2. Register an MCP stdio server with Windsurf.
3. Expose tools to the IDE.
4. Route tool calls to a local inference endpoint.
5. Return structured MCP responses.
6. Debug common deployment failures with clear logs and smoke tests.

## License

Add your preferred license, for example MIT.
