"""
MCP Server Entry Point using Official SDK

This module provides the main entry point using the official MCP Python SDK.
Only supports streamable-http transport.
"""

import argparse
import os
import sys

from wrapper import setup_logging, get_logger, ConfigurationError
from mcp_server.server import create_server_app


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP Server for Microsandbox (using official SDK)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  MCP_SERVER_HOST     Server host address (default: localhost)
  MCP_SERVER_PORT     Server port number (default: 8775)
  MCP_ENABLE_CORS     Enable CORS support (default: false)

Examples:
  python -m mcp_server.main
  python -m mcp_server.main --port 9000
  python -m mcp_server.main --host 0.0.0.0 --enable-cors
        """,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Server host address (overrides MCP_SERVER_HOST)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port number (overrides MCP_SERVER_PORT)",
    )

    parser.add_argument(
        "--enable-cors",
        action="store_true",
        help="Enable CORS support (overrides MCP_ENABLE_CORS)",
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
    config = {
        "host": args.host or os.getenv("MCP_SERVER_HOST", "localhost"),
        "port": args.port or int(os.getenv("MCP_SERVER_PORT", "8775")),
    }

    if args.enable_cors or os.getenv("MCP_ENABLE_CORS", "false").lower() == "true":
        config["cors"] = True

    return config


def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_args()

    setup_logging(level=args.log_level)
    logger = get_logger(__name__)

    try:
        config = get_server_config(args)
        server_app = create_server_app()
        
        logger.info(f"Starting MCP Server on {config['host']}:{config['port']}")
        run_server(server_app, config)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


def run_server(server_app, config):
    """Run MCP server using streamable-http transport."""
    import contextlib
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.middleware.cors import CORSMiddleware
    
    logger = get_logger(__name__)
    
    @contextlib.asynccontextmanager
    async def app_lifespan(app: Starlette):
        from mcp_server.server import get_or_create_wrapper
        
        logger.info("Server lifespan started")
        
        async with contextlib.AsyncExitStack() as stack:
            wrapper = await get_or_create_wrapper()
            logger.info("Wrapper initialized and started")
            
            await stack.enter_async_context(server_app.session_manager.run())
            yield
        
        logger.info("Server lifespan ending")
    
    app = Starlette(
        routes=[Mount("/", server_app.streamable_http_app())],
        lifespan=app_lifespan,
    )
    
    if config.get("cors", False):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    uvicorn.run(
        app,
        host=config["host"],
        port=config["port"],
        log_level="info",
        access_log=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
