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
        logger.info("Starting Netra MCP Server with FastMCP 2...")
        
        # Create server instance
        server = NetraMCPServer(
            name="netra-mcp-server",
            version="2.0.0"
        )
        
        # Get the FastMCP app
        app = server.get_app()
        
        # Run the server
        # FastMCP handles the server lifecycle
        await app.run()
        
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"Error running MCP server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())