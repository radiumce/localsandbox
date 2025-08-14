"""
Configuration and utilities for pin-sandbox end-to-end testing.

This module provides configuration management and utility functions
for running pin-sandbox tests with proper environment setup.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import json


class PinSandboxTestConfig:
    """Configuration for pin-sandbox end-to-end tests."""
    
    # Test timing configuration
    SESSION_TIMEOUT = 5  # Very short timeout to trigger cleanup quickly
    CLEANUP_INTERVAL = 2  # Frequent cleanup checks
    TEST_TIMEOUT = 300  # 5 minutes total test timeout
    
    # MCP server configuration
    MAX_CONCURRENT_SESSIONS = 10
    DEFAULT_EXECUTION_TIMEOUT = 30
    SANDBOX_START_TIMEOUT = 60
    
    # Test data configuration
    TEST_FILE_CONTENT = "Pin-sandbox persistence test file"
    TEST_FILE_PATH = "/workspace/test_persistence.txt"
    
    @classmethod
    def get_test_environment(cls) -> Dict[str, str]:
        """Get environment variables for testing with aggressive cleanup."""
        base_env = os.environ.copy()
        
        test_env = {
            'SESSION_TIMEOUT': str(cls.SESSION_TIMEOUT),
            'CLEANUP_INTERVAL': str(cls.CLEANUP_INTERVAL),
            'MAX_CONCURRENT_SESSIONS': str(cls.MAX_CONCURRENT_SESSIONS),
            'DEFAULT_EXECUTION_TIMEOUT': str(cls.DEFAULT_EXECUTION_TIMEOUT),
            'SANDBOX_START_TIMEOUT': str(cls.SANDBOX_START_TIMEOUT),
            # Ensure Docker is available for testing
            'DOCKER_HOST': base_env.get('DOCKER_HOST', 'unix:///var/run/docker.sock'),
            # Enable debug logging for troubleshooting
            'LOG_LEVEL': 'DEBUG',
            'MCP_LOG_LEVEL': 'DEBUG'
        }
        
        # Merge with existing environment
        base_env.update(test_env)
        return base_env
    
    @classmethod
    def create_test_server_config(cls) -> Path:
        """Create a temporary server configuration file for testing."""
        config = {
            "session_timeout": cls.SESSION_TIMEOUT,
            "cleanup_interval": cls.CLEANUP_INTERVAL,
            "max_concurrent_sessions": cls.MAX_CONCURRENT_SESSIONS,
            "default_execution_timeout": cls.DEFAULT_EXECUTION_TIMEOUT,
            "sandbox_start_timeout": cls.SANDBOX_START_TIMEOUT,
            "shared_volume_mappings": [],
            "enable_debug_logging": True
        }
        
        # Create temporary config file
        temp_dir = Path(tempfile.gettempdir())
        config_file = temp_dir / f"mcp_test_config_{os.getpid()}.json"
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_file


class TestFileManager:
    """Manages test files and verification for pin-sandbox tests."""
    
    def __init__(self, test_id: str):
        self.test_id = test_id
        self.test_files = {}
    
    def generate_test_files_code(self) -> str:
        """Generate Python code to create test files in sandbox."""
        return f'''
import os
import json
import pickle
from datetime import datetime

# Test ID for this run
TEST_ID = "{self.test_id}"

# Create test directory structure
directories = [
    '/workspace/test_data',
    '/workspace/project/src',
    '/workspace/logs'
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {{directory}}")

# Create main test file
test_content = "Pin-sandbox persistence test - ID: {{TEST_ID}} - Created: {{datetime.now().isoformat()}}"
with open('/workspace/test_persistence.txt', 'w') as f:
    f.write(test_content)

# Create JSON configuration file
config_data = {{
    'test_id': TEST_ID,
    'created_at': datetime.now().isoformat(),
    'test_type': 'pin_sandbox_persistence',
    'files_created': [
        '/workspace/test_persistence.txt',
        '/workspace/test_data/config.json',
        '/workspace/project/src/main.py',
        '/workspace/logs/test.log'
    ]
}}

with open('/workspace/test_data/config.json', 'w') as f:
    json.dump(config_data, f, indent=2)

# Create a Python script
python_script = """
def test_function():
    return "This function survived the pin-sandbox cycle!"

if __name__ == '__main__':
    print(test_function())
