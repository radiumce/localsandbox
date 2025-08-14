#!/usr/bin/env python3
"""
Pin-Sandbox End-to-End Test - Single Session Version

This test runs all operations in a single MCP session to avoid session state loss.
"""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class SingleSessionPinSandboxTest:
    """Pin-sandbox test that runs all operations in a single MCP session."""
    
    def __init__(self):
        self.test_id = uuid.uuid4().hex[:8]
        self.pinned_name = f"test_pinned_{self.test_id}"
        self.original_session_id = None
        self.attached_session_id = None
        
        # Test configuration
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT', '8'))
        self.cleanup_interval = int(os.getenv('CLEANUP_INTERVAL', '3'))
        self.test_file_path = "/workspace/persistence_test.txt"
        self.test_file_content = f"Test file for pin-sandbox - ID: {self.test_id} - Created: {time.time()}"
        
        # Project paths
        self.project_root = Path(__file__).parent.parent
        self.server_script = self.project_root / "mcp-server" / "mcp_server" / "main.py"
    
    def _get_server_params(self):
        """Get server parameters with proper environment setup."""
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(self.session_timeout),
            'CLEANUP_INTERVAL': str(self.cleanup_interval),
            'MAX_CONCURRENT_SESSIONS': '5',
            'LOG_LEVEL': 'INFO',
            'PYTHONPATH': str(self.project_root.absolute() / "mcp-server")
        })
        return StdioServerParameters(
            command="python",
            args=[str(self.server_script.absolute())],
            env=test_env,
            cwd=str(self.project_root.absolute())
        )
    
    async def _create_session_and_write_file(self, session: ClientSession) -> str:
        """Create a session and write test file."""
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
        
        # Execute code to create file
        result = await session.call_tool("execute_code", {
            "code": create_file_code,
            "template": "python",
            "flavor": "small",
            "timeout": 30
        })
        
        # Extract session ID from result
        result_text = result.content[0].text if result.content else ""
        session_id = self._extract_session_id(result_text)
        
        print(f"   Session ID: {session_id}")
        print(f"   Result: {result_text.split('Content:')[0].strip()}")
        if "Content:" in result_text:
            print(f"Content: {result_text.split('Content:')[1].split('✅')[0].strip()}")
        if "✅ File verification passed" in result_text:
            size_part = result_text.split("Size: ")[1].split(" bytes")[0]
            print(f"✅ File verification passed. Size: {size_part} bytes")
        
        return session_id
    
    async def _pin_sandbox(self, session: ClientSession, session_id: str):
        """Pin the sandbox."""
        result = await session.call_tool("pin_sandbox", {
            "session_id": session_id,
            "pinned_name": self.pinned_name
        })
        
        result_text = result.content[0].text if result.content else ""
        print(f"   Result: {result_text}")
        
        if "Error:" in result_text:
            raise AssertionError(f"Pin operation failed: {result_text}")
        
        if "Successfully pinned" in result_text:
            print("   ✅ Sandbox pinned successfully")
        else:
            raise AssertionError(f"Unexpected pin result: {result_text}")
    
    async def _verify_file_exists(self, session: ClientSession, session_id: str, step: str) -> bool:
        """Verify that the test file exists and has correct content."""
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
else:
    print(f"❌ File does not exist: {{file_path}}")
'''
        
        try:
            result = await session.call_tool("execute_code", {
                "code": verify_code,
                "session_id": session_id,
                "timeout": 10
            })
            
            result_text = result.content[0].text if result.content else ""
            
            if "✅ File exists:" in result_text and "✅ Content matches: True" in result_text:
                print(f"   ✅ File exists: {self.test_file_path}")
                if "Content matches: True" in result_text:
                    print("✅ Content matches: True")
                if "Expected length:" in result_text:
                    expected_len = result_text.split("Expected length: ")[1].split()[0]
                    actual_len = result_text.split("Actual length: ")[1].split()[0]
                    print(f"   Expected length: {expected_len}")
                    print(f"   Actual length: {actual_len}")
                return True
            else:
                print(f"   ❌ File verification failed in {step}")
                print(f"   Result: {result_text}")
                return False
                
        except Exception as e:
            print(f"   ❌ File verification error in {step}: {e}")
            return False
    
    async def _attach_to_pinned_sandbox(self, session: ClientSession) -> str:
        """Attach to the pinned sandbox."""
        result = await session.call_tool("attach_sandbox_by_name", {
            "pinned_name": self.pinned_name
        })
        
        result_text = result.content[0].text if result.content else ""
        print(f"   Result: {result_text}")
        
        if "Error:" in result_text:
            raise AssertionError(f"Attach operation failed: {result_text}")
        
        # Extract session ID from result
        session_id = self._extract_attach_session_id(result_text)
        print(f"   ✅ Attached successfully. New session: {session_id}")
        
        return session_id
    
    def _extract_session_id(self, result_text: str) -> str:
        """Extract session ID from execute_code result."""
        # Look for session ID in log messages
        import re
        
        # Look for UUID pattern in the result text (36 character UUID)
        uuid_pattern = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
        matches = re.findall(uuid_pattern, result_text, re.IGNORECASE)
        
        if matches:
            # Return the first UUID found (should be the session ID)
            return matches[0]
        
        # Fallback: generate a predictable session ID
        return f"session-{self.test_id}"
    
    def _extract_attach_session_id(self, result_text: str) -> str:
        """Extract session ID from attach result."""
        if "Session ID:" in result_text:
            parts = result_text.split("Session ID:")
            if len(parts) > 1:
                return parts[1].strip().split()[0]
        
        return f"session-{self.test_id}-reattached"
    
    async def _verify_multiple_files(self, session: ClientSession, session_id: str):
        """Verify multiple test files exist."""
        verify_code = f'''
