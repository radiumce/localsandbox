"""
Integration tests for command execution functionality.

These tests verify the Command class shell command execution,
command parameter handling, timeout control, and CommandExecution
object compatibility.
"""

import asyncio
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from python.sandbox.command import Command
from python.sandbox.command_execution import CommandExecution
from python.sandbox.python_sandbox import PythonSandbox
from python.sandbox.node_sandbox import NodeSandbox


class TestCommandExecution:
    """Test Command class functionality."""
    
    @pytest.fixture
    def mock_sandbox(self):
        """Create a mock sandbox instance for testing."""
        sandbox = MagicMock()
        sandbox._is_started = True
        sandbox._container_id = "test-container"
        sandbox._runtime = AsyncMock()
        return sandbox
    
    @pytest.fixture
    def command(self, mock_sandbox):
        """Create a Command instance for testing."""
        return Command(mock_sandbox)
    
    @pytest.mark.asyncio
    async def test_run_simple_command_success(self, command, mock_sandbox):
        """Test running a simple command successfully."""
        # Mock the runtime response - AsyncMock automatically makes this awaitable
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "Hello World\n",
            "stderr": ""
        }
        
        # Execute command
        result = await command.run("echo", ["Hello World"])
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["command"] == "echo"
        assert result.output_data["args"] == ["Hello World"]
        assert result.output_data["exit_code"] == 0
        assert result.output_data["success"] is True
        assert len(result.output_data["output"]) == 1
        assert result.output_data["output"][0]["stream"] == "stdout"
        assert result.output_data["output"][0]["text"] == "Hello World"
        
        # Verify runtime was called correctly
        mock_sandbox._runtime.execute_command.assert_called_once_with(
            "test-container",
            ["echo", "Hello World"],
            timeout=30  # default timeout from config
        )
    
    @pytest.mark.asyncio
    async def test_run_command_without_args(self, command, mock_sandbox):
        """Test running a command without arguments."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "current_directory\n",
            "stderr": ""
        }
        
        # Execute command without args
        result = await command.run("pwd")
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["command"] == "pwd"
        assert result.output_data["args"] == []
        assert result.output_data["exit_code"] == 0
        assert result.output_data["success"] is True
        
        # Verify runtime was called correctly
        mock_sandbox._runtime.execute_command.assert_called_once_with(
            "test-container",
            ["pwd"],
            timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_run_command_with_error(self, command, mock_sandbox):
        """Test running a command that returns an error."""
        # Mock the runtime response with error
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 1,
            "stdout": "",
            "stderr": "ls: cannot access 'nonexistent': No such file or directory\n"
        }
        
        # Execute command that will fail
        result = await command.run("ls", ["nonexistent"])
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["command"] == "ls"
        assert result.output_data["args"] == ["nonexistent"]
        assert result.output_data["exit_code"] == 1
        assert result.output_data["success"] is False
        assert len(result.output_data["output"]) == 1
        assert result.output_data["output"][0]["stream"] == "stderr"
        assert "No such file or directory" in result.output_data["output"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_run_command_with_mixed_output(self, command, mock_sandbox):
        """Test running a command that produces both stdout and stderr."""
        # Mock the runtime response with mixed output
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "This goes to stdout\nAnother stdout line\n",
            "stderr": "This goes to stderr\n"
        }
        
        # Execute command
        result = await command.run("sh", ["-c", "echo 'This goes to stdout'; echo 'Another stdout line'; echo 'This goes to stderr' >&2"])
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["exit_code"] == 0
        assert result.output_data["success"] is True
        assert len(result.output_data["output"]) == 3
        
        # Check stdout outputs
        stdout_outputs = [o for o in result.output_data["output"] if o["stream"] == "stdout"]
        assert len(stdout_outputs) == 2
        assert stdout_outputs[0]["text"] == "This goes to stdout"
        assert stdout_outputs[1]["text"] == "Another stdout line"
        
        # Check stderr output
        stderr_outputs = [o for o in result.output_data["output"] if o["stream"] == "stderr"]
        assert len(stderr_outputs) == 1
        assert stderr_outputs[0]["text"] == "This goes to stderr"
    
    @pytest.mark.asyncio
    async def test_run_command_with_custom_timeout(self, command, mock_sandbox):
        """Test running a command with custom timeout."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "completed\n",
            "stderr": ""
        }
        
        # Execute command with custom timeout
        result = await command.run("sleep", ["1"], timeout=60)
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["success"] is True
        
        # Verify runtime was called with custom timeout
        mock_sandbox._runtime.execute_command.assert_called_once_with(
            "test-container",
            ["sleep", "1"],
            timeout=60
        )
    
    @pytest.mark.asyncio
    async def test_run_command_sandbox_not_started(self, mock_sandbox):
        """Test running a command when sandbox is not started."""
        # Set sandbox as not started
        mock_sandbox._is_started = False
        command = Command(mock_sandbox)
        
        with pytest.raises(RuntimeError, match="Sandbox is not started"):
            await command.run("echo", ["test"])
    
    @pytest.mark.asyncio
    async def test_run_command_runtime_error(self, command, mock_sandbox):
        """Test handling runtime errors during command execution."""
        # Mock the runtime to raise an exception
        mock_sandbox._runtime.execute_command.side_effect = Exception("Container execution failed")
        
        with pytest.raises(RuntimeError, match="Failed to execute command"):
            await command.run("echo", ["test"])
    
    @pytest.mark.asyncio
    async def test_run_command_complex_args(self, command, mock_sandbox):
        """Test running a command with complex arguments."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "file1.txt\nfile2.txt\n",
            "stderr": ""
        }
        
        # Execute command with complex arguments
        result = await command.run("find", [".", "-name", "*.txt", "-type", "f"])
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["command"] == "find"
        assert result.output_data["args"] == [".", "-name", "*.txt", "-type", "f"]
        assert result.output_data["success"] is True
        
        # Verify runtime was called correctly
        mock_sandbox._runtime.execute_command.assert_called_once_with(
            "test-container",
            ["find", ".", "-name", "*.txt", "-type", "f"],
            timeout=30
        )


class TestCommandExecutionObject:
    """Test CommandExecution object structure and compatibility."""
    
    def test_command_execution_structure(self):
        """Test CommandExecution object has the expected structure."""
        output_data = {
            "output": [
                {"stream": "stdout", "text": "Hello World"}
            ],
            "command": "echo",
            "args": ["Hello World"],
            "exit_code": 0,
            "success": True
        }
        
        result = CommandExecution(output_data=output_data)
        
        # Verify object structure
        assert hasattr(result, 'output_data')
        assert isinstance(result.output_data, dict)
        
        # Verify required fields
        required_fields = ['output', 'command', 'args', 'exit_code', 'success']
        for field in required_fields:
            assert field in result.output_data
        
        # Verify field types
        assert isinstance(result.output_data['output'], list)
        assert isinstance(result.output_data['command'], str)
        assert isinstance(result.output_data['args'], list)
        assert isinstance(result.output_data['exit_code'], int)
        assert isinstance(result.output_data['success'], bool)
    
    def test_command_execution_output_format(self):
        """Test CommandExecution output format consistency."""
        output_data = {
            "output": [
                {"stream": "stdout", "text": "line 1"},
                {"stream": "stdout", "text": "line 2"},
                {"stream": "stderr", "text": "error line"}
            ],
            "command": "test",
            "args": [],
            "exit_code": 1,
            "success": False
        }
        
        result = CommandExecution(output_data=output_data)
        
        # Verify output format
        for output_item in result.output_data['output']:
            assert 'stream' in output_item
            assert 'text' in output_item
            assert output_item['stream'] in ['stdout', 'stderr']
            assert isinstance(output_item['text'], str)
    
    def test_command_execution_success_calculation(self):
        """Test that success field correctly reflects exit code."""
        # Test successful command
        success_data = {
            "output": [],
            "command": "true",
            "args": [],
            "exit_code": 0,
            "success": True
        }
        success_result = CommandExecution(output_data=success_data)
        assert success_result.output_data['success'] is True
        
        # Test failed command
        failure_data = {
            "output": [],
            "command": "false",
            "args": [],
            "exit_code": 1,
            "success": False
        }
        failure_result = CommandExecution(output_data=failure_data)
        assert failure_result.output_data['success'] is False


class TestCommandIntegrationWithSandboxes:
    """Test Command integration with different sandbox types."""
    
    @pytest.fixture
    def python_sandbox(self):
        """Create a PythonSandbox instance for testing."""
        return PythonSandbox(
            container_runtime="docker",
            name=f"test-cmd-python-{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.fixture
    def node_sandbox(self):
        """Create a NodeSandbox instance for testing."""
        return NodeSandbox(
            container_runtime="docker",
            name=f"test-cmd-node-{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.mark.asyncio
    async def test_command_with_python_sandbox(self, python_sandbox):
        """Test command execution with PythonSandbox."""
        # Mock the container runtime
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "Python 3.11.0\n",
                "stderr": ""
            }
            
            # Set sandbox as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "python-container"
            
            # Execute command through sandbox
            result = await python_sandbox.command.run("python", ["--version"])
            
            # Verify result
            assert isinstance(result, CommandExecution)
            assert result.output_data["command"] == "python"
            assert result.output_data["args"] == ["--version"]
            assert result.output_data["success"] is True
            assert "Python" in result.output_data["output"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_command_with_node_sandbox(self, node_sandbox):
        """Test command execution with NodeSandbox."""
        # Mock the container runtime
        with patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "v18.17.0\n",
                "stderr": ""
            }
            
            # Set sandbox as started
            node_sandbox._is_started = True
            node_sandbox._container_id = "node-container"
            
            # Execute command through sandbox
            result = await node_sandbox.command.run("node", ["--version"])
            
            # Verify result
            assert isinstance(result, CommandExecution)
            assert result.output_data["command"] == "node"
            assert result.output_data["args"] == ["--version"]
            assert result.output_data["success"] is True
            assert "v18" in result.output_data["output"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_command_cross_sandbox_consistency(self, python_sandbox, node_sandbox):
        """Test that commands produce consistent output across different sandbox types."""
        # Mock both runtimes with similar responses
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_python_runtime, \
             patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_node_runtime:
            
            # Set up identical mock responses for ls command
            mock_response = {
                "returncode": 0,
                "stdout": "file1.txt\nfile2.txt\n",
                "stderr": ""
            }
            mock_python_runtime.execute_command.return_value = mock_response
            mock_node_runtime.execute_command.return_value = mock_response
            
            # Set both sandboxes as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "python-container"
            node_sandbox._is_started = True
            node_sandbox._container_id = "node-container"
            
            # Execute same command in both sandboxes
            python_result = await python_sandbox.command.run("ls", ["-1"])
            node_result = await node_sandbox.command.run("ls", ["-1"])
            
            # Verify both results have the same structure
            assert python_result.output_data.keys() == node_result.output_data.keys()
            
            # Verify command details are identical
            assert python_result.output_data["command"] == node_result.output_data["command"]
            assert python_result.output_data["args"] == node_result.output_data["args"]
            assert python_result.output_data["exit_code"] == node_result.output_data["exit_code"]
            assert python_result.output_data["success"] == node_result.output_data["success"]
            
            # Verify output format is identical
            assert len(python_result.output_data["output"]) == len(node_result.output_data["output"])
            for i in range(len(python_result.output_data["output"])):
                python_output = python_result.output_data["output"][i]
                node_output = node_result.output_data["output"][i]
                assert python_output.keys() == node_output.keys()
                assert python_output["stream"] == node_output["stream"]
                assert python_output["text"] == node_output["text"]


class TestCommandParameterHandling:
    """Test command parameter handling and edge cases."""
    
    @pytest.fixture
    def mock_sandbox(self):
        """Create a mock sandbox instance for testing."""
        sandbox = MagicMock()
        sandbox._is_started = True
        sandbox._container_id = "test-container"
        sandbox._runtime = AsyncMock()
        return sandbox
    
    @pytest.fixture
    def command(self, mock_sandbox):
        """Create a Command instance for testing."""
        return Command(mock_sandbox)
    
    @pytest.mark.asyncio
    async def test_command_with_special_characters(self, command, mock_sandbox):
        """Test command execution with special characters in arguments."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "special chars: !@#$%^&*()\n",
            "stderr": ""
        }
        
        # Execute command with special characters
        result = await command.run("echo", ["special chars: !@#$%^&*()"])
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["args"] == ["special chars: !@#$%^&*()"]
        assert result.output_data["success"] is True
        
        # Verify runtime was called correctly
        mock_sandbox._runtime.execute_command.assert_called_once_with(
            "test-container",
            ["echo", "special chars: !@#$%^&*()"],
            timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_command_with_empty_args(self, command, mock_sandbox):
        """Test command execution with empty arguments list."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "no args\n",
            "stderr": ""
        }
        
        # Execute command with empty args
        result = await command.run("pwd", [])
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["args"] == []
        assert result.output_data["success"] is True
    
    @pytest.mark.asyncio
    async def test_command_with_none_args(self, command, mock_sandbox):
        """Test command execution with None arguments."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "no args\n",
            "stderr": ""
        }
        
        # Execute command with None args
        result = await command.run("pwd", None)
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["args"] == []
        assert result.output_data["success"] is True
    
    @pytest.mark.asyncio
    async def test_command_with_long_output(self, command, mock_sandbox):
        """Test command execution with long output."""
        # Create long output
        long_output = "\n".join([f"line {i}" for i in range(100)])
        
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": long_output + "\n",
            "stderr": ""
        }
        
        # Execute command
        result = await command.run("seq", ["1", "100"])
        
        # Verify result
        assert isinstance(result, CommandExecution)
        assert result.output_data["success"] is True
        assert len(result.output_data["output"]) == 100
        
        # Verify all lines are captured
        for i, output_line in enumerate(result.output_data["output"]):
            assert output_line["stream"] == "stdout"
            assert output_line["text"] == f"line {i}"


