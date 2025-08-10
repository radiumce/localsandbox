"""
Command execution interface for the LocalSandbox Python SDK.
"""

from typing import List, Optional

from .command_execution import CommandExecution
from .config import get_config


class Command:
    """
    Command class for executing shell commands in a sandbox.
    """

    def __init__(self, sandbox_instance):
        """
        Initialize the command instance.

        Args:
            sandbox_instance: The sandbox instance this command belongs to
        """
        self._sandbox = sandbox_instance

    async def run(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> CommandExecution:
        """
        Execute a shell command in the sandbox.

        Args:
            command: The command to execute
            args: Optional list of command arguments
            timeout: Optional timeout in seconds

        Returns:
            A CommandExecution object containing the results

        Raises:
            RuntimeError: If the sandbox is not started or execution fails
        """
        if not self._sandbox._is_started:
            raise RuntimeError("Sandbox is not started. Call start() first.")

        if args is None:
            args = []

        # Build the complete command list
        full_command = [command]
        if args:
            full_command.extend(args)

        try:
            # Use configured timeout if not specified
            if timeout is None:
                config = get_config()
                timeout = config.default_timeout
            
            # Execute command in the container using the container runtime
            result = await self._sandbox._runtime.execute_command(
                self._sandbox._container_id,
                full_command,
                timeout=timeout
            )
            
            # Build output data in the expected format for CommandExecution
            output_data = {
                "output": [],
                "command": command,
                "args": args,
                "exit_code": result["returncode"],
                "success": result["returncode"] == 0
            }
            
            # Add stdout output lines
            if result["stdout"]:
                for line in result["stdout"].splitlines():
                    output_data["output"].append({
                        "stream": "stdout",
                        "text": line
                    })
            
            # Add stderr output lines
            if result["stderr"]:
                for line in result["stderr"].splitlines():
                    output_data["output"].append({
                        "stream": "stderr",
                        "text": line
                    })
            
            return CommandExecution(output_data=output_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {e}")
