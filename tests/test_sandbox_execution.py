"""
Integration tests for sandbox execution functionality.

These tests verify PythonSandbox and NodeSandbox code execution,
output format compatibility, and error handling.
"""

import asyncio
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from python.sandbox.python_sandbox import PythonSandbox
from python.sandbox.node_sandbox import NodeSandbox
from python.sandbox.execution import Execution
from python.sandbox.container_runtime import ContainerConfig


class TestPythonSandboxExecution:
    """Test PythonSandbox code execution functionality."""
    
    @pytest.fixture
    def python_sandbox(self):
        """Create a PythonSandbox instance for testing."""
        return PythonSandbox(
            container_runtime="docker",
            name=f"test-python-{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.mark.asyncio
    async def test_get_default_image(self, python_sandbox):
        """Test getting default Python image."""
        image = await python_sandbox.get_default_image()
        assert "python" in image.lower()
        assert isinstance(image, str)
        assert len(image) > 0
    
    @pytest.mark.asyncio
    async def test_run_simple_code_success(self, python_sandbox):
        """Test running simple Python code successfully."""
        # Mock the container runtime
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "Hello World\n",
                "stderr": ""
            }
            
            # Set sandbox as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "test-container"
            
            # Execute code
            result = await python_sandbox.run("print('Hello World')")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert result.output_data["language"] == "python"
            assert len(result.output_data["output"]) == 1
            assert result.output_data["output"][0]["stream"] == "stdout"
            assert result.output_data["output"][0]["text"] == "Hello World"
            
            # Verify runtime was called correctly
            mock_runtime.execute_command.assert_called_once()
            call_args = mock_runtime.execute_command.call_args
            assert call_args[0][0] == "test-container"  # container_id
            assert call_args[0][1][0] == "python"  # command
            assert call_args[0][1][1] == "-c"  # flag
            assert "print(\\'Hello World\\')" in call_args[0][1][2]  # escaped code
    
    @pytest.mark.asyncio
    async def test_run_code_with_error(self, python_sandbox):
        """Test running Python code that produces an error."""
        # Mock the container runtime
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Traceback (most recent call last):\n  File \"<string>\", line 4, in <module>\nNameError: name 'undefined_var' is not defined\n"
            }
            
            # Set sandbox as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "test-container"
            
            # Execute code with error
            result = await python_sandbox.run("print(undefined_var)")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "error"
            assert result.output_data["language"] == "python"
            assert len(result.output_data["output"]) == 3  # 3 lines of traceback
            assert all(output["stream"] == "stderr" for output in result.output_data["output"])
            assert "NameError" in result.output_data["output"][-1]["text"]
    
    @pytest.mark.asyncio
    async def test_run_code_with_mixed_output(self, python_sandbox):
        """Test running Python code that produces both stdout and stderr."""
        # Mock the container runtime
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "This is stdout\nAnother stdout line\n",
                "stderr": "This is stderr\n"
            }
            
            # Set sandbox as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "test-container"
            
            # Execute code
            result = await python_sandbox.run("import sys; print('This is stdout'); print('Another stdout line'); print('This is stderr', file=sys.stderr)")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert len(result.output_data["output"]) == 3
            
            # Check stdout outputs
            stdout_outputs = [o for o in result.output_data["output"] if o["stream"] == "stdout"]
            assert len(stdout_outputs) == 2
            assert stdout_outputs[0]["text"] == "This is stdout"
            assert stdout_outputs[1]["text"] == "Another stdout line"
            
            # Check stderr output
            stderr_outputs = [o for o in result.output_data["output"] if o["stream"] == "stderr"]
            assert len(stderr_outputs) == 1
            assert stderr_outputs[0]["text"] == "This is stderr"
    
    @pytest.mark.asyncio
    async def test_run_code_not_started(self, python_sandbox):
        """Test running code when sandbox is not started."""
        # Ensure sandbox is not started
        python_sandbox._is_started = False
        
        with pytest.raises(RuntimeError, match="Sandbox is not started"):
            await python_sandbox.run("print('Hello')")
    
    @pytest.mark.asyncio
    async def test_run_code_runtime_error(self, python_sandbox):
        """Test handling runtime errors during code execution."""
        # Mock the container runtime to raise an exception
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.side_effect = Exception("Container execution failed")
            
            # Set sandbox as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "test-container"
            
            with pytest.raises(RuntimeError, match="Failed to execute code"):
                await python_sandbox.run("print('Hello')")
    
    @pytest.mark.asyncio
    async def test_run_code_with_quotes(self, python_sandbox):
        """Test running Python code that contains single quotes."""
        # Mock the container runtime
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "Hello 'World'\n",
                "stderr": ""
            }
            
            # Set sandbox as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "test-container"
            
            # Execute code with single quotes
            result = await python_sandbox.run("print(\"Hello 'World'\")")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert result.output_data["output"][0]["text"] == "Hello 'World'"
            
            # Verify the code was properly escaped in the command
            call_args = mock_runtime.execute_command.call_args[0][1][2]
            assert "Hello \\'World\\'" in call_args