class TestCommandTimeoutHandling:
    """Test command timeout handling and control."""
    
    @pytest.fixture
    def mock_sandbox(self):
        """Create a mock sandbox instance for testing."""
        sandbox = MagicMock()
        sandbox._is_started = True
        sandbox._container_id = "test-container"
        sandbox._runtime = AsyncMock()
        return sandbox
    
    @pytest.fixture
    def command(self, mock_sandbox):
        """Create a Command instance for testing."""
        return Command(mock_sandbox)
    
    @pytest.mark.asyncio
    async def test_command_timeout_error(self, command, mock_sandbox):
        """Test command execution timeout handling."""
        # Mock the runtime to raise a timeout error
        mock_sandbox._runtime.execute_command.side_effect = RuntimeError("Command timed out")
        
        with pytest.raises(RuntimeError, match="Failed to execute command"):
            await command.run("sleep", ["10"], timeout=1)
    
    @pytest.mark.asyncio
    async def test_command_default_timeout(self, command, mock_sandbox):
        """Test that default timeout is used when not specified."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "completed\n",
            "stderr": ""
        }
        
        # Execute command without specifying timeout
        result = await command.run("echo", ["test"])
        
        # Verify default timeout was used
        mock_sandbox._runtime.execute_command.assert_called_once_with(
            "test-container",
            ["echo", "test"],
            timeout=30  # default from config
        )
    
    @pytest.mark.asyncio
    async def test_command_zero_timeout(self, command, mock_sandbox):
        """Test command execution with zero timeout."""
        # Mock the runtime response
        mock_sandbox._runtime.execute_command.return_value = {
            "returncode": 0,
            "stdout": "completed\n",
            "stderr": ""
        }
        
        # Execute command with zero timeout
        result = await command.run("echo", ["test"], timeout=0)
        
        # Verify zero timeout was passed
        mock_sandbox._runtime.execute_command.assert_called_once_with(
            "test-container",
            ["echo", "test"],
            timeout=0
        )


class TestCommandIntegration:
    """Integration tests for command execution with real containers."""
    
    @pytest.fixture
    def python_sandbox(self):
        """Create a PythonSandbox instance for integration testing."""
        return PythonSandbox(
            container_runtime="docker",
            name=f"test-cmd-integration-{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_command_execution(self, python_sandbox):
        """Test command execution with real container."""
        try:
            # Start the sandbox
            await python_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute a simple command
            result = await python_sandbox.command.run("echo", ["Hello from command"])
            
            # Verify result
            assert isinstance(result, CommandExecution)
            assert result.output_data["command"] == "echo"
            assert result.output_data["args"] == ["Hello from command"]
            assert result.output_data["exit_code"] == 0
            assert result.output_data["success"] is True
            assert len(result.output_data["output"]) == 1
            assert result.output_data["output"][0]["stream"] == "stdout"
            assert "Hello from command" in result.output_data["output"][0]["text"]
            
        finally:
            # Clean up
            await python_sandbox.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_command_with_error(self, python_sandbox):
        """Test command execution error handling with real container."""
        try:
            # Start the sandbox
            await python_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute a command that will fail
            result = await python_sandbox.command.run("ls", ["nonexistent_file"])
            
            # Verify error result
            assert isinstance(result, CommandExecution)
            assert result.output_data["command"] == "ls"
            assert result.output_data["args"] == ["nonexistent_file"]
            assert result.output_data["exit_code"] != 0
            assert result.output_data["success"] is False
            
            # Check that error information is in stderr output
            stderr_outputs = [o for o in result.output_data["output"] if o["stream"] == "stderr"]
            assert len(stderr_outputs) > 0
            
            # Verify error details are present
            error_text = " ".join([o["text"] for o in stderr_outputs])
            assert "No such file or directory" in error_text or "cannot access" in error_text
            
        finally:
            # Clean up
            await python_sandbox.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_command_with_timeout(self, python_sandbox):
        """Test command execution timeout with real container."""
        try:
            # Start the sandbox
            await python_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute a command that should timeout
            with pytest.raises(RuntimeError, match="Failed to execute command"):
                await python_sandbox.command.run("sleep", ["10"], timeout=2)
            
        finally:
            # Clean up
            await python_sandbox.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_complex_command(self, python_sandbox):
        """Test complex command execution with real container."""
        try:
            # Start the sandbox
            await python_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute a complex shell command
            result = await python_sandbox.command.run("sh", ["-c", "echo 'stdout line'; echo 'stderr line' >&2; exit 0"])
            
            # Verify result
            assert isinstance(result, CommandExecution)
            assert result.output_data["exit_code"] == 0
            assert result.output_data["success"] is True
            assert len(result.output_data["output"]) == 2
            
            # Check outputs
            stdout_outputs = [o for o in result.output_data["output"] if o["stream"] == "stdout"]
            stderr_outputs = [o for o in result.output_data["output"] if o["stream"] == "stderr"]
            
            assert len(stdout_outputs) == 1
            assert len(stderr_outputs) == 1
            assert "stdout line" in stdout_outputs[0]["text"]
            assert "stderr line" in stderr_outputs[0]["text"]
            
        finally:
            # Clean up
            await python_sandbox.stop()