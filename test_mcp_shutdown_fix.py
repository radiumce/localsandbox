#!/usr/bin/env python3
"""
Test script to verify the MCP server shutdown fix.

This script tests that the MCP server can be started and stopped without
the asyncio.run() error that was occurring in signal handlers.
"""

import asyncio
import signal
import sys
import os
import time
from pathlib import Path

# Add the mcp-server directory to the path
mcp_server_path = Path(__file__).parent / "mcp-server"
sys.path.insert(0, str(mcp_server_path))

from mcp_server.server import create_server_app, shutdown_wrapper_sync


async def test_mcp_server_lifecycle():
    """Test MCP server creation and shutdown."""
    print("Testing MCP server lifecycle...")
    
    try:
        # Create the server
        print("Creating MCP server...")
        server = create_server_app()
        print("MCP server created successfully")
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        # Test signal handler
        print("Testing signal handler...")
        shutdown_wrapper_sync()
        print("Signal handler test completed")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_handler_directly():
    """Test the signal handler directly without asyncio context."""
    print("Testing signal handler directly...")
    
    try:
        shutdown_wrapper_sync()
        print("Direct signal handler test completed successfully")
        return True
    except Exception as e:
        print(f"Direct signal handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Starting MCP server shutdown fix tests...")
    
    # Test 1: Direct signal handler test
    if not test_signal_handler_directly():
        print("❌ Direct signal handler test failed")
        return False
    print("✅ Direct signal handler test passed")
    
    # Test 2: MCP server lifecycle test
    try:
        result = asyncio.run(test_mcp_server_lifecycle())
        if not result:
            print("❌ MCP server lifecycle test failed")
            return False
        print("✅ MCP server lifecycle test passed")
    except Exception as e:
        print(f"❌ MCP server lifecycle test failed with exception: {e}")
        return False
    
    print("🎉 All tests passed! The shutdown fix is working correctly.")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)