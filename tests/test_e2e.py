import pytest
import logging
import uuid
import re
from python.sandbox import BaseSandbox

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

@pytest.mark.asyncio
async def test_e2e_workflow():
    """Verify the E2E workflow, including code execution and shared volume access."""
    async with streamablehttp_client("http://localhost:8775/mcp") as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            session_id = str(uuid.uuid4())
            logging.info(f"Using session_id: {session_id}")

            # Resources that may need cleanup
            pin_name = "my-pinned-sandbox"
            attached_session_id_again = None

            try:
                logging.info("Step 1: Starting Python Hello World Execution...")
                # Define the code to be executed
                code_to_execute = 'print("Hello, World!")'

                # Execute the tool
                result = await session.call_tool(
                    'execute_code',
                    arguments={'code': code_to_execute, 'session_id': session_id}
                )

                # Verify the output
                assert not result.isError, "Tool execution resulted in an error."

                # The tool returns a dictionary with a 'result' key containing the output string.
                structured_result = result.structuredContent
                assert structured_result is not None, "Tool did not return structured content."
                assert 'result' in structured_result, "Expected 'result' in structured result"
                result_string = structured_result['result']

                assert "Hello, World!" in result_string, f"Expected 'Hello, World!' in result string, but got {result_string}"
                assert "[success: True]" in result_string, f"Expected '[success: True]' in result string, but got {result_string}"
                logging.info("Step 1: Python Hello World Execution PASSED.")

                logging.info("Step 2: Starting Shared Volume Access Verification...")
                # Step 2: Verify shared volume access
                command_to_execute = "ls /shared"
                result_command = await session.call_tool(
                    'execute_command',
                    arguments={'command': command_to_execute, 'session_id': session_id}
                )

                # Verify the output
                assert not result_command.isError, "Tool execution resulted in an error."

                structured_result_command = result_command.structuredContent
                assert structured_result_command is not None, "Tool did not return structured content."
                assert 'result' in structured_result_command, "Expected 'result' in structured result"
                result_string_command = structured_result_command['result']

                assert "data.txt" in result_string_command, f"Expected 'data.txt' in result string, but got {result_string_command}"
                assert "[success: True]" in result_string_command, f"Expected '[success: True]' in result string, but got {result_string_command}"
                logging.info("Step 2: Shared Volume Access Verification PASSED.")

                logging.info("Step 3: Starting File Creation and Persistence...")
                # Step 3: Verify file creation and persistence
                hello_content = "hello pinned sandbox"
                create_hello_file_code = f"with open('/hello.txt', 'w') as f: f.write('{hello_content}')"
                await session.call_tool(
                    'execute_code',
                    arguments={'code': create_hello_file_code, 'session_id': session_id}
                )
                logging.info("Step 3: File Creation and Persistence PASSED.")

                # Step 4: Pin the sandbox
                logging.info("Step 4: Starting Sandbox Pinning...")
                result_pin = await session.call_tool(
                    'pin_sandbox',
                    arguments={'pinned_name': pin_name, 'session_id': session_id}
                )
                assert not result_pin.isError, f"Pin sandbox tool execution resulted in an error: {result_pin.content[0].text if result_pin.isError else ''}"

                structured_result_pin = result_pin.structuredContent
                assert structured_result_pin is not None, "Tool did not return structured content."
                assert 'result' in structured_result_pin, "Expected 'result' in structured result"
                assert pin_name in structured_result_pin['result'], f"Expected pin name in result, but got {structured_result_pin['result']}"
                logging.info("Step 4: Sandbox Pinning PASSED.")

                # Step 5: Verify the file in the pinned sandbox
                logging.info("Step 5: Starting Pinned Sandbox Usage Verification...")
                # Verify the file created in the original session still exists by checking its content
                read_file_command = "cat /hello.txt"
                result_read_file = await session.call_tool(
                    'execute_command',
                    arguments={'command': read_file_command, 'session_id': session_id}
                )
                assert not result_read_file.isError, "Read file in pinned sandbox tool execution resulted in an error."

                structured_result_read = result_read_file.structuredContent
                assert 'result' in structured_result_read
                result_string_read = structured_result_read['result']

                assert hello_content in result_string_read, f"Expected '{hello_content}' in pinned sandbox file, but got {result_string_read}"
                logging.info("Step 5: Pinned Sandbox Usage Verification PASSED.")

                # Step 6: Stop the session
                logging.info("Step 6: Stopping the session...")
                result_stop_session = await session.call_tool(
                    'stop_session',
                    arguments={'session_id': session_id}
                )
                assert not result_stop_session.isError, f"Stop session tool execution resulted in an error: {result_stop_session.content[0].text if result_stop_session.isError else ''}"

                structured_result_stop = result_stop_session.structuredContent
                assert 'result' in structured_result_stop, "Expected 'result' in structured result"
                assert f"Session {session_id} stopped successfully" in structured_result_stop['result']

                logging.info("Step 6: Session Stop Verification PASSED.")

                # Step 7: Re-attach to the pinned sandbox
                logging.info("Step 7: Starting Re-attachment to Pinned Sandbox...")
                result_attach_again = await session.call_tool(
                    'attach_sandbox_by_name',
                    arguments={'pinned_name': pin_name}
                )
                assert not result_attach_again.isError, f"Re-attach sandbox tool execution resulted in an error: {result_attach_again.content[0].text if result_attach_again.isError else ''}"

                structured_result_attach_again = result_attach_again.structuredContent
                assert 'result' in structured_result_attach_again, "Expected 'result' in structured result"
                attach_result_text_again = structured_result_attach_again['result']
                assert f"Successfully attached to pinned sandbox '{pin_name}'" in attach_result_text_again

                match_again = re.search(r"Session ID: (\S+)", attach_result_text_again)
                assert match_again, "Could not find session ID in re-attach result"
                attached_session_id_again = match_again.group(1)
                logging.info(f"Step 7: Re-attachment to Pinned Sandbox PASSED. New session ID: {attached_session_id_again}")

                # Step 8: Verify file content in the re-attached sandbox
                logging.info("Step 8: Starting File Content Verification in Re-attached Sandbox...")
                read_file_command_again = "cat /hello.txt"
                result_read_file_again = await session.call_tool(
                    'execute_command',
                    arguments={'command': read_file_command_again, 'session_id': attached_session_id_again}
                )
                assert not result_read_file_again.isError, "Read file in re-attached sandbox tool execution resulted in an error."

                structured_result_read_again = result_read_file_again.structuredContent
                assert 'result' in structured_result_read_again
                result_string_read_again = structured_result_read_again['result']
                assert hello_content in result_string_read_again, f"Expected '{hello_content}' in re-attached sandbox file, but got {result_string_read_again}"
                logging.info("Step 8: File Content Verification in Re-attached Sandbox PASSED.")

                # Step 9: Verify shared volume access in the re-attached sandbox
                logging.info("Step 9: Starting Shared Volume Access Verification in Re-attached Sandbox...")
                list_files_command_again = "ls /shared"
                result_list_files_again = await session.call_tool(
                    'execute_command',
                    arguments={'command': list_files_command_again, 'session_id': attached_session_id_again}
                )
                assert not result_list_files_again.isError, "List files in re-attached sandbox tool execution resulted in an error."

                structured_result_list_again = result_list_files_again.structuredContent
                assert 'result' in structured_result_list_again
                result_string_list_again = structured_result_list_again['result']
                assert "data.txt" in result_string_list_again, f"Expected 'data.txt' in re-attached sandbox, but got {result_string_list_again}"
                logging.info("Step 9: Shared Volume Access Verification in Re-attached Sandbox PASSED.")
            finally:
                # Best-effort cleanup: stop re-attached session and force remove pinned sandbox
                try:
                    if attached_session_id_again:
                        logging.info("Cleanup: Stopping the re-attached session...")
                        _ = await session.call_tool(
                            'stop_session',
                            arguments={'session_id': attached_session_id_again}
                        )
                except Exception as e:
                    logging.warning(f"Cleanup: Failed to stop re-attached session: {e}")

                # Also attempt to stop the original session if it wasn't already stopped
                try:
                    if session_id:
                        logging.info("Cleanup: Stopping the original session if still active...")
                        _ = await session.call_tool(
                            'stop_session',
                            arguments={'session_id': session_id}
                        )
                except Exception as e:
                    logging.warning(f"Cleanup: Failed to stop original session: {e}")

                try:
                    logging.info("Cleanup: Force removing pinned sandbox (if exists)...")
                    await BaseSandbox.force_remove_by_name(pin_name, config_path=".env.test")
                except Exception as e:
                    logging.warning(f"Cleanup: Force remove by name skipped/failed: {e}")