"""

with open('/workspace/project/src/main.py', 'w') as f:
    f.write(python_script)

# Create log file
log_content = f"""[{{datetime.now().isoformat()}}] INFO: Test started - ID: {{TEST_ID}}
[{{datetime.now().isoformat()}}] INFO: Files created for persistence test
[{{datetime.now().isoformat()}}] INFO: Pin-sandbox test in progress
"""

with open('/workspace/logs/test.log', 'w') as f:
    f.write(log_content)

# Create binary data file
binary_data = {{
    'test_id': TEST_ID,
    'timestamp': datetime.now().timestamp(),
    'data': list(range(100))  # Some test data
}}

with open('/workspace/test_data/binary_data.pkl', 'wb') as f:
    pickle.dump(binary_data, f)

print("All test files created successfully!")
print(f"Test ID: {{TEST_ID}}")
print("Files created:")
for file_path in config_data['files_created']:
    print(f"  - {{file_path}}")
print("  - /workspace/test_data/binary_data.pkl")
'''
    
    def generate_verification_code(self) -> str:
        """Generate Python code to verify test files exist and have correct content."""
        return f'''
import os
import json
import pickle
from datetime import datetime

TEST_ID = "{self.test_id}"

def verify_file_persistence():
    """Verify that all test files exist and have correct content."""
    results = {{
        'test_id': TEST_ID,
        'verification_time': datetime.now().isoformat(),
        'files_checked': {{}},
        'content_verified': {{}},
        'all_files_exist': True,
        'content_matches': True
    }}
    
    # Files to check
    files_to_verify = [
        '/workspace/test_persistence.txt',
        '/workspace/test_data/config.json',
        '/workspace/project/src/main.py',
        '/workspace/logs/test.log',
        '/workspace/test_data/binary_data.pkl'
    ]
    
    for file_path in files_to_verify:
        exists = os.path.exists(file_path)
        results['files_checked'][file_path] = exists
        
        if not exists:
            results['all_files_exist'] = False
            continue
        
        # Verify content for specific files
        try:
            if file_path == '/workspace/test_persistence.txt':
                with open(file_path, 'r') as f:
                    content = f.read()
                    content_ok = TEST_ID in content and 'Pin-sandbox persistence test' in content
                    results['content_verified'][file_path] = content_ok
                    if not content_ok:
                        results['content_matches'] = False
            
            elif file_path == '/workspace/test_data/config.json':
                with open(file_path, 'r') as f:
                    config = json.load(f)
                    content_ok = config.get('test_id') == TEST_ID
                    results['content_verified'][file_path] = content_ok
                    if not content_ok:
                        results['content_matches'] = False
            
            elif file_path == '/workspace/project/src/main.py':
                with open(file_path, 'r') as f:
                    content = f.read()
                    content_ok = 'test_function' in content and 'survived the pin-sandbox cycle' in content
                    results['content_verified'][file_path] = content_ok
                    if not content_ok:
                        results['content_matches'] = False
            
            elif file_path == '/workspace/test_data/binary_data.pkl':
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                    content_ok = data.get('test_id') == TEST_ID and 'data' in data
                    results['content_verified'][file_path] = content_ok
                    if not content_ok:
                        results['content_matches'] = False
        
        except Exception as e:
            results['content_verified'][file_path] = False
            results['content_matches'] = False
            results[f'error_{{file_path}}'] = str(e)
    
    return results

# Run verification
verification_results = verify_file_persistence()
print(json.dumps(verification_results, indent=2))

# Also run the test script to verify it works
if verification_results['files_checked'].get('/workspace/project/src/main.py', False):
    print("\\n=== Testing Python script execution ===")
    exec(open('/workspace/project/src/main.py').read())
'''


class MCPTestHelper:
    """Helper utilities for MCP testing."""
    
    @staticmethod
    def extract_session_id(result_text: str) -> Optional[str]:
        """Extract session ID from MCP tool result text."""
        if not result_text:
            return None
        
        lines = result_text.split('\n')
        for line in lines:
            # Look for pattern like "[Session: session-12345]"
            if '[Session:' in line:
                start = line.find('[Session:') + 9
                end = line.find(']', start)
                if start > 8 and end > start:
                    return line[start:end].strip()
            
            # Look for pattern like "Session ID: session-12345"
            elif 'Session ID:' in line:
                parts = line.split('Session ID:')
                if len(parts) > 1:
                    return parts[1].strip().split()[0]  # Take first word after "Session ID:"
        
        return None
    
    @staticmethod
    def parse_verification_results(result_text: str) -> Dict[str, Any]:
        """Parse verification results from MCP tool output."""
        try:
            # Look for JSON in the output
            lines = result_text.split('\n')
            json_start = -1
            json_end = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                elif json_start >= 0 and line.strip().endswith('}'):
                    json_end = i
                    break
            
            if json_start >= 0 and json_end >= 0:
                json_text = '\n'.join(lines[json_start:json_end + 1])
                return json.loads(json_text)
        
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Warning: Could not parse verification results: {e}")
            print(f"Raw output: {result_text}")
        
        return {}
    
    @staticmethod
    def validate_pin_result(result_text: str) -> bool:
        """Validate that pin operation was successful."""
        return "Successfully pinned session" in result_text
    
    @staticmethod
    def validate_attach_result(result_text: str) -> bool:
        """Validate that attach operation was successful."""
        return "Successfully attached" in result_text
    
    @staticmethod
    def extract_attach_session_id(result_text: str) -> Optional[str]:
        """Extract session ID from attach operation result."""
        # Look for pattern like "Session ID: session-12345"
        if "Session ID:" in result_text:
            parts = result_text.split("Session ID:")
            if len(parts) > 1:
                return parts[1].strip().split()[0]
        
        return None