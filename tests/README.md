# LocalSandbox Integration Tests

This directory contains comprehensive integration tests for the Docker-based LocalSandbox implementation. The tests verify container runtime functionality, sandbox execution, and command execution capabilities.

## Test Structure

### Test Files

- **`test_container_runtime.py`** - Tests for the container runtime abstraction layer
  - `ContainerConfig` and `ContainerStats` data model validation
  - `DockerRuntime` implementation testing
  - Container lifecycle management (create, start, stop, remove)
  - Command execution within containers
  - Error handling and timeout scenarios

- **`test_sandbox_execution.py`** - Tests for sandbox code execution
  - `PythonSandbox` and `NodeSandbox` functionality
  - Code execution with various scenarios (success, error, mixed output)
  - Output format compatibility and consistency
  - Error handling and exception scenarios

- **`test_command_execution.py`** - Tests for shell command execution
  - `Command` class functionality
  - Shell command execution with various parameters
  - Timeout handling and control
  - `CommandExecution` object compatibility
  - Cross-sandbox consistency

### Configuration Files

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`pytest.ini`** - Pytest settings and markers
- **`run_tests.py`** - Test runner script with various options

## Test Types

### Unit Tests
Unit tests mock external dependencies and focus on testing individual components in isolation. They don't require Docker to be installed and run quickly.

**Markers**: `@pytest.mark.unit` (applied automatically to non-integration tests)

### Integration Tests
Integration tests require Docker to be installed and running. They test the complete functionality with real containers.

**Markers**: `@pytest.mark.integration`

## Prerequisites

### Required Dependencies
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Optional: for coverage reports
pip install pytest-cov
```

### Docker Requirements
For integration tests, you need:
- Docker installed and running
- Access to pull Python and Node.js images
- Sufficient permissions to create/manage containers

## Running Tests

### Using the Test Runner Script

The `run_tests.py` script provides a convenient way to run different types of tests:

```bash
# Run all unit tests (default, no Docker required)
python tests/run_tests.py

# Run all tests including integration tests (requires Docker)
python tests/run_tests.py --integration

# Run only unit tests explicitly
python tests/run_tests.py --unit-only

# Run specific test modules
python tests/run_tests.py --container    # Container runtime tests
python tests/run_tests.py --sandbox     # Sandbox execution tests
python tests/run_tests.py --command     # Command execution tests

# Run with verbose output
python tests/run_tests.py --verbose

# Run with coverage report
python tests/run_tests.py --coverage

# Run with HTML coverage report
python tests/run_tests.py --html-coverage
```

### Using Pytest Directly

You can also run pytest directly from the tests directory:

```bash
cd tests

# Run all unit tests
pytest -m "not integration"

# Run all tests including integration
pytest

# Run only integration tests
pytest -m integration

