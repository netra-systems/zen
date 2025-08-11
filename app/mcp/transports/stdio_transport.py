"""
MCP Standard I/O Transport

Implements JSON-RPC 2.0 over stdin/stdout for CLI integrations.
"""

import sys
import json
import asyncio
from typing import Optional, Dict, Any
import signal

from app.logging_config import CentralLogger
from app.mcp.server import MCPServer

logger = CentralLogger()


class StdioTransport:
    """
    Standard I/O transport for MCP
    
    Used by Claude Code, Cursor, and other CLI-based integrations.
    """
    
    def __init__(self, server: Optional[MCPServer] = None):
        self.server = server or MCPServer()
        self.session_id = None
        self.running = False
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    async def start(self):
        """Start the stdio transport"""
        self.running = True
        logger.info("MCP stdio transport started")
        
        # Send initialization
        await self._send_server_info()
        
        # Main loop
        await self._read_loop()
        
    async def _read_loop(self):
        """Main read loop for stdin"""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        while self.running:
            try:
                # Read line from stdin
                line_bytes = await reader.readline()
                if not line_bytes:
                    break
                    
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue
                    
                # Parse and handle request
                try:
                    request = json.loads(line)
                    await self._handle_request(request)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    await self._send_error(-32700, "Parse error")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in stdio read loop: {e}", exc_info=True)
                await self._send_error(-32603, f"Internal error: {str(e)}")
                
        logger.info("Stdio transport stopped")
        
    async def _handle_request(self, request: Dict[str, Any]):
        """Handle incoming request"""
        # Special handling for initialization
        if request.get("method") == "initialize":
            params = request.get("params", {})
            params["transport"] = "stdio"
            request["params"] = params
            
        # Process through server
        response = await self.server.handle_request(request, self.session_id)
        
        # Update session ID if this was initialization
        if request.get("method") == "initialize" and "result" in response:
            # Extract session ID from server (would need to enhance server to return this)
            pass
            
        # Send response
        if response:
            await self._send_response(response)
            
    async def _send_response(self, response: Dict[str, Any]):
        """Send response to stdout"""
        try:
            response_str = json.dumps(response)
            sys.stdout.write(response_str + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error sending response: {e}", exc_info=True)
            
    async def _send_error(self, code: int, message: str, request_id: Optional[Any] = None):
        """Send error response"""
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        if request_id is not None:
            error_response["id"] = request_id
        await self._send_response(error_response)
        
    async def _send_server_info(self):
        """Send server information on startup"""
        info = {
            "jsonrpc": "2.0",
            "method": "server.info",
            "params": {
                "name": "Netra MCP Server",
                "version": "1.0.0",
                "transport": "stdio"
            }
        }
        await self._send_response(info)
        
    async def shutdown(self):
        """Shutdown the transport"""
        self.running = False
        if self.server:
            await self.server.shutdown()


async def main():
    """Main entry point for stdio transport"""
    transport = StdioTransport()
    try:
        await transport.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await transport.shutdown()


if __name__ == "__main__":
    # This allows running as: python -m app.mcp.transports.stdio_transport
    asyncio.run(main())