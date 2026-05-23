#!/usr/bin/env bash
set -euo pipefail

# Copy llama/config.example.env to llama/config.env and edit paths first.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-$SCRIPT_DIR/config.env}"

if [[ -f "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi

LLAMA_BIN="${LLAMA_BIN:-/absolute/path/to/llama.cpp/llama-server}"
MODEL_PATH="${MODEL_PATH:-/absolute/path/to/models/model.gguf}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8090}"
CTX_SIZE="${CTX_SIZE:-2048}"
BATCH_SIZE="${BATCH_SIZE:-64}"
GPU_LAYERS="${GPU_LAYERS:-10}"

if [[ ! -x "$LLAMA_BIN" ]]; then
  echo "ERROR: llama-server binary not found or not executable: $LLAMA_BIN" >&2
  exit 1
fi

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "ERROR: GGUF model file not found: $MODEL_PATH" >&2
  exit 1
fi

echo "Starting llama.cpp server on http://$HOST:$PORT" >&2
echo "Model: $MODEL_PATH" >&2

"$LLAMA_BIN" \
  --model "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$CTX_SIZE" \
  -b "$BATCH_SIZE" \
  -ngl "$GPU_LAYERS" \
  --timeout 0 \
  --cont-batching \
  --no-mmap
