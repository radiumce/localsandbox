"""
MCP Server using Official SDK

This module implements the MCP server using the official MCP Python SDK,
replacing the custom implementation with a standards-compliant solution.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field, ConfigDict

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


# Global wrapper instance
_global_wrapper: Optional[MicrosandboxWrapper] = None
_wrapper_lock = asyncio.Lock()


async def get_or_create_wrapper() -> MicrosandboxWrapper:
    """Get or create the global wrapper instance."""
    global _global_wrapper
    
    async with _wrapper_lock:
        if _global_wrapper is None:
            logger.info("Creating and starting MicrosandboxWrapper")
            _global_wrapper = MicrosandboxWrapper()
            await _global_wrapper.start()
            logger.info("MicrosandboxWrapper started successfully")
            
            # Register atexit handler for cleanup on process exit
            import atexit
            atexit.register(_shutdown_on_exit)
        
        return _global_wrapper


def _shutdown_on_exit():
    """Cleanup handler called on process exit."""
    global _global_wrapper
    
    if _global_wrapper is not None and _global_wrapper.is_started():
        try:
            logger.info("Process exit - shutting down MicrosandboxWrapper")
            shutdown_result = _global_wrapper.emergency_shutdown_sync()
            logger.info(f"Shutdown completed: {shutdown_result['status']}")
        except Exception as e:
            logger.debug(f"Error during shutdown: {e}")


# Create MCP server
mcp = FastMCP("Microsandbox Server")


# Tool implementations using the official SDK
@mcp.tool()
async def execute_code(
    code: str = Field(description="Code to execute"),
    template: str = Field(default="python", description="Sandbox template. Supported values: 'python' (Python environment), 'node'/'nodejs'/'javascript' (Node.js environment)"),
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
    template: str = Field(default="python", description="Sandbox template. Supported values: 'python' (Python environment), 'node'/'nodejs'/'javascript' (Node.js environment)"),
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
