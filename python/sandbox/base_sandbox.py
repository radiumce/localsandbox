"""
Base sandbox implementation for the Microsandbox Python SDK.
"""

import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Optional

from .command import Command
from .config import get_config, get_runtime_command
# TODO: Metrics implementation removed - will be implemented later
# from .metrics import Metrics
from .container_runtime import ContainerRuntime, DockerRuntime


class BaseSandbox(ABC):
    """
    Base sandbox environment for executing code safely.

    This class provides the base interface for interacting with the Microsandbox server.
    It handles common functionality like sandbox creation, management, and communication.
    """

    def __init__(
        self,
        container_runtime: Optional[str] = None,
        namespace: str = "default",
        name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a base sandbox instance.

        Args:
            container_runtime: Container runtime to use ('docker' or 'podman'). If not provided, will use configuration from environment variables.
            namespace: Namespace for the sandbox
            name: Optional name for the sandbox. If not provided, a random name will be generated.
            **kwargs: Additional arguments for backward compatibility (ignored)
        """
        # Load configuration
        self._config = get_config()
        
        # Set container runtime, using config default if not specified
        self._container_runtime_name = container_runtime or self._config.runtime_type
        self._namespace = namespace
        self._name = name or f"sandbox-{uuid.uuid4().hex[:8]}"
        self._container_id: Optional[str] = None
        self._is_started = False
        
        # Initialize container runtime
        self._runtime = self._create_runtime()

    def _create_runtime(self) -> ContainerRuntime:
        """Create container runtime instance with validation"""
        try:
            # Get the validated runtime command
            runtime_cmd = get_runtime_command(self._container_runtime_name)
            return DockerRuntime(runtime_cmd)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to initialize container runtime: {e}")

    @abstractmethod
    async def get_default_image(self) -> str:
        """
        Get the default Docker image for this sandbox type.

        Returns:
            A string containing the Docker image name and tag
        """
        pass

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        container_runtime: Optional[str] = None,
        namespace: str = "default",
        name: Optional[str] = None,
        image: Optional[str] = None,
        memory: Optional[int] = None,
        cpus: Optional[float] = None,
        timeout: float = 180.0,
        volumes: Optional[list] = None,
        **kwargs
    ):
        """
        Create and initialize a new sandbox as an async context manager.

        Args:
            container_runtime: Container runtime to use ('docker' or 'podman'). If not provided, will use configuration from environment variables.
            namespace: Namespace for the sandbox
            name: Optional name for the sandbox. If not provided, a random name will be generated.
            image: Docker image to use for the sandbox (defaults to language-specific image)
            memory: Memory limit in MB (defaults to configuration value)
            cpus: CPU limit (defaults to configuration value)
            timeout: Maximum time in seconds to wait for the sandbox to start (default: 180 seconds)
            volumes: List of volume mappings in format ["host_path:container_path", ...]. 
                    Supports both relative paths (relative to project directory) and absolute paths.
            **kwargs: Additional arguments for backward compatibility (ignored)

        Returns:
            An instance of the sandbox ready for use
        """
        sandbox = cls(
            container_runtime=container_runtime,
            namespace=namespace,
            name=name,
            **kwargs
        )
        try:
            # Start the sandbox
            await sandbox.start(
                image=image,
                memory=memory,
                cpus=cpus,
                timeout=timeout,
                volumes=volumes,
            )
            yield sandbox
        finally:
            # Stop the sandbox
            await sandbox.stop()

    async def start(
        self,
        image: Optional[str] = None,
        memory: Optional[int] = None,
        cpus: Optional[float] = None,
        timeout: float = 180.0,
        volumes: Optional[list] = None,
    ) -> None:
        """
        Start the sandbox container.

        Args:
            image: Docker image to use for the sandbox (defaults to language-specific image)
            memory: Memory limit in MB (defaults to configuration value)
            cpus: CPU limit (defaults to configuration value)
            timeout: Maximum time in seconds to wait for the sandbox to start (default: 180 seconds)
            volumes: List of volume mappings in format ["host_path:container_path", ...]. 
                    Supports both relative paths (relative to project directory) and absolute paths.

        Raises:
            RuntimeError: If the sandbox fails to start
            TimeoutError: If the sandbox doesn't start within the specified timeout
        """
        if self._is_started:
            return

        sandbox_image = image or await self.get_default_image()
        
        # Use configuration defaults if not specified
        memory_limit = memory or self._config.default_memory_mb
        cpu_limit = cpus or self._config.default_cpu_limit
        
        # Import ContainerConfig here to avoid circular imports
        from .container_runtime import ContainerConfig
        
        # Build the container configuration
        config = ContainerConfig(
            image=sandbox_image,
            name=self._name,
            memory=memory_limit,
            cpus=cpu_limit,
            volumes=volumes or [],
            working_dir=self._config.default_working_dir,
            command=["sleep", "infinity"]  # Keep container running
        )
        
        try:
            # Create and start container
            self._container_id = await self._runtime.create_container(config)
            await self._runtime.start_container(self._container_id)
            self._is_started = True
        except Exception as e:
            raise RuntimeError(f"Failed to start sandbox: {e}")

    async def stop(self) -> None:
        """
        Stop the sandbox container.

        Raises:
            RuntimeError: If the sandbox fails to stop
        """
        if not self._is_started or not self._container_id:
            return

        try:
            await self._runtime.stop_container(self._container_id)
            await self._runtime.remove_container(self._container_id)
            self._is_started = False
            self._container_id = None
        except Exception as e:
            raise RuntimeError(f"Failed to stop sandbox: {e}")

    @abstractmethod
    async def run(self, code: str):
        """
        Execute code in the sandbox.

        Args:
            code: Code to execute

        Returns:
            An Execution object representing the executed code

        Raises:
            RuntimeError: If execution fails
        """
        pass

    @property
    def command(self):
        """
        Access the command namespace for executing shell commands in the sandbox.

        Returns:
            A Command instance bound to this sandbox
        """
        return Command(self)

    @property
    def metrics(self):
        """
        Access the metrics namespace for retrieving sandbox metrics.

        TODO: Metrics functionality is not yet implemented for container-based sandboxes.
        This will be implemented in a future version.

        Returns:
            A placeholder object that raises NotImplementedError for all metric operations
        """
        # TODO: Implement metrics for container-based sandboxes
        class MetricsTODO:
            def __init__(self, sandbox_instance):
                self._sandbox = sandbox_instance
            
            async def all(self):
                raise NotImplementedError("Metrics functionality is not yet implemented for container-based sandboxes")
            
            async def cpu(self):
                raise NotImplementedError("Metrics functionality is not yet implemented for container-based sandboxes")
            
            async def memory(self):
                raise NotImplementedError("Metrics functionality is not yet implemented for container-based sandboxes")
            
            async def disk(self):
                raise NotImplementedError("Metrics functionality is not yet implemented for container-based sandboxes")
            
            async def is_running(self):
                raise NotImplementedError("Metrics functionality is not yet implemented for container-based sandboxes")
        
        return MetricsTODO(self)
