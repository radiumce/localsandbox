"""
Integration tests for container runtime functionality.

These tests verify the DockerRuntime implementation including container
lifecycle management, command execution, and error handling.
"""

import asyncio
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from python.sandbox.container_runtime import (
    ContainerRuntime,
    DockerRuntime,
    ContainerConfig,
    ContainerStats
)


class TestContainerConfig:
    """Test ContainerConfig data class validation and initialization."""
    
    def test_container_config_valid(self):
        """Test valid container configuration."""
        config = ContainerConfig(
            image="python:3.11-slim",
            name="test-container",
            memory=512,
            cpus=1.0,
            volumes=["/host:/container"],
            environment={"TEST": "value"},
            working_dir="/workspace"
        )
        
        assert config.image == "python:3.11-slim"
        assert config.name == "test-container"
        assert config.memory == 512
        assert config.cpus == 1.0
        assert config.volumes == ["/host:/container"]
        assert config.environment == {"TEST": "value"}
        assert config.working_dir == "/workspace"
    
    def test_container_config_defaults(self):
        """Test container configuration with defaults."""
        config = ContainerConfig(
            image="python:3.11-slim",
            name="test-container"
        )
        
        assert config.volumes == []
        assert config.environment == {}
        assert config.working_dir == "/workspace"
        assert config.memory is None
        assert config.cpus is None
        assert config.command is None
    
    def test_container_config_validation_errors(self):
        """Test container configuration validation errors."""
        # Missing image
        with pytest.raises(ValueError, match="Container image is required"):
            ContainerConfig(image="", name="test")
        
        # Missing name
        with pytest.raises(ValueError, match="Container name is required"):
            ContainerConfig(image="python:3.11", name="")
        
        # Invalid memory
        with pytest.raises(ValueError, match="Memory limit must be positive"):
            ContainerConfig(image="python:3.11", name="test", memory=-1)
        
        # Invalid CPU
        with pytest.raises(ValueError, match="CPU limit must be positive"):
            ContainerConfig(image="python:3.11", name="test", cpus=-0.5)


class TestContainerStats:
    """Test ContainerStats data class validation."""
    
    def test_container_stats_valid(self):
        """Test valid container statistics."""
        stats = ContainerStats(
            cpu_percent=25.5,
            memory_usage_mb=256,
            memory_limit_mb=512,
            is_running=True
        )
        
        assert stats.cpu_percent == 25.5
        assert stats.memory_usage_mb == 256
        assert stats.memory_limit_mb == 512
        assert stats.is_running is True
    
    def test_container_stats_defaults(self):
        """Test container statistics with defaults."""
        stats = ContainerStats()
        
        assert stats.cpu_percent is None
        assert stats.memory_usage_mb is None
        assert stats.memory_limit_mb is None
        assert stats.is_running is False
    
    def test_container_stats_validation_errors(self):
        """Test container statistics validation errors."""
        # Invalid CPU percentage
        with pytest.raises(ValueError, match="CPU percentage must be between 0 and 100"):
            ContainerStats(cpu_percent=150.0)
        
        with pytest.raises(ValueError, match="CPU percentage must be between 0 and 100"):
            ContainerStats(cpu_percent=-10.0)
        
        # Invalid memory usage
        with pytest.raises(ValueError, match="Memory usage must be non-negative"):
            ContainerStats(memory_usage_mb=-100)
        
        # Invalid memory limit
        with pytest.raises(ValueError, match="Memory limit must be positive"):
            ContainerStats(memory_limit_mb=-512)


