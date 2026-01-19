
import subprocess
import importlib.util
import pytest
import shutil
import sys

def test_imports():
    """Test that key modules can be imported."""
    modules = [
        "server",
        "server.main",
        "server.scripts",
        "wrapper",
        "sandbox"
    ]
    for module_name in modules:
        try:
            spec = importlib.util.find_spec(module_name)
            assert spec is not None, f"Module {module_name} not found"
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import {module_name}: {e}")

def test_commands_available():
    """Test that entry point commands are available in the PATH."""
    commands = [
        "microsandbox-mcp-server",
        "mcp-server",
        "start-localsandbox"
    ]
    
    for command in commands:
        assert shutil.which(command) is not None, f"Command {command} not found in PATH"

@pytest.mark.skipif(shutil.which("microsandbox-mcp-server") is None, reason="Package not installed")
def test_command_execution():
    """Test that commands can actually run (help flag)."""
    commands = [
        "microsandbox-mcp-server",
        "mcp-server",
        "start-localsandbox"
    ]
    
    for command in commands:
        try:
            result = subprocess.run(
                [command, '--help'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            assert result.returncode == 0, f"Command {command} --help failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.fail(f"Command {command} timed out")