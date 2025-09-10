"""
MCP Server using Official SDK

This module implements the MCP server using the official MCP Python SDK,
replacing the custom implementation with a standards-compliant solution.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field, ConfigDict
import mcp.types as types

from wrapper.wrapper import MicrosandboxWrapper

# Patch FastMCP's ArgModelBase to forbid extra fields
from mcp.server.fastmcp.utilities.func_metadata import ArgModelBase
ArgModelBase.model_config = ConfigDict(
    arbitrary_types_allowed=True,
    extra='forbid',  # This will cause validation errors for undefined parameters
)
from wrapper.models import SandboxFlavor
from wrapper.exceptions import (
    MicrosandboxWrapperError,
    ResourceLimitError,
    ConfigurationError,
    SandboxCreationError,
    CodeExecutionError,
    CommandExecutionError,
    SessionNotFoundError,
    ContainerNotFoundError,
    PinnedSandboxNotFoundError,
    ContainerStartError,
    SessionCreationError,
    ConnectionError as WrapperConnectionError
)

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context with typed dependencies."""
    wrapper: MicrosandboxWrapper


# Global wrapper instance - managed at process level, independent of FastMCP lifespan
_global_wrapper: Optional[MicrosandboxWrapper] = None
_wrapper_lock = asyncio.Lock()
_wrapper_initialized = False
_shutdown_registered = False
_shutdown_in_progress = False


async def get_or_create_wrapper() -> MicrosandboxWrapper:
    """Get or create the global wrapper instance."""
    global _global_wrapper, _wrapper_initialized, _shutdown_registered
    
    async with _wrapper_lock:
        if _global_wrapper is None:
            logger.info("Creating and starting global MicrosandboxWrapper instance (process-level)")
            _global_wrapper = MicrosandboxWrapper()
            await _global_wrapper.start()
            _wrapper_initialized = True
            logger.info("Global MicrosandboxWrapper started successfully - orphan cleanup and resource management are now active")
            
            # Register process-level atexit handler only once
            # Signal handlers are managed by main.py
            if not _shutdown_registered:
                import atexit
                
                def sync_shutdown():
                    """Synchronous wrapper for shutdown_wrapper."""
                    global _shutdown_in_progress
                    if _shutdown_in_progress:
                        return  # Avoid duplicate shutdown - signal handler already handled it
                    
                    if _global_wrapper is not None and _global_wrapper.is_started():
                        _shutdown_in_progress = True
                        logger.info("Process exit detected - shutting down MicrosandboxWrapper")
                        try:
                            # Use wrapper's emergency shutdown method
                            logger.info("Process exit detected, using wrapper emergency shutdown")
                            shutdown_result = _global_wrapper.emergency_shutdown_sync()
                            logger.info(f"Emergency shutdown completed with status: {shutdown_result['status']}")
                        except Exception as e:
                            # Suppress errors during process exit to avoid noise
                            logger.debug(f"Error during process exit wrapper shutdown: {e}")
                
                # Register only atexit handler - signals handled by main.py
                atexit.register(sync_shutdown)
                _shutdown_registered = True
                logger.info("Process-level atexit handler registered for MicrosandboxWrapper")
        
        return _global_wrapper


async def _force_shutdown_wrapper() -> None:
    """Force shutdown the global wrapper instance - used by process exit handlers."""
    global _global_wrapper
    
    if _global_wrapper is not None:
        try:
            logger.info("Force shutting down global MicrosandboxWrapper")
            await _global_wrapper.stop()
            logger.info("Global MicrosandboxWrapper force shutdown complete")
        except Exception as e:
            logger.error(f"Error during force shutdown: {e}")
        finally:
            _global_wrapper = None





async def shutdown_wrapper() -> None:
    """Shutdown the global wrapper instance - no-op for process-level management."""
    # For process-level management, we don't shutdown on FastMCP lifespan events
    # The wrapper will be shutdown when the process exits
    logger.debug("shutdown_wrapper() called - ignoring due to process-level management")
    pass


def shutdown_wrapper_sync() -> None:
    """Synchronously shutdown the global wrapper instance - for signal handlers."""
    global _global_wrapper, _shutdown_in_progress
    
    if _shutdown_in_progress:
        return  # Avoid duplicate shutdown
    
    _shutdown_in_progress = True
    logger.info("Signal handler: shutting down MicrosandboxWrapper")
    
    try:
        # Use wrapper's emergency shutdown method which respects existing cleanup logic
        if _global_wrapper is not None:
            shutdown_result = _global_wrapper.emergency_shutdown_sync()
            logger.info(f"Signal handler: emergency shutdown completed with status: {shutdown_result['status']}")
            _global_wrapper = None
        else:
            logger.debug("Signal handler: wrapper not initialized, nothing to shutdown")
            
    except Exception as e:
        logger.error(f"Error during signal handler wrapper shutdown: {e}")


# Create MCP server with lifespan management for wrapper initialization
from contextlib import asynccontextmanager