class TestDockerRuntime:
    """Test DockerRuntime implementation."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for testing."""
        return DockerRuntime("docker")
    
    @pytest.fixture
    def container_config(self):
        """Create a test container configuration."""
        return ContainerConfig(
            image="python:3.11-slim",
            name=f"test-container-{uuid.uuid4().hex[:8]}",
            memory=256,
            cpus=0.5,
            volumes=[],
            environment={"TEST_ENV": "test_value"},
            working_dir="/workspace"
        )
    
    @pytest.mark.asyncio
    async def test_run_command_success(self, runtime):
        """Test successful command execution."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"output", b"")
            mock_subprocess.return_value = mock_process
            
            result = await runtime._run_command(["version"], timeout=10)
            
            assert result["returncode"] == 0
            assert result["stdout"] == "output"
            assert result["stderr"] == ""
            
            # Verify subprocess was called correctly
            mock_subprocess.assert_called_once_with(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
    
    @pytest.mark.asyncio
    async def test_run_command_error(self, runtime):
        """Test command execution with error."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock failed process
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = (b"", b"error message")
            mock_subprocess.return_value = mock_process
            
            result = await runtime._run_command(["invalid-command"], timeout=10)
            
            assert result["returncode"] == 1
            assert result["stdout"] == ""
            assert result["stderr"] == "error message"
    
    @pytest.mark.asyncio
    async def test_run_command_timeout(self, runtime):
        """Test command execution timeout."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock process that times out
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_process.kill = AsyncMock()
            mock_process.wait = AsyncMock()
            mock_subprocess.return_value = mock_process
            
            with pytest.raises(RuntimeError, match="Command timed out"):
                await runtime._run_command(["sleep", "10"], timeout=1)
            
            # Verify process was killed
            mock_process.kill.assert_called_once()
            mock_process.wait.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_command_exception(self, runtime):
        """Test command execution with exception."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_subprocess.side_effect = OSError("Command not found")
            
            with pytest.raises(RuntimeError, match="Failed to execute command"):
                await runtime._run_command(["nonexistent"], timeout=10)
    
    @pytest.mark.asyncio
    async def test_create_container_success(self, runtime, container_config):
        """Test successful container creation."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "container123456",
                "stderr": ""
            }
            
            container_id = await runtime.create_container(container_config)
            
            assert container_id == "container123456"
            
            # Verify the docker create command was called with correct arguments
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            
            assert "create" in args
            assert "--name" in args
            assert container_config.name in args
            assert "--memory" in args
            assert "256m" in args
            assert "--cpus" in args
            assert "0.5" in args
            assert "-e" in args
            assert "TEST_ENV=test_value" in args
            assert "-w" in args
            assert "/workspace" in args
            assert container_config.image in args
    
    @pytest.mark.asyncio
    async def test_create_container_failure(self, runtime, container_config):
        """Test container creation failure."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Image not found"
            }
            
            with pytest.raises(RuntimeError, match="Failed to create container"):
                await runtime.create_container(container_config)
    
    @pytest.mark.asyncio
    async def test_create_container_no_id(self, runtime, container_config):
        """Test container creation with no container ID returned."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "",
                "stderr": ""
            }
            
            with pytest.raises(RuntimeError, match="Failed to get container ID"):
                await runtime.create_container(container_config)
    
    @pytest.mark.asyncio
    async def test_start_container_success(self, runtime):
        """Test successful container start."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "container123456",
                "stderr": ""
            }
            
            await runtime.start_container("container123456")
            
            mock_run.assert_called_once_with(["start", "container123456"], timeout=30)
    
    @pytest.mark.asyncio
    async def test_start_container_failure(self, runtime):
        """Test container start failure."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Container not found"
            }
            
            with pytest.raises(RuntimeError, match="Failed to start container"):
                await runtime.start_container("nonexistent")
    
    @pytest.mark.asyncio
    async def test_stop_container_success(self, runtime):
        """Test successful container stop."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "container123456",
                "stderr": ""
            }
            
            await runtime.stop_container("container123456")
            
            mock_run.assert_called_once_with(["stop", "container123456"], timeout=30)
    
    @pytest.mark.asyncio
    async def test_stop_container_failure(self, runtime):
        """Test container stop failure."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Container not running"
            }
            
            with pytest.raises(RuntimeError, match="Failed to stop container"):
                await runtime.stop_container("nonexistent")
    
    @pytest.mark.asyncio
    async def test_remove_container_success(self, runtime):
        """Test successful container removal."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "container123456",
                "stderr": ""
            }
            
            await runtime.remove_container("container123456")
            
            mock_run.assert_called_once_with(["rm", "container123456"], timeout=30)
    
    @pytest.mark.asyncio
    async def test_remove_container_failure(self, runtime):
        """Test container removal failure."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Container not found"
            }
            
            with pytest.raises(RuntimeError, match="Failed to remove container"):
                await runtime.remove_container("nonexistent")
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, runtime):
        """Test successful command execution in container."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "Hello World",
                "stderr": ""
            }
            
            result = await runtime.execute_command(
                "container123456",
                ["python", "-c", "print('Hello World')"],
                timeout=30
            )
            
            assert result["returncode"] == 0
            assert result["stdout"] == "Hello World"
            assert result["stderr"] == ""
            
            mock_run.assert_called_once_with(
                ["exec", "container123456", "python", "-c", "print('Hello World')"],
                timeout=30
            )
    
    @pytest.mark.asyncio
    async def test_execute_command_error(self, runtime):
        """Test command execution with error in container."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "SyntaxError: invalid syntax"
            }
            
            result = await runtime.execute_command(
                "container123456",
                ["python", "-c", "invalid syntax"],
                timeout=30
            )
            
            assert result["returncode"] == 1
            assert result["stdout"] == ""
            assert result["stderr"] == "SyntaxError: invalid syntax"
    
    @pytest.mark.asyncio
    async def test_is_container_running_true(self, runtime):
        """Test checking if container is running (true case)."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "true",
                "stderr": ""
            }
            
            is_running = await runtime.is_container_running("container123456")
            
            assert is_running is True
            mock_run.assert_called_once_with(
                ["inspect", "--format", "{{.State.Running}}", "container123456"],
                timeout=10
            )
    
    @pytest.mark.asyncio
    async def test_is_container_running_false(self, runtime):
        """Test checking if container is running (false case)."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "false",
                "stderr": ""
            }
            
            is_running = await runtime.is_container_running("container123456")
            
            assert is_running is False
    
    @pytest.mark.asyncio
    async def test_is_container_running_not_found(self, runtime):
        """Test checking if container is running (container not found)."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "No such container"
            }
            
            is_running = await runtime.is_container_running("nonexistent")
            
            assert is_running is False
    
    @pytest.mark.asyncio
    async def test_get_container_stats_success(self, runtime):
        """Test successful container stats retrieval."""
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.return_value = {
                "returncode": 0,
                "stdout": '{"CPUPerc": "25.50%", "MemUsage": "256MiB / 512MiB"}',
                "stderr": ""
            }
            mock_running.return_value = True
            
            stats = await runtime.get_container_stats("container123456")
            
            assert stats.cpu_percent == 25.50
            assert stats.memory_usage_mb == 268  # 256 MiB converted to MB
            assert stats.memory_limit_mb == 536  # 512 MiB converted to MB
            assert stats.is_running is True
    
    @pytest.mark.asyncio
    async def test_get_container_stats_failure(self, runtime):
        """Test container stats retrieval failure."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "No such container"
            }
            
            with pytest.raises(RuntimeError, match="Failed to get container stats"):
                await runtime.get_container_stats("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_container_stats_invalid_json(self, runtime):
        """Test container stats with invalid JSON response."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "invalid json",
                "stderr": ""
            }
            
            with pytest.raises(RuntimeError, match="Failed to parse container stats JSON"):
                await runtime.get_container_stats("container123456")
    
    def test_parse_memory_string(self, runtime):
        """Test memory string parsing."""
        # Test MiB to MB conversion
        assert runtime._parse_memory_string("256MiB") == 268
        
        # Test MB (no conversion needed)
        assert runtime._parse_memory_string("256MB") == 256
        
        # Test GiB to MB conversion
        assert runtime._parse_memory_string("1GiB") == 1073
        
        # Test GB to MB conversion
        assert runtime._parse_memory_string("1GB") == 1000
        
        # Test KiB to MB conversion
        assert runtime._parse_memory_string("1024KiB") == 1
        
        # Test KB to MB conversion
        assert runtime._parse_memory_string("1000KB") == 1
        
        # Test bytes to MB conversion
        assert runtime._parse_memory_string("1000000") == 1
        
        # Test invalid format
        assert runtime._parse_memory_string("invalid") == 0


