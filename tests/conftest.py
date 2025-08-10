"""
Pytest configuration and shared fixtures for localsandbox tests.

This module provides common test configuration, fixtures, and utilities
for testing the Docker-based sandbox implementation.
"""

import asyncio
import os
import pytest
import sys
from pathlib import Path

# Add the python directory to the Python path so we can import the sandbox modules
project_root = Path(__file__).parent.parent
python_dir = project_root / "python"
sys.path.insert(0, str(python_dir))

# Set test environment variables
os.environ.setdefault("CONTAINER_RUNTIME", "docker")
os.environ.setdefault("LOCALSANDBOX_PYTHON_IMAGE", "python:3.11-slim")
os.environ.setdefault("LOCALSANDBOX_NODE_IMAGE", "node:18-slim")


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.
    
    This is needed for async tests to work properly across the entire test suite.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Set up the test environment before each test.
    
    This fixture runs automatically before each test to ensure
    a clean and consistent test environment.
    """
    # Set test-specific environment variables
    original_env = {}
    test_env_vars = {
        "CONTAINER_RUNTIME": "docker",
        "LOCALSANDBOX_PYTHON_IMAGE": "python:3.11-slim",
        "LOCALSANDBOX_NODE_IMAGE": "node:18-slim",
        "LOCALSANDBOX_DEFAULT_MEMORY": "128",
        "LOCALSANDBOX_DEFAULT_CPU": "0.5",
        "LOCALSANDBOX_DEFAULT_TIMEOUT": "30"
    }
    
    # Save original values and set test values
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring Docker"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add 'unit' marker to tests that don't have 'integration' marker
        if "integration" not in [marker.name for marker in item.iter_markers()]:
            item.add_marker(pytest.mark.unit)


def pytest_runtest_setup(item):
    """Set up individual test runs."""
    # Skip integration tests if Docker is not available
    if "integration" in [marker.name for marker in item.iter_markers()]:
        if not is_docker_available():
            pytest.skip("Docker is not available - skipping integration test")


def is_docker_available():
    """
    Check if Docker is available and running.
    
    Returns:
        bool: True if Docker is available, False otherwise
    """
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


@pytest.fixture
def docker_available():
    """
    Fixture that provides Docker availability status.
    
    Returns:
        bool: True if Docker is available, False otherwise
    """
    return is_docker_available()


@pytest.fixture
def skip_if_no_docker():
    """
    Fixture that skips the test if Docker is not available.
    
    Use this fixture in tests that require Docker but are not marked
    as integration tests.
    """
    if not is_docker_available():
        pytest.skip("Docker is not available")


# Async test utilities
@pytest.fixture
async def async_cleanup():
    """
    Fixture for async cleanup operations.
    
    Yields a list that test functions can append cleanup coroutines to.
    All cleanup coroutines will be executed after the test completes.
    """
    cleanup_tasks = []
    yield cleanup_tasks
    
    # Execute all cleanup tasks
    for cleanup_coro in cleanup_tasks:
        try:
            await cleanup_coro
        except Exception as e:
            # Log cleanup errors but don't fail the test
            print(f"Cleanup error: {e}")


# Test data fixtures
@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return "print('Hello, World!')"


@pytest.fixture
def sample_python_error_code():
    """Sample Python code that produces an error."""
    return "raise ValueError('Test error')"


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return "console.log('Hello, World!')"


@pytest.fixture
def sample_javascript_error_code():
    """Sample JavaScript code that produces an error."""
    return "throw new Error('Test error')"


@pytest.fixture
def sample_shell_commands():
    """Sample shell commands for testing."""
    return {
        "simple": ("echo", ["Hello, World!"]),
        "with_args": ("ls", ["-la", "/"]),
        "error": ("ls", ["nonexistent_file"]),
        "complex": ("sh", ["-c", "echo 'stdout'; echo 'stderr' >&2"])
    }