# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Repository overview
- Purpose: Microsandbox MCP Server and LocalSandbox SDK for secure, containerized code execution with MCP transports (stdio, HTTP streamable, SSE).
- Layout highlights:
  - mcp-server/: MCP HTTP/stdio/SSE server and Microsandbox wrapper
  - python/: LocalSandbox Python SDK (containerized execution primitives)
  - tests/: Unit/integration and e2e tests (Docker-based)

Common development commands
- Environment setup (recommended)
  - Create venv and install in editable mode with dev extras:
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
  - Alternatively, base install:
    pip install .

- Linting/formatting/type checks
  - Black (format):
    black .
  - Flake8 (lint):
    flake8 .
  - MyPy (type check):
    mypy .

- Run tests (pytest configured via pyproject/pytest.ini)
  - Unit tests only (default in tests/run_tests.py):
    pytest -m "not integration"
  - All tests including integration (requires Docker):
    pytest
  - Single test file:
    pytest tests/test_container_runtime.py -v
  - Single test case:
    pytest tests/test_container_runtime.py::TestDockerRuntime::test_create_container_success -q
  - With coverage (SDK focus):
    pytest --cov=python.sandbox --cov-report=term-missing
  - Scripted runner with switches:
    python tests/run_tests.py --integration        # include Docker integration tests
    python tests/run_tests.py --container          # container runtime tests only
    python tests/run_tests.py --sandbox            # sandbox execution tests only
    python tests/run_tests.py --command            # command execution tests only
    python tests/run_tests.py --coverage

- Build distributions
  - From repo root (PEP 517):
    python -m build

- Start MCP server
  - Stdio transport (for MCP clients):
    microsandbox-mcp-server
  - HTTP streamable:
    microsandbox-mcp-server --transport streamable-http --host 0.0.0.0 --port 8775
  - SSE transport:
    microsandbox-mcp-server --transport sse --host localhost --port 8775 --enable-cors
  - LocalSandbox convenience launcher (loads .env.local, checks Docker, pulls images):
    start-localsandbox
  - Health checks:
    curl http://localhost:8775/health
    curl -X POST http://localhost:8775/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

- Pin-sandbox E2E helpers
  - Run simple/full/all:
    python tests/run_pin_sandbox_e2e.py --simple
    python tests/run_pin_sandbox_e2e.py --full
    python tests/run_pin_sandbox_e2e.py --all
  - Useful flags:
    --timeout N  --cleanup N  --debug  --no-docker  --dry-run  --direct

Key configuration
- Environment variables (server and sandbox)
  - MCP server:
    MCP_SERVER_HOST, MCP_SERVER_PORT, MCP_ENABLE_CORS, MSB_DEFAULT_FLAVOR
  - Container runtime/images/timeouts:
    CONTAINER_RUNTIME=docker|podman
    LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim
    LOCALSANDBOX_NODE_IMAGE=node:18-slim
    LOCALSANDBOX_DEFAULT_TIMEOUT=30
  - Sessions and volumes:
    MSB_MAX_SESSIONS, MSB_SESSION_TIMEOUT, MSB_SHARED_VOLUME_PATH='["/host:/workspace"]'
  - Logging during troubleshooting:
    MSB_LOG_LEVEL=DEBUG
- LocalSandbox env file used by start-localsandbox (copy from template):
  cp .env.example .env.local
  # Edit as needed (port, images, volume mappings, timeouts)

High-level architecture and execution flow
- Packaging and entry points
  - Single Python distribution built from multiple package roots via pyproject/setuptools mapping:
    - mcp_server = mcp-server/mcp_server
    - microsandbox_wrapper = mcp-server/microsandbox_wrapper
    - sandbox = python/sandbox
  - Console scripts (installed by pip):
    - microsandbox-mcp-server, mcp-server -> mcp_server.main:main
    - start-localsandbox -> mcp_server.scripts:start_docker_server

- Components and responsibilities
  - MCP Server (mcp-server/mcp_server)
    - Transports: stdio, HTTP streamable, SSE
    - JSON-RPC MCP endpoints: tools/list, tools/call, etc.
    - Tool routing and error mapping to MCP-compliant responses
    - Exposes high-level tools like execute_code, execute_command, get_sessions, stop_session, get_volume_path
  - Microsandbox Wrapper (mcp-server/microsandbox_wrapper)
    - SessionManager: create/reuse/cleanup sandbox sessions
    - ResourceManager: resource limits and lifecycle
    - Config/logging integration; error normalization
    - Delegates to LocalSandbox primitives
  - LocalSandbox SDK (python/sandbox)
    - Container abstractions (Docker/Podman) and command execution
    - Language sandboxes (PythonSandbox, NodeSandbox) built atop container runtime
    - Execution model returns structured results (stdout/stderr/exit status)

- Typical request path (HTTP transport)
  1) Client sends MCP JSON-RPC request to /mcp
  2) MCP server validates and dispatches to a tool implementation
  3) Tool calls into Microsandbox Wrapper for session and resource handling
  4) Wrapper uses LocalSandbox SDK to run code/commands in a container
  5) Results/errors converted to MCP-compliant JSON-RPC response

Testing strategy and markers
- Unit vs Integration
  - Unit tests mock container runtime; fast and do not require Docker
  - Integration tests run real containers; require Docker images (python:3.11-slim, node:18-slim)
- Markers
  - integration: require Docker
  - Default unit-only run: pytest -m "not integration"
- E2E pin-sandbox flows are driven via tests/run_pin_sandbox_e2e.py

Important references from repo docs
- README.md and QUICKSTART.md: startup commands, transports, .env.local usage
- mcp-server/README.md: tool semantics, JSON-RPC examples, health/status endpoints
- tests/README.md: how to select test groups and run coverage

Troubleshooting notes (project-specific)
- Prioritize logs on the critical execution path: enable verbose server logs via MSB_LOG_LEVEL=DEBUG and re-run the failing command/test. For integration issues, verify Docker availability and image pulls, and use the health endpoints and tools/list calls to isolate where requests fail.

