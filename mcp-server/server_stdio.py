#!/usr/bin/env python3
"""Windsurf MCP stdio bridge for a local llama.cpp llama-server.

Architecture:
    Windsurf -> MCP over stdio -> this Python process -> llama.cpp /completion

Important MCP rule:
    stdout is reserved for JSON-RPC messages only. All logs must go to stderr.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import dataclass
from typing import Any

import requests

SERVER_NAME = "windsurf-llama-cpp-mcp-bridge"
SERVER_VERSION = "0.2.0"
DEFAULT_COMPLETION_URL = "http://127.0.0.1:8090/completion"

LLAMA_COMPLETION_URL = os.getenv("LLAMA_COMPLETION_URL", DEFAULT_COMPLETION_URL).strip()
LLAMA_TIMEOUT_S = float(os.getenv("LLAMA_TIMEOUT_S", "120"))


def log(*parts: Any) -> None:
    print("[windsurf-llama-mcp]", *parts, file=sys.stderr, flush=True)


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def result(req_id: Any, value: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": value}


def error(req_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


@dataclass(frozen=True)
class CompletionArgs:
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CompletionArgs":
        prompt = raw.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("`prompt` is required and must be a non-empty string")
        max_tokens = int(raw.get("max_tokens", 256))
        temperature = float(raw.get("temperature", 0.7))
        if max_tokens <= 0:
            raise ValueError("`max_tokens` must be greater than 0")
        if not 0 <= temperature <= 2:
            raise ValueError("`temperature` must be between 0 and 2")
        return cls(prompt=prompt, max_tokens=max_tokens, temperature=temperature)


TOOLS: list[dict[str, Any]] = [
    {
        "name": "complete",
        "description": "Send a prompt to a local llama.cpp llama-server /completion endpoint and return the generated text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Prompt to send to llama.cpp."},
                "max_tokens": {"type": "integer", "default": 256, "minimum": 1},
                "temperature": {"type": "number", "default": 0.7, "minimum": 0, "maximum": 2},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "review_code",
        "description": "Review a code snippet for bugs, unclear logic, and maintainability issues using the local llama.cpp model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code snippet to review."},
                "language": {"type": "string", "default": "python"},
                "max_tokens": {"type": "integer", "default": 512, "minimum": 1},
            },
            "required": ["code"],
        },
    },
    {
        "name": "llama_health",
        "description": "Check whether the configured local llama.cpp completion endpoint is reachable.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def call_llama(prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    response = requests.post(LLAMA_COMPLETION_URL, json=payload, timeout=LLAMA_TIMEOUT_S)
    response.raise_for_status()
    data = response.json()

    # llama.cpp /completion commonly returns {"content": "..."}.
    if isinstance(data, dict):
        for key in ("content", "completion", "text"):
            value = data.get(key)
            if isinstance(value, str):
                return value.strip()
    return json.dumps(data, ensure_ascii=False, indent=2)


def check_llama_health() -> str:
    payload = {"prompt": "Say OK.", "n_predict": 4, "temperature": 0.0, "stream": False}
    response = requests.post(LLAMA_COMPLETION_URL, json=payload, timeout=min(LLAMA_TIMEOUT_S, 30))
    response.raise_for_status()
    return f"OK: llama.cpp completion endpoint is reachable at {LLAMA_COMPLETION_URL}"


def text_content(text: str, *, is_error: bool = False) -> dict[str, Any]:
    response: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        response["isError"] = True
    return response


def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "complete":
        args = CompletionArgs.from_dict(arguments)
        return text_content(call_llama(args.prompt, args.max_tokens, args.temperature))

    if name == "review_code":
        code = arguments.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("`code` is required and must be a non-empty string")
        language = str(arguments.get("language", "python"))
        max_tokens = int(arguments.get("max_tokens", 512))
        prompt = (
            "You are a senior software engineer reviewing code for correctness, maintainability, "
            "security, and clear next steps. Be concise and practical.\n\n"
            f"Language: {language}\n\n"
            f"Code:\n{code}\n\n"
            "Review:"
        )
        return text_content(call_llama(prompt, max_tokens=max_tokens, temperature=0.2))

    if name == "llama_health":
        return text_content(check_llama_health())

    raise ValueError(f"Unknown tool: {name}")


def handle_jsonrpc(message: dict[str, Any]) -> dict[str, Any] | None:
    req_id = message.get("id")
    method = message.get("method")

    # Notifications have no id and normally require no response.
    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return result(
            req_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "ping":
        return result(req_id, {})

    if method == "tools/list":
        return result(req_id, {"tools": TOOLS})

    if method == "resources/list":
        return result(req_id, {"resources": []})

    if method == "prompts/list":
        return result(req_id, {"prompts": []})

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return error(req_id, -32602, "Invalid params: `name` is required")
        if not isinstance(arguments, dict):
            return error(req_id, -32602, "Invalid params: `arguments` must be an object")
        try:
            return result(req_id, handle_tool_call(name, arguments))
        except requests.exceptions.RequestException as exc:
            log("llama.cpp request failed:", repr(exc))
            return result(
                req_id,
                text_content(
                    "Could not reach llama.cpp. Check that llama-server is running and that "
                    f"LLAMA_COMPLETION_URL is correct. Current URL: {LLAMA_COMPLETION_URL}\n\n{exc}",
                    is_error=True,
                ),
            )
        except Exception as exc:
            log("tool call failed:", repr(exc))
            return result(req_id, text_content(str(exc), is_error=True))

    if req_id is not None:
        return error(req_id, -32601, f"Method not found: {method}")
    return None


def main() -> int:
    log(f"starting {SERVER_NAME} v{SERVER_VERSION}")
    log(f"LLAMA_COMPLETION_URL={LLAMA_COMPLETION_URL}")

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            send(error(None, -32700, "Parse error", str(exc)))
            continue

        try:
            response = handle_jsonrpc(message)
            if response is not None:
                send(response)
        except Exception as exc:  # Defensive: never crash the MCP process on one bad request.
            log("fatal request error:", repr(exc))
            log(traceback.format_exc())
            send(error(message.get("id"), -32603, "Internal error", str(exc)))

    log("stdin closed; exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
