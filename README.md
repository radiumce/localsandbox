# Microsandbox MCP Server

A Model Context Protocol (MCP) server that provides secure code execution capabilities through sandboxed environments.

## Features

- **MCP Protocol Support**: Full implementation of the Model Context Protocol for seamless integration with AI assistants
- **Multiple Transport Options**: Support for stdio, HTTP streaming, and Server-Sent Events (SSE) transports
- **Secure Sandboxing**: Execute code in isolated Docker containers for maximum security
- **Language Support**: Support for multiple programming languages including Python, JavaScript, and more
- **Resource Management**: Intelligent resource allocation and cleanup
- **Background Task Management**: Handle long-running tasks with proper lifecycle management

## Installation

Install the package using pip:

```bash
pip install microsandbox-mcp-server
```

Or install from source:

```bash
git clone <repository-url>
cd <repository-name>
pip install .
```

For development installation:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Start the MCP Server (stdio transport)

```bash
microsandbox-mcp-server
```

### Start with LocalSandbox (recommended)

```bash
start-localsandbox
```

This will:
- Load configuration from `.env.local` file
- Check Docker availability
- Pull required Docker images
- Setup shared directories
- Start the server with HTTP transport

### Start with HTTP transport

```bash
microsandbox-mcp-server --transport streamable-http --host 0.0.0.0 --port 8775
```

### Start with SSE transport

```bash
microsandbox-mcp-server --transport sse --host localhost --port 8775 --enable-cors
```

## Configuration

The server can be configured through command-line arguments or environment variables:

### Command Line Options

- `--transport`: Transport type (stdio, streamable-http, sse) - default: stdio
- `--host`: Server host address for HTTP transports - default: localhost
- `--port`: Server port number for HTTP transports - default: 8775
- `--enable-cors`: Enable CORS support for HTTP transports
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR) - default: INFO

### Environment Variables

#### Basic MCP Server Configuration
- `MCP_SERVER_HOST`: Server host address for HTTP transports
- `MCP_SERVER_PORT`: Server port number for HTTP transports  
- `MCP_ENABLE_CORS`: Enable CORS support for HTTP transports

#### Docker Sandbox Configuration
- `CONTAINER_RUNTIME`: Container runtime (docker or podman)
- `LOCALSANDBOX_PYTHON_IMAGE`: Python Docker image (default: python:3.11-slim)
- `LOCALSANDBOX_NODE_IMAGE`: Node.js Docker image (default: node:18-slim)
- `LOCALSANDBOX_DEFAULT_TIMEOUT`: Default execution timeout in seconds
- `MSB_MAX_SESSIONS`: Maximum concurrent sessions
- `MSB_SESSION_TIMEOUT`: Session timeout in seconds
- `MSB_SHARED_VOLUME_PATH`: JSON array of volume mappings for containers

### LocalSandbox Configuration File

The `start-localsandbox` command uses a `.env.local` file for configuration. Example:

```bash
# MCP Server Configuration
MCP_ENABLE_CORS=true
MCP_SERVER_PORT=8775

# Docker-based Sandbox Configuration
CONTAINER_RUNTIME=docker
LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim
LOCALSANDBOX_NODE_IMAGE=node:18-slim
LOCALSANDBOX_DEFAULT_TIMEOUT=1800

# Session Management
MSB_MAX_SESSIONS=5
MSB_SESSION_TIMEOUT=3600
MSB_DEFAULT_FLAVOR=small

# Volume Mapping
MSB_ENABLE_VOLUME_MAPPING=true
MSB_SHARED_VOLUME_PATH='["/path/to/host/dir:/workspace"]'

# Logging
MSB_LOG_LEVEL=DEBUG
```

## Usage Examples

### Basic stdio usage (for MCP clients)

```bash
microsandbox-mcp-server
```

### HTTP server for web integration

```bash
microsandbox-mcp-server --transport streamable-http --port 9000 --enable-cors
```

### SSE server with custom configuration

```bash
MCP_SERVER_HOST=0.0.0.0 MCP_SERVER_PORT=8080 microsandbox-mcp-server --transport sse --enable-cors
```

### LocalSandbox with custom environment file

```bash
start-localsandbox --env-file /path/to/custom/.env.local
```

### Skip Docker checks (for development)

```bash
start-localsandbox --skip-docker-check --skip-image-pull
```

## Development

### Running Tests

```bash
pip install -e ".[test]"
pytest tests/
```

### Integration (E2E) Tests

Follow these steps to run the end-to-end integration test locally:

1. Copy the example env file to a test env file and adjust values as needed (e.g., set `CONTAINER_RUNTIME`, images, ports):

```bash
cp .env.example .env.test
```

2. Install the project (from the repository root):

```bash
pip install .
```

3. Start the MCP server using LocalSandbox in a separate terminal:

```bash
start-localsandbox --env-file .env.test
```

4. From the project root, run the E2E test module:

```bash
python3 -m pytest tests/test_e2e.py
```

Notes:
- The E2E test expects the server to be running (step 3) and will use `.env.test` for its configuration.
- You can edit `.env.test` to switch runtimes (e.g., `CONTAINER_RUNTIME=podman`) and set default images.

### Code Formatting

```bash
pip install -e ".[dev]"
black .
flake8 .
mypy .
```

## Architecture

The project consists of several key components:

- **MCP Server**: Core MCP protocol implementation
- **Microsandbox Wrapper**: Abstraction layer for sandbox operations
- **Transport Layer**: Support for multiple communication protocols
- **Resource Management**: Container lifecycle and resource allocation
- **Session Management**: Handle multiple concurrent sessions

## Requirements

- Python 3.8+
- Docker (for sandbox execution)
- Network access (for HTTP transports)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests to the main repository.

## Support

For issues and questions, please use the GitHub issue tracker or contact support@microsandbox.io.