class TestNodeSandboxExecution:
    """Test NodeSandbox code execution functionality."""
    
    @pytest.fixture
    def node_sandbox(self):
        """Create a NodeSandbox instance for testing."""
        return NodeSandbox(
            container_runtime="docker",
            name=f"test-node-{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.mark.asyncio
    async def test_get_default_image(self, node_sandbox):
        """Test getting default Node.js image."""
        image = await node_sandbox.get_default_image()
        assert "node" in image.lower()
        assert isinstance(image, str)
        assert len(image) > 0
    
    @pytest.mark.asyncio
    async def test_run_simple_code_success(self, node_sandbox):
        """Test running simple JavaScript code successfully."""
        # Mock the container runtime
        with patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "Hello World\n",
                "stderr": ""
            }
            
            # Set sandbox as started
            node_sandbox._is_started = True
            node_sandbox._container_id = "test-container"
            
            # Execute code
            result = await node_sandbox.run("console.log('Hello World')")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert result.output_data["language"] == "nodejs"
            assert len(result.output_data["output"]) == 1
            assert result.output_data["output"][0]["stream"] == "stdout"
            assert result.output_data["output"][0]["text"] == "Hello World"
            
            # Verify runtime was called correctly
            mock_runtime.execute_command.assert_called_once()
            call_args = mock_runtime.execute_command.call_args
            assert call_args[0][0] == "test-container"  # container_id
            assert call_args[0][1] == ["node", "-e", "console.log('Hello World')"]
    
    @pytest.mark.asyncio
    async def test_run_code_with_error(self, node_sandbox):
        """Test running JavaScript code that produces an error."""
        # Mock the container runtime
        with patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "ReferenceError: undefinedVar is not defined\n    at [eval]:1:13\n"
            }
            
            # Set sandbox as started
            node_sandbox._is_started = True
            node_sandbox._container_id = "test-container"
            
            # Execute code with error
            result = await node_sandbox.run("console.log(undefinedVar)")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "error"
            assert result.output_data["language"] == "nodejs"
            assert len(result.output_data["output"]) == 2  # 2 lines of error
            assert all(output["stream"] == "stderr" for output in result.output_data["output"])
            assert "ReferenceError" in result.output_data["output"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_run_code_with_mixed_output(self, node_sandbox):
        """Test running JavaScript code that produces both stdout and stderr."""
        # Mock the container runtime
        with patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "This is stdout\nAnother stdout line\n",
                "stderr": "This is stderr\n"
            }
            
            # Set sandbox as started
            node_sandbox._is_started = True
            node_sandbox._container_id = "test-container"
            
            # Execute code
            result = await node_sandbox.run("console.log('This is stdout'); console.log('Another stdout line'); console.error('This is stderr')")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert len(result.output_data["output"]) == 3
            
            # Check stdout outputs
            stdout_outputs = [o for o in result.output_data["output"] if o["stream"] == "stdout"]
            assert len(stdout_outputs) == 2
            assert stdout_outputs[0]["text"] == "This is stdout"
            assert stdout_outputs[1]["text"] == "Another stdout line"
            
            # Check stderr output
            stderr_outputs = [o for o in result.output_data["output"] if o["stream"] == "stderr"]
            assert len(stderr_outputs) == 1
            assert stderr_outputs[0]["text"] == "This is stderr"
    
    @pytest.mark.asyncio
    async def test_run_code_not_started(self, node_sandbox):
        """Test running code when sandbox is not started."""
        # Ensure sandbox is not started
        node_sandbox._is_started = False
        
        with pytest.raises(RuntimeError, match="Sandbox is not started"):
            await node_sandbox.run("console.log('Hello')")
    
    @pytest.mark.asyncio
    async def test_run_code_runtime_error(self, node_sandbox):
        """Test handling runtime errors during code execution."""
        # Mock the container runtime to raise an exception
        with patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.side_effect = Exception("Container execution failed")
            
            # Set sandbox as started
            node_sandbox._is_started = True
            node_sandbox._container_id = "test-container"
            
            with pytest.raises(RuntimeError, match="Failed to execute code"):
                await node_sandbox.run("console.log('Hello')")


