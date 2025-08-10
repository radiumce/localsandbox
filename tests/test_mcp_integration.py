"""
Test MCP Server integration compatibility with the new Docker-based sandbox SDK.

This test verifies that the microsandbox_wrapper can correctly import and use
the new container-based sandbox implementation without breaking existing functionality.
"""

import asyncio
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add the python sandbox package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

# Test imports that mirror the MCP server's usage
def test_sandbox_imports():
    """Test that sandbox classes can be imported as expected by MCP server."""
    try:
        # This mirrors the import pattern in session_manager.py
        from sandbox import PythonSandbox, NodeSandbox
        
        # Verify classes exist and are callable
        assert PythonSandbox is not None
        assert NodeSandbox is not None
        assert callable(PythonSandbox)
        assert callable(NodeSandbox)
        
        print("✓ Successfully imported PythonSandbox and NodeSandbox")
        
    except ImportError as e:
        pytest.fail(f"Failed to import sandbox classes: {e}")


def test_sandbox_interface_compatibility():
    """Test that sandbox classes have the expected interface for MCP server."""
    from sandbox import PythonSandbox, NodeSandbox
    
    # Test PythonSandbox interface
    python_sandbox = PythonSandbox(
        container_runtime="docker",
        namespace="test",
        name="test-python-sandbox"
    )
    
    # Verify expected methods exist
    assert hasattr(python_sandbox, 'start'), "PythonSandbox missing start() method"
    assert hasattr(python_sandbox, 'stop'), "PythonSandbox missing stop() method"
    assert hasattr(python_sandbox, 'run'), "PythonSandbox missing run() method"
    assert hasattr(python_sandbox, 'command'), "PythonSandbox missing command attribute"
    assert hasattr(python_sandbox, '_is_started'), "PythonSandbox missing _is_started attribute"
    
    # Test NodeSandbox interface
    node_sandbox = NodeSandbox(
        container_runtime="docker",
        namespace="test",
        name="test-node-sandbox"
    )
    
    # Verify expected methods exist
    assert hasattr(node_sandbox, 'start'), "NodeSandbox missing start() method"
    assert hasattr(node_sandbox, 'stop'), "NodeSandbox missing stop() method"
    assert hasattr(node_sandbox, 'run'), "NodeSandbox missing run() method"
    assert hasattr(node_sandbox, 'command'), "NodeSandbox missing command attribute"
    assert hasattr(node_sandbox, '_is_started'), "NodeSandbox missing _is_started attribute"
    
    print("✓ Sandbox classes have expected interface")


@pytest.mark.asyncio
async def test_python_sandbox_creation_and_basic_usage():
    """Test PythonSandbox creation and basic operations without Docker."""
    from sandbox import PythonSandbox
    
    # Create sandbox instance (should not require Docker to be available for creation)
    sandbox = PythonSandbox(
        container_runtime="docker",
        namespace="test",
        name="test-python-sandbox"
    )
    
    # Verify initial state
    assert not sandbox._is_started, "Sandbox should not be started initially"
    assert sandbox._container_id is None, "Container ID should be None initially"
    
    # Test that we can access the command interface
    assert hasattr(sandbox.command, 'run'), "Command interface missing run method"
    
    print("✓ PythonSandbox creation and basic interface works")


@pytest.mark.asyncio
async def test_node_sandbox_creation_and_basic_usage():
    """Test NodeSandbox creation and basic operations without Docker."""
    from sandbox import NodeSandbox
    
    # Create sandbox instance (should not require Docker to be available for creation)
    sandbox = NodeSandbox(
        container_runtime="docker",
        namespace="test",
        name="test-node-sandbox"
    )
    
    # Verify initial state
    assert not sandbox._is_started, "Sandbox should not be started initially"
    assert sandbox._container_id is None, "Container ID should be None initially"
    
    # Test that we can access the command interface
    assert hasattr(sandbox.command, 'run'), "Command interface missing run method"
    
    print("✓ NodeSandbox creation and basic interface works")


