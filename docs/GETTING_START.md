# Getting Started with LocalSandbox

This guide will help you install, configure, and run the LocalSandbox MCP Server.

## Installation

We recommend using the provided installation script, which automatically detects your environment and sets up the necessary dependencies.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd localsandbox
    ```

2.  **Run the installation script:**
    ```bash
    chmod +x install.sh
    ./install.sh
    ```
    This script will:
    - Check for `uv` (recommended) or fall back to `pip`.
    - Create a virtual environment (`.venv`).
    - Install the `lsb` CLI and all dependencies.
    - Providing instructions on how to activate the environment.

3.  **Ensure Docker is running:**
    The server requires Docker to spin up sandbox environments. Make sure Docker Desktop or the Docker daemon is running.

## Running the Service

The project uses the `lsb` CLI to manage the server.

### Start the Server
To start the server in the foreground (or background if you use `&`):

```bash
uv run lsb start
```

You can also specify a custom environment file:
```bash
uv run lsb start --env-file .env.prod
```

### Stop the Server
To stop the running server instance:

```bash
uv run lsb stop
```

## Viewing Logs

By default, the server writes structured logs to the `logs/` directory in the project root.

To view the latest logs:
```bash
tail -f logs/server.log
```

### Configuring MCP Clients

Since this server uses the HTTP streamable transport, you should configure your MCP client to connect via the HTTP endpoint.

**Server URL:** `http://localhost:8775/mcp`