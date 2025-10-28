# LocalSandbox MCP Service User Guide

## Overview

LocalSandbox MCP Service is a secure code execution service based on the Model Context Protocol (MCP), providing isolated sandbox environments through Docker containers. The service supports code execution in multiple programming languages with comprehensive session management, resource control, and error handling mechanisms.

## Core Features

- **🌐 MCP Protocol Support**: Full implementation of MCP protocol supporting stdio, HTTP streaming, and SSE transports
- **🔒 Secure Sandbox**: Isolated execution environments based on Docker/Podman
- **🚀 Multi-language Support**: Support for Python, Node.js, and other programming languages
- **📊 Resource Management**: Intelligent resource allocation and session management
- **🔄 Session Persistence**: Support for sandbox pinning and state restoration
- **📁 Volume Mapping**: File sharing between host and containers
- **⚡ Concurrent Execution**: Handle multiple concurrent requests

## Installation and Configuration

### System Requirements

- Python 3.8+
- Docker or Podman (installed and running)
- Sufficient permissions to run containers

### Quick Installation

```bash
# Clone the project
git clone <repository-url>
cd localsandbox

# Install dependencies
pip install .

# Or development installation
pip install -e ".[dev]"
```

### Environment Configuration

1. **Copy configuration template**:
```bash
cp .env.example .env.local
```

2. **Edit configuration file**:
```bash
# MCP Server Configuration
MCP_SERVER_PORT=8775
MCP_SERVER_HOST=localhost
MCP_ENABLE_CORS=true

# Container Runtime Configuration
CONTAINER_RUNTIME=docker  # or podman
LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim
LOCALSANDBOX_NODE_IMAGE=node:18-slim

# Session Management
MSB_MAX_SESSIONS=5
MSB_SESSION_TIMEOUT=3600
MSB_DEFAULT_FLAVOR=small

# Volume Mapping Configuration
MSB_ENABLE_VOLUME_MAPPING=true
MSB_SHARED_VOLUME_PATH='["./data:/shared"]'

# Logging Configuration
MSB_LOG_LEVEL=INFO
```

## Starting the Service

### Method 1: Using LocalSandbox (Recommended)

```bash
# Start service (automatically loads .env.local)
start-localsandbox

# Specify configuration file
start-localsandbox --env-file .env.local

# Skip Docker checks
start-localsandbox --skip-docker-check
```

### Method 2: Standard MCP Protocol

```bash
# stdio transport (for MCP clients)
microsandbox-mcp-server

# HTTP streaming transport
microsandbox-mcp-server --transport streamable-http --port 8775

# SSE transport
microsandbox-mcp-server --transport sse --enable-cors
```

## MCP Tool Interfaces

### 1. execute_code - Code Execution

Execute code in a sandbox environment:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "execute_code",
    "arguments": {
      "code": "print('Hello, World!')\nx = 42\nprint(f'x = {x}')",
      "template": "python",
      "flavor": "small",
      "session_id": "optional-session-id",
      "timeout": 30
    }
  }
}
```

**Parameter Description**:
- `code`: Code to execute
- `template`: Language template (python, node, etc.)
- `flavor`: Resource specification (small, medium, large)
- `session_id`: Optional session ID
- `timeout`: Execution timeout in seconds

### 2. execute_command - Command Execution

Execute complete shell commands with pipes and redirections:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "execute_command",
    "arguments": {
      "command": "ls -la /tmp | grep -E '\\.(py|txt)$' | head -5",
      "template": "python",
      "session_id": "optional-session-id"
    }
  }
}
```

**Features**:
- Support for pipes (`|`), redirections (`>`), (`>>`)
- Support for command chaining (`&&`, `||`)
- Environment variables and shell expansion
- Complex command workflows

### 3. get_sessions - Session Management

Get active session information:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_sessions",
    "arguments": {
      "session_id": "optional-specific-session-id"
    }
  }
}
```

### 4. stop_session - Stop Session

Stop specified session:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "stop_session",
    "arguments": {
      "session_id": "session-to-stop"
    }
  }
}
```

### 5. pin_sandbox - Pin Sandbox

