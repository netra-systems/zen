"""
Shared WebSocket utilities for E2E testing.
Extracted from multiple large test files to comply with size limits.
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

import websockets
from websockets import ConnectionClosed, InvalidStatus

logger = logging.getLogger(__name__)

class MockWebSocketServer:
    """Mock WebSocket server for E2E testing"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.connected_clients = set()
        self.message_handlers = {}
        
    async def start(self):
        """Start the mock WebSocket server"""
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info(f"Mock WebSocket server started on {self.host}:{self.port}")
        
    async def stop(self):
        """Stop the mock WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Mock WebSocket server stopped")
            
    async def handle_client(self, websocket, path):
        """Handle individual client connections"""
        client_id = str(uuid.uuid4())
        self.connected_clients.add(websocket)
        logger.debug(f"Client {client_id} connected")
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message, client_id)
        except ConnectionClosed:
            logger.debug(f"Client {client_id} disconnected")
        finally:
            self.connected_clients.discard(websocket)
            
    async def process_message(self, websocket, message: str, client_id: str):
        """Process incoming message from client"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            # Echo message back with timestamp
            response = {
                "type": f"{message_type}_response",
                "original_message": data,
                "server_timestamp": time.time(),
                "client_id": client_id
            }
            
            await websocket.send(json.dumps(response))
            
        except json.JSONDecodeError:
            error_response = {
                "type": "error",
                "message": "Invalid JSON format",
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(error_response))

@asynccontextmanager
async def test_websocket_test_context(server_url: str, timeout: float = 30.0):
    """Context manager for WebSocket connections in tests"""
    connection = None
    try:
        connection = await asyncio.wait_for(
            websockets.connect(server_url),
            timeout=timeout
        )
        yield connection
    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")
        raise
    finally:
        if connection:
            await connection.close()

async def send_and_receive(websocket, message: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
    """Send message and wait for response"""
    message_json = json.dumps(message)
    await websocket.send(message_json)
    
    response_json = await asyncio.wait_for(websocket.recv(), timeout=timeout)
    return json.loads(response_json)

async def bulk_send_messages(websocket, messages: List[Dict[str, Any]], 
                           batch_size: int = 10, delay_ms: float = 0) -> List[Dict[str, Any]]:
    """Send multiple messages in batches"""
    responses = []
    
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        
        # Send batch
        send_tasks = []
        for msg in batch:
            send_tasks.append(websocket.send(json.dumps(msg)))
        await asyncio.gather(*send_tasks)
        
        # Receive responses
        for _ in batch:
            try:
                response_json = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                responses.append(json.loads(response_json))
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for response")
                responses.append({"error": "timeout"})
        
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)
    
    return responses

def validate_message_ordering(sent_messages: List[Dict], received_messages: List[Dict]) -> bool:
    """Validate that message ordering is preserved"""
    if len(sent_messages) != len(received_messages):
        return False
        
    for sent, received in zip(sent_messages, received_messages):
        sent_id = sent.get("message_id")
        received_original_id = received.get("original_message", {}).get("message_id")
        
        if sent_id != received_original_id:
            return False
            
    return True

async def stress_test_connections(server_url: str, num_connections: int, 
                                messages_per_connection: int) -> Dict[str, Any]:
    """Create multiple concurrent connections and send messages"""
    results = {
        "total_connections": num_connections,
        "successful_connections": 0,
        "failed_connections": 0,
        "total_messages_sent": 0,
        "total_messages_received": 0,
        "errors": []
    }
    
    async def single_connection_test(connection_id: int):
        try:
            async with test_websocket_test_context(server_url) as websocket:
                results["successful_connections"] += 1
                
                for i in range(messages_per_connection):
                    message = {
                        "message_id": f"conn_{connection_id}_msg_{i}",
                        "connection_id": connection_id,
                        "sequence": i,
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(message))
                    results["total_messages_sent"] += 1
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        results["total_messages_received"] += 1
                    except asyncio.TimeoutError:
                        results["errors"].append(f"Timeout on connection {connection_id}, message {i}")
                        
        except Exception as e:
            results["failed_connections"] += 1
            results["errors"].append(f"Connection {connection_id} failed: {str(e)}")
    
    # Run all connections concurrently
    tasks = [single_connection_test(i) for i in range(num_connections)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return results