# Run specific test file
pytest test_container_runtime.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=python.sandbox --cov-report=term-missing
```

### Environment Variables

The tests use the following environment variables (with defaults):

```bash
CONTAINER_RUNTIME=docker                    # Container runtime to use
LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim # Python container image
LOCALSANDBOX_NODE_IMAGE=node:18-slim       # Node.js container image
LOCALSANDBOX_DEFAULT_MEMORY=128            # Default memory limit (MB)
LOCALSANDBOX_DEFAULT_CPU=0.5               # Default CPU limit
LOCALSANDBOX_DEFAULT_TIMEOUT=30            # Default timeout (seconds)
```

## Test Categories

### Container Runtime Tests (`test_container_runtime.py`)

**Data Model Tests**:
- `TestContainerConfig` - Configuration validation and defaults
- `TestContainerStats` - Statistics data validation

**Runtime Implementation Tests**:
- `TestDockerRuntime` - Docker CLI command execution
- Container lifecycle operations
- Command execution within containers
- Error handling and timeouts

**Integration Tests**:
- `TestDockerRuntimeIntegration` - Real container operations
- Full lifecycle testing with actual Docker containers

### Sandbox Execution Tests (`test_sandbox_execution.py`)

**Python Sandbox Tests**:
- `TestPythonSandboxExecution` - Python code execution
- Default image configuration
- Code execution scenarios (success, error, mixed output)
- Error handling and validation

**Node.js Sandbox Tests**:
- `TestNodeSandboxExecution` - JavaScript code execution
- Similar test scenarios as Python sandbox

**Compatibility Tests**:
- `TestSandboxOutputCompatibility` - Cross-language consistency
- Output format validation
- Error output consistency

**Integration Tests**:
- `TestSandboxIntegration` - Real container execution
- Context manager usage
- Error handling with real containers

### Command Execution Tests (`test_command_execution.py`)

**Command Class Tests**:
- `TestCommandExecution` - Basic command execution
- Parameter handling and validation
- Timeout control and error handling

**CommandExecution Object Tests**:
- `TestCommandExecutionObject` - Output format validation
- Structure and compatibility testing

**Integration Tests**:
- `TestCommandIntegrationWithSandboxes` - Cross-sandbox consistency
- `TestCommandParameterHandling` - Edge cases and special characters
- `TestCommandTimeoutHandling` - Timeout scenarios
- `TestCommandIntegration` - Real container command execution

## Test Patterns and Best Practices

### Mocking Strategy
Unit tests use `unittest.mock` to mock external dependencies:
- Container runtime operations are mocked for fast, isolated testing
- Real Docker operations are only used in integration tests
- Consistent mock response formats ensure realistic testing

### Async Testing
All tests use `pytest-asyncio` for proper async/await support:
- `@pytest.mark.asyncio` decorator for async test functions
- Proper event loop management through fixtures
- Async cleanup handling for resource management

### Error Testing
Comprehensive error scenario testing:
- Network/Docker unavailability
- Container creation/start failures
- Command execution errors and timeouts
- Invalid configuration and parameter validation

### Resource Cleanup
Proper cleanup in integration tests:
- Container cleanup in finally blocks
- Async cleanup fixtures for complex scenarios
- Automatic cleanup on test failures

## Troubleshooting

### Common Issues

**Docker Not Available**:
```
SKIPPED [1] conftest.py:XX: Docker is not available - skipping integration test
```
- Ensure Docker is installed and running
- Check Docker permissions for your user
- Verify Docker daemon is accessible

**Import Errors**:
```
ModuleNotFoundError: No module named 'python.sandbox'
```
- Ensure you're running tests from the correct directory
- Check that the Python path includes the project root
- Verify all required dependencies are installed

**Container Image Pull Failures**:
```
RuntimeError: Failed to create container: Unable to find image 'python:3.11-slim'
```
- Ensure internet connectivity for image pulls
- Pre-pull required images: `docker pull python:3.11-slim node:18-slim`
- Check Docker Hub accessibility

**Permission Errors**:
```
RuntimeError: Failed to create container: permission denied
```
- Add your user to the docker group: `sudo usermod -aG docker $USER`
- Restart your session after adding to docker group
- Or run tests with sudo (not recommended)

### Debug Mode

For debugging test failures, use verbose output and specific test selection:

```bash
# Run a specific test with maximum verbosity
pytest -vvv -s test_container_runtime.py::TestDockerRuntime::test_create_container_success

# Run with Python debugging
python -m pdb -m pytest test_container_runtime.py

# Run with custom markers for debugging
pytest -m "not integration" -v --tb=long
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` files, `Test*` classes, `test_*` methods
2. **Use appropriate markers**: `@pytest.mark.integration` for tests requiring Docker
3. **Mock external dependencies** in unit tests
4. **Clean up resources** in integration tests
5. **Test both success and error scenarios**
6. **Maintain output format compatibility**
7. **Add docstrings** explaining test purpose and scenarios

## Coverage Goals

The test suite aims for high coverage of:
- All public API methods and properties
- Error handling and edge cases
- Cross-platform compatibility (Docker/Podman)
- Output format consistency
- Resource management and cleanup

Current coverage targets:
- Container runtime: >95%
- Sandbox execution: >90%
- Command execution: >90%
- Overall project: >85%