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