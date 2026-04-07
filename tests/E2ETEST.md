# End-to-End (E2E) Integration Tests

This document describes how to run the end-to-end integration tests for the LocalSandbox MCP Server.

## 1. Installation

We recommend using the provided installation script:

```bash
chmod +x install.sh
./install.sh
```

## 2. Start the Server

Start the LocalSandbox server in a separate terminal window. You can use a specific environment file (e.g., `.env.test`) to configure the server for testing.

```bash
# In Terminal 1
uv run lsb start --env-file .env.test
```

> **Note:** Ensure `.env.test` is configured correctly (e.g., `MCP_SERVER_HOST=localhost`, `MCP_SERVER_PORT=8775`).

## 3. Run the Tests

Execute the E2E tests using `pytest` in your main terminal window:

```bash
# In Terminal 2
uv run pytest tests/test_e2e.py
```

or

```bash
# In Terminal 2
uv run pytest tests/test_cli_e2e.py
```

The tests will automatically connect to the running server, perform a sequence of validation steps (including sandbox creation, file persistence, and session management), and report the results.
