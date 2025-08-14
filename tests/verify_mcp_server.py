#!/usr/bin/env python3
"""
Quick verification script for MCP server functionality.

This script performs basic checks to ensure the MCP server is working
before running the full pin-sandbox end-to-end tests.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


async def verify_mcp_server():
    """Verify basic MCP server functionality."""
    print("🔍 Verifying MCP Server Functionality")
    print("="*50)
    
    if not MCP_AVAILABLE:
        print("❌ MCP client not available. Install with: pip install mcp")
        return False
    
    # Find server script
    server_paths = [
        project_root / "mcp-server" / "mcp_server" / "main.py",
        project_root / "mcp-server" / "main.py"
    ]
    
    server_script = None
    for path in server_paths:
        if path.exists():
            server_script = path
            break
    
    if not server_script:
        print("❌ MCP server script not found")
        return False
    
    print(f"✅ Found MCP server: {server_script}")
    
    # Test environment
    test_env = os.environ.copy()
    test_env.update({
        'SESSION_TIMEOUT': '30',
        'CLEANUP_INTERVAL': '10',
        'LOG_LEVEL': 'INFO'
    })
    
    # Start server
    server_params = StdioServerParameters(
        command="python",
        args=[str(server_script)],
        env=test_env
    )
    
    print("🚀 Starting MCP server...")
    
    try:
        async with stdio_client(server_params) as (session, server_process):
            print(f"✅ MCP server started (PID: {server_process.pid})")
            
            # Test basic functionality
            print("\n🧪 Testing basic functionality...")
            
            # Test 1: Execute simple code
            print("   Test 1: Execute simple Python code")
            result = await session.call_tool("execute_code", {
                "code": "print('Hello from MCP server!')\nprint('Basic functionality test passed')",
                "template": "python",
                "flavor": "small",
                "timeout": 10
            })
            
            result_text = result.content[0].text if result.content else ""
            if "Hello from MCP server!" in result_text:
                print("   ✅ Code execution works")
                session_id = extract_session_id(result_text)
                print(f"   Session ID: {session_id}")
            else:
                print("   ❌ Code execution failed")
                print(f"   Result: {result_text}")
                return False
            
            # Test 2: Get sessions
            print("   Test 2: Get sessions")
            result = await session.call_tool("get_sessions", {})
            result_text = result.content[0].text if result.content else ""
            if session_id in result_text:
                print("   ✅ Session management works")
            else:
                print("   ❌ Session management failed")
                print(f"   Result: {result_text}")
            
            # Test 3: Pin sandbox (should work)
            print("   Test 3: Pin sandbox")
            test_pin_name = f"test_pin_{int(time.time())}"
            result = await session.call_tool("pin_sandbox", {
                "session_id": session_id,
                "pinned_name": test_pin_name
            })
            result_text = result.content[0].text if result.content else ""
            if "Successfully pinned session" in result_text:
                print("   ✅ Pin sandbox works")
            else:
                print("   ❌ Pin sandbox failed")
                print(f"   Result: {result_text}")
                return False
            
            # Test 4: Attach to pinned sandbox
            print("   Test 4: Attach to pinned sandbox")
            result = await session.call_tool("attach_sandbox_by_name", {
                "pinned_name": test_pin_name
            })
            result_text = result.content[0].text if result.content else ""
            if "Successfully attached" in result_text:
                print("   ✅ Attach sandbox works")
            else:
                print("   ❌ Attach sandbox failed")
                print(f"   Result: {result_text}")
                return False
            
            print("\n✅ All basic functionality tests passed!")
            print("🧹 Server cleanup completed")
            return True
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False


def extract_session_id(result_text: str) -> str:
    """Extract session ID from result text."""
    lines = result_text.split('\n')
    for line in lines:
        if '[Session:' in line:
            start = line.find('[Session:') + 9
            end = line.find(']', start)
            if start > 8 and end > start:
                return line[start:end].strip()
    return "unknown"


async def main():
    """Main verification function."""
    success = await verify_mcp_server()
    
    print("\n" + "="*50)
    if success:
        print("🎉 MCP Server Verification PASSED!")
        print("✅ Ready to run pin-sandbox end-to-end tests")
        print("\nNext steps:")
        print("  python tests/run_pin_sandbox_e2e.py --simple")
        print("  python tests/run_pin_sandbox_e2e.py --all")
    else:
        print("❌ MCP Server Verification FAILED!")
        print("⚠️  Fix issues before running end-to-end tests")
    
    return success


if __name__ == "__main__":
    if not MCP_AVAILABLE:
        print("❌ MCP client not available. Install with: pip install mcp")
        sys.exit(1)
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)