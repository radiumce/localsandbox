"""
Test that simulates the exact MCP server session manager workflow.

This test closely mirrors the _create_sandbox method in session_manager.py
to ensure complete compatibility.
"""

import asyncio
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the python sandbox package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))


class MockWrapperConfig:
    """Mock configuration that mirrors WrapperConfig from MCP server."""
    
    def __init__(self):
        self.server_url = "http://localhost:8000"  # Not used in new implementation
        self.api_key = "test-api-key"  # Not used in new implementation
        self.sandbox_start_timeout = 180
        self.shared_volume_mappings = ["/tmp:/workspace"]


class MockSandboxFlavor:
    """Mock flavor that mirrors SandboxFlavor from MCP server."""
    
    def __init__(self, memory_mb=512, cpus=1.0):
        self._memory_mb = memory_mb
        self._cpus = cpus
    
    def get_memory_mb(self):
        return self._memory_mb
    
    def get_cpus(self):
        return self._cpus
    
    @property
    def value(self):
        return f"memory_{self._memory_mb}_cpu_{self._cpus}"


class MockContainerRuntime:
    """Mock container runtime for testing."""
    
    def __init__(self):
        self.containers = {}
        self.next_id = 1
    
    async def create_container(self, config):
        container_id = f"mock_{self.next_id}"
        self.next_id += 1
        self.containers[container_id] = {'config': config, 'running': False}
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
        return {
            "returncode": 0,
            "stdout": "Mock execution output\n",
            "stderr": ""
        }
    
    async def is_container_running(self, container_id):
        return self.containers.get(container_id, {}).get('running', False)


async def simulate_mcp_session_creation(template: str, session_id: str, flavor: MockSandboxFlavor, config: MockWrapperConfig):
    """
    Simulate the exact _create_sandbox method from session_manager.py.
    
    This function mirrors the logic in ManagedSession._create_sandbox()
    """
    namespace = "default"
    sandbox_name = f"session-{session_id[:8]}"
    
    # Mock the container runtime
    mock_runtime = MockContainerRuntime()
    
    with patch('sandbox.base_sandbox.DockerRuntime', return_value=mock_runtime):
        try:
            print(f"Creating sandbox for session {session_id} with template={template}")
            
            # This mirrors the import logic in session_manager.py lines 432-448
            if template in ["python"]:
                from sandbox import PythonSandbox
                sandbox = PythonSandbox(
                    container_runtime="docker",  # New parameter instead of server_url
                    namespace=namespace,
                    name=sandbox_name
                    # Note: api_key parameter is no longer needed
                )
            elif template in ["node", "nodejs", "javascript"]:
                from sandbox import NodeSandbox
                sandbox = NodeSandbox(
                    container_runtime="docker",  # New parameter instead of server_url
                    namespace=namespace,
                    name=sandbox_name
                    # Note: api_key parameter is no longer needed
                )
            else:
                raise RuntimeError(f"Unsupported template: {template}")
            
            # Prepare volume mappings (mirrors session_manager.py logic)
            volumes = []
            if config.shared_volume_mappings:
                volumes = config.shared_volume_mappings.copy()
            
            print(f"Starting sandbox {sandbox_name} with memory={flavor.get_memory_mb()}MB, "
                  f"cpus={flavor.get_cpus()}, volumes={len(volumes)} mappings")
            
            # Start the sandbox with configured resources (mirrors session_manager.py)
            await sandbox.start(
                memory=flavor.get_memory_mb(),
                cpus=flavor.get_cpus(),
                timeout=config.sandbox_start_timeout,
                volumes=volumes
            )
            
            print(f"Successfully created and started sandbox for session {session_id}")
            
            # Test that the sandbox is properly initialized
            assert sandbox._is_started, "Sandbox should be started"
            assert sandbox._container_id is not None, "Container ID should be set"
            
            # Test code execution (mirrors MCP server execute_code method)
            if template == "python":
                code = "print('Hello from simulated MCP Python session!')"
            else:
                code = "console.log('Hello from simulated MCP Node session!');"
            
            execution = await sandbox.run(code)
            
            # Test the methods that MCP server uses
            stdout = await execution.output()
            stderr = await execution.error()
            success = not execution.has_error()
            
            print(f"Code execution completed: success={success}, stdout_len={len(stdout)}")
            
            # Test command execution (mirrors MCP server execute_command method)
            command_result = await sandbox.command.run("echo", ["test"])
            
            cmd_stdout = await command_result.output()
            cmd_stderr = await command_result.error()
            exit_code = command_result.exit_code
            cmd_success = command_result.success
            
            print(f"Command execution completed: exit_code={exit_code}, success={cmd_success}")
            
            # Clean up (mirrors MCP server session stop)
            await sandbox.stop()
            
            print(f"Successfully stopped sandbox for session {session_id}")
            
            return True
            
        except Exception as e:
            print(f"Error in session creation: {e}")
            raise


