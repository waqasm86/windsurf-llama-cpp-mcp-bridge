import os
from fastmcp import FastMCP
import requests
from pydantic import BaseModel

LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8090/completion")

class CompletionRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7

def call_llama_server(prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "stop": ["</s>", "User:", "Assistant:"],
        "stream": False,
    }
    resp = requests.post(LLAMA_SERVER_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "content" in data:
        return data["content"]
    return str(data)

server = FastMCP(name="local-gguf-assistant")

@server.tool("complete")
def complete(req: CompletionRequest) -> str:
    """Call local GGUF model running in llama.cpp to get an assistant-style completion."""
    return call_llama_server(req.prompt, req.max_tokens, req.temperature)

@server.tool("review_code")
def review_code(req: ReviewCodeRequest) -> str:
    """Explain/refactor a code snippet for readability and security concerns."""
    prompt = (
        "You are a code security and readability reviewer.\n"
        "Point out obvious bugs, unsafe patterns, and unclear logic.\n\n"
        f"Language: {req.language}\nCode:\n{req.code}\n\nReview:"
    )
    return call_llama_server(prompt, max_tokens=256, temperature=0.4)