@asynccontextmanager
async def mcp_lifespan(app):
    """Lifespan manager for FastMCP - does NOT initialize wrapper (session-level, called for each MCP connection)."""
    logger.debug("FastMCP lifespan started (session-level)")
    
    # DO NOT initialize wrapper here - this is called for each MCP session/connection
    # Wrapper initialization should happen at process level instead
    
    yield
    
    logger.debug("FastMCP lifespan ending (session-level)")
    # No wrapper management - wrapper is managed at process level

mcp = FastMCP("Microsandbox Server", lifespan=mcp_lifespan)


# Direct parameter definitions - no wrapper models needed


# Tool implementations using the official SDK
@mcp.tool()
async def execute_code(
    code: str = Field(description="Code to execute"),
    template: str = Field(default="python", description="Sandbox template"),
    session_id: Optional[str] = Field(None, description="Optional session ID for session reuse"),
    flavor: Optional[str] = Field(default=None, description="Resource configuration (small/medium/large/xlarge). If omitted, uses server default from environment (MSB_DEFAULT_FLAVOR)"),
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds"),
    ctx: Context = None,
) -> str:
    """Execute code in a sandbox with automatic session management. 
    If you do not fill in the session_id parameter, the service will 
    automatically create a new sandbox for you and return the session_id 
    corresponding to this sandbox. This is generally used for starting tasks 
    from scratch. When you fill in the session_id, the code will execute within 
    the same sandbox instance corresponding to the session_id, thereby maintaining
     the continuity of the sandbox state. This is a necessary foundation for 
     continuously completing a series of tasks. """
    try:
        # Always use the global wrapper instance for consistent behavior across all transports
        wrapper = await get_or_create_wrapper()
        
        # Determine flavor: use wrapper config default if not provided
        if flavor is None:
            flavor_enum = wrapper.get_config().default_flavor
        else:
            flavor_enum = SandboxFlavor(flavor)
        
        # Execute code through wrapper
        result = await wrapper.execute_code(
            code=code,
            template=template,
            session_id=session_id,
            flavor=flavor_enum,
            timeout=timeout
        )
        
        # Format result for MCP protocol
        output_text = result.stdout
        if result.stderr:
            if output_text:
                output_text += "\n" + result.stderr
            else:
                output_text = result.stderr
        
        # Add metadata information
        metadata = (
            f"\n[session_id: {result.session_id}] "
            f"[time: {result.execution_time_ms}ms] "
            f"[template: {result.template}] "
            f"[success: {result.success}]"
        )
        
        return output_text + metadata
        
    except Exception as e:
        logger.error(f"Code execution failed: {e}", exc_info=True)
        raise


@mcp.tool()
async def execute_command(
    command: str = Field(description="Complete command line to execute (including arguments, pipes, redirections, etc.)"),
    template: str = Field(default="python", description="Sandbox template"),
    session_id: Optional[str] = Field(None, description="Optional session ID for session reuse"),
    flavor: Optional[str] = Field(default=None, description="Resource configuration (small/medium/large/xlarge). If omitted, uses server default from environment (MSB_DEFAULT_FLAVOR)"),
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds"),
    ctx: Context = None,
) -> str:
    """Execute a command line in a sandbox with automatic session management.
    If you do not fill in the session_id parameter, the service will 
    automatically create a new sandbox for you and return the session_id 
    corresponding to this sandbox. This is generally used for starting tasks 
    from scratch. When you fill in the session_id, the command will execute within 
    the same sandbox instance corresponding to the session_id, thereby maintaining
     the continuity of the sandbox state. This is a necessary foundation for 
     continuously completing a series of tasks."""
    try:
        # Always use the global wrapper instance for consistent behavior across all transports
        wrapper = await get_or_create_wrapper()
        
        # Determine flavor: use wrapper config default if not provided
        if flavor is None:
            flavor_enum = wrapper.get_config().default_flavor
        else:
            flavor_enum = SandboxFlavor(flavor)
        
        # Execute command line through shell using wrapper
        result = await wrapper.execute_command(
            command="sh",
            args=["-c", command],
            template=template,
            session_id=session_id,
            flavor=flavor_enum,
            timeout=timeout
        )
        
        # Format result for MCP protocol
        output_text = result.stdout
        if result.stderr:
            if output_text:
                output_text += "\n" + result.stderr
            else:
                output_text = result.stderr
        
        # Add metadata information
        metadata = (
            f"\n[session_id: {result.session_id}] "
            f"[command: {command}] "
            f"[exit code: {result.exit_code}] "
            f"[time: {result.execution_time_ms}ms] "
            f"[success: {result.success}]"
        )
        
        return output_text + metadata
        
    except Exception as e:
        logger.error(f"Command execution failed: {e}", exc_info=True)
        raise