Save sandbox state for later restoration:

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "pin_sandbox",
    "arguments": {
      "pinned_name": "my-pinned-sandbox",
      "session_id": "current-session-id"
    }
  }
}
```

### 6. attach_pinned_sandbox - Attach Pinned Sandbox

Restore previously pinned sandbox:

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "attach_pinned_sandbox",
    "arguments": {
      "pinned_name": "my-pinned-sandbox"
    }
  }
}
```

### 7. get_volume_path - Get Volume Mapping

Get configured volume mapping information:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "get_volume_path",
    "arguments": {}
  }
}
```

## Resource Specifications (Flavors)

| Flavor | Memory | CPU | Use Cases |
|--------|--------|-----|-----------|
| small | 1GB | 1 core | Lightweight scripts, quick tests |
| medium | 2GB | 2 cores | Data analysis, moderate processing |
| large | 4GB | 4 cores | Heavy computation, complex operations |

## Session Management

### Session Lifecycle

1. **Create Session**: Automatically created on first tool call
2. **Session Reuse**: Use returned `session_id` to reuse session
3. **Session Pinning**: Use `pin_sandbox` to save state
4. **Session Restoration**: Use `attach_pinned_sandbox` to restore state
5. **Session Cleanup**: Cleaned up on timeout or manual stop

### Session Example

```python
# First call creates session
response1 = await session.call_tool('execute_code', {
    'code': 'x = 42',
    'template': 'python'
})
session_id = response1.structuredContent['session_id']

# Reuse session
response2 = await session.call_tool('execute_code', {
    'code': 'print(f"x = {x}")',  # Can access previously defined variables
    'template': 'python',
    'session_id': session_id
})
```

## Volume Mapping and File Sharing

### Configure Volume Mapping

Configure in `.env.local`:

```bash
# Enable volume mapping
MSB_ENABLE_VOLUME_MAPPING=true

# Configure shared paths (JSON array format)
MSB_SHARED_VOLUME_PATH='["./data:/shared", "/tmp/output:/results"]'
```

### Using Volume Mapping

```python
# Write file to host from container
await session.call_tool('execute_code', {
    'code': '''
with open("/shared/output.txt", "w") as f:
    f.write("Hello from sandbox!")
''',
    'template': 'python'
})

# Read host file
await session.call_tool('execute_code', {
    'code': '''
with open("/shared/input.txt", "r") as f:
    content = f.read()
print(content)
''',
    'template': 'python'
})
```

## Error Handling

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Code execution failed: Syntax error in Python code",
    "data": {
      "error_code": "CODE_EXECUTION_ERROR",
      "category": "execution",
      "severity": "medium",
      "recovery_suggestions": [
        "Check your code syntax",
        "Verify the template matches your code language"
      ],
      "context": {
        "template": "python",
        "session_id": "session-123"
      }
    }
  }
}
```

### Common Error Types

| Error Code | Description | Solution |
|------------|-------------|----------|
| RESOURCE_LIMIT_EXCEEDED | Resource limit exceeded | Use smaller flavor or optimize code |
| SESSION_NOT_FOUND | Session not found | Check session_id or create new session |
| CODE_EXECUTION_ERROR | Code execution failed | Check code syntax and logic |
| CONTAINER_RUNTIME_ERROR | Container runtime error | Check Docker/Podman status |

## Client Integration Examples

### Python Client

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:8775/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Execute Python code
            result = await session.call_tool('execute_code', {
                'code': 'print("Hello from MCP!")',
                'template': 'python'
            })
            
            print(result.structuredContent['result'])

asyncio.run(main())
```

### JavaScript Client

```javascript
const { MCPClient } = require('@modelcontextprotocol/sdk');

async function main() {
    const client = new MCPClient();
    await client.connect('http://localhost:8775/mcp');
    
    // Execute code
    const result = await client.callTool('execute_code', {
        code: 'console.log("Hello from MCP!")',
        template: 'node'
    });
    
    console.log(result.result);
}

