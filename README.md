# LocalSandbox MCP Server

A Model Context Protocol (MCP) wrapped sandbox implementation that provides secure code execution capabilities through sandboxed environments.

It's designed as a lightweight, local, single-machine sandbox environment tailored for AI Agents.

*   **Primary Use Case**: Task execution for agents and lightweight code execution (Python/Node.js).
*   **Not Intended For**: Full-scale, project-level software development.


## Features

- **MCP Protocol Support**: Full implementation of the Model Context Protocol for seamless integration with AI Agents.
- **Transport Options**: Support for HTTP streaming transport
- **Secure Sandboxing**: Execute code in isolated Docker containers for maximum security
- **Language Support**: Support Python, JavaScript scripts interpretation.

## Installation


### 1. From Source (Recommended)

This project uses modern Python packaging.

**Using `install.sh` (Auto-setup):**
```bash
./install.sh
```
This script detects if you have `uv` installed (recommended) or falls back to standard `pip`. It automatically manages virtual environments.

**Manual Installation:**
```bash
# Using uv (Recommended)
uv sync

# Using pip
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

## Quick Start


### Start with LocalSandbox (recommended)

cd <repository-name>
cp .env.example .env.local

```bash
lsb start
```

This will:
- Load configuration from `.env.local` file
- Check Docker availability
- Pull required Docker images
- Start the server with HTTP transport


## Configuration

The server can be configured through command-line arguments or environment variables:

### Command Line Options

- `--transport`: Transport type (streamable-http)
- `--host`: Server host address - default: localhost
- `--port`: Server port number - default: 8775
- `--enable-cors`: Enable CORS support
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR) - default: INFO

### Environment Variables

#### Basic MCP Server Configuration
- `MCP_SERVER_HOST`: Server host address
- `MCP_SERVER_PORT`: Server port number
- `MCP_ENABLE_CORS`: Enable CORS support

#### Docker Sandbox Configuration
- `CONTAINER_RUNTIME`: Container runtime (docker or podman)
- `LOCALSANDBOX_PYTHON_IMAGE`: Python Docker image (default: python:3.11-slim)
- `LOCALSANDBOX_NODE_IMAGE`: Node.js Docker image (default: node:18-slim)
- `LOCALSANDBOX_DEFAULT_TIMEOUT`: Default execution timeout in seconds
- `LSB_MAX_SESSIONS`: Maximum concurrent sessions
- `LSB_SESSION_TIMEOUT`: Session timeout in seconds
- `LSB_SHARED_VOLUME_PATH`: JSON array of volume mappings for containers

### LocalSandbox Configuration File

The `lsb start` command uses a `.env.local` file for configuration. Example:

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
LSB_MAX_SESSIONS=5
LSB_SESSION_TIMEOUT=3600
LSB_DEFAULT_FLAVOR=small

# Volume Mapping
LSB_ENABLE_VOLUME_MAPPING=true
LSB_SHARED_VOLUME_PATH='["/path/to/host/dir:/workspace"]'

# Logging
LSB_LOG_LEVEL=DEBUG
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
lsb start --env-file .env.test
```

4. From the project root, run the E2E test module:

```bash
python3 -m pytest tests/test_e2e.py
```

Notes:
- The E2E test expects the server to be running (step 3) and will use `.env.test` for its configuration.
- You can edit `.env.test` to switch runtimes (e.g., `CONTAINER_RUNTIME=podman`) and set default images.


## Architecture

The project consists of several key components:

- **MCP Server**: Core MCP protocol implementation
- **LocalSandbox Wrapper**: Abstraction layer for sandbox operations
- **Transport Layer**: Support for multiple communication protocols
- **Resource Management**: Container lifecycle and resource allocation

## Requirements

- Python 3.10+
- Docker (for sandbox execution) (or Podman)
- Network access (for HTTP transports)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests to the main repository.