@mcp.tool()
async def get_sessions(
    session_id: Optional[str] = Field(None, description="Optional specific session ID to query"),
    ctx: Context = None,
) -> str:
    """Get information about active sandbox sessions."""
    try:
        # Always use the global wrapper instance for consistent behavior across all transports
        wrapper = await get_or_create_wrapper()
        
        # Get sessions through wrapper
        sessions = await wrapper.get_sessions(session_id)
        
        # Format sessions information
        if not sessions:
            return "No active sessions found."
        
        session_info = []
        for session in sessions:
            info = (
                f"Session ID: {session.session_id}\n"
                f"  Template: {session.template}\n"
                f"  Flavor: {session.flavor.value}\n"
                f"  Status: {session.status.value}\n"
                f"  Created: {session.created_at.isoformat()}\n"
                f"  Last Accessed: {session.last_accessed.isoformat()}\n"
                f"  Namespace: {session.namespace}\n"
                f"  Sandbox Name: {session.sandbox_name}"
            )
            session_info.append(info)
        
        return "\n\n".join(session_info)
        
    except Exception as e:
        logger.error(f"Get sessions failed: {e}", exc_info=True)
        raise


@mcp.tool()
async def stop_session(
    session_id: str = Field(description="ID of the session to stop"),
    ctx: Context = None,
) -> str:
    """Stop a specific sandbox session and clean up its resources."""
    try:
        # Always use the global wrapper instance for consistent behavior across all transports
        wrapper = await get_or_create_wrapper()
        
        # Stop session through wrapper
        success = await wrapper.stop_session(session_id)
        
        if success:
            return f"Session {session_id} stopped successfully"
        else:
            return f"Session {session_id} not found or already stopped"
        
    except Exception as e:
        logger.error(f"Stop session failed: {e}", exc_info=True)
        raise


@mcp.tool()
async def get_volume_mappings(ctx: Context = None) -> str:
    """Get configured volume mappings between host and container paths."""
    try:
        # Always use the global wrapper instance for consistent behavior across all transports
        wrapper = await get_or_create_wrapper()
        
        # Get volume mappings through wrapper
        mappings = await wrapper.get_volume_mappings()
        
        if not mappings:
            return "No volume mappings configured."
        
        mapping_info = []
        for mapping in mappings:
            info = f"Host: {mapping.host_path} -> Container: {mapping.sandbox_path}"
            mapping_info.append(info)
        
        return "\n".join(mapping_info)
        
    except Exception as e:
        logger.error(f"Get volume mappings failed: {e}", exc_info=True)
        raise


@mcp.tool()
async def pin_sandbox(
    session_id: str = Field(description="ID of the session to pin"),
    pinned_name: str = Field(description="Human-readable name for the pinned sandbox"),
    ctx: Context = None,
) -> str:
    """Pin a sandbox with a custom name for persistence beyond session cleanup."""
    try:
        # Always use the global wrapper instance for consistent behavior across all transports
        wrapper = await get_or_create_wrapper()
        
        # Call wrapper's pin_session method
        result = await wrapper.pin_session(session_id, pinned_name)
        
        return result
        
    except SessionNotFoundError as e:
        logger.error(f"Pin sandbox failed - session not found: {e}", exc_info=True)
        return f"Error: {e.message}"
    except ContainerNotFoundError as e:
        logger.error(f"Pin sandbox failed - container not found: {e}", exc_info=True)
        return f"Error: {e.message}"
    except RuntimeError as e:
        logger.error(f"Pin sandbox failed - runtime error: {e}", exc_info=True)
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Pin sandbox failed with unexpected error: {e}", exc_info=True)
        return f"Error: An unexpected error occurred while pinning sandbox: {str(e)}"


@mcp.tool()
async def attach_sandbox_by_name(
    pinned_name: str = Field(description="Name of the pinned sandbox to attach to"),
    ctx: Context = None,
) -> str:
    """Attach to a previously pinned sandbox by name and return session ID."""
    try:
        # Always use the global wrapper instance for consistent behavior across all transports
        wrapper = await get_or_create_wrapper()
        
        # Call wrapper's attach_to_pinned_sandbox method
        session_id = await wrapper.attach_to_pinned_sandbox(pinned_name)
        
        return f"Successfully attached to pinned sandbox '{pinned_name}'. Session ID: {session_id}"
        
    except PinnedSandboxNotFoundError as e:
        logger.error(f"Attach sandbox failed - pinned sandbox not found: {e}", exc_info=True)
        return f"Error: {e.message}"
    except ContainerStartError as e:
        logger.error(f"Attach sandbox failed - container start error: {e}", exc_info=True)
        return f"Error: {e.message}"
    except SessionCreationError as e:
        logger.error(f"Attach sandbox failed - session creation error: {e}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.error(f"Attach sandbox failed with unexpected error: {e}", exc_info=True)
        return f"Error: An unexpected error occurred while attaching to pinned sandbox: {str(e)}"


def create_server_app() -> FastMCP:
    """Create and return the configured MCP server."""
    return mcp
