"""
Container runtime abstraction layer for the Docker-based sandbox implementation.

This module provides the abstract base class and data models for container runtime
implementations, supporting both Docker and Podman as container runtimes.
"""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ContainerConfig:
    """
    Container configuration data class.
    
    Defines all the parameters needed to create and configure a container,
    including resource limits, volume mappings, and environment variables.
    """
    image: str
    name: str
    memory: Optional[int] = None  # Memory limit in MB
    cpus: Optional[float] = None  # CPU limit
    volumes: Optional[List[str]] = field(default_factory=list)  # Volume mappings
    environment: Optional[Dict[str, str]] = field(default_factory=dict)  # Environment variables
    working_dir: str = "/workspace"  # Working directory inside container
    command: Optional[List[str]] = None  # Command to run in container
    labels: Optional[Dict[str, str]] = field(default_factory=dict)  # Container labels
    
    def __post_init__(self):
        """Validate configuration parameters and set defaults."""
        if not self.image:
            raise ValueError("Container image is required")
        if not self.name:
            raise ValueError("Container name is required")
        
        # Ensure volumes is a list
        if self.volumes is None:
            self.volumes = []
        
        # Ensure environment is a dict
        if self.environment is None:
            self.environment = {}
        
        # Validate memory limit
        if self.memory is not None and self.memory <= 0:
            raise ValueError("Memory limit must be positive")
        
        # Validate CPU limit
        if self.cpus is not None and self.cpus <= 0:
            raise ValueError("CPU limit must be positive")


@dataclass
class ContainerStats:
    """
    Container statistics data class.
    
    Contains runtime statistics and status information about a container,
    including resource usage and running state.
    """
    cpu_percent: Optional[float] = None  # CPU usage percentage
    memory_usage_mb: Optional[int] = None  # Current memory usage in MB
    memory_limit_mb: Optional[int] = None  # Memory limit in MB
    is_running: bool = False  # Whether the container is currently running
    
    def __post_init__(self):
        """Validate statistics data."""
        # Validate CPU percentage
        if self.cpu_percent is not None and (self.cpu_percent < 0 or self.cpu_percent > 100):
            raise ValueError("CPU percentage must be between 0 and 100")
        
        # Validate memory values
        if self.memory_usage_mb is not None and self.memory_usage_mb < 0:
            raise ValueError("Memory usage must be non-negative")
        
        if self.memory_limit_mb is not None and self.memory_limit_mb <= 0:
            raise ValueError("Memory limit must be positive")


