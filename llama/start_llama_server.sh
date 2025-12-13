#!/usr/bin/env bash
set -euo pipefail

# ── EDIT THESE PATHS FOR YOUR MACHINE ──────────────────
LLAMA_BIN="/absolute/path/to/llama.cpp/llama-server"
MODEL_PATH="/absolute/path/to/models/gemma-3-1b-it.gguf"

HOST="127.0.0.1"
PORT="8081"

# Flags tuned for low VRAM GPUs (like 940M ~1GB):
# -ngl: how many layers to offload to GPU (reduce if OOM)
# -c / --ctx-size: context tokens
# -b: batch size
# --no-mmap: more stable on some distros
# --cont-batching: better streaming

"$LLAMA_BIN" \
  --model "$MODEL_PATH" \
  --host $HOST \
  --port $PORT \
  -c 2048 \
  --ctx-size 2048 \
  -b 64 \
  -ngl 10 \
  --timeout 0 \
  --cont-batching \
  --no-mmap

