import pytest
import logging
import uuid
import re
import os
from sandbox import BaseSandbox
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Configure logging
# Using a custom formatter could also work, but direct string formatting is simpler for specific headers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

# Constants
SERVER_PORT = os.getenv("MCP_SERVER_PORT", "8776") 
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}/mcp"
PIN_NAME = "my-pinned-sandbox"
HELLO_CONTENT = "hello pinned sandbox"
HELLO_FILE = "/hello.txt"
SHARED_PATH = "/shared"
EXPECTED_SHARED_FILE = "data.txt"

# ANSI Colors for formatting
class Style:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BOLD_GREEN = '\033[1;92m'

def log_header(text):
    """Log a major section header."""
    logging.info(f"\n{Style.HEADER}{Style.BOLD}{'='*10} {text} {'='*10}{Style.ENDC}")

def log_step_start(step_num, title):
    """Log the start of a test step."""
    logging.info("") # Empty line for spacing
    logging.info(f"{Style.CYAN}{Style.BOLD}▶ STEP {step_num}: {title.upper()}{Style.ENDC}")
    logging.info(f"{Style.CYAN}{'-'*60}{Style.ENDC}")

def log_success(step_num, message):
    """Log a successful step."""
    # Using fixed width for alignment if possible, but simple bold green is key
    logging.info(f"{Style.BOLD}✔ Step {step_num}: {message:<40} {Style.BOLD_GREEN}PASSED{Style.ENDC}")

def log_info(message):
    """Log general info."""
    logging.info(f"  {Style.BLUE}ℹ {message}{Style.ENDC}")

# Helper Functions

async def execute_tool(session, tool_name, arguments):
    """Execute a tool and return the structured result string."""
    result = await session.call_tool(tool_name, arguments=arguments)
    assert not result.isError, f"Tool {tool_name} execution failed: {result.content[0].text if result.isError else ''}"
    assert result.structuredContent is not None, "Tool did not return structured content."
    assert 'result' in result.structuredContent, "Expected 'result' in structured result"
    return result.structuredContent['result']

async def verify_python_execution(session, session_id):
    """Step 1: Verify basic Python code execution."""
    log_step_start(1, "Python Hello World Execution")
    code = 'print("Hello, World!")'
    result = await execute_tool(session, 'execute_code', {'code': code, 'session_id': session_id})
    assert "Hello, World!" in result
    assert "[success: True]" in result
    log_success(1, "Python Hello World Execution")

async def verify_shared_volume(session, session_id, step_num=2):
    """Verify access to the shared volume."""
    log_step_start(step_num, "Shared Volume Access Verification")
    result = await execute_tool(session, 'execute_command', {'command': f"ls {SHARED_PATH}", 'session_id': session_id})
    assert EXPECTED_SHARED_FILE in result
    assert "[success: True]" in result
    log_success(step_num, "Shared Volume Access Verification")

async def create_persistence_file(session, session_id):
    """Step 3: Create a file to test persistence."""
    log_step_start(3, "File Creation and Persistence")
    code = f"with open('{HELLO_FILE}', 'w') as f: f.write('{HELLO_CONTENT}')"
    await execute_tool(session, 'execute_code', {'code': code, 'session_id': session_id})
    log_success(3, "File Creation and Persistence")

async def pin_sandbox_session(session, session_id):
    """Step 4: Pin the current sandbox."""
    log_step_start(4, "Sandbox Pinning")
    result = await execute_tool(session, 'pin_sandbox', {'pinned_name': PIN_NAME, 'session_id': session_id})
    assert PIN_NAME in result
    log_success(4, "Sandbox Pinning")

async def verify_file_content(session, session_id, step_num=5):
    """Verify that the persistence file exists and has correct content."""
    log_step_start(step_num, "File Content Verification")
    result = await execute_tool(session, 'execute_command', {'command': f"cat {HELLO_FILE}", 'session_id': session_id})
    assert HELLO_CONTENT in result
    log_success(step_num, "File Content Verification")

async def stop_session(session, session_id, step_num=6, is_cleanup=False):
    """Stop the session."""
    if not is_cleanup:
        log_step_start(step_num, "Stop Session")
    
    try:
        result = await execute_tool(session, 'stop_session', {'session_id': session_id})
        assert f"Session {session_id} stopped successfully" in result
        if not is_cleanup:
            log_success(step_num, "Session Stop")
        else:
            logging.info(f"  {Style.BLUE}Cleanup: Session stopped.{Style.ENDC}")
    except Exception as e:
        if not is_cleanup:
            raise e
        logging.warning(f"  {Style.YELLOW}Cleanup Warning: Failed to stop session {session_id}: {e}{Style.ENDC}")

