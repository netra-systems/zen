"""
Mock WebSocket server for E2E testing.

Business Value Justification (BVJ):
- Segment: All Segments
- Business Goal: Test Infrastructure
- Value Impact: Provides reliable WebSocket server for E2E testing
- Strategic/Revenue Impact: Enables comprehensive testing without external dependencies
"""

import asyncio
import json
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

import websockets
from websockets import ServerConnection

logger = logging.getLogger(__name__)

class MockWebSocketServer:
    """Mock WebSocket server for testing rapid message scenarios."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.ServerConnection] = {}
        self.message_queue: deque = deque()
        self.processing_delay: float = 0.1
        self.simulate_failures: bool = False
        self.failure_rate: float = 0.05
        self.server = None
        self.running = False
        
    async def handle_client(self, websocket: websockets.ServerConnection, path: str):
        """Handle individual client connections."""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        logger.info(f"Client {client_id} connected")
        
        try:
            async for message in websocket:
                await self.process_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def process_message(self, client_id: str, message: str):
        """Process incoming message with optional delay and failure simulation."""
        try:
            data = json.loads(message)
            
            # Simulate processing delay
            if self.processing_delay > 0:
                await asyncio.sleep(self.processing_delay)
            
            # Simulate random failures
            if self.simulate_failures and random.random() < self.failure_rate:
                response = {
                    "message_id": data.get("message_id"),
                    "status": "error",
                    "error": "Simulated processing failure",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                response = {
                    "message_id": data.get("message_id"),
                    "response_id": str(uuid.uuid4()),
                    "status": "success",
                    "content": f"Processed: {data.get('content', 'No content')}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent_id": f"agent_{uuid.uuid4().hex[:8]}"
                }
            
            # Send response
            websocket = self.clients.get(client_id)
            if websocket:
                await websocket.send(json.dumps(response))
                
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
            
    async def start(self):
        """Start the mock WebSocket server."""
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        self.running = True
        logger.info(f"Mock WebSocket server started on {self.host}:{self.port}")
        
    async def stop(self):
        """Stop the mock WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            logger.info("Mock WebSocket server stopped")
            
    def configure_behavior(self, processing_delay: float = 0.1, 
                          simulate_failures: bool = False, 
                          failure_rate: float = 0.05):
        """Configure server behavior for testing."""
        self.processing_delay = processing_delay
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
