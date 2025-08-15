# Design Document

## Overview

The E2E integration test system will be implemented as a comprehensive Python test script that validates the complete MCP server functionality through a series of sequential operations. The design follows the existing test patterns in the codebase while implementing the specific test sequence requested: Python hello world execution, volume mapping verification, file persistence testing, sandbox pinning, session management, and state restoration through reattachment.

The system will use the official MCP SDK client to ensure standards compliance and will start the MCP server using the same environment configuration as specified in .env.example. The test will be self-contained, handling server startup, client connection, test execution, and cleanup automatically.

## Architecture

### Component Structure

```
E2E Integration Test System
├── Test Runner (e2e_integration_test.py)
│   ├── MCPServerManager - Server lifecycle management
│   ├── MCPClientManager - Client connection management  
│   ├── TestSequenceExecutor - Test step execution
│   └── TestReporter - Results collection and reporting
├── Configuration Manager
│   ├── Environment loader (.env.example parsing)
│   └── Test configuration validation
└── Documentation (E2ETEST.md)
    ├── Setup instructions
    ├── Execution guide
    └── Troubleshooting guide
```

### Test Flow Architecture

The test follows a linear sequence with comprehensive validation at each step:

1. **Environment Setup Phase**
   - Load environment variables from .env.example
   - Validate MCP client dependencies
   - Prepare test workspace

2. **Server Startup Phase**
   - Start MCP server with test configuration
   - Establish client connection using official MCP SDK
   - Verify server readiness

3. **Test Execution Phase**
   - Execute 9 sequential test steps
   - Validate each step's output
   - Maintain state between steps

4. **Cleanup Phase**
   - Stop active sessions
   - Terminate server process
   - Generate test report

## Components and Interfaces

### MCPServerManager

**Purpose:** Manages MCP server lifecycle including startup, configuration, and shutdown.

**Key Methods:**
- `start_server(env_config: Dict) -> ServerProcess`
- `stop_server(process: ServerProcess) -> bool`
- `is_server_healthy() -> bool`

**Configuration:**
- Uses environment variables from .env.example
- Applies test-specific overrides for timeouts
- Manages server process lifecycle

### MCPClientManager

**Purpose:** Handles MCP client connection using official SDK.

**Key Methods:**
- `connect() -> ClientSession`
- `disconnect() -> None`
- `call_tool(tool_name: str, params: Dict) -> ToolResult`

**Implementation:**
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connection establishment
server_params = StdioServerParameters(
    command="python",
    args=["-m", "mcp_server.main"],
    env=environment_config
)
session, process = await stdio_client(server_params)
```

### TestSequenceExecutor

**Purpose:** Executes the 9-step test sequence with validation.

**Test Steps:**
1. `execute_python_hello_world() -> TestResult`
2. `verify_shared_volume_access() -> TestResult`
3. `create_hello_txt_file() -> TestResult`
4. `pin_sandbox() -> TestResult`
5. `verify_pinned_sandbox_files() -> TestResult`
6. `stop_session() -> TestResult`
7. `attach_to_pinned_sandbox() -> TestResult`
8. `verify_restored_files() -> TestResult`
9. `verify_shared_volume_in_restored() -> TestResult`

**State Management:**
- Maintains session_id across steps 1-6
- Stores pinned_name for step 7
- Tracks new session_id for steps 7-9

### TestReporter

**Purpose:** Collects and formats test results.

**Key Methods:**
- `record_step_result(step: int, result: TestResult) -> None`
- `generate_report() -> TestReport`
- `print_summary() -> None`

**Output Format:**
- Step-by-step execution log
- Success/failure indicators
- Error details for failed steps
- Performance metrics (execution times)
- Final summary with overall result

## Data Models

### TestResult

```python
@dataclass
class TestResult:
    step_number: int
    step_name: str
    success: bool
    output: str
    error_message: Optional[str]
    execution_time_ms: int
    session_id: Optional[str]
    metadata: Dict[str, Any]
```

### TestConfiguration

```python
@dataclass
class TestConfiguration:
    server_host: str
    server_port: int
    shared_volume_path: str
    container_runtime: str
    python_image: str
    session_timeout: int
    max_sessions: int
    test_timeout: int
```

### EnvironmentConfig

```python
@dataclass
class EnvironmentConfig:
    mcp_server_port: int
    mcp_server_host: str
    container_runtime: str
    python_image: str
    shared_volume_path: str
    session_timeout: int
    max_sessions: int
    # ... other environment variables from .env.example
```

## Error Handling

### Error Categories

1. **Configuration Errors**
   - Missing .env.example file
   - Invalid environment variables
   - Missing MCP client dependencies

2. **Server Startup Errors**
   - Port already in use
   - Docker/container runtime not available
   - Server process startup failure

3. **Client Connection Errors**
   - MCP protocol handshake failure
   - Server not responding
   - Network connectivity issues

4. **Test Execution Errors**
   - Tool call failures
   - Sandbox creation errors
   - File operation failures
   - Session management errors

### Error Handling Strategy

```python
class E2ETestError(Exception):
    """Base exception for E2E test errors."""
    pass

