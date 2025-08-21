"""
MCP Server Runner

Standalone script to run the Netra MCP server.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.netra_mcp.netra_mcp_server import NetraMCPServer
from app.logging_config import CentralLogger

logger = CentralLogger()


async def main():
    """Run the MCP server"""
    try:
        server = await _create_mcp_server()
        await _run_mcp_server(server)
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        _handle_server_error(e)

async def _create_mcp_server():
    """Create and configure MCP server instance."""
    logger.info("Starting Netra MCP Server with FastMCP 2...")
    return NetraMCPServer(name="netra-mcp-server", version="2.0.0")

async def _run_mcp_server(server):
    """Run the MCP server with FastMCP app."""
    app = server.get_app()
    await app.run()

def _handle_server_error(error):
    """Handle server startup/runtime errors."""
    logger.error(f"Error running MCP server: {error}", exc_info=True)
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())