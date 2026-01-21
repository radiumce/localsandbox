# LocalSandbox Usage Guide

## 1. Design Goals

**LocalSandbox** is designed as a lightweight, local, single-machine sandbox environment tailored for AI Agents.

*   **Primary Use Case**: Task execution for agents and lightweight code execution (Python/Node.js).
*   **Not Intended For**: Full-scale, project-level software development or heavy CI/CD pipelines.

It provides a secure, isolated container environment where agents can execute code, run shell commands, and manipulate files without risking the host system's integrity.

## 2. Dependencies

LocalSandbox relies on a container runtime to create isolated environments. It supports both **Docker** and **Podman**.

*   **Docker** (Default): Widely used, robust containerization platform.
*   **Podman**: Daemonless alternative, compatible with Docker CLI commands.

### Configuration
You can configure the underlying engine by setting the `CONTAINER_RUNTIME` environment variable in your `.env` file or process environment:

```bash
# Use Docker (Default)
CONTAINER_RUNTIME=docker

# Switch to Podman
CONTAINER_RUNTIME=podman
```

Ensure the selected runtime is installed and its CLI is accessible in your system's PATH.

## 3. Functionality & Demo

The following workflow demonstrates how an agent can utilize the LocalSandbox tools to complete a complex task. This is based on our End-to-End (E2E) testing suite, showing the tools in action.

### Agent Workflow Example

1.  **Initialize Session**: The agent connects to the MCP server. A new sandbox session is automatically created upon the first request (if no session ID is provided).

2.  **Code Execution (`execute_code`)**:
    The agent verifies the environment by running a simple Python script.
    ```python
    # Tool: execute_code
    {
      "code": "print('Hello, World!')"
    }
    # Result: "Hello, World!"
    ```

3.  **Command Execution (`execute_command`)**:
    The agent runs shell commands to investigate the environment or file system.
    ```bash
    # Tool: execute_command
    {
      "command": "ls -la /"
    }
    ```

4.  **File Persistence (`execute_code` / `write_to_file`)**:
    The agent creates a file that needs to persist for later use.
    ```python
    # Tool: execute_code
    {
      "code": "with open('/hello.txt', 'w') as f: f.write('Important Data')"
    }
    ```

5.  **Pinning the Sandbox (`pin_sandbox`)**:
    *Critically*, if the agent determines this environment contains valuable state (like some libs hand scripts.), it can "pin" the sandbox.
    ```json
    # Tool: pin_sandbox
    {
      "pinned_name": "research-task-01",
      "session_id": "current-session-uuid"
    }
    ```
    **Result**: This sandbox will **NOT** be auto-reclaimed by the garbage collector. It is saved under the name "research-task-01".

6.  **Re-attaching (`attach_sandbox_by_name`)**:
    Later, or in a different conversation turn, the agent can resume work in exactly the same state.
    ```json
    # Tool: attach_sandbox_by_name
    {
      "pinned_name": "research-task-01"
    }
    ```
    The agent receives a new Session ID that connects to the *same* container. The `hello.txt` file is still there.

### Key Features Explained

#### Volume Mapping
LocalSandbox supports mounting host directories into the sandbox. This is configured via `LSB_SHARED_VOLUME_PATH`.

*   **Mechanism**: Maps a path on your Host machine to a path inside the Sandbox container (e.g., `./workspace:/sandbox/workspace`).
*   **Benefit**: This is significantly more efficient than using file upload/download tools for every change. Agents can read/write files directly in the shared folder, and the changes are instantly reflected on the host. This effectivelybridges the gap between the isolated sandbox and the agent's workspace.

#### Pinned Sandboxes
Standard sessions are ephemeral and managed by a strict timeout policy (see below). **Pinning** exempts a sandbox from this cleanup and save it as a container image.
*   **Use Case**: Persisting successful environments, scripts, or dependencies after task completion.
*   **Future Roadmap**: Support for restoring pinned sandboxes directly from container images.
*   **Management**: Pinned sandboxes persist until explicitly removed or unpinned.

## 4. Lifecycle & Resource Management

LocalSandbox includes an automated Resource Manager to keep your system clean and efficient. This is controlled by several environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LSB_SESSION_TIMEOUT` | 3600s (1h) | **Session TTL**. If a session sees no activity (tool calls) for this duration, it is considered expired. |
| `LSB_CLEANUP_INTERVAL` | 60s | **Garbage Collection Frequency**. How often the background task checks for expired sessions. |
| `LSB_MAX_SESSIONS` | 10 | **Concurrency Limit**. The maximum number of active sandbox containers allowed simultaneously. |
| `LSB_ENABLE_LRU_EVICTION` | `true` | **LRU Policy**. If `MAX_SESSIONS` is reached, the server will automatically stop the *Least Recently Used* (LRU) session to make room for a new one, ensuring availability. |
| `LSB_ORPHAN_CLEANUP_INTERVAL` | 60s | **Orphan Sweeping**. Checks for Docker containers that might have been left behind (e.g., if the server crashed) and cleans them up to free resources. |

**Lifecycle Logic**:
1.  **Creation**: A container is spun up on demand.
2.  **Active**: Every tool call updates the "last accessed" timestamp.
3.  **Expiry**: If `current_time - last_accessed > SESSION_TIMEOUT`, the session is stopped and the container is removed.
4.  **Eviction**: If the server is full (`MAX_SESSIONS`), the oldest inactive session is killed immediately to handle the new request.

## 5. Agent Prompts & Skills

To effectively use LocalSandbox, you can leverage the `SKILL.md` file provided in the project root.

*   **For Skill-Supported Agent Systems**: The `SKILL.md` file is designed to be directly ingested by Agent systems that support "Skills". It teaches the agent the correct protocols for using the sandbox tools (session management, file mapping, etc.).
*   **Manual Prompting**: You can also directly copy the content of `SKILL.md` and paste it into your Agent's system prompt to instruct it on how to use the sandbox effectively.

## 6. TODO

*   [ ] **SDK**: Future versions will expose a formal Python SDK, allowing developers to integrate the LocalSandbox capability programmatically into their own applications without relying solely on the MCP server interface.