class ContainerRuntime(ABC):
    """
    Abstract base class for container runtime implementations.
    
    This class defines the interface that all container runtime implementations
    must follow, providing methods for container lifecycle management and
    command execution within containers.
    """
    
    @abstractmethod
    async def create_container(self, config: ContainerConfig) -> str:
        """
        Create a new container with the specified configuration.
        
        Args:
            config: Container configuration parameters
            
        Returns:
            Container ID of the created container
            
        Raises:
            RuntimeError: If container creation fails
        """
        pass
    
    @abstractmethod
    async def start_container(self, container_id: str) -> None:
        """
        Start an existing container.
        
        Args:
            container_id: ID of the container to start
            
        Raises:
            RuntimeError: If container start fails
        """
        pass
    
    @abstractmethod
    async def stop_container(self, container_id: str) -> None:
        """
        Stop a running container.
        
        Args:
            container_id: ID of the container to stop
            
        Raises:
            RuntimeError: If container stop fails
        """
        pass
    
    @abstractmethod
    async def remove_container(self, container_id: str) -> None:
        """
        Remove a container (must be stopped first).
        
        Args:
            container_id: ID of the container to remove
            
        Raises:
            RuntimeError: If container removal fails
        """
        pass
    
    @abstractmethod
    async def force_remove_container(self, container_id: str) -> None:
        """
        Force remove a container regardless of its state.
        
        This should stop the container if necessary and remove it forcibly.
        
        Args:
            container_id: ID or name of the container to force remove
            
        Raises:
            RuntimeError: If force removal fails
        """
        pass

    @abstractmethod
    async def force_remove_by_name(self, name: str, namespace: Optional[str] = None) -> None:
        """
        Force remove a container by name or pinned label, ignoring pinned status.

        Args:
            name: The container name or pinned_name label value
            namespace: Optional namespace label to narrow the search

        Raises:
            RuntimeError: If the container cannot be found or removal fails
        """
        pass
    
    @abstractmethod
    async def execute_command(
        self, 
        container_id: str, 
        command: List[str],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a command inside a running container.
        
        Args:
            container_id: ID of the container to execute command in
            command: Command and arguments to execute
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary containing:
            - returncode: Exit code of the command
            - stdout: Standard output as string
            - stderr: Standard error as string
            
        Raises:
            RuntimeError: If command execution fails
            TimeoutError: If command execution times out
        """
        pass
    
    @abstractmethod
    async def get_container_stats(self, container_id: str) -> ContainerStats:
        """
        Get runtime statistics for a container.
        
        Args:
            container_id: ID of the container to get stats for
            
        Returns:
            ContainerStats object with current statistics
            
        Raises:
            RuntimeError: If stats retrieval fails
        """
        pass

    @abstractmethod
    async def get_container_info(self, container_name_or_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific container.
        
        Args:
            container_name_or_id: Container name or ID
            
        Returns:
            Dictionary containing container information
            
        Raises:
            RuntimeError: If the container is not found or command fails
        """
        pass
    
    @abstractmethod
    async def is_container_running(self, container_id: str) -> bool:
        """
        Check if a container is currently running.
        
        Args:
            container_id: ID of the container to check
            
        Returns:
            True if container is running, False otherwise
            
        Raises:
            RuntimeError: If status check fails
        """
        pass


class DockerRuntime(ContainerRuntime):
    """
    Docker container runtime implementation.
    
    This class implements the ContainerRuntime interface using Docker CLI commands.
    It supports both Docker and Podman (which is Docker CLI compatible).
    """
    
    def __init__(self, docker_cmd: str = "docker"):
        """
        Initialize Docker runtime.
        
        Args:
            docker_cmd: Docker command to use (e.g., "docker" or "podman")
        """
        self.docker_cmd = docker_cmd
    
    async def _run_command(self, args: List[str], timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a Docker CLI command.
        
        Args:
            args: Command arguments (without the docker command itself)
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary containing:
            - returncode: Exit code of the command
            - stdout: Standard output as string
            - stderr: Standard error as string
            
        Raises:
            RuntimeError: If command execution fails
            TimeoutError: If command execution times out
        """
        cmd = [self.docker_cmd] + args
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8')
            }
        except asyncio.TimeoutError:
            # Kill the process if it times out
            try:
                process.kill()
                await process.wait()
            except:
                pass
            raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
        except Exception as e:
            raise RuntimeError(f"Failed to execute command {' '.join(cmd)}: {e}")
    
    async def create_container(self, config: ContainerConfig) -> str:
        """Create a Docker container with the specified configuration."""
        # Build docker run command arguments
        args = ["create"]
        
        # Add name
        args.extend(["--name", config.name])
        
        # Add memory limit
        if config.memory:
            args.extend(["--memory", f"{config.memory}m"])
        
        # Add CPU limit
        if config.cpus:
            args.extend(["--cpus", str(config.cpus)])
        
        # Add volumes
        for volume in config.volumes:
            args.extend(["-v", volume])
        
        # Add environment variables
        for key, value in config.environment.items():
            args.extend(["-e", f"{key}={value}"])

        # Add labels
        if config.labels:
            for key, value in config.labels.items():
                # docker requires key[=value]; always provide value for determinism
                args.extend(["--label", f"{key}={value}"])

        # Add working directory
        args.extend(["-w", config.working_dir])
        
        # Add image
        args.append(config.image)
        
        # Add command if specified
        if config.command:
            args.extend(config.command)
        
        # Execute the command
        result = await self._run_command(args, timeout=30)
        
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to create container: {result['stderr']}")
        
        # Return the container ID (from stdout)
        container_id = result["stdout"].strip()
        if not container_id:
            raise RuntimeError("Failed to get container ID from docker create command")
        
        return container_id
    
    async def start_container(self, container_id: str) -> None:
        """Start a Docker container."""
        result = await self._run_command(["start", container_id], timeout=30)
        
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to start container {container_id}: {result['stderr']}")
    
    async def stop_container(self, container_id: str) -> None:
        """Stop a Docker container."""
        result = await self._run_command(["stop", container_id], timeout=30)
        
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to stop container {container_id}: {result['stderr']}")
    
    async def remove_container(self, container_id: str) -> None:
        """Remove a Docker container."""
        result = await self._run_command(["rm", container_id], timeout=30)
        
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to remove container {container_id}: {result['stderr']}")
    
    async def force_remove_container(self, container_id: str) -> None:
        """Force remove a Docker container (stops and removes if running)."""
        result = await self._run_command(["rm", "-f", container_id], timeout=30)
        
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to force remove container {container_id}: {result['stderr']}")

    async def force_remove_by_name(self, name: str, namespace: Optional[str] = None) -> None:
        """Force remove a Docker container by name or pinned label."""
        info: Dict[str, Any] = {}
        # Try docker inspect by exact name first
        try:
            info = await self.get_container_info(name)
        except Exception:
            info = {}

        container_id: Optional[str] = None
        if info:
            container_id = info.get('Id') or info.get('id')
        else:
            # Fallback: search by labels via docker ps
            label_filters: Dict[str, str] = {"pinned_name": name}
            if namespace:
                label_filters["localsandbox.namespace"] = namespace
            containers = await self.get_containers_by_label(label_filters)
            if containers:
                first = containers[0]
                container_id = first.get('id') or first.get('Id')

        if not container_id:
            raise RuntimeError(f"No container found to force remove for name '{name}'")

        await self.force_remove_container(container_id)
    
    async def execute_command(
        self, 
        container_id: str, 
        command: List[str],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a command inside a Docker container."""
        args = ["exec", container_id] + command
        
        result = await self._run_command(args, timeout=timeout)
        
        return {
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"]
        }
    
    async def get_container_stats(self, container_id: str) -> ContainerStats:
        """Get runtime statistics for a Docker container."""
        # Use docker stats with --no-stream and --format to get JSON output
        args = ["stats", "--no-stream", "--format", "json", container_id]
        
        result = await self._run_command(args, timeout=10)
        
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to get container stats: {result['stderr']}")
        
        try:
            # Parse JSON output
            stats_data = json.loads(result["stdout"].strip())
            
            # Extract relevant statistics
            cpu_percent = None
            memory_usage_mb = None
            memory_limit_mb = None
            
            # Parse CPU percentage (format: "1.23%")
            if "CPUPerc" in stats_data:
                cpu_str = stats_data["CPUPerc"].rstrip('%')
                try:
                    cpu_percent = float(cpu_str)
                except ValueError:
                    pass
            
            # Parse memory usage (format: "123.4MiB / 512MiB")
            if "MemUsage" in stats_data:
                mem_usage = stats_data["MemUsage"]
                try:
                    # Split on " / " to get usage and limit
                    usage_str, limit_str = mem_usage.split(" / ")
                    
                    # Convert to MB (handle MiB, MB, GiB, etc.)
                    memory_usage_mb = self._parse_memory_string(usage_str)
                    memory_limit_mb = self._parse_memory_string(limit_str)
                except (ValueError, IndexError):
                    pass
            
            # Check if container is running
            is_running = await self.is_container_running(container_id)
            
            return ContainerStats(
                cpu_percent=cpu_percent,
                memory_usage_mb=memory_usage_mb,
                memory_limit_mb=memory_limit_mb,
                is_running=is_running
            )
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse container stats JSON: {e}")
    
    def _parse_memory_string(self, mem_str: str) -> int:
        """
        Parse memory string like "123.4MiB" to MB.
        
        Args:
            mem_str: Memory string with unit
            
        Returns:
            Memory value in MB
        """
        mem_str = mem_str.strip()
        
        # Extract number and unit
        if mem_str.endswith("MiB"):
            value = float(mem_str[:-3])
            return int(value * 1.048576)  # MiB to MB
        elif mem_str.endswith("MB"):
            value = float(mem_str[:-2])
            return int(value)
        elif mem_str.endswith("GiB"):
            value = float(mem_str[:-3])
            return int(value * 1073.741824)  # GiB to MB
        elif mem_str.endswith("GB"):
            value = float(mem_str[:-2])
            return int(value * 1000)  # GB to MB
        elif mem_str.endswith("KiB"):
            value = float(mem_str[:-3])
            return int(value / 1024)  # KiB to MB
        elif mem_str.endswith("KB"):
            value = float(mem_str[:-2])
            return int(value / 1000)  # KB to MB
        else:
            # Assume bytes
            try:
                value = float(mem_str)
                return int(value / 1000000)  # Bytes to MB
            except ValueError:
                return 0
    
    async def is_container_running(self, container_id: str) -> bool:
        """Check if a Docker container is running."""
        args = ["inspect", "--format", "{{.State.Running}}", container_id]
        
        result = await self._run_command(args, timeout=10)
        
        if result["returncode"] != 0:
            # Container might not exist
            return False
        
        # Docker returns "true" or "false" as string
        return result["stdout"].strip().lower() == "true"

    async def list_containers(
        self,
        all: bool = True,
        label_filters: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = 15,
    ) -> List[Dict[str, Any]]:
        """
        List containers with optional label filters.

        Args:
            all: If True, include stopped containers (docker ps -a)
            label_filters: Dict of label_key -> label_value to filter by
            timeout: Command timeout in seconds

        Returns:
            List of dicts containing id, name, labels, status, running
        """
        args: List[str] = ["ps"]
        if all:
            args.append("-a")

        # Apply label filters
        if label_filters:
            for k, v in label_filters.items():
                args.extend(["--filter", f"label={k}={v}"])

        # Output each container as a JSON object per line
        args.extend(["--format", "{{json .}}"])

        result = await self._run_command(args, timeout=timeout)
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to list containers: {result['stderr']}")

        lines = [l for l in result["stdout"].splitlines() if l.strip()]
        containers: List[Dict[str, Any]] = []
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

            name = obj.get("Names") or obj.get("Name")
            cid = obj.get("ID") or obj.get("Id")
            status = obj.get("Status", "") or ""
            labels_str = obj.get("Labels") or ""

            # Parse labels string "k=v,m=n" into dict
            labels: Dict[str, str] = {}
            if labels_str and labels_str.lower() != "<none>":
                for pair in labels_str.split(","):
                    pair = pair.strip()
                    if not pair:
                        continue
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        labels[k] = v
                    else:
                        labels[pair] = "true"

            running = status.lower().startswith("up")
            containers.append({
                "id": cid,
                "name": name,
                "labels": labels,
                "status": status,
                "running": running,
            })

        return containers

    async def rename_container(self, container_id: str, new_name: str) -> None:
        """
        Rename a container.
        
        Args:
            container_id: ID or current name of the container to rename
            new_name: New name for the container
            
        Raises:
            RuntimeError: If container rename fails
        """
        result = await self._run_command(["rename", container_id, new_name], timeout=30)
        
        if result["returncode"] != 0:
            raise RuntimeError(f"Failed to rename container {container_id} to {new_name}: {result['stderr']}")

    async def update_container_labels(self, container_id: str, labels: Dict[str, str]) -> None:
        """
        Update container labels by recreating the container with updated labels.
        
        Since Docker doesn't support updating labels on existing containers,
        we commit the current state and recreate with new labels.
        
        Args:
            container_id: ID or name of the container to update labels for
            labels: Dictionary of label key-value pairs to add/update
            
        Raises:
            RuntimeError: If label update fails
        """
        # Get current container info
        inspect_result = await self._run_command(["inspect", container_id], timeout=10)
        if inspect_result["returncode"] != 0:
            raise RuntimeError(f"Failed to inspect container {container_id}: {inspect_result['stderr']}")
        
        try:
            container_info = json.loads(inspect_result["stdout"])[0]
            container_name = container_info.get("Name", "").lstrip("/")
            if not container_name:
                raise RuntimeError(f"Could not determine name for container {container_id}")
            
            # Check if container is running
            was_running = await self.is_container_running(container_id)
            
            # Create a temporary image with the current container state
            temp_image = f"temp_pin_{container_name}_{hash(str(labels)) % 10000}"
            
            # Simple commit without changes first
            commit_result = await self._run_command(["commit", container_id, temp_image], timeout=30)
            if commit_result["returncode"] != 0:
                raise RuntimeError(f"Failed to commit container: {commit_result['stderr']}")
            
            try:
                # Stop the container if running
                if was_running:
                    await self.stop_container(container_id)
                
                # Remove the old container (with retry logic for race conditions)
                try:
                    await self.remove_container(container_id)
                except RuntimeError as e:
                    if "removal of container" in str(e) and "is already in progress" in str(e):
                        # Container removal is already in progress, wait a bit and continue
                        await asyncio.sleep(1)
                    elif "No such container" in str(e):
                        # Container already removed, that's fine
                        pass
                    else:
                        raise
                
                # Get original configuration for basic settings
                config = container_info.get("Config", {})
                host_config = container_info.get("HostConfig", {})
                
                # Build run command with simplified configuration
                run_args = ["run", "-d", "--name", container_name]
                
                # Add labels (both existing and new)
                current_labels = config.get("Labels") or {}
                updated_labels = {**current_labels, **labels}
                for key, value in updated_labels.items():
                    run_args.extend(["--label", f"{key}={value}"])
                
                # Add basic resource limits only
                if host_config.get("Memory"):
                    memory_mb = host_config["Memory"] // (1024 * 1024)
                    run_args.extend(["--memory", f"{memory_mb}m"])
                
                if host_config.get("NanoCpus"):
                    cpus = host_config["NanoCpus"] / 1000000000
                    run_args.extend(["--cpus", str(cpus)])
                
                # Add volume mounts from original container
                mounts = container_info.get("Mounts", [])
                for mount in mounts:
                    if mount.get("Type") == "bind":
                        source = mount.get("Source")
                        destination = mount.get("Destination")
                        if source and destination:
                            # Verify source directory exists before adding mount
                            import os
                            if os.path.exists(source):
                                run_args.extend(["-v", f"{source}:{destination}"])
                
                # Only add basic environment variables (skip PATH and complex ones)
                env_vars = config.get("Env", [])
                for env_var in env_vars:
                    if "=" in env_var and not any(env_var.startswith(skip) for skip in ["PATH=", "HOSTNAME=", "HOME="]):
                        run_args.extend(["-e", env_var])
                
                # Add working directory if it exists
                working_dir = config.get("WorkingDir")
                if working_dir:
                    run_args.extend(["-w", working_dir])
                
                # Add the committed image
                run_args.append(temp_image)
                
                # Add original command if it exists
                cmd = config.get("Cmd")
                if cmd:
                    run_args.extend(cmd)
                
                # Create the new container
                create_result = await self._run_command(run_args, timeout=30)
                if create_result["returncode"] != 0:
                    raise RuntimeError(f"Failed to recreate container with labels: {create_result['stderr']}")
                
                # For pinned containers, always start them after recreation
                # This ensures the container is available for continued use with the same session
                await self.start_container(container_name)
                    
            finally:
                # Clean up temporary image
                await self._run_command(["rmi", temp_image], timeout=10)
                
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to parse container inspection data: {e}")

    async def get_container_info(self, container_name_or_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific container.
        
        Args:
            container_name_or_id: Container name or ID
            
        Returns:
            Dictionary containing container information
            
        Raises:
            RuntimeError: If the container is not found or command fails
        """
        inspect_result = await self._run_command(["inspect", container_name_or_id], timeout=10)
        if inspect_result["returncode"] != 0:
            raise RuntimeError(f"Container {container_name_or_id} not found: {inspect_result['stderr']}")
        
        try:
            container_info = json.loads(inspect_result["stdout"])[0]
            return container_info
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to parse container inspection data: {e}")

    async def get_containers_by_label(self, label_filters: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Find containers by label filters.
        
        Args:
            label_filters: Dictionary of label key-value pairs to filter by
            
        Returns:
            List of dictionaries containing container information:
            - id: Container ID
            - name: Container name
            - labels: Dictionary of container labels
            - status: Container status string
            - running: Boolean indicating if container is running
            
        Raises:
            RuntimeError: If container listing fails
        """
        return await self.list_containers(all=True, label_filters=label_filters)

    async def stop_and_remove(self, container_id: str) -> None:
        """
        Stop container if running and remove it.
        
        For pinned containers (those with pinned=true label), only stop the container
        but do not remove it to preserve the pinned sandbox.
        """
        try:
            # Stop the container if it's running
            if await self.is_container_running(container_id):
                await self.stop_container(container_id)
            
            # Only remove if not pinned
            is_pinned = await self.is_container_pinned(container_id)
            if not is_pinned:
                await self.remove_container(container_id)
                
        except RuntimeError as e:
            # If container doesn't exist, that's fine for cleanup operations
            if "No such container" not in str(e):
                raise

    async def is_container_pinned(self, container_id: str) -> bool:
        """
        Check if a container is pinned (has pinned=true label).
        
        Args:
            container_id: Container ID to check
            
        Returns:
            bool: True if container is pinned, False otherwise
        """
        try:
            inspect_result = await self._run_command(["inspect", container_id], timeout=10)
            
            if inspect_result["returncode"] == 0:
                try:
                    container_info = json.loads(inspect_result["stdout"])[0]
                    labels = container_info.get("Config", {}).get("Labels") or {}
                    return labels.get("pinned", "").lower() == "true"
                except (json.JSONDecodeError, KeyError, IndexError):
                    # If we can't parse labels, assume not pinned
                    return False
            
            return False
        except Exception:
            # If any error occurs, assume not pinned
            return False