class TestSandboxOutputCompatibility:
    """Test output format compatibility between different sandbox types."""
    
    @pytest.fixture
    def python_sandbox(self):
        """Create a PythonSandbox instance for testing."""
        return PythonSandbox(name=f"test-python-{uuid.uuid4().hex[:8]}")
    
    @pytest.fixture
    def node_sandbox(self):
        """Create a NodeSandbox instance for testing."""
        return NodeSandbox(name=f"test-node-{uuid.uuid4().hex[:8]}")
    
    @pytest.mark.asyncio
    async def test_execution_object_structure(self, python_sandbox):
        """Test that Execution objects have the expected structure."""
        # Mock the container runtime
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_runtime:
            mock_runtime.execute_command.return_value = {
                "returncode": 0,
                "stdout": "test output\n",
                "stderr": ""
            }
            
            # Set sandbox as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "test-container"
            
            # Execute code
            result = await python_sandbox.run("print('test output')")
            
            # Verify Execution object structure
            assert hasattr(result, 'output_data')
            assert isinstance(result.output_data, dict)
            
            # Verify required fields
            required_fields = ['output', 'status', 'language']
            for field in required_fields:
                assert field in result.output_data
            
            # Verify output structure
            assert isinstance(result.output_data['output'], list)
            if result.output_data['output']:
                output_item = result.output_data['output'][0]
                assert 'stream' in output_item
                assert 'text' in output_item
                assert output_item['stream'] in ['stdout', 'stderr']
    
    @pytest.mark.asyncio
    async def test_cross_language_output_consistency(self, python_sandbox, node_sandbox):
        """Test that Python and Node.js sandboxes produce consistent output formats."""
        # Mock both runtimes
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_python_runtime, \
             patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_node_runtime:
            
            # Set up identical mock responses
            mock_response = {
                "returncode": 0,
                "stdout": "Hello World\n",
                "stderr": ""
            }
            mock_python_runtime.execute_command.return_value = mock_response
            mock_node_runtime.execute_command.return_value = mock_response
            
            # Set both sandboxes as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "python-container"
            node_sandbox._is_started = True
            node_sandbox._container_id = "node-container"
            
            # Execute equivalent code in both sandboxes
            python_result = await python_sandbox.run("print('Hello World')")
            node_result = await node_sandbox.run("console.log('Hello World')")
            
            # Verify both results have the same structure
            assert python_result.output_data.keys() == node_result.output_data.keys()
            
            # Verify status consistency
            assert python_result.output_data['status'] == node_result.output_data['status']
            
            # Verify output format consistency
            assert len(python_result.output_data['output']) == len(node_result.output_data['output'])
            
            python_output = python_result.output_data['output'][0]
            node_output = node_result.output_data['output'][0]
            
            assert python_output.keys() == node_output.keys()
            assert python_output['stream'] == node_output['stream']
            assert python_output['text'] == node_output['text']
            
            # Verify language-specific fields
            assert python_result.output_data['language'] == 'python'
            assert node_result.output_data['language'] == 'nodejs'
    
    @pytest.mark.asyncio
    async def test_error_output_consistency(self, python_sandbox, node_sandbox):
        """Test that error outputs are consistently formatted across languages."""
        # Mock both runtimes with error responses
        with patch.object(python_sandbox, '_runtime', new=AsyncMock()) as mock_python_runtime, \
             patch.object(node_sandbox, '_runtime', new=AsyncMock()) as mock_node_runtime:
            
            mock_python_runtime.execute_command.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Error: Something went wrong\n"
            }
            mock_node_runtime.execute_command.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Error: Something went wrong\n"
            }
            
            # Set both sandboxes as started
            python_sandbox._is_started = True
            python_sandbox._container_id = "python-container"
            node_sandbox._is_started = True
            node_sandbox._container_id = "node-container"
            
            # Execute code that produces errors
            python_result = await python_sandbox.run("raise Exception('Something went wrong')")
            node_result = await node_sandbox.run("throw new Error('Something went wrong')")
            
            # Verify both results indicate error status
            assert python_result.output_data['status'] == 'error'
            assert node_result.output_data['status'] == 'error'
            
            # Verify error output structure
            python_error = python_result.output_data['output'][0]
            node_error = node_result.output_data['output'][0]
            
            assert python_error['stream'] == 'stderr'
            assert node_error['stream'] == 'stderr'
            assert 'Error' in python_error['text']
            assert 'Error' in node_error['text']


