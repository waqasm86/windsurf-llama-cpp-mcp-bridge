# Local GGUF MCP Server

This is a Windsurf MCP stdio bridge that lets Windsurf call a local llama.cpp llama-server GGUF model through a complete tool.

## Prerequisites

- Python 3.8+
- pip
- Git

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd windsurf-local-llm-mcp
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   cd mcp-server
   pip install -r requirements.txt
   ```

## Running the Server

1. Start the server:
   ```bash
   cd mcp-server
   python server.py
   ```

2. The server will start on `http://127.0.0.1:8001`

## API Endpoints

- `GET /docs` - Interactive API documentation
- `POST /mcp/...` - MCP protocol endpoints

## Configuration

Create a `.env` file in the `mcp-server` directory to set environment variables:

```
MODEL_PATH=/path/to/your/gguf/model.gguf
```

## Development

For development, you can use:

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

## License

[Add your license here]
