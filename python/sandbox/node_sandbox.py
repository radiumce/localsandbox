"""
Node.js-specific sandbox implementation for the LocalSandbox Python SDK.
"""

import os
import uuid

from .base_sandbox import BaseSandbox
from .config import get_config
from .execution import Execution


class NodeSandbox(BaseSandbox):
    """
    Node.js-specific sandbox for executing JavaScript code.
    """

    async def get_default_image(self) -> str:
        """
        Get the default Docker image for Node.js sandbox.

        Returns:
            A string containing the Docker image name and tag
        """
        config = get_config()
        return config.default_node_image

    async def run(self, code: str) -> Execution:
        """
        Execute JavaScript code in the sandbox.

        Args:
            code: JavaScript code to execute

        Returns:
            An Execution object that represents the executed code

        Raises:
            RuntimeError: If the sandbox is not started or execution fails
        """
        if not self._is_started:
            raise RuntimeError("Sandbox is not started. Call start() first.")

        # Execute JavaScript code in the container using Node.js
        command = ["node", "-e", code]
        
        try:
            # Use configured timeout
            config = get_config()
            result = await self._runtime.execute_command(
                self._container_id,
                command,
                timeout=config.default_timeout
            )
            
            # Build output data compatible with original Execution format
            output_data = {
                "output": [],
                "status": "success" if result["returncode"] == 0 else "error",
                "language": "nodejs"
            }
            
            # Add stdout output
            if result["stdout"]:
                for line in result["stdout"].splitlines():
                    output_data["output"].append({
                        "stream": "stdout",
                        "text": line
                    })
            
            # Add stderr output
            if result["stderr"]:
                for line in result["stderr"].splitlines():
                    output_data["output"].append({
                        "stream": "stderr", 
                        "text": line
                    })
            
            return Execution(output_data=output_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute code: {e}")
