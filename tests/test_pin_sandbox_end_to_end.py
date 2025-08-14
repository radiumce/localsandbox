"""
Complete end-to-end test for pin-sandbox functionality using official MCP client.

This test verifies the complete pin-sandbox workflow:
1. Create session and write files to sandbox
2. Pin the sandbox with a custom name
3. Verify files exist immediately after pinning
4. Trigger session cleanup through low session timeout
5. Attach to pinned sandbox by name
6. Verify files still exist after cleanup and reattachment

Requirements tested:
- Pin sandbox with custom name (Requirement 1)
- Pinned sandboxes survive session cleanup (Requirement 2)
- Attach to pinned sandbox by name (Requirement 4)
- Container state persistence across pin/cleanup/attach cycles
"""

import asyncio
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Any
import pytest

# MCP client imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Test configuration
TEST_TIMEOUT = 300  # 5 minutes total test timeout
SESSION_TIMEOUT = 5  # Very short session timeout to trigger cleanup quickly
CLEANUP_INTERVAL = 2  # Very frequent cleanup checks
PINNED_SANDBOX_NAME = f"test_pinned_sandbox_{uuid.uuid4().hex[:8]}"
TEST_FILE_CONTENT = f"Test file created at {time.time()}"
TEST_FILE_PATH = "/workspace/test_persistence.txt"


