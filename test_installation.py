#!/usr/bin/env python3
"""
Test script to verify Microsandbox MCP Server installation
"""

import sys
import subprocess
import importlib.util


def test_import(module_name):
    """Test if a module can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False, f"Module {module_name} not found"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, f"Module {module_name} imported successfully"
    except Exception as e:
        return False, f"Failed to import {module_name}: {e}"


def test_command(command):
    """Test if a command is available."""
    try:
        result = subprocess.run([command, '--help'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            return True, f"Command {command} is available"
        else:
            return False, f"Command {command} failed: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, f"Command {command} timed out"
    except FileNotFoundError:
        return False, f"Command {command} not found"
    except Exception as e:
        return False, f"Error testing command {command}: {e}"


def main():
    """Run installation tests."""
    print("🧪 Testing Microsandbox MCP Server Installation")
    print("=" * 50)
    
    tests = [
        # Test module imports
        ("Import mcp_server", lambda: test_import("mcp_server")),
        ("Import mcp_server.main", lambda: test_import("mcp_server.main")),
        ("Import mcp_server.scripts", lambda: test_import("mcp_server.scripts")),
        ("Import microsandbox_wrapper", lambda: test_import("microsandbox_wrapper")),
        
        # Test command availability
        ("Command microsandbox-mcp-server", lambda: test_command("microsandbox-mcp-server")),
        ("Command mcp-server", lambda: test_command("mcp-server")),
        ("Command start-localsandbox", lambda: test_command("start-localsandbox")),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success, message = test_func()
            if success:
                print(f"✅ {test_name}: {message}")
                passed += 1
            else:
                print(f"❌ {test_name}: {message}")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: Unexpected error: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Installation is successful.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the installation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())