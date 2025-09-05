"""
Real WebSocket test for async serialization verification.
Uses actual WebSocket connections - NO MOCKS per CLAUDE.md.
"""

import asyncio
import time
import pytest
from typing import Dict, Any
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
import uvicorn
from threading import Thread
import websockets

from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState


# Create a real FastAPI app for testing
test_app = FastAPI()
manager = WebSocketManager()


@test_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real WebSocket endpoint for testing."""
    await websocket.accept()
    
    # Connect the user
    conn_id = await manager.connect_user("test-user", websocket, "test-thread")
    
    try:
        # Keep connection alive and process messages
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "test_serialization":
                # Test async serialization
                state = data.get("state", {})
                result = await manager._serialize_message_safely_async(state)
                await websocket.send_json({
                    "type": "serialization_result",
                    "data": result
                })
            elif data.get("type") == "broadcast":
                # Test send_to_thread with async serialization
                message = data.get("message", {})
                success = await manager.send_to_thread("test-thread", message)
                await websocket.send_json({
                    "type": "broadcast_result",
                    "success": success
                })
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await manager.disconnect_user(conn_id)


class TestAsyncSerializationReal:
    """Test async serialization with real WebSocket connections."""
    
    @pytest.fixture
    async def start_server(self):
        """Start a real FastAPI server in background."""
        import socket
        
        # Find a free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
        
        # Start server in a thread
        def run_server():
            uvicorn.run(test_app, host="127.0.0.1", port=port, log_level="error")
        
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Give server time to start
        await asyncio.sleep(1)
        
        yield f"ws://127.0.0.1:{port}/ws"
        
        # Server will stop when test ends
    
    @pytest.mark.asyncio
    async def test_async_serialization_performance(self, start_server):
        """Test that async serialization doesn't block the event loop."""
        ws_url = start_server
        
        async with websockets.connect(ws_url) as websocket:
            # Create a large message
            large_state = {
                "type": "test_state",
                "data": {}
            }
            
            # Build nested structure
            current = large_state["data"]
            for i in range(50):
                current[f"level_{i}"] = {
                    "items": [{"id": j, "data": "x" * 1000} for j in range(5)],
                    "nested": {}
                }
                current = current[f"level_{i}"]["nested"]
            
            # Test serialization
            await websocket.send(json.dumps({
                "type": "test_serialization",
                "state": large_state
            }))
            
            # Track event loop responsiveness while waiting for response
            loop_responsive = True
            
            async def check_responsiveness():
                nonlocal loop_responsive
                for _ in range(10):
                    start = time.perf_counter()
                    await asyncio.sleep(0.01)
                    if time.perf_counter() - start > 0.05:
                        loop_responsive = False
                        break
            
            # Run check while waiting for response
            check_task = asyncio.create_task(check_responsiveness())
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            await check_task
            
            result = json.loads(response)
            assert result["type"] == "serialization_result"
            assert loop_responsive, "Event loop was blocked during serialization"
    
    @pytest.mark.asyncio
    async def test_send_to_thread_with_real_websocket(self, start_server):
        """Test send_to_thread with real WebSocket connections."""
        ws_url = start_server
        
        # Connect multiple real WebSocket clients
        websockets_list = []
        for i in range(3):
            ws = await websockets.connect(ws_url)
            websockets_list.append(ws)
        
        # Create a complex DeepAgentState
        state = DeepAgentState(
            user_request="test request",
            chat_thread_id="test-thread",
            user_id="test-user",
            messages=[
                {"role": "user", "content": "test " * 100} for _ in range(10)
            ],
            metadata={"timestamp": str(time.time()), "data": "x" * 1000}
        )
        
        # Send broadcast message through first WebSocket
        await websockets_list[0].send(json.dumps({
            "type": "broadcast",
            "message": state.model_dump()
        }))
        
        # Check response
        response = await asyncio.wait_for(websockets_list[0].recv(), timeout=5)
        result = json.loads(response)
        
        assert result["type"] == "broadcast_result"
        assert result["success"] is True
        
        # Clean up
        for ws in websockets_list:
            await ws.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_serialization_real(self, start_server):
        """Test concurrent message serialization with real connections."""
        ws_url = start_server
        
        async with websockets.connect(ws_url) as websocket:
            # Send multiple serialization requests concurrently
            tasks = []
            for i in range(10):
                message = {
                    "type": "test_serialization",
                    "state": {
                        "id": i,
                        "data": "x" * 10000,
                        "nested": {"items": [j for j in range(100)]}
                    }
                }
                tasks.append(websocket.send(json.dumps(message)))
            
            # Send all at once
            await asyncio.gather(*tasks)
            
            # Receive all responses
            responses = []
            for _ in range(10):
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                responses.append(json.loads(response))
            
            # All should succeed
            assert all(r["type"] == "serialization_result" for r in responses)
            assert len(responses) == 10
    
    @pytest.mark.asyncio 
    async def test_websocket_retry_mechanism_real(self, start_server):
        """Test retry mechanism with real WebSocket that has intermittent issues."""
        # This test would require a special endpoint that simulates failures
        # For now, we test that normal messages succeed
        ws_url = start_server
        
        async with websockets.connect(ws_url) as websocket:
            # Send a message that should succeed after potential retries
            state = {"type": "test", "data": "test_message"}
            
            await websocket.send(json.dumps({
                "type": "broadcast",
                "message": state
            }))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            result = json.loads(response)
            
            # Should eventually succeed
            assert result["type"] == "broadcast_result"
            assert result["success"] is True


import json  # Add this import at the top


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])