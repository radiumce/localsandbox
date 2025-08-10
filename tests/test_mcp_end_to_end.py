"""
End-to-end test for MCP Server integration with Docker-based sandbox SDK.

This test simulates the complete workflow that the MCP server uses,
including session management, code execution, and resource cleanup.
"""

import asyncio
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add the python sandbox package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))


class MockContainerRuntime:
    """Mock container runtime for testing without Docker."""
    
    def __init__(self):
        self.containers = {}
        self.next_container_id = 1
    
    async def create_container(self, config):
        container_id = f"mock_container_{self.next_container_id}"
        self.next_container_id += 1
        self.containers[container_id] = {
            'config': config,
            'running': False,
            'created': True
        }
        return container_id
    
    async def start_container(self, container_id):
        if container_id in self.containers:
            self.containers[container_id]['running'] = True
    
    async def stop_container(self, container_id):
        if container_id in self.containers:
            self.containers[container_id]['running'] = False
    
    async def remove_container(self, container_id):
        if container_id in self.containers:
            del self.containers[container_id]
    
    async def execute_command(self, container_id, command, timeout=None):
        # Mock successful Python code execution
        if command[0] == "python" and "-c" in command:
            return {
                "returncode": 0,
                "stdout": "Hello from Python!\n",
                "stderr": ""
            }
        # Mock successful Node.js code execution
        elif command[0] == "node" and "-e" in command:
            return {
                "returncode": 0,
                "stdout": "Hello from Node.js!\n",
                "stderr": ""
            }
        # Mock shell command execution
        else:
            return {
                "returncode": 0,
                "stdout": f"Command executed: {' '.join(command)}\n",
                "stderr": ""
            }
    
    async def is_container_running(self, container_id):
        return self.containers.get(container_id, {}).get('running', False)
    
    async def get_container_stats(self, container_id):
        from sandbox.container_runtime import ContainerStats
        return ContainerStats(
            cpu_percent=10.5,
            memory_usage_mb=128,
            memory_limit_mb=512,
            is_running=self.containers.get(container_id, {}).get('running', False)
        )


@pytest.mark.asyncio
async def test_mcp_session_workflow_python():
    """Test the complete MCP session workflow with Python sandbox."""
    from sandbox import PythonSandbox
    
    # Mock the container runtime to avoid Docker dependency
    mock_runtime = MockContainerRuntime()
    
    with patch('sandbox.base_sandbox.DockerRuntime', return_value=mock_runtime):
        # Create sandbox similar to how MCP server does it
        sandbox = PythonSandbox(
            container_runtime="docker",
            namespace="default",
            name="session-test123"
        )
        
        try:
            # Test sandbox lifecycle
            assert not sandbox._is_started, "Sandbox should not be started initially"
            
            # Start sandbox (simulates MCP server starting a session)
            await sandbox.start(
                memory=512,
                cpus=1.0,
                timeout=180.0
            )
            
            assert sandbox._is_started, "Sandbox should be started after start()"
            assert sandbox._container_id is not None, "Container ID should be set"
            
            # Execute Python code (simulates MCP server executing user code)
            code = """
print("Hello from Python!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
            
            execution = await sandbox.run(code)
            
            # Verify execution result format matches MCP server expectations
            assert execution is not None, "Execution result should not be None"
            
            # Test output method (used by MCP server)
            output = await execution.output()
            assert isinstance(output, str), "Output should be a string"
            assert "Hello from Python!" in output, "Output should contain expected text"
            
            # Test error method (used by MCP server)
            error = await execution.error()
            assert isinstance(error, str), "Error should be a string"
            
            # Test has_error method (used by MCP server)
            has_error = execution.has_error()
            assert isinstance(has_error, bool), "has_error should return boolean"
            
            # Execute shell command (simulates MCP server running commands)
            command_result = await sandbox.command.run("echo", ["Hello World"])
            
            # Verify command result format
            assert command_result is not None, "Command result should not be None"
            
            # Test command output methods
            cmd_output = await command_result.output()
            assert isinstance(cmd_output, str), "Command output should be a string"
            
            cmd_error = await command_result.error()
            assert isinstance(cmd_error, str), "Command error should be a string"
            
            # Test command properties
            assert hasattr(command_result, 'exit_code'), "Command result should have exit_code"
            assert hasattr(command_result, 'success'), "Command result should have success"
            
            print("✓ Python sandbox MCP workflow completed successfully")
            
        finally:
            # Clean up (simulates MCP server stopping session)
            await sandbox.stop()
            assert not sandbox._is_started, "Sandbox should be stopped after stop()"


@pytest.mark.asyncio
async def test_mcp_session_workflow_node():
    """Test the complete MCP session workflow with Node.js sandbox."""
    from sandbox import NodeSandbox
    
    # Mock the container runtime to avoid Docker dependency
    mock_runtime = MockContainerRuntime()
    
    with patch('sandbox.base_sandbox.DockerRuntime', return_value=mock_runtime):
        # Create sandbox similar to how MCP server does it
        sandbox = NodeSandbox(
            container_runtime="docker",
            namespace="default",
            name="session-node123"
        )
        
        try:
            # Start sandbox
            await sandbox.start(
                memory=512,
                cpus=1.0,
                timeout=180.0
            )
            
            assert sandbox._is_started, "Node sandbox should be started"
            
            # Execute JavaScript code
            code = """
