"""
MCP Server Entry Point

This module provides the main entry point for the HTTP-based MCP server.
"""

import sys
import logging
from wrapper import setup_logging, get_logger, ConfigurationError
from server.server import create_server_app

def start_mcp_server(host: str, port: int, enable_cors: bool = False):
    """
    Start the MCP server with the given configuration.
    
    Args:
        host: Server host
        port: Server port
        enable_cors: Whether to enable CORS
    """
    setup_logging()
    logger = get_logger(__name__)

    try:
        config = {
            "host": host,
            "port": port,
            "cors": enable_cors
        }
        
        server_app = create_server_app()
        logger.info(f"Starting MCP Server on {host}:{port}")
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
        from server.server import get_or_create_wrapper
        
        logger.info("Server lifespan started")
        
        async with contextlib.AsyncExitStack() as stack:
            # Initialize wrapper
            await get_or_create_wrapper()
            logger.info("Wrapper initialized")
            
            # Start session manager
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

