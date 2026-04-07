# LocalSandbox MCP Server

## 1. Overview

**LocalSandbox** is a lightweight, local, and single-machine sandbox environment tailored specifically for **AI Agents**. It wraps secure code execution capabilities within docker containers under the Model Context Protocol (MCP), enabling AI agents to autonomously and safely write, test, and run code (Python/Node.js) on your own machine.

*   **Primary Use Case**: Secure execution environments for AI code agents, automated multi-stage tasks, and persistent data manipulation via isolated sessions.
*   **Key Features**: Sandboxed code execution (Python/Node.js), seamless host-volume integrations, and granular context caching (sessions/pinning).

---

## 2. Prerequisites

Before installing, ensure you have the following on your system:
- **Docker** (or Podman) running in the background.
- **Python 3.10+** and [**uv**](https://github.com/astral-sh/uv) (strongly recommended for ultra-fast dependency management).
- *(Optional)* **Go 1.22+** if you prefer explicitly compiling the Go-based CLI from source.

---

## 3. Server Installation & Start

Use our interactive setup script to install the background MCP server:

```bash
# Provide execute permissions and install the Python backend
chmod +x install.sh
./install.sh
```

**Starting the LocalSandbox Server:**
Create a local configuration (this avoids committing personal configs to git):

```bash
cp .env.example .env.local
lsb start
```
*Note: This will read `.env.local`, check if the Docker daemon is ready, automatically pull required container images (Python/Node), and spin up the MCP server daemon.*

---

## 4. Install the CLI Client (Public Network)

LocalSandbox provides a blazing-fast, independently compiled **Go-based CLI Client** (`lsb-cli`) to manually manage sandboxes, execute arbitrary code, and orchestrate runtime sessions.

You can install it instantly onto `~/.local/bin` using our public installation script without pulling the entire source code:

```bash
curl -fsSL https://raw.githubusercontent.com/radiumce/localsandbox/main/install-lsb-cli.sh | bash
```

*(This automatically recognizes macOS/Linux and ARM64/AMD64 to fetch the precise pre-compiled native binary!)*

---

## 5. Main Configurations (`.env.local`)

When you copied `.env.example` to `.env.local`, you gained access to powerful variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVER_PORT` | The HTTP streaming port the MCP server binds to. | `8776` |
| `CONTAINER_RUNTIME` | Select between `docker` or `podman`. | `docker` |
| `LOCALSANDBOX_PYTHON_IMAGE` | The base docker container image for Python execution. | `python:3.11-slim` |
| `LSB_MAX_SESSIONS` | Maximum limit for active concurrent docker sandboxes. | `5` |
| `LSB_SHARED_VOLUME_PATH` | Host-to-Container volume mappings for moving big files. | `["./tests/data:/shared"]` |

---

## 6. Typical Usage Demo

The `lsb-cli` provides robust utilities. Here is an end-to-end integration flow typically run by our `test_cli_e2e.py` suites:

**1. Execute Python Code**
Instantly run code; this provisions a brand-new container session and prints its output.
```bash
lsb-cli exec-code -c 'print("Hello, LocalSandbox!")'
# Output includes your Session ID (e.g. 46dba2df-...)
```

**2. Persist Data within that Session**
You can reuse a previous execution environment using the `-s` (session) flag.
```bash
lsb-cli exec-code -c "with open('/hello.txt', 'w') as f: f.write('sandbox is alive')" -s <SESSION_ID>
```

**3. Verify via Shell Execution**
Execute Bash commands directly inside the container to verify the file was recorded.
```bash
lsb-cli exec-cmd -c "cat /hello.txt" -s <SESSION_ID>
```

**4. Pin a Sandbox Workspace**
Avoid losing valuable contexts (or downloaded container libraries) by pinning a session.
```bash
lsb-cli pin <SESSION_ID> my-agent-workspace
```

**5. Return to the Pinned Sandbox at Any Time**
```bash
lsb-cli attach my-agent-workspace
# Instantly returns the Session ID belonging to that persistent workspace.
```

---

## 7. AI Agent Integrations (Skills)

If you are incorporating this sandbox for another LLM or Agent locally (e.g., Anthropic Claude, OpenAI, custom Go tools), we supply a curated **Agent Skill / Guide**.

**Recommendation:** Load the markdown instructions located at `skills/use-sandbox/SKILL.md` (or copy it into your agent's `.agent/skills/` directory). It grants the AI agent comprehensive "knowledge" on how to efficiently interface with the sandboxes via MCP or REST, handle persistence, and correctly formulate execution templates.