@pytest.mark.asyncio
async def test_execute_command_creates_session():
    """Verify that calling execute_command without a session_id creates a new session."""
    async with streamablehttp_client("http://localhost:8775/mcp") as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            new_session_id = None
            try:
                command_to_execute = "echo 'hello world'"
                logging.info("Testing execute_command without session_id...")

                result = await session.call_tool(
                    'execute_command',
                    arguments={'command': command_to_execute}
                )

                assert not result.isError, f"Tool execution failed: {result.content[0].text if result.isError else ''}"

                structured_result = result.structuredContent
                assert 'result' in structured_result, "Expected 'result' in structured result"
                result_string = structured_result['result']

                assert "hello world" in result_string, f"Expected 'hello world' in result, but got {result_string}"
                assert "[success: True]" in result_string, f"Expected success status in result, but got {result_string}"

                # Extract session_id from the result string
                match = re.search(r"\[session_id: (\S+)\]", result_string)
                assert match, f"Could not find session ID in result: {result_string}"
                new_session_id = match.group(1)
                assert uuid.UUID(new_session_id), f"Invalid session ID format: {new_session_id}"

                logging.info(f"execute_command without session_id PASSED. New session created: {new_session_id}")
            finally:
                if new_session_id:
                    try:
                        logging.info("Cleanup: Stopping the auto-created session...")
                        _ = await session.call_tool(
                            'stop_session',
                            arguments={'session_id': new_session_id}
                        )
                    except Exception as e:
                        logging.warning(f"Cleanup: Failed to stop auto-created session: {e}")