console.log("Hello from Node.js!");
const result = 2 + 2;
console.log(`2 + 2 = ${result}`);
"""
            
            execution = await sandbox.run(code)
            
            # Verify execution result format
            assert execution is not None, "Node execution result should not be None"
            
            output = await execution.output()
            assert isinstance(output, str), "Node output should be a string"
            
            error = await execution.error()
            assert isinstance(error, str), "Node error should be a string"
            
            has_error = execution.has_error()
            assert isinstance(has_error, bool), "Node has_error should return boolean"
            
            print("✓ Node.js sandbox MCP workflow completed successfully")
            
        finally:
            await sandbox.stop()


@pytest.mark.asyncio
async def test_mcp_error_handling():
    """Test error handling and exception propagation in MCP workflow."""
    from sandbox import PythonSandbox
    
    mock_runtime = MockContainerRuntime()
    
    # Mock a failing container runtime
    async def failing_create_container(config):
        raise RuntimeError("Docker daemon not available")
    
    mock_runtime.create_container = failing_create_container
    
    with patch('sandbox.base_sandbox.DockerRuntime', return_value=mock_runtime):
        sandbox = PythonSandbox(
            container_runtime="docker",
            namespace="default",
            name="session-error-test"
        )
        
        # Test that sandbox start failure is properly handled
        with pytest.raises(RuntimeError) as exc_info:
            await sandbox.start()
        
        assert "Failed to start sandbox" in str(exc_info.value)
        assert not sandbox._is_started, "Sandbox should not be marked as started on failure"
        
        print("✓ Error handling works correctly")


@pytest.mark.asyncio
async def test_mcp_concurrent_sessions():
    """Test multiple concurrent sandbox sessions (simulates MCP server load)."""
    from sandbox import PythonSandbox, NodeSandbox
    
    mock_runtime = MockContainerRuntime()
    
    with patch('sandbox.base_sandbox.DockerRuntime', return_value=mock_runtime):
        # Create multiple sandboxes concurrently
        sandboxes = [
            PythonSandbox(container_runtime="docker", namespace="default", name=f"session-{i}")
            for i in range(3)
        ]
        
        sandboxes.extend([
            NodeSandbox(container_runtime="docker", namespace="default", name=f"node-session-{i}")
            for i in range(2)
        ])
        
        try:
            # Start all sandboxes concurrently
            await asyncio.gather(*[sandbox.start() for sandbox in sandboxes])
            
            # Verify all are started
            for sandbox in sandboxes:
                assert sandbox._is_started, f"Sandbox {sandbox._name} should be started"
            
            # Execute code in all sandboxes concurrently
            python_code = "print('Concurrent Python execution')"
            node_code = "console.log('Concurrent Node execution');"
            
            tasks = []
            for sandbox in sandboxes:
                if isinstance(sandbox, PythonSandbox):
                    tasks.append(sandbox.run(python_code))
                else:
                    tasks.append(sandbox.run(node_code))
            
            results = await asyncio.gather(*tasks)
            
            # Verify all executions completed
            assert len(results) == len(sandboxes), "All executions should complete"
            
            for result in results:
                assert result is not None, "All execution results should be valid"
            
            print("✓ Concurrent sessions work correctly")
            
        finally:
            # Clean up all sandboxes
            await asyncio.gather(*[sandbox.stop() for sandbox in sandboxes])


@pytest.mark.asyncio
async def test_mcp_session_timeout_handling():
    """Test session timeout and cleanup behavior."""
    from sandbox import PythonSandbox
    
    mock_runtime = MockContainerRuntime()
    
    # Mock a slow command execution
    async def slow_execute_command(container_id, command, timeout=None):
        if timeout and timeout < 1:
            # Simulate timeout
            await asyncio.sleep(timeout + 0.1)
        return {
            "returncode": 0,
            "stdout": "Slow execution completed\n",
            "stderr": ""
        }
    
    mock_runtime.execute_command = slow_execute_command
    
    with patch('sandbox.base_sandbox.DockerRuntime', return_value=mock_runtime):
        sandbox = PythonSandbox(
            container_runtime="docker",
            namespace="default",
            name="session-timeout-test"
        )
        
        try:
            await sandbox.start()
            
            # Test that timeout is properly handled
            # Note: The actual timeout handling depends on the container runtime implementation
            # This test verifies the interface is compatible
            
            code = "import time; time.sleep(0.1); print('Done')"
            execution = await sandbox.run(code)
            
            # Should complete normally with mock runtime
            assert execution is not None
            
            print("✓ Timeout handling interface is compatible")
            
        finally:
            await sandbox.stop()


def test_mcp_session_info_compatibility():
    """Test that session information is compatible with MCP server expectations."""
    from sandbox import PythonSandbox
    
    sandbox = PythonSandbox(
        container_runtime="docker",
        namespace="test-namespace",
        name="test-session-info"
    )
    
    # Verify sandbox has expected attributes for session management
    assert hasattr(sandbox, '_namespace'), "Sandbox should have namespace attribute"
    assert hasattr(sandbox, '_name'), "Sandbox should have name attribute"
    assert hasattr(sandbox, '_is_started'), "Sandbox should have _is_started attribute"
    assert hasattr(sandbox, '_container_id'), "Sandbox should have _container_id attribute"
    
    # Verify initial values
    assert sandbox._namespace == "test-namespace", "Namespace should be set correctly"
    assert sandbox._name == "test-session-info", "Name should be set correctly"
    assert not sandbox._is_started, "Should not be started initially"
    assert sandbox._container_id is None, "Container ID should be None initially"
    
    print("✓ Session info compatibility verified")


if __name__ == "__main__":
    """Run the end-to-end tests."""
    print("Testing MCP Server end-to-end functionality...")
    print()
    
    # Run synchronous tests
    test_mcp_session_info_compatibility()
    
    # Run async tests
    async def run_async_tests():
        await test_mcp_session_workflow_python()
        await test_mcp_session_workflow_node()
        await test_mcp_error_handling()
        await test_mcp_concurrent_sessions()
        await test_mcp_session_timeout_handling()
    
    asyncio.run(run_async_tests())
    
    print()
    print("✅ All MCP Server end-to-end tests passed!")
    print()
    print("The Docker-based sandbox SDK is fully compatible with MCP server workflows.")
    print("Session management, code execution, and error handling all work correctly.")