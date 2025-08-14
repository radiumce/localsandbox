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
            command=["sleep", "infinity"],  # Keep container running
            labels={
                "localsandbox": "true",
                "localsandbox.namespace": self._namespace,
                "localsandbox.name": self._name,
            }
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
            
            # Check if this is a pinned container - if so, don't remove it
            is_pinned = await self._runtime.is_container_pinned(self._container_id)
            if not is_pinned:
                await self._runtime.remove_container(self._container_id)
                self._container_id = None
            
            self._is_started = False
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

    async def pin(self, pinned_name: str) -> None:
        """
        Pin the sandbox with a persistent name.
        
        This allows the sandbox to be reattached later using the pinned name,
        even after the current session ends.
        
        Args:
            pinned_name: The persistent name to assign to this sandbox
            
        Raises:
            RuntimeError: If the sandbox is not started or pinning fails
        """
        if not self._is_started or not self._container_id:
            raise RuntimeError("Cannot pin sandbox: sandbox is not started")
        
        try:
            # Store original container ID and name for reference
            original_container_id = self._container_id
            original_name = self._name
            
            # First, rename the container to the pinned name
            await self._runtime.rename_container(original_name, pinned_name)
            
            # Update container labels to mark it as pinned
            # Use the original container ID to avoid confusion during the update process
            labels = {
                "pinned": "true",
                "pinned_name": pinned_name
            }
            await self._runtime.update_container_labels(original_container_id, labels)
            
            # Update internal name tracking
            self._name = pinned_name
            
            # After label update, get the new container info to update our references
            try:
                container_info = await self._runtime.get_container_info(pinned_name)
                if container_info and 'Id' in container_info:
                    # Update container ID as it may have changed during label update
                    self._container_id = container_info['Id']
                else:
                    raise RuntimeError("Failed to get container info after pin operation")
            except Exception as verify_error:
                raise RuntimeError(f"Failed to verify container after pin operation: {verify_error}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to pin sandbox as '{pinned_name}': {e}")
    
    @classmethod
    async def attach_to_pinned(
        cls,
        pinned_name: str,
        container_runtime: Optional[str] = None,
        namespace: str = "default",
        **kwargs
    ):
        """
        Attach to an existing pinned sandbox.
        
        Args:
            pinned_name: The name of the pinned sandbox to attach to
            container_runtime: Container runtime to use ('docker' or 'podman')
            namespace: Namespace for the sandbox
            **kwargs: Additional arguments for backward compatibility (ignored)
            
        Returns:
            A sandbox instance attached to the existing pinned sandbox
            
        Raises:
            RuntimeError: If the pinned sandbox cannot be found or attached
        """
        # Create sandbox instance
        sandbox = cls(
            container_runtime=container_runtime,
            namespace=namespace,
            name=pinned_name,
            **kwargs
        )
        
        try:
            # Try to get container info by name first
            container_info = await sandbox._runtime.get_container_info(pinned_name)
        except Exception:
            # If not found by name, try searching by label
            try:
                containers = await sandbox._runtime.get_containers_by_label({"pinned_name": pinned_name})
                if not containers:
                    raise RuntimeError(f"No pinned sandbox found with name '{pinned_name}'")
                container_info = containers[0]
            except Exception as e:
                raise RuntimeError(f"Failed to find pinned sandbox '{pinned_name}': {e}")
        
        # Extract container ID and check if it's running
        container_id = container_info['Id']
        container_state = container_info.get('State', {})
        is_running = container_state.get('Running', False)
        
        # Start container if it's stopped
        if not is_running:
            try:
                await sandbox._runtime.start_container(container_id)
            except Exception as e:
                raise RuntimeError(f"Failed to start pinned sandbox '{pinned_name}': {e}")
        
        # Update sandbox state
        sandbox._container_id = container_id
        sandbox._is_started = True
        
        return sandbox
    
    @classmethod
    async def list_pinned(
        cls,
        container_runtime: Optional[str] = None,
        namespace: Optional[str] = None
    ) -> list:
        """
        List all pinned sandboxes.
        
        Args:
            container_runtime: Container runtime to use ('docker' or 'podman')
            namespace: Optional namespace filter
            
        Returns:
            List of dictionaries containing pinned sandbox information
        """
        # Create a temporary runtime instance
        config = get_config()
        runtime_name = container_runtime or config.runtime_type
        runtime_cmd = get_runtime_command(runtime_name)
        runtime = DockerRuntime(runtime_cmd)
        
        try:
            # Search for containers with pinned=true label
            search_labels = {"pinned": "true"}
            if namespace:
                search_labels["localsandbox.namespace"] = namespace
                
            containers = await runtime.get_containers_by_label(search_labels)
            
            pinned_sandboxes = []
            for container in containers:
                labels = container.get('Labels', {})
                pinned_sandboxes.append({
                    'name': labels.get('pinned_name', 'unknown'),
                    'container_id': container['Id'],
                    'state': container.get('State', 'unknown'),
                    'image': container.get('Image', 'unknown'),
                    'namespace': labels.get('localsandbox.namespace', 'default'),
                    'template': labels.get('template', 'unknown')
                })
            
            return pinned_sandboxes
            
        except Exception as e:
            raise RuntimeError(f"Failed to list pinned sandboxes: {e}")

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
