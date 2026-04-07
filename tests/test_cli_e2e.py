import pytest
import subprocess
import logging
import re
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

# Constants
SERVER_PORT = os.getenv("MCP_SERVER_PORT", "8776") 
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
PIN_NAME = "my-cli-pinned-sandbox"
HELLO_CONTENT = "hello CLI pinned sandbox"
HELLO_FILE = "/hello_cli.txt"
SHARED_PATH = "/shared"
EXPECTED_SHARED_FILE = "data.txt"

# ANSI Colors for formatting
class Style:
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    PASS_BADGE = '\033[48;2;50;205;50m'
    PASS_EMOJI = '✅'

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
    logging.info(f"{Style.BOLD}✔ Step {step_num}: {message:<40} {Style.PASS_BADGE} PASSED {Style.ENDC} {Style.PASS_EMOJI}")

def log_info(message):
    """Log general info."""
    logging.info(f"  {Style.BLUE}ℹ {message}{Style.ENDC}")

async def run_cli_cmd(command_args):
    """Run an lsb-cli command and return stdout/stderr via asyncio subprocess."""
    import shutil
    import sys
    lsb_cli_path = shutil.which("lsb-cli") or os.path.expanduser("~/.local/bin/lsb-cli")
    cmd = [lsb_cli_path, "-server", SERVER_URL] + command_args
    import asyncio
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    class Result:
        pass
    res = Result()
    res.returncode = process.returncode
    res.stdout = stdout.decode()
    res.stderr = stderr.decode()
    return res

def extract_session_id(output):
    """Extract Session ID from CLI metadata block."""
    match = re.search(r"Session ID:\s*([a-zA-Z0-9\-]+)", output)
    if match and match.group(1) != "None":
        return match.group(1).strip()
    return None

# Main Test Workflow

@pytest.mark.asyncio
async def test_cli_e2e_workflow():
    """Verify the complete E2E workflow using the lsb-cli tool."""
    log_header("STARTING CLI E2E WORKFLOW TEST")
    
    session_id = None
    attached_session_id = None

    try:
        # 1. Hello World
        log_step_start(1, "Python Hello World Execution")
        code = 'print("Hello, CLI!")'
        res = await run_cli_cmd(["exec-code", "-c", code])
        assert res.returncode == 0, f"Command failed: {res.stderr}"
        assert "Hello, CLI!" in res.stdout
        session_id = extract_session_id(res.stdout)
        assert session_id, "Session ID not found in execution result"
        log_success(1, f"Python Hello World Execution (Session: {session_id})")

        # 2. Shared Volume Verification
        log_step_start(2, "Shared Volume Access Verification")
        res = await run_cli_cmd(["exec-cmd", "-c", f"ls {SHARED_PATH}", "-s", session_id])
        assert res.returncode == 0
        assert EXPECTED_SHARED_FILE in res.stdout
        log_success(2, "Shared Volume Access Verification")

        # 3. Create Persistence File
        log_step_start(3, "File Creation and Persistence")
        code = f"with open('{HELLO_FILE}', 'w') as f: f.write('{HELLO_CONTENT}')"
        res = await run_cli_cmd(["exec-code", "-c", code, "-s", session_id])
        assert res.returncode == 0
        log_success(3, "File Creation and Persistence")

        # 4. Pin Sandbox
        log_step_start(4, "Sandbox Pinning")
        res = await run_cli_cmd(["pin", session_id, PIN_NAME])
        assert res.returncode == 0
        assert "Successfully pinned sandbox" in res.stdout
        log_success(4, "Sandbox Pinning")

        # 5. Verify Pinned File (in original session)
        log_step_start(5, "File Content Verification")
        res = await run_cli_cmd(["exec-cmd", "-c", f"cat {HELLO_FILE}", "-s", session_id])
        assert res.returncode == 0
        assert HELLO_CONTENT in res.stdout
        log_success(5, "File Content Verification")

        # 6. Stop Original Session
        log_step_start(6, "Stop Session")
        res = await run_cli_cmd(["stop", session_id])
        assert res.returncode == 0
        assert f"stopped successfully" in res.stdout
        log_success(6, "Session Stop")

        # 7. Re-attach to Pinned Sandbox
        log_step_start(7, "Re-attachment to Pinned Sandbox")
        res = await run_cli_cmd(["attach", PIN_NAME])
        assert res.returncode == 0
        attached_session_id = extract_session_id(res.stdout)
        assert attached_session_id, "Could not extract new session ID from attach"
        log_success(7, f"Re-attachment (Session ID: {attached_session_id})")

        # 8. Verify File in Re-attached Sandbox
        log_step_start(8, "File Content Verification")
        res = await run_cli_cmd(["exec-cmd", "-c", f"cat {HELLO_FILE}", "-s", attached_session_id])
        assert res.returncode == 0
        assert HELLO_CONTENT in res.stdout
        log_success(8, "File Content Verification")

        # 9. Verify Shared Volume in Re-attached Sandbox
        log_step_start(9, "Shared Volume Access Verification")
        res = await run_cli_cmd(["exec-cmd", "-c", f"ls {SHARED_PATH}", "-s", attached_session_id])
        assert res.returncode == 0
        assert EXPECTED_SHARED_FILE in res.stdout
        log_success(9, "Shared Volume Access Verification")
        
        log_header("CLI E2E WORKFLOW TEST COMPLETED SUCCESSFULLY")

    finally:
        log_header("STARTING CLEANUP")
        
        # Cleanup: Stop attached session
        if attached_session_id:
            log_info(f"Stopping attached session {attached_session_id}...")
            await run_cli_cmd(["stop", attached_session_id])
        
        # Cleanup: Ensure original session is stopped
        if session_id:
            try:
                await run_cli_cmd(["stop", session_id])
            except Exception:
                pass # Ignore if already stopped

        # Cleanup: Force remove pinned sandbox directly via internal module to bypass CLI
        try:
            log_info("Force removing pinned sandbox via BaseSandbox...")
            from sandbox import BaseSandbox
            await BaseSandbox.force_remove_by_name(PIN_NAME, config_path=".env.test")
            log_info("Cleanup complete.")
        except Exception as e:
            logging.warning(f"Cleanup removal failed: {e}")

@pytest.mark.asyncio
async def test_cli_execute_command_creates_session():
    """Verify that calling execute-cmd without a session creates a new session."""
    log_header("TEST: CLI EXECUTE COMMAND NO-SESSION")
    
    new_session_id = None
    try:
        log_info("Calling exec-cmd without session...")
        res = await run_cli_cmd(["exec-cmd", "-c", "echo 'hello CLI world'"])
        
        assert res.returncode == 0, f"Command failed: {res.stderr}"
        assert "hello CLI world" in res.stdout

        new_session_id = extract_session_id(res.stdout)
        assert new_session_id, f"Could not find session ID in result: {res.stdout}"
        
        log_success("Auto-Session", f"Created Session: {new_session_id}")
    finally:
        if new_session_id:
            await run_cli_cmd(["stop", new_session_id])

@pytest.mark.asyncio
async def test_cli_parameter_validation():
    """Verify validation refutation directly parsing command line args."""
    log_header("TEST: CLI PARAMETER VALIDATION")
    
    try:
        log_info("Testing with incorrect fields (invalid flag)...")
        res = await run_cli_cmd(["exec-code", "-c", "print('hi')", "--invalid-flag"])
        
        assert res.returncode != 0
        assert "invalid-flag" in res.stderr or "flag provided but not defined" in res.stderr or "invalid-flag" in res.stdout or "flag provided but not defined" in res.stdout
    except Exception as e:
        pytest.fail(f"Unexpected error: {e}")
