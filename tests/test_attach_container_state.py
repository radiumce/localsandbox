#!/usr/bin/env python3
"""
Test to verify container state after attach operation.
"""

import asyncio
import uuid
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_attach_container_state():
    """Test that container is running after attach operation."""
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

test_content = "Test file for attach test - ID: {test_id}"
file_path = "/workspace/attach_test.txt"

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
            original_session_id = matches[0] if matches else f"session-{test_id}"
            
            print(f"Original Session ID: {original_session_id}")
            
            print("Step 2: Pinning sandbox")
            
            # Pin the sandbox
            pin_result = await session.call_tool("pin_sandbox", {
                "session_id": original_session_id,
                "pinned_name": pinned_name
            })
            
            pin_text = pin_result.content[0].text if pin_result.content else ""
            print(f"Pin result: {pin_text}")
            
            if "Error:" in pin_text:
                raise Exception(f"Pin failed: {pin_text}")
            
            print("Step 3: Simulating container stop (to test attach functionality)")
            
            # Stop the container to simulate a stopped pinned container
            import subprocess
            try:
                subprocess.run(["docker", "stop", pinned_name], check=True, capture_output=True)
                print(f"✅ Container {pinned_name} stopped successfully")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Failed to stop container: {e}")
            
            print("Step 4: Attaching to pinned sandbox")
            
            # Attach to the pinned sandbox
            attach_result = await session.call_tool("attach_sandbox_by_name", {
                "pinned_name": pinned_name
            })
            
            attach_text = attach_result.content[0].text if attach_result.content else ""
            print(f"Attach result: {attach_text}")
            
            if "Error:" in attach_text:
                raise Exception(f"Attach failed: {attach_text}")
            
            # Extract new session ID
            if "Session ID:" in attach_text:
                new_session_id = attach_text.split("Session ID:")[1].strip().split()[0]
            else:
                new_session_id = original_session_id  # Fallback
            
            print(f"New Session ID: {new_session_id}")
            
            print("Step 5: Testing container state after attach")
            
            # Try to execute code immediately after attach to verify container is running
            verify_code = f'''
import os
import time

file_path = "/workspace/attach_test.txt"
expected_content = "Test file for attach test - ID: {test_id}"

print(f"Container is running and accessible after attach!")
print(f"Current time: {{time.time()}}")

if os.path.exists(file_path):
    with open(file_path, "r") as f:
        actual_content = f.read()
    
    if actual_content == expected_content:
        print("✅ File exists and content matches after attach!")
        print(f"Content: {{actual_content}}")
    else:
        print("❌ File exists but content doesn't match")
        print(f"Expected: {{expected_content}}")
        print(f"Actual: {{actual_content}}")
else:
    print("❌ File does not exist after attach")
'''
            
            verify_result = await session.call_tool("execute_code", {
                "code": verify_code,
                "session_id": new_session_id,
                "timeout": 10
            })
            
            verify_text = verify_result.content[0].text if verify_result.content else ""
            print(f"Verify result: {verify_text}")
            
            if "✅ File exists and content matches after attach!" in verify_text and "Container is running and accessible after attach!" in verify_text:
                print("🎉 ATTACH CONTAINER STATE TEST PASSED!")
                print("✅ Container is running after attach operation")
                print("✅ New session ID works after attach")
                print("✅ File persistence verified after attach")
                return True
            else:
                print("❌ ATTACH CONTAINER STATE TEST FAILED!")
                print("❌ Container not accessible after attach operation")
                return False


if __name__ == "__main__":
    success = asyncio.run(test_attach_container_state())
    exit(0 if success else 1)