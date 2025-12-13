#!/usr/bin/env python3
import os
import sys
import json
import traceback
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

LLAMA_COMPLETION_URL = os.getenv("LLAMA_COMPLETION_URL", "http://127.0.0.1:8090/completion")
TIMEOUT_S = float(os.getenv("LLAMA_TIMEOUT_S", "120"))

def log(*a):
    # IMPORTANT: log only to STDERR (never STDOUT)
    print("[MCP]", *a, file=sys.stderr, flush=True)

def log_err(*parts):
    print(*parts, file=sys.stderr, flush=True)

def send(obj: dict):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def jsonrpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}

def jsonrpc_error(req_id, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}

def call_llama(prompt: str, max_tokens: int, temperature: float) -> str:
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": float(temperature),
        "stream": False,
    }
    r = requests.post(LLAMA_COMPLETION_URL, json=payload, timeout=TIMEOUT_S)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, dict):
        if isinstance(data.get("content"), str):
            return data["content"]
        if isinstance(data.get("completion"), str):
            return data["completion"]

    return json.dumps(data, ensure_ascii=False)

TOOLS = [
    {
        "name": "complete",
        "description": "Call local llama.cpp /completion endpoint and return text completion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "max_tokens": {"type": "integer", "default": 256},
                "temperature": {"type": "number", "default": 0.7},
            },
            "required": ["prompt"],
        },
    }
]

def handle_jsonrpc(msg):
    """Handle a JSON-RPC message and return the response"""
    req_id = msg.get("id")
    method = msg.get("method", "")

    log("method=", method, "id=", req_id)

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {"name": "local-llama-stdio", "version": "0.1.0"},
            }
            return jsonrpc_result(req_id, result)

        elif method == "notifications/initialized":
            # notification, no response needed
            return None

        elif method == "resources/list":
            return jsonrpc_result(req_id, {"resources": []})

        elif method == "prompts/list":
            return jsonrpc_result(req_id, {"prompts": []})

        elif method == "tools/list":
            return jsonrpc_result(req_id, {"tools": TOOLS})

        elif method == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}

            if name != "complete":
                return jsonrpc_error(req_id, -32601, f"Unknown tool: {name}")

            prompt = args.get("prompt", "")
            max_tokens = int(args.get("max_tokens", 256))
            temperature = float(args.get("temperature", 0.7))

            text = call_llama(prompt, max_tokens, temperature)
            return jsonrpc_result(req_id, {"content": [{"type": "text", "text": text}]})

        else:
            if req_id is not None:
                return jsonrpc_error(req_id, -32601, f"Method not found: {method}")
            return None

    except Exception as e:
        tb = traceback.format_exc()
        log_err("Server error:", e, "\n", tb)
        if req_id is not None:
            return jsonrpc_error(req_id, -32603, "Internal error", str(e))
        return None


class MCPHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Log HTTP requests to stderr
        log_err(f"{self.address_string()} - {format % args}")

    def do_POST(self):
        if self.path == '/tools/call':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                request = json.loads(post_data)
                response = handle_jsonrpc(request)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                tb = traceback.format_exc()
                log_err("HTTP handler error:", e, "\n", tb)
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    }
                }).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


def start_http_server(port=8001):
    server_address = ('', port)
    httpd = HTTPServer(server_address, MCPHTTPHandler)
    log(f"Starting HTTP server on port {port}")
    httpd.serve_forever()


def main():
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Handle stdio JSON-RPC messages
    log("MCP stdio server started, waiting for messages...")
    
    try:
        for raw in sys.stdin:
            raw = raw.strip()
            if not raw:
                continue

            try:
                msg = json.loads(raw)
            except Exception as e:
                send(jsonrpc_error(None, -32700, "Parse error", str(e)))
                continue

            response = handle_jsonrpc(msg)
            if response is not None:
                send(response)

    except KeyboardInterrupt:
        log("Shutting down...")
    except Exception as e:
        log_err("Fatal error:", e)
        traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()