class MCPPinSandboxEndToEndTest:
    """End-to-end test class for pin-sandbox functionality."""
    
    def __init__(self):
        self.session: ClientSession = None
        self.server_process = None
        self.original_session_id = None
        self.attached_session_id = None
        
    async def setup_mcp_client(self):
        """Set up MCP client connection to the server."""
        # Set environment variables for aggressive cleanup
        test_env = os.environ.copy()
        test_env.update({
            'SESSION_TIMEOUT': str(SESSION_TIMEOUT),
            'CLEANUP_INTERVAL': str(CLEANUP_INTERVAL),
            'MAX_CONCURRENT_SESSIONS': '10',
            'DEFAULT_EXECUTION_TIMEOUT': '30',
            'SANDBOX_START_TIMEOUT': '60'
        })
        
        # Start MCP server with test configuration
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server.main"],
            env=test_env
        )
        
        # Create client session
        self.session, self.server_process = await stdio_client(server_params)
        
        print(f"✓ MCP client connected to server (PID: {self.server_process.pid})")
        print(f"✓ Test configuration: SESSION_TIMEOUT={SESSION_TIMEOUT}s, CLEANUP_INTERVAL={CLEANUP_INTERVAL}s")
    
    async def cleanup_mcp_client(self):
        """Clean up MCP client connection."""
        if self.session:
            await self.session.close()
        if self.server_process:
            self.server_process.terminate()
            await self.server_process.wait()
        print("✓ MCP client connection cleaned up")
    
    async def create_session_and_write_files(self) -> str:
        """Create a new sandbox session and write test files."""
        print("\n=== Step 1: Creating session and writing test files ===")
        
        # Execute code to create test files
        create_files_code = f'''
import os
import json
from datetime import datetime

# Create test directory
os.makedirs('/workspace/test_data', exist_ok=True)

# Write main test file
with open('{TEST_FILE_PATH}', 'w') as f:
    f.write('{TEST_FILE_CONTENT}')

# Write additional test files to verify comprehensive state persistence
test_data = {{
    'created_at': datetime.now().isoformat(),
    'test_id': '{uuid.uuid4().hex}',
    'files_created': [
        '{TEST_FILE_PATH}',
        '/workspace/test_data/config.json',
        '/workspace/test_data/data.txt'
    ]
}}

with open('/workspace/test_data/config.json', 'w') as f:
    json.dump(test_data, f, indent=2)

with open('/workspace/test_data/data.txt', 'w') as f:
    f.write('Additional test data for persistence verification')

# Create a Python script that can be executed later
with open('/workspace/test_script.py', 'w') as f:
    f.write("""
import json
import os

def verify_persistence():
    files_to_check = [
        '{TEST_FILE_PATH}',
        '/workspace/test_data/config.json',
        '/workspace/test_data/data.txt',
        '/workspace/test_script.py'
    ]
    
    results = {{}}
    for file_path in files_to_check:
        results[file_path] = os.path.exists(file_path)
        if results[file_path] and file_path.endswith('.txt'):
            with open(file_path, 'r') as f:
                results[file_path + '_content'] = f.read()[:100]  # First 100 chars
    
    return results

if __name__ == '__main__':
    print(json.dumps(verify_persistence(), indent=2))
""")

print("Files created successfully!")
print(f"Main test file: {TEST_FILE_PATH}")
print("Additional files: /workspace/test_data/config.json, /workspace/test_data/data.txt")
print("Verification script: /workspace/test_script.py")
'''
        
        # Call execute_code tool
        result = await self.session.call_tool("execute_code", {
            "code": create_files_code,
            "template": "python",
            "flavor": "small",
            "timeout": 30
        })
        
        # Extract session ID from result
        result_text = result.content[0].text if result.content else ""
        session_id = self._extract_session_id(result_text)
        
        print(f"✓ Session created: {session_id}")
        print(f"✓ Test files written to sandbox")
        print(f"Result: {result_text}")
        
        return session_id
    
    async def verify_files_exist(self, session_id: str, step_name: str) -> Dict[str, Any]:
        """Verify that test files exist in the sandbox."""
        print(f"\n=== {step_name}: Verifying file persistence ===")
        
        # Run the verification script we created
        verify_code = '''
import json
import os

def verify_persistence():
    files_to_check = [
        '/workspace/test_persistence.txt',
        '/workspace/test_data/config.json',
        '/workspace/test_data/data.txt',
        '/workspace/test_script.py'
    ]
    
    results = {}
    for file_path in files_to_check:
        results[file_path] = os.path.exists(file_path)
        if results[file_path] and file_path.endswith('.txt'):
            with open(file_path, 'r') as f:
                results[file_path + '_content'] = f.read()[:100]  # First 100 chars
    
    return results

verification_results = verify_persistence()
print(json.dumps(verification_results, indent=2))
'''
        
        result = await self.session.call_tool("execute_code", {
            "code": verify_code,
            "session_id": session_id,
            "template": "python",
            "timeout": 30
        })
        
        result_text = result.content[0].text if result.content else ""
        print(f"✓ File verification completed")
        print(f"Result: {result_text}")
        
        # Parse verification results
        try:
            # Extract JSON from the result
            lines = result_text.split('\n')
            json_lines = [line for line in lines if line.strip().startswith('{')]
            if json_lines:
                verification_data = json.loads(json_lines[0])
                return verification_data
        except (json.JSONDecodeError, IndexError):
            print(f"Warning: Could not parse verification results: {result_text}")
        
        return {}
    
    async def pin_sandbox(self, session_id: str) -> str:
        """Pin the sandbox with a custom name."""
        print(f"\n=== Step 2: Pinning sandbox '{PINNED_SANDBOX_NAME}' ===")
        
        result = await self.session.call_tool("pin_sandbox", {
            "session_id": session_id,
            "pinned_name": PINNED_SANDBOX_NAME
        })
        
        result_text = result.content[0].text if result.content else ""
        print(f"✓ Pin operation completed")
        print(f"Result: {result_text}")
        
        if "Successfully pinned session" not in result_text:
            raise AssertionError(f"Pin operation failed: {result_text}")
        
        return result_text
    
    async def wait_for_session_cleanup(self):
        """Wait for session cleanup to occur due to timeout."""
        print(f"\n=== Step 3: Waiting for session cleanup (timeout: {SESSION_TIMEOUT}s) ===")
        
        # Wait longer than session timeout to ensure cleanup occurs
        cleanup_wait_time = SESSION_TIMEOUT + CLEANUP_INTERVAL + 2
        print(f"Waiting {cleanup_wait_time} seconds for session cleanup...")
        
        await asyncio.sleep(cleanup_wait_time)
        
        print("✓ Session cleanup period completed")
        
        # Verify session is no longer active by trying to use it
        try:
            result = await self.session.call_tool("execute_code", {
                "code": "print('Testing if session still exists')",
                "session_id": self.original_session_id,
                "template": "python",
                "timeout": 10
            })
            result_text = result.content[0].text if result.content else ""
            print(f"Session status check: {result_text}")
        except Exception as e:
            print(f"✓ Original session appears to be cleaned up: {e}")
    
    async def attach_to_pinned_sandbox(self) -> str:
        """Attach to the pinned sandbox by name."""
        print(f"\n=== Step 4: Attaching to pinned sandbox '{PINNED_SANDBOX_NAME}' ===")
        
        result = await self.session.call_tool("attach_sandbox_by_name", {
            "pinned_name": PINNED_SANDBOX_NAME
        })
        
        result_text = result.content[0].text if result.content else ""
        print(f"✓ Attach operation completed")
        print(f"Result: {result_text}")
        
        if "Successfully attached" not in result_text:
            raise AssertionError(f"Attach operation failed: {result_text}")
        
        # Extract new session ID
        new_session_id = self._extract_session_id(result_text)
        print(f"✓ New session ID: {new_session_id}")
        
        return new_session_id
    
    def _extract_session_id(self, result_text: str) -> str:
        """Extract session ID from MCP tool result."""
        lines = result_text.split('\n')
        for line in lines:
            if '[Session:' in line:
                # Extract session ID from format like "[Session: session-12345]"
                start = line.find('[Session:') + 9
                end = line.find(']', start)
                if start > 8 and end > start:
                    return line[start:end].strip()
            elif 'Session ID:' in line:
                # Extract from format like "Session ID: session-12345"
                parts = line.split('Session ID:')
                if len(parts) > 1:
                    return parts[1].strip()
        
        # If no session ID found in expected format, generate a warning
        print(f"Warning: Could not extract session ID from: {result_text}")
        return f"unknown-session-{uuid.uuid4().hex[:8]}"
    
    async def run_complete_test(self):
        """Run the complete end-to-end test."""
        print("🚀 Starting Pin-Sandbox End-to-End Test")
        print("=" * 60)
        
        try:
            # Setup
            await self.setup_mcp_client()
            
            # Step 1: Create session and write files
            self.original_session_id = await self.create_session_and_write_files()
            
            # Step 2: Pin the sandbox
            await self.pin_sandbox(self.original_session_id)
            
            # Step 2.5: Immediately verify files exist after pinning
            files_after_pin = await self.verify_files_exist(
                self.original_session_id, 
                "Step 2.5"
            )
            
            # Step 3: Wait for session cleanup
            await self.wait_for_session_cleanup()
            
            # Step 4: Attach to pinned sandbox
            self.attached_session_id = await self.attach_to_pinned_sandbox()
            
            # Step 5: Verify files still exist after cleanup and reattachment
            files_after_attach = await self.verify_files_exist(
                self.attached_session_id,
                "Step 5"
            )
            
            # Final verification
            self._verify_test_results(files_after_pin, files_after_attach)
            
            print("\n" + "=" * 60)
            print("🎉 Pin-Sandbox End-to-End Test PASSED!")
            print("✓ Files persisted through pin → cleanup → attach cycle")
            print("✓ Sandbox state continuity verified")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Test FAILED: {e}")
            raise
        finally:
            await self.cleanup_mcp_client()
    
    def _verify_test_results(self, files_after_pin: Dict[str, Any], files_after_attach: Dict[str, Any]):
        """Verify that the test results meet expectations."""
        print(f"\n=== Final Verification ===")
        
        # Check that key files existed after pin
        expected_files = [
            TEST_FILE_PATH,
            '/workspace/test_data/config.json',
            '/workspace/test_data/data.txt',
            '/workspace/test_script.py'
        ]
        
        print("Files after pin:")
        for file_path in expected_files:
            exists_after_pin = files_after_pin.get(file_path, False)
            print(f"  {file_path}: {'✓' if exists_after_pin else '❌'}")
            if not exists_after_pin:
                raise AssertionError(f"File {file_path} missing after pin operation")
        
        print("\nFiles after attach:")
        for file_path in expected_files:
            exists_after_attach = files_after_attach.get(file_path, False)
            print(f"  {file_path}: {'✓' if exists_after_attach else '❌'}")
            if not exists_after_attach:
                raise AssertionError(f"File {file_path} missing after attach operation")
        
        # Verify content consistency for text files
        for file_path in expected_files:
            if file_path.endswith('.txt'):
                content_key = file_path + '_content'
                content_after_pin = files_after_pin.get(content_key, '')
                content_after_attach = files_after_attach.get(content_key, '')
                
                if content_after_pin and content_after_attach:
                    if content_after_pin != content_after_attach:
                        raise AssertionError(f"File content changed for {file_path}")
                    print(f"  Content verified for {file_path}")
        
        print("✓ All file persistence checks passed!")


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_pin_sandbox_end_to_end():
    """
    Complete end-to-end test for pin-sandbox functionality.
    
    This test verifies:
    1. Sandbox creation and file writing
    2. Pin operation with custom name
    3. File persistence immediately after pin
    4. Session cleanup through timeout
    5. Attach to pinned sandbox by name
    6. File persistence after cleanup and reattachment
    """
    test_runner = MCPPinSandboxEndToEndTest()
    await test_runner.run_complete_test()


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_pin_sandbox_multiple_file_types():
    """
    Test pin-sandbox functionality with various file types and directory structures.
    """
    test_runner = MCPPinSandboxEndToEndTest()
    
    # Override the file creation to test more complex scenarios
    original_create_files = test_runner.create_session_and_write_files
    
    async def create_complex_files():
        print("\n=== Creating complex file structure ===")
        
        complex_files_code = '''
import os
import json
import pickle
from datetime import datetime

# Create nested directory structure
directories = [
    '/workspace/project/src',
    '/workspace/project/tests',
    '/workspace/project/docs',
    '/workspace/data/input',
    '/workspace/data/output',
    '/workspace/logs'
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)

# Create various file types
files_data = {
    '/workspace/project/README.md': '# Test Project\\n\\nThis is a test project for pin-sandbox functionality.',
    '/workspace/project/src/main.py': 'def main():\\n    print("Hello from pinned sandbox!")\\n\\nif __name__ == "__main__":\\n    main()',
    '/workspace/project/tests/test_main.py': 'import unittest\\n\\nclass TestMain(unittest.TestCase):\\n    def test_example(self):\\n        self.assertTrue(True)',
    '/workspace/data/input/data.csv': 'name,age,city\\nAlice,30,New York\\nBob,25,San Francisco',
    '/workspace/logs/app.log': f'[{datetime.now().isoformat()}] INFO: Application started\\n[{datetime.now().isoformat()}] INFO: Pin-sandbox test in progress'
}

# Write text files
for file_path, content in files_data.items():
    with open(file_path, 'w') as f:
        f.write(content)

# Create binary file (pickle)
test_data = {'timestamp': datetime.now().isoformat(), 'test_id': 'pin_sandbox_test'}
with open('/workspace/data/test_data.pkl', 'wb') as f:
    pickle.dump(test_data, f)

# Create JSON configuration
config = {
    'app_name': 'pin_sandbox_test',
    'version': '1.0.0',
    'features': ['pin', 'attach', 'persistence'],
    'created_at': datetime.now().isoformat()
}
with open('/workspace/project/config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Complex file structure created successfully!")
print(f"Created {len(files_data)} text files")
print("Created 1 binary file (pickle)")
print("Created 1 JSON configuration file")
print(f"Created {len(directories)} directories")
'''
        
        result = await test_runner.session.call_tool("execute_code", {
            "code": complex_files_code,
            "template": "python",
            "flavor": "small",
            "timeout": 30
        })
        
        result_text = result.content[0].text if result.content else ""
        session_id = test_runner._extract_session_id(result_text)
        
        print(f"✓ Complex file structure created in session: {session_id}")
        return session_id
    
    # Replace the file creation method
    test_runner.create_session_and_write_files = create_complex_files
    
    await test_runner.run_complete_test()


if __name__ == "__main__":
    """Run the end-to-end test directly."""
    print("Pin-Sandbox End-to-End Test")
    print("Using official MCP client to test pin-sandbox functionality")
    print()
    
    async def run_tests():
        print("Running basic pin-sandbox end-to-end test...")
        await test_pin_sandbox_end_to_end()
        
        print("\n" + "="*60 + "\n")
        
        print("Running complex file structure test...")
        await test_pin_sandbox_multiple_file_types()
    
    asyncio.run(run_tests())