class TestSandboxIntegration:
    """Integration tests for sandbox execution with real containers."""
    
    @pytest.fixture
    def python_sandbox(self):
        """Create a PythonSandbox instance for integration testing."""
        return PythonSandbox(
            container_runtime="docker",
            name=f"test-integration-python-{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.fixture
    def node_sandbox(self):
        """Create a NodeSandbox instance for integration testing."""
        return NodeSandbox(
            container_runtime="docker",
            name=f"test-integration-node-{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_python_sandbox_real_execution(self, python_sandbox):
        """Test Python sandbox with real container execution."""
        try:
            # Start the sandbox
            await python_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute simple Python code
            result = await python_sandbox.run("print('Hello from Python container')")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert result.output_data["language"] == "python"
            assert len(result.output_data["output"]) == 1
            assert result.output_data["output"][0]["stream"] == "stdout"
            assert "Hello from Python container" in result.output_data["output"][0]["text"]
            
        finally:
            # Clean up
            await python_sandbox.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_node_sandbox_real_execution(self, node_sandbox):
        """Test Node.js sandbox with real container execution."""
        try:
            # Start the sandbox
            await node_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute simple JavaScript code
            result = await node_sandbox.run("console.log('Hello from Node container')")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert result.output_data["language"] == "nodejs"
            assert len(result.output_data["output"]) == 1
            assert result.output_data["output"][0]["stream"] == "stdout"
            assert "Hello from Node container" in result.output_data["output"][0]["text"]
            
        finally:
            # Clean up
            await node_sandbox.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_python_sandbox_error_handling(self, python_sandbox):
        """Test Python sandbox error handling with real container."""
        try:
            # Start the sandbox
            await python_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute Python code that raises an error
            result = await python_sandbox.run("raise ValueError('Test error message')")
            
            # Verify error result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "error"
            assert result.output_data["language"] == "python"
            
            # Check that error information is in stderr output
            stderr_outputs = [o for o in result.output_data["output"] if o["stream"] == "stderr"]
            assert len(stderr_outputs) > 0
            
            # Verify error details are present
            error_text = " ".join([o["text"] for o in stderr_outputs])
            assert "ValueError" in error_text
            assert "Test error message" in error_text
            
        finally:
            # Clean up
            await python_sandbox.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_node_sandbox_error_handling(self, node_sandbox):
        """Test Node.js sandbox error handling with real container."""
        try:
            # Start the sandbox
            await node_sandbox.start(memory=128, cpus=0.5, timeout=60)
            
            # Execute JavaScript code that throws an error
            result = await node_sandbox.run("throw new Error('Test error message')")
            
            # Verify error result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "error"
            assert result.output_data["language"] == "nodejs"
            
            # Check that error information is in stderr output
            stderr_outputs = [o for o in result.output_data["output"] if o["stream"] == "stderr"]
            assert len(stderr_outputs) > 0
            
            # Verify error details are present
            error_text = " ".join([o["text"] for o in stderr_outputs])
            assert "Error" in error_text
            assert "Test error message" in error_text
            
        finally:
            # Clean up
            await node_sandbox.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_sandbox_context_manager(self, python_sandbox):
        """Test sandbox usage as async context manager."""
        # Use sandbox as context manager
        async with PythonSandbox.create(
            container_runtime="docker",
            name=f"test-context-{uuid.uuid4().hex[:8]}",
            memory=128,
            cpus=0.5,
            timeout=60
        ) as sandbox:
            # Execute code
            result = await sandbox.run("print('Context manager test')")
            
            # Verify result
            assert isinstance(result, Execution)
            assert result.output_data["status"] == "success"
            assert "Context manager test" in result.output_data["output"][0]["text"]
        
        # Sandbox should be automatically stopped after context exit
        # (We can't easily test this without accessing private attributes)