async def attach_pinned_sandbox(session):
    """Step 7: Attach to the pinned sandbox."""
    log_step_start(7, "Re-attachment to Pinned Sandbox")
    result = await execute_tool(session, 'attach_sandbox_by_name', {'pinned_name': PIN_NAME})
    assert f"Successfully attached to pinned sandbox '{PIN_NAME}'" in result
    
    match = re.search(r"Session ID: (\S+)", result)
    assert match, "Could not find session ID in re-attach result"
    new_session_id = match.group(1)
    
    log_success(7, f"Re-attachment (Session ID: {new_session_id})")
    return new_session_id

# Main Test Workflow

@pytest.mark.asyncio
async def test_e2e_workflow():
    """Verify the complete E2E workflow using modular helper functions."""
    log_header("STARTING E2E WORKFLOW TEST")
    
    async with streamablehttp_client(SERVER_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # Start with a fresh session ID
            session_id = str(uuid.uuid4())
            log_info(f"Initialized with Session ID: {session_id}")

            attached_session_id = None

            try:
                # 1. Hello World
                await verify_python_execution(session, session_id)

                # 2. Shared Volume Verification
                await verify_shared_volume(session, session_id, step_num=2)

                # 3. Create Persistence File
                await create_persistence_file(session, session_id)

                # 4. Pin Sandbox
                await pin_sandbox_session(session, session_id)

                # 5. Verify Pinned File (in original session)
                await verify_file_content(session, session_id, step_num=5)

                # 6. Stop Original Session
                await stop_session(session, session_id, step_num=6)

                # 7. Re-attach to Pinned Sandbox
                attached_session_id = await attach_pinned_sandbox(session)

                # 8. Verify File in Re-attached Sandbox
                await verify_file_content(session, attached_session_id, step_num=8)

                # 9. Verify Shared Volume in Re-attached Sandbox
                await verify_shared_volume(session, attached_session_id, step_num=9)
                
                log_header("E2E WORKFLOW TEST COMPLETED SUCCESSFULLY")

            finally:
                log_header("STARTING CLEANUP")
                
                # Cleanup: Stop attached session
                if attached_session_id:
                     await stop_session(session, attached_session_id, is_cleanup=True)
                
                # Cleanup: Ensure original session is stopped
                if session_id:
                    try:
                        await session.call_tool('stop_session', arguments={'session_id': session_id})
                    except Exception:
                        pass # Ignore if already stopped

                # Cleanup: Force remove pinned sandbox
                try:
                    log_info("Force removing pinned sandbox...")
                    await BaseSandbox.force_remove_by_name(PIN_NAME, config_path=".env.test")
                    log_info("Cleanup complete.")
                except Exception as e:
                    logging.warning(f"Cleanup removal failed: {e}")

@pytest.mark.asyncio
async def test_execute_command_creates_session():
    """Verify that calling execute_command without a session_id creates a new session."""
    log_header("TEST: EXECUTE COMMAND NO-SESSION")
    
    async with streamablehttp_client(SERVER_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            new_session_id = None
            try:
                log_info("Calling execute_command without session_id...")
                result = await execute_tool(session, 'execute_command', {'command': "echo 'hello world'"})
                
                assert "hello world" in result
                assert "[success: True]" in result

                # Extract session_id
                match = re.search(r"\[session_id: (\S+)\]", result)
                assert match, f"Could not find session ID in result: {result}"
                new_session_id = match.group(1)
                
                log_success("Auto-Session", f"Created Session: {new_session_id}")
            finally:
                if new_session_id:
                    await stop_session(session, new_session_id, is_cleanup=True)

@pytest.mark.asyncio
async def test_parameter_validation_incorrect_session_field():
    """Verify validation refutation."""
    log_header("TEST: PARAMETER VALIDATION (FIELD NAME)")
    async with streamablehttp_client(SERVER_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            log_info("Testing with incorrect 'session' field...")
            try:
                result = await session.call_tool(
                    'execute_code', 
                    arguments={'code': 'print("hi")', 'session': 'invalid'}
                )
                assert result.isError, "Expected tool execution to fail"
                error_text = result.content[0].text if result.content else ""
                assert "Extra inputs are not permitted" in error_text
                log_success("Validation", "Correctly rejected 'session' field")
            except Exception as e:
                 assert "Extra inputs are not permitted" in str(e)
                 log_success("Validation", "Correctly raised exception for 'session'")

@pytest.mark.asyncio
async def test_parameter_validation_multiple_incorrect_fields():
    """Verify validation refutation."""
    log_header("TEST: PARAMETER VALIDATION (MULTIPLE)")
    async with streamablehttp_client(SERVER_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            log_info("Testing with multiple incorrect fields...")
            try:
                result = await session.call_tool(
                    'execute_command',
                    arguments={'command': 'echo', 'session': 'bad', 'time_out': 30}
                )
                assert result.isError
                assert "Extra inputs are not permitted" in result.content[0].text
                log_success("Validation", "Correctly rejected multiple fields")
            except Exception as e:
                assert "Extra inputs are not permitted" in str(e)
                log_success("Validation", "Correctly raised exception for mulitple fields")