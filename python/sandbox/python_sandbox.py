"""
Python-specific sandbox implementation for the LocalSandbox Python SDK.
"""

from .base_sandbox import BaseSandbox
from .config import get_config
from .execution import Execution


class PythonSandbox(BaseSandbox):
    """
    Python-specific sandbox for executing Python code.
    """

    async def get_default_image(self) -> str:
        """
        Get the default Docker image for Python sandbox.

        Returns:
            A string containing the Docker image name and tag
        """
        config = get_config()
        return config.default_python_image

    async def run(self, code: str) -> Execution:
        """
        Execute Python code in the sandbox.

        Args:
            code: Python code to execute

        Returns:
            An Execution object that represents the executed code

        Raises:
            RuntimeError: If the sandbox is not started or execution fails
        """
        if not self._is_started:
            raise RuntimeError("Sandbox is not started. Call start() first.")

        # Create Python script with error handling and output capture
        # Use base64 encoding to safely pass the code without escaping issues
        import base64
        encoded_code = base64.b64encode(code.encode('utf-8')).decode('ascii')
        script_content = f"""
import sys
import traceback
import base64

try:
    # Decode and execute user code
    user_code = base64.b64decode('{encoded_code}').decode('utf-8')
    exec(user_code)
except Exception as e:
    # Print exception to stderr and exit with error code
    traceback.print_exc()
    sys.exit(1)
"""

        # Execute Python code in the container
        command = ["python", "-c", script_content]
        
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
                "language": "python"
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
            
            return Execution(output_data=output_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute code: {e}")
