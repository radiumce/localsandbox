"""
MCP Server Entry Point using Official SDK

This module provides the main entry point using the official MCP Python SDK.
"""

import argparse
import asyncio
import atexit
import logging
import os
import signal
import sys

from wrapper import setup_logging, get_logger, ConfigurationError
from mcp_server.server import create_server_app, shutdown_wrapper


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP Server for Microsandbox (using official SDK)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport Options:
  streamable-http   HTTP streaming transport (default)
  sse               Server-Sent Events transport

Environment Variables:
  MCP_SERVER_HOST     Server host address for HTTP transports (default: localhost)
  MCP_SERVER_PORT     Server port number for HTTP transports (default: 8775)
  MCP_ENABLE_CORS     Enable CORS support for HTTP transports (default: false)

Examples:
  python -m mcp_server.main
  python -m mcp_server.main --transport streamable-http --port 9000
  python -m mcp_server.main --transport sse --host 0.0.0.0 --enable-cors
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse"],
        default="streamable-http",
        help="Transport type (default: streamable-http)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Server host address for HTTP transports (overrides MCP_SERVER_HOST)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port number for HTTP transports (overrides MCP_SERVER_PORT)",
    )

    parser.add_argument(
        "--enable-cors",
        action="store_true",
        help="Enable CORS support for HTTP transports (overrides MCP_ENABLE_CORS)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )

    return parser.parse_args()


def get_server_config(args: argparse.Namespace) -> dict:
    """Get server configuration from args and environment."""
    config = {}

    if args.transport in ["streamable-http", "sse"]:
        # HTTP-based transports need host and port
        config["host"] = args.host or os.getenv("MCP_SERVER_HOST", "localhost")
        config["port"] = args.port or int(os.getenv("MCP_SERVER_PORT", "8775"))

        if args.enable_cors or os.getenv("MCP_ENABLE_CORS", "false").lower() == "true":
            config["cors"] = True

    return config


def setup_cleanup_handlers():
    """Setup cleanup handlers for graceful shutdown."""
    shutdown_initiated = False
    
    def signal_handler(signum, frame):
        """Signal handler for graceful shutdown."""
        nonlocal shutdown_initiated
        
        if shutdown_initiated:
            print("Force quit - second CTRL+C received", file=sys.stderr)
            os._exit(1)  # Force immediate exit
        
        shutdown_initiated = True
        print(f"Received signal {signum}, shutting down gracefully... (Press CTRL+C again to force quit)", file=sys.stderr)
        
        # Import here to avoid circular imports
        from mcp_server.server import shutdown_wrapper_sync
        
        # Try to shutdown wrapper cleanly before exiting
        try:
            shutdown_wrapper_sync()
        except Exception as e:
            print(f"Warning: Error during wrapper shutdown: {e}", file=sys.stderr)
        
        # Set a longer timeout only as a safety net for truly stuck processes
        def force_exit():
            print("Graceful shutdown timeout - forcing exit", file=sys.stderr)
            os._exit(1)
        
        # Give 10 seconds for graceful shutdown, then force exit (only as safety net)
        import threading
        timer = threading.Timer(10.0, force_exit)
        timer.start()
        
        try:
            sys.exit(0)
        finally:
            # Cancel the timer if we exit normally
            timer.cancel()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()

    # Setup logging. Logging uses stderr in the wrapper setup
    setup_logging(level=args.log_level)
    logger = get_logger(__name__)
    
    # Setup cleanup handlers for graceful shutdown
    setup_cleanup_handlers()
    
    # Wrapper will be initialized when the server starts via lifespan events
    # This ensures background tasks are created in the main event loop
    logger.debug("Wrapper will initialize when server starts")

    try:
        logger.info(f"Starting MCP Server with transport: {args.transport}")

        # Get server configuration
        config = get_server_config(args)

        # Create the server app
        server_app = create_server_app()

        # Run with the specified transport
        if args.transport == "streamable-http":
            # For HTTP transports, always use custom uvicorn approach to have full control
            logger.info(f"Using Streamable HTTP transport on {config['host']}:{config['port']}")
            run_http_server(server_app, config)
        elif args.transport == "sse":
            # For SSE transport, always use custom uvicorn approach to have full control
            logger.info(f"Using SSE transport on {config['host']}:{config['port']}")
            run_sse_server(server_app, config)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


def run_http_server(server_app, config):
    """Run HTTP server with custom configuration using Starlette + uvicorn."""
    import contextlib
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.middleware.cors import CORSMiddleware
    
    # Get logger for this function
    logger = get_logger(__name__)
    
    # Create a lifespan manager that manages FastMCP session manager AND wrapper
    @contextlib.asynccontextmanager
    async def app_lifespan(app: Starlette):
        from mcp_server.server import get_or_create_wrapper
        
        logger.info("HTTP server lifespan started")
        
        async with contextlib.AsyncExitStack() as stack:
            # Start the wrapper first - this ensures background tasks start in main event loop
            wrapper = await get_or_create_wrapper()
            logger.info("Wrapper initialized and started in HTTP server lifespan")
            
            # Start the FastMCP session manager
            await stack.enter_async_context(server_app.session_manager.run())
            yield
        
        logger.info("HTTP server lifespan ending")
    
    # Create Starlette app and mount the MCP server
    app = Starlette(
        routes=[
            Mount("/", server_app.streamable_http_app()),
        ],
        lifespan=app_lifespan,
    )
    
    # Add CORS middleware if enabled
    if config.get("cors", False):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Run with uvicorn with improved shutdown handling
    uvicorn.run(
        app,
        host=config["host"],
        port=config["port"],
        log_level="info",
        access_log=False,  # Reduce log noise
        server_header=False,  # Reduce response headers
        timeout_keep_alive=5,  # Shorter keep-alive timeout
        timeout_graceful_shutdown=3,  # Shorter graceful shutdown timeout
    )


def run_sse_server(server_app, config):
    """Run SSE server with custom configuration using Starlette + uvicorn."""
    import contextlib
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.middleware.cors import CORSMiddleware
    
    # Get logger for this function
    logger = get_logger(__name__)
    
    # Create a lifespan manager that manages FastMCP session manager AND wrapper
    @contextlib.asynccontextmanager
    async def app_lifespan(app: Starlette):
        from mcp_server.server import get_or_create_wrapper
        
        logger.info("SSE server lifespan started")
        
        async with contextlib.AsyncExitStack() as stack:
            # Start the wrapper first - this ensures background tasks start in main event loop
            wrapper = await get_or_create_wrapper()
            logger.info("Wrapper initialized and started in SSE server lifespan")
            
            # Start the FastMCP session manager
            await stack.enter_async_context(server_app.session_manager.run())
            yield
        
        logger.info("SSE server lifespan ending")
    
    # Create Starlette app and mount the MCP server
    app = Starlette(
        routes=[
            Mount("/", server_app.sse_app()),
        ],
        lifespan=app_lifespan,
    )
    
    # Add CORS middleware if enabled
    if config.get("cors", False):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Run with uvicorn with improved shutdown handling
    uvicorn.run(
        app,
        host=config["host"],
        port=config["port"],
        log_level="info",
        access_log=False,  # Reduce log noise
        server_header=False,  # Reduce response headers
        timeout_keep_alive=5,  # Shorter keep-alive timeout
        timeout_graceful_shutdown=3,  # Shorter graceful shutdown timeout
    )


if __name__ == "__main__":
    main()
