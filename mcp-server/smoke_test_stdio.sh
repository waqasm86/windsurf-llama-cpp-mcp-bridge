#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' \
  | python3.11 -u server_stdio.py

echo
echo "If llama-server is running, test a real completion with:"
echo "printf '{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"complete\",\"arguments\":{\"prompt\":\"Say hello in one line.\",\"max_tokens\":64,\"temperature\":0.2}}}\\n' | LLAMA_COMPLETION_URL=http://127.0.0.1:8090/completion python3.11 -u server_stdio.py"