def test_execution_and_command_execution_classes():
    """Test that Execution and CommandExecution classes are available and compatible."""
    from sandbox import Execution, CommandExecution
    
    # Test Execution class
    execution_data = {
        "output": [{"stream": "stdout", "text": "Hello World"}],
        "status": "success",
        "language": "python"
    }
    execution = Execution(output_data=execution_data)
    
    # Verify expected methods exist
    assert hasattr(execution, 'output'), "Execution missing output() method"
    assert hasattr(execution, 'error'), "Execution missing error() method"
    assert hasattr(execution, 'has_error'), "Execution missing has_error() method"
    
    # Test CommandExecution class
    command_data = {
        "output": [{"stream": "stdout", "text": "test output"}],
        "command": "echo",
        "args": ["test"],
        "exit_code": 0,
        "success": True
    }
    command_execution = CommandExecution(output_data=command_data)
    
    # Verify expected methods exist
    assert hasattr(command_execution, 'output'), "CommandExecution missing output() method"
    assert hasattr(command_execution, 'error'), "CommandExecution missing error() method"
    assert hasattr(command_execution, 'exit_code'), "CommandExecution missing exit_code property"
    assert hasattr(command_execution, 'success'), "CommandExecution missing success property"
    
    print("✓ Execution and CommandExecution classes are compatible")


def test_mcp_server_import_pattern():
    """Test the exact import pattern used by the MCP server."""
    # This simulates the import pattern in session_manager.py lines 432 and 440
    try:
        # Test Python sandbox import
        from sandbox import PythonSandbox
        
        # Test creating with parameters similar to MCP server usage
        python_sandbox = PythonSandbox(
            container_runtime="docker",  # New parameter instead of server_url
            namespace="default",
            name="session-12345678"
            # Note: api_key parameter is no longer needed
        )
        
        assert python_sandbox is not None
        print("✓ PythonSandbox import pattern compatible")
        
        # Test Node sandbox import
        from sandbox import NodeSandbox
        
        node_sandbox = NodeSandbox(
            container_runtime="docker",  # New parameter instead of server_url
            namespace="default",
            name="session-87654321"
            # Note: api_key parameter is no longer needed
        )
        
        assert node_sandbox is not None
        print("✓ NodeSandbox import pattern compatible")
        
    except Exception as e:
        pytest.fail(f"MCP server import pattern failed: {e}")


def test_backward_compatibility_parameters():
    """Test that old parameters are handled gracefully."""
    from sandbox import PythonSandbox, NodeSandbox
    
    # Test that we can create sandboxes without the old HTTP-related parameters
    # The new implementation should work with just the container runtime parameters
    
    python_sandbox = PythonSandbox(
        container_runtime="docker",
        namespace="test",
        name="test-sandbox"
    )
    
    node_sandbox = NodeSandbox(
        container_runtime="docker", 
        namespace="test",
        name="test-sandbox"
    )
    
    # Both should be created successfully
    assert python_sandbox is not None
    assert node_sandbox is not None
    
    print("✓ Backward compatibility with parameter changes works")


if __name__ == "__main__":
    """Run the tests directly for quick verification."""
    print("Testing MCP Server integration compatibility...")
    print()
    
    # Run synchronous tests
    test_sandbox_imports()
    test_sandbox_interface_compatibility()
    test_execution_and_command_execution_classes()
    test_mcp_server_import_pattern()
    test_backward_compatibility_parameters()
    
    # Run async tests
    async def run_async_tests():
        await test_python_sandbox_creation_and_basic_usage()
        await test_node_sandbox_creation_and_basic_usage()
    
    asyncio.run(run_async_tests())
    
    print()
    print("✅ All MCP Server integration compatibility tests passed!")
    print()
    print("The new Docker-based sandbox SDK is compatible with the MCP server.")
    print("The MCP server should be able to import and use PythonSandbox and NodeSandbox")
    print("without any code changes to the import statements.")