#!/usr/bin/env python3
"""
Minimal WebSocket Test - Diagnose Core Connection Issues
This test bypasses the full app startup to focus solely on WebSocket connectivity.
"""

import asyncio
import json
import logging
import subprocess
import time
import signal
import os
from typing import Optional
import websockets
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MinimalWebSocketServer:
    """Minimal WebSocket server to test core connectivity."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        
    async def handler(self, websocket):
        """Handle WebSocket connections."""
        logger.info(f"Client connected: {websocket.remote_address}")
        
        try:
            # Send connection established message
            await websocket.send(json.dumps({
                "type": "connection_established",
                "connection_id": f"conn-{int(time.time())}",
                "user_id": "test-user", 
                "connection_ready": True,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "config": {"heartbeat_interval": 30}
            }))
            
            # Listen for messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Received: {data}")
                    
                    # Handle ping/pong
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }))
                    
                    # Handle echo
                    elif data.get("type") == "echo":
                        await websocket.send(json.dumps({
                            "type": "echo_response",
                            "original": data
                        }))
                    
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "error_code": "FORMAT_ERROR",
                        "message": "Invalid JSON format"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Handler error: {e}")
            
    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        self.server = await websockets.serve(self.handler, self.host, self.port)
        logger.info("WebSocket server started successfully")
        
    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")


class WebSocketTester:
    """Test WebSocket connections and functionality."""
    
    def __init__(self, server_url: str = "ws://localhost:8765"):
        self.server_url = server_url
        
    async def test_connection_success(self):
        """Test successful WebSocket connection."""
        logger.info("Testing WebSocket connection success...")
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(self.server_url),
                timeout=10.0
            )
            
            # Should receive connection_established message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            assert data["type"] == "connection_established"
            assert "connection_id" in data
            assert "user_id" in data
            assert data["connection_ready"] is True
            
            await websocket.close()
            logger.info(" PASS:  Connection success test passed")
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  Connection success test failed: {e}")
            return False
            
    async def test_connection_timeout(self):
        """Test connection timeout handling."""
        logger.info("Testing connection timeout...")
        
        try:
            # Try to connect to non-existent server
            await asyncio.wait_for(
                websockets.connect("ws://localhost:9999"),
                timeout=2.0
            )
            logger.error(" FAIL:  Expected timeout but connection succeeded")
            return False
            
        except asyncio.TimeoutError:
            logger.info(" PASS:  Connection timeout test passed")
            return True
        except Exception as e:
            # Connection refused or connect call failed is also expected
            if "Connection refused" in str(e) or "Connect call failed" in str(e):
                logger.info(" PASS:  Connection timeout test passed (connection refused)")
                return True
            logger.error(f" FAIL:  Unexpected error in timeout test: {e}")
            return False
            
    async def test_ping_pong(self):
        """Test ping/pong messaging."""
        logger.info("Testing ping/pong messaging...")
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(self.server_url),
                timeout=10.0
            )
            
            # Wait for connection established
            await websocket.recv()
            
            # Send ping message
            ping_message = {
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(ping_message))
            
            # Should receive pong response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            assert data["type"] == "pong"
            assert "timestamp" in data
            
            await websocket.close()
            logger.info(" PASS:  Ping/pong test passed")
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  Ping/pong test failed: {e}")
            return False
            
    async def test_echo_functionality(self):
        """Test echo functionality."""
        logger.info("Testing echo functionality...")
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(self.server_url),
                timeout=10.0
            )
            
            # Wait for connection established
            await websocket.recv()
            
            # Send echo message
            echo_message = {
                "type": "echo",
                "content": "Hello WebSocket!",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send(json.dumps(echo_message))
            
            # Should receive echo response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            
            assert data["type"] == "echo_response"
            assert data["original"] == echo_message
            
            await websocket.close()
            logger.info(" PASS:  Echo test passed")
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  Echo test failed: {e}")
            return False
            
    async def run_all_tests(self):
        """Run all WebSocket tests."""
        logger.info("Running all WebSocket tests...")
        
        tests = [
            ("Connection Success", self.test_connection_success),
            ("Connection Timeout", self.test_connection_timeout), 
            ("Ping/Pong", self.test_ping_pong),
            ("Echo Functionality", self.test_echo_functionality)
        ]
        
        results = {}
        for test_name, test_func in tests:
            results[test_name] = await test_func()
            
        # Print results
        logger.info("\n=== TEST RESULTS ===")
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"{test_name}: {status}")
            
        total_tests = len(results)
        passed_tests = sum(results.values())
        logger.info(f"\nTotal: {passed_tests}/{total_tests} tests passed")
        
        return all(results.values())


async def main():
    """Main test execution."""
    logger.info("Starting WebSocket minimal test suite...")
    
    # Start minimal server
    server = MinimalWebSocketServer()
    await server.start()
    
    try:
        # Wait a moment for server to be ready
        await asyncio.sleep(1)
        
        # Run tests
        tester = WebSocketTester()
        all_passed = await tester.run_all_tests()
        
        if all_passed:
            logger.info(" CELEBRATION:  All tests passed! WebSocket functionality is working.")
        else:
            logger.error("[U+1F4A5] Some tests failed. WebSocket has issues.")
            
        return all_passed
        
    finally:
        await server.stop()


if __name__ == "__main__":
    # Check if we can run tests
    success = asyncio.run(main())
    exit(0 if success else 1)