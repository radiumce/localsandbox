#!/usr/bin/env python3
"""
Fixed simplified end-to-end test for pin-sandbox functionality using official MCP client.

This test focuses on the core workflow:
1. Create session and write test file
2. Pin sandbox with custom name
3. Verify file exists immediately after pin
4. Wait for session cleanup (low timeout)
5. Attach to pinned sandbox
6. Verify file still exists after cleanup and reattachment

This is a corrected version that uses the proper MCP client API.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import pytest

# Import MCP client components
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    print("Warning: MCP client not available. Install with: pip install mcp")
    MCP_AVAILABLE = False


class SimplePinSandboxE2ETest:
    """Simplified end-to-end test for pin-sandbox functionality."""
    
    def __init__(self):
        self.test_id = uuid.uuid4().hex[:8]
        self.pinned_name = f"test_pinned_{self.test_id}"
        self.original_session_id = None
        self.attached_session_id = None
        
        # Test configuration
        self.session_timeout = 8  # Short timeout for quick cleanup
        self.cleanup_interval = 3  # Frequent cleanup
        self.test_file_path = "/workspace/persistence_test.txt"
        self.test_file_content = f"Test file for pin-sandbox - ID: {self.test_id} - Created: {time.time()}"
    
    async def create_session_and_write_file(self) -> str:
        """Create sandbox session and write test file."""
        print("📝 Step 1: Creating session and writing test file")
        
        # Find the MCP server script
        project_root = Path(__file__).parent.parent
        server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
        
        if not server_script.exists():
            # Try alternative path
            server_script = project_root / "mcp-server" / "main.py"
        
        if not server_script.exists():
            raise FileNotFoundError(f"MCP server script not found. Looked in: {server_script}")
        
        # Prepare environment with aggressive cleanup settings
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(self.session_timeout),
            'CLEANUP_INTERVAL': str(self.cleanup_interval),
            'MAX_CONCURRENT_SESSIONS': '5',
            'LOG_LEVEL': 'INFO'
        })
        
        # Configure server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script)],
            env=test_env
        )
        
        # Code to create test file
        create_file_code = f'''
import os
from datetime import datetime

# Create test file
test_content = """{self.test_file_content}"""

# Ensure directory exists
os.makedirs(os.path.dirname("{self.test_file_path}"), exist_ok=True)

# Write test file
with open("{self.test_file_path}", "w") as f:
    f.write(test_content)

print(f"✅ Test file created: {self.test_file_path}")
print(f"Content: {{test_content[:50]}}...")

# Verify file was created
if os.path.exists("{self.test_file_path}"):
    with open("{self.test_file_path}", "r") as f:
        content = f.read()
    print(f"✅ File verification passed. Size: {{len(content)}} bytes")
else:
    print("❌ File creation failed!")
'''
        
        # Execute code to create file using MCP client
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Execute code to create file
                result = await session.call_tool("execute_code", {
                    "code": create_file_code,
                    "template": "python",
                    "flavor": "small",
                    "timeout": 30
                })
                
                # Extract session ID from result
                result_text = str(result.content[0].text) if result.content else ""
                session_id = self._extract_session_id(result_text)
                
                print(f"   Session ID: {session_id}")
                print(f"   Result: {result_text.split('[Session:')[0].strip()}")
                
                return session_id
    
    async def verify_file_exists(self, session_id: str, step_name: str) -> bool:
        """Verify test file exists and has correct content."""
        print(f"🔍 {step_name}: Verifying file persistence")
        
        verify_code = f'''
import os

file_path = "{self.test_file_path}"
expected_content = """{self.test_file_content}"""

if os.path.exists(file_path):
    with open(file_path, "r") as f:
        actual_content = f.read()
    
    content_matches = actual_content == expected_content
    
    print(f"✅ File exists: {{file_path}}")
    print(f"✅ Content matches: {{content_matches}}")
    print(f"   Expected length: {{len(expected_content)}}")
    print(f"   Actual length: {{len(actual_content)}}")
    
    if not content_matches:
        print(f"   Expected: {{expected_content[:50]}}...")
        print(f"   Actual: {{actual_content[:50]}}...")
    
    # Return verification result
    print(f"VERIFICATION_RESULT: {{content_matches}}")
else:
    print(f"❌ File does not exist: {{file_path}}")
    print("VERIFICATION_RESULT: False")
'''
        
        # Find the MCP server script
        project_root = Path(__file__).parent.parent
        server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
        
        if not server_script.exists():
            server_script = project_root / "mcp-server" / "main.py"
        
        # Prepare environment
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(self.session_timeout),
            'CLEANUP_INTERVAL': str(self.cleanup_interval),
            'MAX_CONCURRENT_SESSIONS': '5',
            'LOG_LEVEL': 'INFO'
        })
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script)],
            env=test_env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("execute_code", {
                    "code": verify_code,
                    "session_id": session_id,
                    "template": "python",
                    "timeout": 20
                })
                
                result_text = str(result.content[0].text) if result.content else ""
                print(f"   {result_text.split('[Session:')[0].strip()}")
                
                # Parse verification result
                verification_passed = "VERIFICATION_RESULT: True" in result_text
                return verification_passed
    
    async def pin_sandbox(self, session_id: str):
        """Pin the sandbox with custom name."""
        print(f"📌 Step 2: Pinning sandbox as '{self.pinned_name}'")
        
        # Find the MCP server script
        project_root = Path(__file__).parent.parent
        server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
        
        if not server_script.exists():
            server_script = project_root / "mcp-server" / "main.py"
        
        # Prepare environment
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(self.session_timeout),
            'CLEANUP_INTERVAL': str(self.cleanup_interval),
            'MAX_CONCURRENT_SESSIONS': '5',
            'LOG_LEVEL': 'INFO'
        })
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script)],
            env=test_env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("pin_sandbox", {
                    "session_id": session_id,
                    "pinned_name": self.pinned_name
                })
                
                result_text = str(result.content[0].text) if result.content else ""
                print(f"   Result: {result_text}")
                
                if "Successfully pinned session" not in result_text:
                    raise AssertionError(f"Pin operation failed: {result_text}")
                
                print("   ✅ Sandbox pinned successfully")
    
    async def wait_for_cleanup(self):
        """Wait for session cleanup to occur."""
        cleanup_wait = self.session_timeout + self.cleanup_interval + 2
        print(f"⏳ Step 3: Waiting {cleanup_wait}s for session cleanup")
        
        await asyncio.sleep(cleanup_wait)
        
        print("   ✅ Cleanup wait period completed")
        
        # Try to verify original session is gone
        try:
            # Find the MCP server script
            project_root = Path(__file__).parent.parent
            server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
            
            if not server_script.exists():
                server_script = project_root / "mcp-server" / "main.py"
            
            # Prepare environment
            test_env = os.environ.copy()
            test_env.update({
                'SESSION_TIMEOUT': str(self.session_timeout),
                'CLEANUP_INTERVAL': str(self.cleanup_interval),
                'MAX_CONCURRENT_SESSIONS': '5',
                'LOG_LEVEL': 'INFO'
            })
            
            server_params = StdioServerParameters(
                command="python",
                args=[str(server_script)],
                env=test_env
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool("execute_code", {
                        "code": "print('Testing original session')",
                        "session_id": self.original_session_id,
                        "template": "python",
                        "timeout": 10
                    })
                    print("   ⚠️  Original session may still be active")
        except Exception:
            print("   ✅ Original session appears to be cleaned up")
    
    async def attach_to_pinned_sandbox(self) -> str:
        """Attach to the pinned sandbox."""
        print(f"🔗 Step 4: Attaching to pinned sandbox '{self.pinned_name}'")
        
        # Find the MCP server script
        project_root = Path(__file__).parent.parent
        server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
        
        if not server_script.exists():
            server_script = project_root / "mcp-server" / "main.py"
        
        # Prepare environment
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(self.session_timeout),
            'CLEANUP_INTERVAL': str(self.cleanup_interval),
            'MAX_CONCURRENT_SESSIONS': '5',
            'LOG_LEVEL': 'INFO'
        })
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script)],
            env=test_env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("attach_sandbox_by_name", {
                    "pinned_name": self.pinned_name
                })
                
                result_text = str(result.content[0].text) if result.content else ""
                print(f"   Result: {result_text}")
                
                if "Successfully attached" not in result_text:
                    raise AssertionError(f"Attach operation failed: {result_text}")
                
                # Extract new session ID
                new_session_id = self._extract_attach_session_id(result_text)
                print(f"   ✅ Attached successfully. New session: {new_session_id}")
                
                return new_session_id
    
    def _extract_session_id(self, result_text: str) -> str:
        """Extract session ID from execute_code result."""
        lines = result_text.split('\n')
        for line in lines:
            if '[Session:' in line:
                start = line.find('[Session:') + 9
                end = line.find(']', start)
                if start > 8 and end > start:
                    return line[start:end].strip()
        
        return f"unknown-{self.test_id}"
    
    def _extract_attach_session_id(self, result_text: str) -> str:
        """Extract session ID from attach result."""
        if "Session ID:" in result_text:
            parts = result_text.split("Session ID:")
            if len(parts) > 1:
                return parts[1].strip().split()[0]
        
        return f"attached-{self.test_id}"
    
    async def run_test(self):
        """Run the complete end-to-end test."""
        print("🚀 Starting Pin-Sandbox End-to-End Test")
        print("=" * 50)
        
        try:
            # Step 1: Create session and write file
            self.original_session_id = await self.create_session_and_write_file()
            
            # Step 2: Pin sandbox
            await self.pin_sandbox(self.original_session_id)
            
            # Step 2.5: Verify file exists after pin
            file_exists_after_pin = await self.verify_file_exists(
                self.original_session_id, 
                "Step 2.5"
            )
            if not file_exists_after_pin:
                raise AssertionError("File missing immediately after pin operation")
            
            # Step 3: Wait for cleanup
            await self.wait_for_cleanup()
            
            # Step 4: Attach to pinned sandbox
            self.attached_session_id = await self.attach_to_pinned_sandbox()
            
            # Step 5: Verify file still exists
            file_exists_after_attach = await self.verify_file_exists(
                self.attached_session_id,
                "Step 5"
            )
            if not file_exists_after_attach:
                raise AssertionError("File missing after cleanup and reattachment")
            
            # Success!
            print("=" * 50)
            print("🎉 PIN-SANDBOX TEST PASSED!")
            print("✅ File persisted through pin → cleanup → attach cycle")
            print("✅ Sandbox state continuity verified")
            print("=" * 50)
            
        except Exception as e:
            print("=" * 50)
            print(f"❌ TEST FAILED: {e}")
            print("=" * 50)
            raise


@pytest.mark.asyncio
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP client not available")
async def test_pin_sandbox_simple_e2e():
    """Simple end-to-end test for pin-sandbox functionality."""
    test = SimplePinSandboxE2ETest()
    await test.run_test()


@pytest.mark.asyncio
@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP client not available")
async def test_pin_sandbox_with_multiple_files():
    """Test pin-sandbox with multiple files and directories."""
    test = SimplePinSandboxE2ETest()
    
    # Override file creation to test multiple files
    original_create = test.create_session_and_write_file
    
    async def create_multiple_files():
        print("📝 Step 1: Creating session with multiple files")
        
        # Find the MCP server script
        project_root = Path(__file__).parent.parent
        server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
        
        if not server_script.exists():
            server_script = project_root / "mcp-server" / "main.py"
        
        # Prepare environment
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(test.session_timeout),
            'CLEANUP_INTERVAL': str(test.cleanup_interval),
            'MAX_CONCURRENT_SESSIONS': '5',
            'LOG_LEVEL': 'INFO'
        })
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script)],
            env=test_env
        )
        
        create_files_code = f'''
import os
import json
from datetime import datetime

# Create directory structure
directories = [
    "/workspace/data",
    "/workspace/scripts",
    "/workspace/logs"
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)

# Create multiple test files
files = {{
    "{test.test_file_path}": """{test.test_file_content}""",
    "/workspace/data/config.json": json.dumps({{
        "test_id": "{test.test_id}",
        "created_at": datetime.now().isoformat(),
        "type": "pin_sandbox_test"
    }}, indent=2),
    "/workspace/scripts/test.py": """
