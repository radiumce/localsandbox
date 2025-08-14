#!/usr/bin/env python3
"""
Test to verify container state after pin operation.
"""

import asyncio
import uuid
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_pin_container_state():
    """Test that container remains running after pin operation."""
    test_id = uuid.uuid4().hex[:8]
    pinned_name = f"test_pinned_{test_id}"
    
    # Project paths
    project_root = Path(__file__).parent.parent
    server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
    
    # Server parameters
    test_env = {
        'SESSION_TIMEOUT': '3600',
        'CLEANUP_INTERVAL': '60',
        'MAX_CONCURRENT_SESSIONS': '5',
        'LOG_LEVEL': 'INFO',
        'PYTHONPATH': str(project_root.absolute() / "mcp-server")
    }
    
    server_params = StdioServerParameters(
        command="python",
        args=[str(server_script.absolute())],
        env=test_env,
        cwd=str(project_root.absolute())
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Step 1: Creating session and writing test file")
            
            # Create test file
            create_code = f'''
import os

test_content = "Test file for pin-sandbox - ID: {test_id}"
file_path = "/workspace/test_file.txt"

with open(file_path, "w") as f:
    f.write(test_content)

print(f"Created file: {{file_path}}")
print(f"Content: {{test_content}}")
'''
            
            result = await session.call_tool("execute_code", {
                "code": create_code,
                "template": "python",
                "flavor": "small",
                "timeout": 30
            })
            
            result_text = result.content[0].text if result.content else ""
            print(f"Create result: {result_text}")
            
            # Extract session ID
            import re
            uuid_pattern = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
            matches = re.findall(uuid_pattern, result_text, re.IGNORECASE)
            session_id = matches[0] if matches else f"session-{test_id}"
            
            print(f"Session ID: {session_id}")
            
            print("Step 2: Pinning sandbox")
            
            # Pin the sandbox
            pin_result = await session.call_tool("pin_sandbox", {
                "session_id": session_id,
                "pinned_name": pinned_name
            })
            
            pin_text = pin_result.content[0].text if pin_result.content else ""
            print(f"Pin result: {pin_text}")
            
            if "Error:" in pin_text:
                raise Exception(f"Pin failed: {pin_text}")
            
            print("Step 3: Testing container state after pin")
            
            # Try to execute code immediately after pin to verify container is running
            verify_code = f'''
import os
import time

file_path = "/workspace/test_file.txt"
expected_content = "Test file for pin-sandbox - ID: {test_id}"

print(f"Container is running and accessible!")
print(f"Current time: {{time.time()}}")

if os.path.exists(file_path):
    with open(file_path, "r") as f:
        actual_content = f.read()
    
    if actual_content == expected_content:
        print("✅ File exists and content matches after pin!")
        print(f"Content: {{actual_content}}")
    else:
        print("❌ File exists but content doesn't match")
        print(f"Expected: {{expected_content}}")
        print(f"Actual: {{actual_content}}")
else:
    print("❌ File does not exist after pin")
'''
            
            verify_result = await session.call_tool("execute_code", {
                "code": verify_code,
                "session_id": session_id,
                "timeout": 10
            })
            
            verify_text = verify_result.content[0].text if verify_result.content else ""
            print(f"Verify result: {verify_text}")
            
            if "✅ File exists and content matches after pin!" in verify_text and "Container is running and accessible!" in verify_text:
                print("🎉 CONTAINER STATE TEST PASSED!")
                print("✅ Container remains running after pin operation")
                print("✅ Session ID continues to work after pin")
                return True
            else:
                print("❌ CONTAINER STATE TEST FAILED!")
                print("❌ Container not accessible after pin operation")
                return False


if __name__ == "__main__":
    success = asyncio.run(test_pin_container_state())
    exit(0 if success else 1)