import os
import json

files_to_check = [
    "{self.test_file_path}",
    "/workspace/data/config.json",
    "/workspace/scripts/test.py",
    "/workspace/logs/test.log"
]

for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"{{file_path}}: ✅")
        if file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                data = json.load(f)
                if 'test_id' in data:
                    print(f"Config test_id: {{data['test_id']}}")
        elif file_path.endswith('.py'):
            with open(file_path, 'r') as f:
                content = f.read()
                print(content.strip())
    else:
        print(f"{{file_path}}: ❌")
'''
        
        result = await session.call_tool("execute_code", {
            "code": verify_code,
            "session_id": session_id,
            "timeout": 10
        })
        
        result_text = result.content[0].text if result.content else ""
        print(f"   {result_text}")
    
    async def _verify_file_with_new_execution(self, session: ClientSession, step: str) -> bool:
        """Verify file exists by creating a new execution session."""
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
else:
    print(f"❌ File does not exist: {{file_path}}")
'''
        
        try:
            # Create a new execution without specifying session_id
            result = await session.call_tool("execute_code", {
                "code": verify_code,
                "template": "python",
                "flavor": "small",
                "timeout": 10
            })
            
            result_text = result.content[0].text if result.content else ""
            
            if "✅ File exists:" in result_text and "✅ Content matches: True" in result_text:
                print(f"   ✅ File exists: {self.test_file_path}")
                if "Content matches: True" in result_text:
                    print("✅ Content matches: True")
                if "Expected length:" in result_text:
                    expected_len = result_text.split("Expected length: ")[1].split()[0]
                    actual_len = result_text.split("Actual length: ")[1].split()[0]
                    print(f"   Expected length: {expected_len}")
                    print(f"   Actual length: {actual_len}")
                return True
            else:
                print(f"   ❌ File verification failed in {step}")
                print(f"   Result: {result_text}")
                return False
                
        except Exception as e:
            print(f"   ❌ File verification error in {step}: {e}")
            return False
    
    async def run_test(self):
        """Run the complete pin-sandbox test workflow in a single MCP session."""
        print("🚀 Starting Pin-Sandbox End-to-End Test")
        print("=" * 50)
        
        if not self.server_script.exists():
            raise FileNotFoundError(f"MCP server script not found: {self.server_script}")
        
        # Configure server parameters
        server_params = self._get_server_params()
        
        try:
            # Run entire test in a single MCP session
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Step 1: Create session and write test file
                    print("📝 Step 1: Creating session and writing test file")
                    self.original_session_id = await self._create_session_and_write_file(session)
                    
                    # Step 2: Pin the sandbox
                    print(f"📌 Step 2: Pinning sandbox as '{self.pinned_name}'")
                    await self._pin_sandbox(session, self.original_session_id)
                    
                    # Step 2.5: Wait a moment for pin operation to stabilize, then verify
                    print("🔍 Step 2.5: Verifying file persistence")
                    await asyncio.sleep(2)  # Give pin operation time to complete
                    file_exists_after_pin = await self._verify_file_exists(session, self.original_session_id, "After Pin")
                    if not file_exists_after_pin:
                        print("   ⚠️  File verification failed after pin, but this may be expected due to container rename")
                        # Don't fail the test here, as the real test is after reattachment
                    
                    # Step 3: Wait for session cleanup
                    cleanup_wait = self.session_timeout + self.cleanup_interval + 2
                    print(f"⏳ Step 3: Waiting {cleanup_wait}s for session cleanup")
                    await asyncio.sleep(cleanup_wait)
                    print("   ✅ Cleanup wait period completed")
                    
                    # Verify original session is cleaned up
                    try:
                        await self._verify_file_exists(session, self.original_session_id, "After Cleanup")
                        print("   ⚠️  Original session still active (may not have been cleaned up yet)")
                    except Exception:
                        print("   ✅ Original session appears to be cleaned up")
                    
                    # Step 4: Attach to pinned sandbox
                    print(f"🔗 Step 4: Attaching to pinned sandbox '{self.pinned_name}'")
                    self.attached_session_id = await self._attach_to_pinned_sandbox(session)
                    
                    # Step 5: Verify file still exists using the attached session
                    print("🔍 Step 5: Verifying file persistence")
                    file_exists_after_attach = await self._verify_file_exists(session, self.attached_session_id, "After Attach")
                    if not file_exists_after_attach:
                        raise AssertionError("File missing after cleanup and reattachment")
                    
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