main().catch(console.error);
```

### curl Command Line Testing

```bash
# Test tools list
curl -X POST http://localhost:8775/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Execute Python code
curl -X POST http://localhost:8775/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "execute_code",
      "arguments": {
        "code": "print(\"Hello from curl!\")",
        "template": "python"
      }
    }
  }'
```

## Performance Optimization Recommendations

### Session Reuse

```python
# Good practice: reuse sessions
session_id = None
for task in tasks:
    args = {'code': task.code, 'template': 'python'}
    if session_id:
        args['session_id'] = session_id
    
    result = await session.call_tool('execute_code', args)
    if not session_id:
        session_id = result.structuredContent['session_id']
```

### Resource Planning

```bash
# High throughput, lightweight workloads
MSB_MAX_SESSIONS=50
MSB_DEFAULT_FLAVOR=small
MSB_SESSION_TIMEOUT=300

# Resource-intensive, long-running workloads
MSB_MAX_SESSIONS=5
MSB_DEFAULT_FLAVOR=large
MSB_SESSION_TIMEOUT=3600
```

### Monitoring and Debugging

```bash
# Enable verbose logging
MSB_LOG_LEVEL=DEBUG start-localsandbox

# Check active sessions
curl -X POST http://localhost:8775/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_sessions","arguments":{}}}'
```

## Deployment Guide

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install .

EXPOSE 8775

CMD ["start-localsandbox"]
```

### Production Environment Configuration

```bash
# Production environment variables
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
MCP_ENABLE_CORS=false
MSB_MAX_SESSIONS=20
MSB_SESSION_TIMEOUT=1800
MSB_LOG_LEVEL=WARNING
```

### systemd Service

```ini
[Unit]
Description=LocalSandbox MCP Server
After=network.target docker.service

[Service]
Type=simple
User=localsandbox
WorkingDirectory=/opt/localsandbox
Environment=MSB_LOG_LEVEL=INFO
ExecStart=/opt/localsandbox/venv/bin/start-localsandbox
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Common Issues

1. **Service fails to start**
   ```bash
   # Check Docker status
   docker ps
   
   # Check port usage
   lsof -i :8775
   
   # View detailed logs
   MSB_LOG_LEVEL=DEBUG start-localsandbox
   ```

2. **Container permission issues**
   ```bash
   # Ensure user is in docker group (Linux)
   sudo usermod -aG docker $USER
   
   # Re-login or restart
   ```

3. **Volume mapping failures**
   ```bash
   # Check path permissions
   ls -la ./data
   
   # Verify path format
   echo $MSB_SHARED_VOLUME_PATH
   ```

### Health Checks

```bash
# Check service status
curl http://localhost:8775/

# Check MCP protocol
curl -X POST http://localhost:8775/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Testing

### Running E2E Tests

```bash
# Start server
start-localsandbox --env-file .env.test

# Run end-to-end tests
python -m pytest tests/test_e2e.py -v
```

### Test Coverage

E2E tests include the following steps:
1. Python Hello World Execution
2. Shared Volume Access Verification
3. File Creation and Persistence
4. Sandbox Pinning
5. Pinned Sandbox File Verification
6. Session Termination
7. Sandbox Reattachment
8. Restored File Content Verification
9. Restored Shared Volume Verification

## Best Practices

1. **Session Management**: Reuse sessions for related operations to improve performance
2. **Resource Selection**: Choose appropriate flavors based on workload requirements
3. **Error Handling**: Implement proper JSON-RPC error handling in MCP clients
4. **Timeout Settings**: Set reasonable timeouts for long-running operations
5. **Monitoring**: Regularly check session status and resource usage
6. **Security**: Only enable CORS when needed in production environments
7. **Logging**: Use appropriate log levels for production deployments
8. **Health Checks**: Implement health monitoring mechanisms

## Support and Resources

- **Project Documentation**: See README.md in the project root
- **MCP Protocol**: Refer to [MCP Specification](https://spec.modelcontextprotocol.io/)
- **Issue Reporting**: Report bugs and feature requests via GitHub Issues
- **Example Code**: Check `examples/` directory for more usage examples

---

**Ready to get started?** Start the service and begin using LocalSandbox MCP service with any MCP-compatible client!
