

## Overview

The E2E integration test validates the complete MCP server functionality through a series of 9 sequential test steps:

1. **Python Hello World Execution** - Validates basic sandbox code execution
2. **Shared Volume Access Verification** - Tests volume mapping between host and container
3. **File Creation and Persistence** - Verifies file operations within sandbox sessions
4. **Sandbox Pinning** - Tests the ability to preserve sandbox state beyond session cleanup
5. **Pinned Sandbox File Verification** - Validates that files persist after pinning
6. **Session Termination** - Tests proper session lifecycle management
7. **Sandbox Reattachment** - Validates the ability to restore pinned sandboxes
8. **Restored File Content Verification** - Ensures state persistence across pin-attach cycle
9. **Restored Shared Volume Verification** - Validates volume mapping persistence

The test uses the official MCP SDK client to ensure standards compliance and follows the exact environment configuration specified in `.env.example`.

## Prerequisites

### System Requirements

- **Operating System**: macOS, Linux, or Windows with WSL2
- **Python**: Version 3.8 or higher
- **Container Runtime**: Docker or Podman
- **Memory**: At least 2GB available RAM
- **Disk Space**: At least 1GB free space

### Software Dependencies

1. **Python Dependencies**:
   ```bash
   pip install mcp asyncio
   ```

2. **Container Runtime**:
   - **Docker**: Install from [docker.com](https://www.docker.com/get-started)

3. **MCP Server**: Ensure the MCP server code is available in the current directory

## Installation and Setup

### 1. Clone or Download the Repository

Ensure you have the MCP server code and the E2E test script in your working directory:

```bash
# Your directory should contain:
# - e2e_integration_test.py
# - .env.example
# - mcp_server/ (MCP server code)
# - Other project files
```

### 2. Install Python Dependencies

```bash
# Install required Python packages
pip install mcp asyncio

# Or if using a virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install mcp asyncio
```

### 3. Verify Container Runtime

Test that your container runtime is working:

```bash
# For Docker:
docker --version
docker ps


### 4. Configure Environment

Copy and customize the environment configuration:

```bash
# The test uses .env.example by default
# Optionally, create a custom configuration:
cp .env.example .env.custom
# Edit .env.custom as needed
```

## Configuration

### Environment File Structure

The test reads configuration from `.env.example` (or a custom file specified with `--config`). Key configuration sections include:

#### MCP Server Configuration
```bash
MCP_ENABLE_CORS=true
MCP_SERVER_PORT=8775
MCP_SERVER_HOST=localhost
```

#### Container Runtime Configuration
```bash
CONTAINER_RUNTIME=docker  # or podman
LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim
LOCALSANDBOX_NODE_IMAGE=node:18-slim
LOCALSANDBOX_DEFAULT_TIMEOUT=1800
```

#### Session Management
```bash
MSB_MAX_SESSIONS=5
MSB_SESSION_TIMEOUT=3600
MSB_DEFAULT_FLAVOR=small
MSB_SESSION_CLEANUP_INTERVAL=60
```

#### Volume Mapping
```bash
MSB_ENABLE_VOLUME_MAPPING=true
MSB_SHARED_VOLUME_PATH='["/path/to/host/data:/shared"]'
```

### Critical Configuration Notes

1. **Shared Volume Path**: Must be a JSON array of volume mappings in the format `["host_path:container_path"]`
2. **Container Runtime**: Must be either `docker` or `podman`
3. **Port Availability**: Ensure the MCP server port (default 8775) is available
4. **File Permissions**: Ensure the shared volume paths are readable/writable

## Test Sequence

The E2E test executes the following sequence:

### Step 1: Python Hello World Execution
- **Purpose**: Validate basic sandbox code execution
- **Action**: Execute `print("Hello, World!")` in a Python sandbox
- **Validation**: Output contains "Hello, World!" and returns valid session_id

### Step 2: Shared Volume Access Verification  
- **Purpose**: Test volume mapping between host and container
- **Action**: Execute `ls /shared` command in the sandbox
- **Validation**: Shared directory is accessible and contains expected files

### Step 3: File Creation and Persistence
- **Purpose**: Verify file operations within sandbox sessions
- **Action**: Create `/hello.txt` file with content "hello sandbox"
- **Validation**: File exists and contains correct content

### Step 4: Sandbox Pinning
- **Purpose**: Test the ability to preserve sandbox state
- **Action**: Pin the current sandbox with a unique name
- **Validation**: Pin operation returns success confirmation

### Step 5: Pinned Sandbox File Verification
- **Purpose**: Validate that files persist after pinning
- **Action**: Verify `/hello.txt` still exists in pinned sandbox
- **Validation**: File is accessible with correct content

### Step 6: Session Termination
- **Purpose**: Test proper session lifecycle management
- **Action**: Stop the current session
- **Validation**: Session is no longer active

### Step 7: Sandbox Reattachment
- **Purpose**: Validate the ability to restore pinned sandboxes
- **Action**: Attach to the previously pinned sandbox by name
- **Validation**: New session_id returned for restored sandbox

### Step 8: Restored File Content Verification
- **Purpose**: Ensure state persistence across pin-attach cycle
- **Action**: Read `/hello.txt` from the restored sandbox
- **Validation**: File contains original "hello sandbox" content

### Step 9: Restored Shared Volume Verification
- **Purpose**: Validate volume mapping persistence
- **Action**: Execute `ls /shared` in the restored sandbox
- **Validation**: Shared volume is still accessible with same contents