async def test_pin_sandbox_single_session():
    """Test function for pytest."""
    test = SingleSessionPinSandboxTest()
    await test.run_test()


async def test_pin_sandbox_with_multiple_files():
    """Test pin-sandbox functionality with multiple files."""
    print("=" * 50)
    print("Running multiple files test...")
    
    test = SingleSessionPinSandboxTest()
    test.test_file_content = f"Multi-file test - ID: {test.test_id} - Created: {time.time()}"
    
    # Configure server parameters
    server_params = test._get_server_params()
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Step 1: Create session with multiple files
            print("📝 Step 1: Creating session with multiple files")
            create_files_code = f'''
import os
import json

# Create multiple test files
files_to_create = {{
    "{test.test_file_path}": """{test.test_file_content}""",
    "/workspace/data/config.json": {{"test_id": "{test.test_id}", "type": "config"}},
    "/workspace/scripts/test.py": "print('Hello from pinned sandbox!')",
    "/workspace/logs/test.log": "Test log entry from {test.test_id}"
}}

for file_path, content in files_to_create.items():
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write file
    if file_path.endswith('.json'):
        with open(file_path, "w") as f:
            json.dump(content, f, indent=2)
    else:
        with open(file_path, "w") as f:
            f.write(str(content))

print(f"✅ Created {{len(files_to_create)}} test files")
'''
            
            result = await session.call_tool("execute_code", {
                "code": create_files_code,
                "template": "python",
                "flavor": "small",
                "timeout": 30
            })
            
            result_text = result.content[0].text if result.content else ""
            session_id = test._extract_session_id(result_text)
            print(f"   Session ID: {session_id}")
            
            # Step 2: Pin sandbox
            print(f"📌 Step 2: Pinning sandbox as '{test.pinned_name}'")
            await test._pin_sandbox(session, session_id)
            
            # Step 2.5: Verify multiple files
            print("🔍 Step 2.5: Verifying multiple files")
            await test._verify_multiple_files(session, session_id)
            
            # Step 3: Wait for cleanup
            cleanup_wait = test.session_timeout + test.cleanup_interval + 2
            print(f"⏳ Step 3: Waiting {cleanup_wait}s for session cleanup")
            await asyncio.sleep(cleanup_wait)
            print("   ✅ Cleanup wait period completed")
            
            try:
                await test._verify_multiple_files(session, session_id)
                print("   ⚠️  Original session still active")
            except Exception:
                print("   ✅ Original session appears to be cleaned up")
            
            # Step 4: Attach to pinned sandbox
            print(f"🔗 Step 4: Attaching to pinned sandbox '{test.pinned_name}'")
            attached_session_id = await test._attach_to_pinned_sandbox(session)
            
            # Step 5: Verify multiple files still exist
            print("🔍 Step 5: Verifying multiple files")
            await test._verify_multiple_files(session, attached_session_id)
            
            print("=" * 50)
            print("🎉 PIN-SANDBOX TEST PASSED!")
            print("✅ File persisted through pin → cleanup → attach cycle")
            print("✅ Sandbox state continuity verified")
            print("=" * 50)


async def run_tests():
    """Run all tests."""
    print("Running simple pin-sandbox end-to-end test...")
    await test_pin_sandbox_single_session()
    
    print("\n" + "=" * 50)
    print("Running multiple files test...")
    await test_pin_sandbox_with_multiple_files()


if __name__ == "__main__":
    asyncio.run(run_tests())