class ServerStartupError(E2ETestError):
    """Server failed to start properly."""
    pass

class ClientConnectionError(E2ETestError):
    """Client failed to connect to server."""
    pass

class TestStepError(E2ETestError):
    """Individual test step failed."""
    def __init__(self, step_number: int, step_name: str, original_error: Exception):
        self.step_number = step_number
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(f"Step {step_number} ({step_name}) failed: {original_error}")
```

### Recovery Mechanisms

- **Server Startup Failure:** Retry with different port, check dependencies
- **Client Connection Failure:** Retry connection, verify server health
- **Test Step Failure:** Log detailed error, attempt cleanup, continue with remaining steps where possible
- **Resource Cleanup:** Always attempt cleanup even if test fails

## Testing Strategy

### Unit Testing Approach

The E2E test itself will be thoroughly tested with:

1. **Mock Server Testing**
   - Test client connection logic with mock server
   - Validate error handling paths
   - Test configuration parsing

2. **Integration Testing**
   - Test against real MCP server in controlled environment
   - Validate all 9 test steps individually
   - Test error recovery mechanisms

3. **Environment Testing**
   - Test with different .env.example configurations
   - Validate Docker vs Podman compatibility
   - Test volume mapping variations

### Test Data Management

```python
TEST_DATA = {
    "hello_world_code": 'print("Hello, World!")',
    "hello_txt_content": "hello sandbox",
    "hello_txt_path": "/hello.txt",
    "shared_volume_commands": ["ls /shared", "cat /shared/data.txt"],
    "pinned_sandbox_name": "e2e-test-sandbox-{timestamp}"
}
```

### Validation Criteria

Each test step includes specific validation:

1. **Python Hello World:** Output contains "Hello, World!"
2. **Volume Access:** `/shared` directory exists and contains expected files
3. **File Creation:** `/hello.txt` exists with correct content
4. **Sandbox Pinning:** Pin operation returns success confirmation
5. **Pin Verification:** Files still accessible after pinning
6. **Session Stop:** Session no longer appears in active sessions
7. **Sandbox Attach:** New session_id returned for pinned sandbox
8. **File Restoration:** Original files still exist with correct content
9. **Volume Restoration:** Shared volume still accessible in restored sandbox

## Implementation Details

### Environment Configuration Loading

```python
def load_env_config() -> EnvironmentConfig:
    """Load configuration from .env.example file."""
    env_path = Path(".env.example")
    if not env_path.exists():
        raise ConfigurationError("Missing .env.example file")
    
    config = {}
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                config[key] = value
    
    return EnvironmentConfig(
        mcp_server_port=int(config.get('MCP_SERVER_PORT', '8775')),
        mcp_server_host=config.get('MCP_SERVER_HOST', 'localhost'),
        container_runtime=config.get('CONTAINER_RUNTIME', 'docker'),
        python_image=config.get('LOCALSANDBOX_PYTHON_IMAGE', 'python:3.11-slim'),
        shared_volume_path=config.get('MSB_SHARED_VOLUME_PATH', '[]'),
        session_timeout=int(config.get('MSB_SESSION_TIMEOUT', '3600')),
        max_sessions=int(config.get('MSB_MAX_SESSIONS', '5'))
    )
```

### MCP Client Integration

```python
async def setup_mcp_client(self, env_config: EnvironmentConfig) -> ClientSession:
    """Set up MCP client connection using official SDK."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.main"],
        env={
            'MCP_SERVER_PORT': str(env_config.mcp_server_port),
            'MCP_SERVER_HOST': env_config.mcp_server_host,
            'CONTAINER_RUNTIME': env_config.container_runtime,
            'LOCALSANDBOX_PYTHON_IMAGE': env_config.python_image,
            'MSB_SHARED_VOLUME_PATH': env_config.shared_volume_path,
            'MSB_SESSION_TIMEOUT': str(env_config.session_timeout),
            'MSB_MAX_SESSIONS': str(env_config.max_sessions)
        }
    )
    
    session, process = await stdio_client(server_params)
    self.server_process = process
    return session
```

### Test Step Implementation Pattern

```python
async def execute_test_step(self, step_number: int, step_name: str, 
                          step_function: Callable) -> TestResult:
    """Execute a single test step with error handling and timing."""
    start_time = time.time()
    
    try:
        result = await step_function()
        execution_time = int((time.time() - start_time) * 1000)
        
        return TestResult(
            step_number=step_number,
            step_name=step_name,
            success=True,
            output=result.get('output', ''),
            error_message=None,
            execution_time_ms=execution_time,
            session_id=result.get('session_id'),
            metadata=result.get('metadata', {})
        )
    
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        
        return TestResult(
            step_number=step_number,
            step_name=step_name,
            success=False,
            output='',
            error_message=str(e),
            execution_time_ms=execution_time,
            session_id=None,
            metadata={'exception_type': type(e).__name__}
        )
```

This design provides a robust, maintainable, and comprehensive E2E testing solution that validates all aspects of the MCP server functionality while following established patterns in the codebase.