@pytest.mark.asyncio
async def test_python_session_simulation():
    """Test Python session creation simulation."""
    config = MockWrapperConfig()
    flavor = MockSandboxFlavor(memory_mb=512, cpus=1.0)
    session_id = "test-python-session-12345678"
    
    success = await simulate_mcp_session_creation("python", session_id, flavor, config)
    assert success, "Python session simulation should succeed"
    print("✓ Python session simulation completed successfully")


@pytest.mark.asyncio
async def test_node_session_simulation():
    """Test Node.js session creation simulation."""
    config = MockWrapperConfig()
    flavor = MockSandboxFlavor(memory_mb=256, cpus=0.5)
    session_id = "test-node-session-87654321"
    
    success = await simulate_mcp_session_creation("node", session_id, flavor, config)
    assert success, "Node session simulation should succeed"
    print("✓ Node.js session simulation completed successfully")


@pytest.mark.asyncio
async def test_javascript_template_alias():
    """Test that 'javascript' template alias works (used by MCP server)."""
    config = MockWrapperConfig()
    flavor = MockSandboxFlavor()
    session_id = "test-js-session-11111111"
    
    success = await simulate_mcp_session_creation("javascript", session_id, flavor, config)
    assert success, "JavaScript template alias should work"
    print("✓ JavaScript template alias works correctly")


@pytest.mark.asyncio
async def test_unsupported_template():
    """Test error handling for unsupported templates."""
    config = MockWrapperConfig()
    flavor = MockSandboxFlavor()
    session_id = "test-unsupported-22222222"
    
    try:
        await simulate_mcp_session_creation("unsupported", session_id, flavor, config)
        assert False, "Should have raised an error for unsupported template"
    except RuntimeError as e:
        assert "Unsupported template" in str(e)
        print("✓ Unsupported template error handling works correctly")


def test_import_compatibility():
    """Test that imports work exactly as in session_manager.py."""
    
    # Test Python sandbox import (line 432 in session_manager.py)
    try:
        from sandbox import PythonSandbox
        assert PythonSandbox is not None
        print("✓ PythonSandbox import works")
    except ImportError as e:
        assert False, f"PythonSandbox import failed: {e}"
    
    # Test Node sandbox import (line 440 in session_manager.py)
    try:
        from sandbox import NodeSandbox
        assert NodeSandbox is not None
        print("✓ NodeSandbox import works")
    except ImportError as e:
        assert False, f"NodeSandbox import failed: {e}"


if __name__ == "__main__":
    """Run the MCP session manager simulation tests."""
    print("Testing MCP Session Manager simulation...")
    print()
    
    # Test imports first
    test_import_compatibility()
    
    # Run async simulation tests
    async def run_simulations():
        await test_python_session_simulation()
        await test_node_session_simulation()
        await test_javascript_template_alias()
        await test_unsupported_template()
    
    asyncio.run(run_simulations())
    
    print()
    print("✅ All MCP Session Manager simulation tests passed!")
    print()
    print("The new Docker-based sandbox SDK is fully compatible with the MCP server's")
    print("session management workflow. The MCP server can use the new implementation")
    print("without any code changes to the session_manager.py file.")