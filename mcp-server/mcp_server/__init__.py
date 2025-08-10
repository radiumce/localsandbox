"""
MCP Server Package

A lightweight HTTP streamable transport implementation for the Model Context Protocol (MCP)
that integrates with the existing MicrosandboxWrapper.
"""

__version__ = "0.1.0"
__all__ = ["main", "__version__"]

def main(*args, **kwargs):
    """Lazy entry point to avoid importing submodules at package import time.
    This prevents runpy warnings when executing `python -m mcp_server.main`.
    """
    from . import main as _main  # Local import to avoid eager submodule load
    return _main.main(*args, **kwargs)

# MCPServer will be imported once it's implemented in task 3
# from .server import MCPServer