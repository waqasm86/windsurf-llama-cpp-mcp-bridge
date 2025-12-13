import uvicorn
from fastapi import FastAPI
from fastmcp import create_fastapi_router
from fastmcp_wrapper import server  # the MCPServer instance

app = FastAPI(title="Local GGUF MCP Server")

# expose MCP over HTTP so Windsurf can talk to it
app.include_router(create_fastapi_router(server), prefix="/mcp")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)