class TestDockerRuntimeIntegration:
    """Integration tests that require Docker to be available."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for integration testing."""
        return DockerRuntime("docker")
    
    @pytest.fixture
    def container_config(self):
        """Create a test container configuration for integration tests."""
        return ContainerConfig(
            image="python:3.11-slim",
            name=f"test-integration-{uuid.uuid4().hex[:8]}",
            memory=128,
            cpus=0.5,
            working_dir="/workspace"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_container_lifecycle(self, runtime, container_config):
        """Test complete container lifecycle: create, start, execute, stop, remove."""
        container_id = None
        
        try:
            # Create container
            container_id = await runtime.create_container(container_config)
            assert container_id is not None
            assert len(container_id) > 0
            
            # Start container
            await runtime.start_container(container_id)
            
            # Verify container is running
            is_running = await runtime.is_container_running(container_id)
            assert is_running is True
            
            # Execute a simple command
            result = await runtime.execute_command(
                container_id,
                ["python", "-c", "print('Hello from container')"],
                timeout=10
            )
            
            assert result["returncode"] == 0
            assert "Hello from container" in result["stdout"]
            
            # Get container stats
            stats = await runtime.get_container_stats(container_id)
            assert stats.is_running is True
            
            # Stop container
            await runtime.stop_container(container_id)
            
            # Verify container is stopped
            is_running = await runtime.is_container_running(container_id)
            assert is_running is False
            
        finally:
            # Clean up: remove container if it exists
            if container_id:
                try:
                    await runtime.remove_container(container_id)
                except:
                    pass  # Ignore cleanup errors
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_container_command_timeout(self, runtime, container_config):
        """Test command execution timeout in container."""
        container_id = None
        
        try:
            # Create and start container
            container_id = await runtime.create_container(container_config)
            await runtime.start_container(container_id)
            
            # Execute a command that should timeout
            with pytest.raises(RuntimeError, match="Command timed out"):
                await runtime.execute_command(
                    container_id,
                    ["python", "-c", "import time; time.sleep(10)"],
                    timeout=2
                )
            
        finally:
            # Clean up
            if container_id:
                try:
                    await runtime.stop_container(container_id)
                    await runtime.remove_container(container_id)
                except:
                    pass
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_container_error_handling(self, runtime, container_config):
        """Test error handling in container operations."""
        container_id = None
        
        try:
            # Create and start container
            container_id = await runtime.create_container(container_config)
            await runtime.start_container(container_id)
            
            # Execute a command that will fail
            result = await runtime.execute_command(
                container_id,
                ["python", "-c", "raise ValueError('Test error')"],
                timeout=10
            )
            
            assert result["returncode"] != 0
            assert "ValueError: Test error" in result["stderr"]
            
        finally:
            # Clean up
            if container_id:
                try:
                    await runtime.stop_container(container_id)
                    await runtime.remove_container(container_id)
                except:
                    pass