def hello():
    return "Hello from pinned sandbox!"

if __name__ == "__main__":
    print(hello())
""",
    "/workspace/logs/test.log": f"[{{datetime.now().isoformat()}}] Test started - ID: {test.test_id}\\n"
}}

# Write all files
for file_path, content in files.items():
    with open(file_path, "w") as f:
        f.write(content)
    print(f"✅ Created: {{file_path}}")

print(f"✅ Created {{len(files)}} test files")
'''
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("execute_code", {
                    "code": create_files_code,
                    "template": "python",
                    "flavor": "small",
                    "timeout": 30
                })
                
                result_text = str(result.content[0].text) if result.content else ""
                session_id = test._extract_session_id(result_text)
                
                print(f"   Session ID: {session_id}")
                return session_id
    
    # Override verification to check multiple files
    original_verify = test.verify_file_exists
    
    async def verify_multiple_files(session_id: str, step_name: str) -> bool:
        print(f"🔍 {step_name}: Verifying multiple files")
        
        verify_code = f'''
import os
import json

files_to_check = [
    "{test.test_file_path}",
    "/workspace/data/config.json",
    "/workspace/scripts/test.py",
    "/workspace/logs/test.log"
]

all_exist = True
for file_path in files_to_check:
    exists = os.path.exists(file_path)
    print(f"{{file_path}}: {{'✅' if exists else '❌'}}")
    if not exists:
        all_exist = False

# Test JSON file content
if os.path.exists("/workspace/data/config.json"):
    with open("/workspace/data/config.json", "r") as f:
        config = json.load(f)
    print(f"Config test_id: {{config.get('test_id')}}")
    if config.get('test_id') != "{test.test_id}":
        all_exist = False

# Test Python script execution
if os.path.exists("/workspace/scripts/test.py"):
    exec(open("/workspace/scripts/test.py").read())

print(f"VERIFICATION_RESULT: {{all_exist}}")
'''
        
        # Find the MCP server script
        project_root = Path(__file__).parent.parent
        server_script = project_root / "mcp-server" / "mcp_server" / "main.py"
        
        if not server_script.exists():
            server_script = project_root / "mcp-server" / "main.py"
        
        # Prepare environment
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(test.session_timeout),
            'CLEANUP_INTERVAL': str(test.cleanup_interval),
            'MAX_CONCURRENT_SESSIONS': '5',
            'LOG_LEVEL': 'INFO'
        })
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script)],
            env=test_env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool("execute_code", {
                    "code": verify_code,
                    "session_id": session_id,
                    "template": "python",
                    "timeout": 20
                })
                
                result_text = str(result.content[0].text) if result.content else ""
                print(f"   {result_text.split('[Session:')[0].strip()}")
                
                return "VERIFICATION_RESULT: True" in result_text
    
    # Replace methods
    test.create_session_and_write_file = create_multiple_files
    test.verify_file_exists = verify_multiple_files
    
    await test.run_test()


if __name__ == "__main__":
    """Run the test directly."""
    if not MCP_AVAILABLE:
        print("❌ MCP client not available. Install with: pip install mcp")
        exit(1)
    
    async def run_tests():
        print("Running simple pin-sandbox end-to-end test...")
        await test_pin_sandbox_simple_e2e()
        
        print("\n" + "="*50 + "\n")
        
        print("Running multiple files test...")
        await test_pin_sandbox_with_multiple_files()
    
    asyncio.run(run_tests())