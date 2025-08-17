"""
Configuration management for the LocalSandbox Python SDK.

This module provides centralized configuration management with environment variable
support, validation, and default values for container runtime settings.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv


@dataclass
class ContainerRuntimeConfig:
    """
    Container runtime configuration with environment variable support.
    
    This class centralizes all configuration options for the container runtime,
    including default images, resource limits, and runtime selection.
    """
    # Container runtime selection
    runtime_type: str = "docker"  # docker or podman
    
    # Default container images
    default_python_image: str = "python:3.11-slim"
    default_node_image: str = "node:18-slim"
    
    # Default resource limits
    default_memory_mb: int = 512
    default_cpu_limit: float = 1.0
    default_timeout: int = 1800  # 30 minutes
    
    # Container configuration
    default_working_dir: str = "/root"
    
    def __post_init__(self):
        """Validate configuration parameters."""
        self._validate_runtime_type()
        self._validate_resource_limits()
    
    def _validate_runtime_type(self):
        """Validate that the runtime type is supported."""
        supported_runtimes = ["docker", "podman"]
        if self.runtime_type.lower() not in supported_runtimes:
            raise ValueError(
                f"Unsupported container runtime: {self.runtime_type}. "
                f"Supported runtimes: {', '.join(supported_runtimes)}"
            )
    
    def _validate_resource_limits(self):
        """Validate resource limit parameters."""
        if self.default_memory_mb <= 0:
            raise ValueError("Default memory limit must be positive")
        
        if self.default_cpu_limit <= 0:
            raise ValueError("Default CPU limit must be positive")
        
        if self.default_timeout <= 0:
            raise ValueError("Default timeout must be positive")


class ConfigManager:
    """
    Configuration manager that loads settings from environment variables.
    
    This class provides a centralized way to access configuration settings
    with proper validation and error handling.
    """
    
    def __init__(self, dotenv_path: Optional[str] = None):
        """Initialize the configuration manager."""
        load_dotenv(dotenv_path=dotenv_path)
        self._config: Optional[ContainerRuntimeConfig] = None
    
    def get_config(self) -> ContainerRuntimeConfig:
        """
        Get the current configuration, loading from environment variables if needed.
        
        Returns:
            ContainerRuntimeConfig instance with current settings
            
        Raises:
            ValueError: If configuration validation fails
        """
        if self._config is None:
            self._config = self._load_from_environment()
        return self._config
    
    def _load_from_environment(self) -> ContainerRuntimeConfig:
        """
        Load configuration from environment variables.
        
        Returns:
            ContainerRuntimeConfig instance loaded from environment
            
        Raises:
            ValueError: If environment variable values are invalid
        """
        try:
            # Container runtime selection
            runtime_type = os.environ.get("CONTAINER_RUNTIME", "docker").lower()
            
            # Default container images
            python_image = os.environ.get("LOCALSANDBOX_PYTHON_IMAGE", "python:3.11-slim")
            node_image = os.environ.get("LOCALSANDBOX_NODE_IMAGE", "node:18-slim")
            
            # Resource limits with validation
            memory_mb = self._parse_int_env("LOCALSANDBOX_DEFAULT_MEMORY", 512)
            cpu_limit = self._parse_float_env("LOCALSANDBOX_DEFAULT_CPU", 1.0)
            timeout = self._parse_int_env("LOCALSANDBOX_DEFAULT_TIMEOUT", 1800)
            
            # Working directory
            working_dir = os.environ.get("LOCALSANDBOX_WORKING_DIR", "/root")
            
            return ContainerRuntimeConfig(
                runtime_type=runtime_type,
                default_python_image=python_image,
                default_node_image=node_image,
                default_memory_mb=memory_mb,
                default_cpu_limit=cpu_limit,
                default_timeout=timeout,
                default_working_dir=working_dir
            )
            
        except Exception as e:
            raise ValueError(f"Failed to load configuration from environment: {e}")
    
    def _parse_int_env(self, env_var: str, default: int) -> int:
        """
        Parse an integer environment variable with validation.
        
        Args:
            env_var: Environment variable name
            default: Default value if not set
            
        Returns:
            Parsed integer value
            
        Raises:
            ValueError: If the value cannot be parsed as an integer
        """
        value_str = os.environ.get(env_var)
        if value_str is None:
            return default
        
        try:
            value = int(value_str)
            if value <= 0:
                raise ValueError(f"Environment variable {env_var} must be positive, got: {value}")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid value for {env_var}: {value_str}. Must be a positive integer.") from e
    
    def _parse_float_env(self, env_var: str, default: float) -> float:
        """
        Parse a float environment variable with validation.
        
        Args:
            env_var: Environment variable name
            default: Default value if not set
            
        Returns:
            Parsed float value
            
        Raises:
            ValueError: If the value cannot be parsed as a float
        """
        value_str = os.environ.get(env_var)
        if value_str is None:
            return default
        
        try:
            value = float(value_str)
            if value <= 0:
                raise ValueError(f"Environment variable {env_var} must be positive, got: {value}")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid value for {env_var}: {value_str}. Must be a positive number.") from e
    
    def validate_runtime_available(self, runtime_type: str) -> bool:
        """
        Check if the specified container runtime is available on the system.
        
        Args:
            runtime_type: Runtime type to check ("docker" or "podman")
            
        Returns:
            True if runtime is available, False otherwise
        """
        import subprocess
        import asyncio
        
        try:
            # Try to run the runtime command with --version
            result = subprocess.run(
                [runtime_type, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def get_runtime_command(self, runtime_type: Optional[str] = None) -> str:
        """
        Get the command to use for the container runtime.
        
        Args:
            runtime_type: Optional runtime type override
            
        Returns:
            Command string for the container runtime
            
        Raises:
            RuntimeError: If the specified runtime is not available
        """
        if runtime_type is None:
            runtime_type = self.get_config().runtime_type
        
        runtime_type = runtime_type.lower()
        
        if not self.validate_runtime_available(runtime_type):
            raise RuntimeError(
                f"Container runtime '{runtime_type}' is not available. "
                f"Please install {runtime_type} or set CONTAINER_RUNTIME to a different value."
            )
        
        return runtime_type


# Global configuration manager instance
_config_manager = ConfigManager()


def get_config() -> ContainerRuntimeConfig:
    """
    Get the global configuration instance.
    
    Returns:
        ContainerRuntimeConfig instance with current settings
    """
    return _config_manager.get_config()


def get_runtime_command(runtime_type: Optional[str] = None) -> str:
    """
    Get the command to use for the container runtime.
    
    Args:
        runtime_type: Optional runtime type override
        
    Returns:
        Command string for the container runtime
        
    Raises:
        RuntimeError: If the specified runtime is not available
    """
    return _config_manager.get_runtime_command(runtime_type)


def validate_runtime_available(runtime_type: str) -> bool:
    """
    Check if the specified container runtime is available on the system.
    
    Args:
        runtime_type: Runtime type to check ("docker" or "podman")
        
    Returns:
        True if runtime is available, False otherwise
    """
    return _config_manager.validate_runtime_available(runtime_type)