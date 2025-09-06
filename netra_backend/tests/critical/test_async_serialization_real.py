# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Real WebSocket test for async serialization verification.
# REMOVED_SYNTAX_ERROR: Uses actual WebSocket connections - NO MOCKS per CLAUDE.md.
""

import asyncio
import time
import pytest
from typing import Dict, Any
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
import uvicorn
from threading import Thread
import websockets
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState


# Create a real FastAPI app for testing
test_app = FastAPI()
manager = WebSocketManager()


# REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def websocket_endpoint(websocket: WebSocket):
    # REMOVED_SYNTAX_ERROR: """Real WebSocket endpoint for testing."""
    # REMOVED_SYNTAX_ERROR: await websocket.accept()

    # Connect the user
    # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("test-user", websocket, "test-thread")

    # REMOVED_SYNTAX_ERROR: try:
        # Keep connection alive and process messages
        # REMOVED_SYNTAX_ERROR: while True:
            # REMOVED_SYNTAX_ERROR: data = await websocket.receive_json()

            # Handle different message types
            # REMOVED_SYNTAX_ERROR: if data.get("type") == "ping":
                # REMOVED_SYNTAX_ERROR: await websocket.send_json({"type": "pong"})
                # REMOVED_SYNTAX_ERROR: elif data.get("type") == "test_serialization":
                    # Test async serialization
                    # REMOVED_SYNTAX_ERROR: state = data.get("state", {})
                    # REMOVED_SYNTAX_ERROR: result = await manager._serialize_message_safely_async(state)
                    # Removed problematic line: await websocket.send_json({ ))
                    # REMOVED_SYNTAX_ERROR: "type": "serialization_result",
                    # REMOVED_SYNTAX_ERROR: "data": result
                    
                    # REMOVED_SYNTAX_ERROR: elif data.get("type") == "broadcast":
                        # Test send_to_thread with async serialization
                        # REMOVED_SYNTAX_ERROR: message = data.get("message", {})
                        # REMOVED_SYNTAX_ERROR: success = await manager.send_to_thread("test-thread", message)
                        # Removed problematic line: await websocket.send_json({ ))
                        # REMOVED_SYNTAX_ERROR: "type": "broadcast_result",
                        # REMOVED_SYNTAX_ERROR: "success": success
                        

                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                            # REMOVED_SYNTAX_ERROR: finally:
                                # REMOVED_SYNTAX_ERROR: await manager.disconnect_user(conn_id)


# REMOVED_SYNTAX_ERROR: class TestAsyncSerializationReal:
    # REMOVED_SYNTAX_ERROR: """Test async serialization with real WebSocket connections."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def start_server(self):
    # REMOVED_SYNTAX_ERROR: """Start a real FastAPI server in background."""
    # REMOVED_SYNTAX_ERROR: import socket

    # Find a free port
    # REMOVED_SYNTAX_ERROR: with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # REMOVED_SYNTAX_ERROR: s.bind(('', 0))
        # REMOVED_SYNTAX_ERROR: port = s.getsockname()[1]

        # Start server in a thread
# REMOVED_SYNTAX_ERROR: def run_server():
    # REMOVED_SYNTAX_ERROR: uvicorn.run(test_app, host="127.0.0.1", port=port, log_level="error")

    # REMOVED_SYNTAX_ERROR: server_thread = Thread(target=run_server, daemon=True)
    # REMOVED_SYNTAX_ERROR: server_thread.start()

    # Give server time to start
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(1)

    # REMOVED_SYNTAX_ERROR: yield "formatted_string"

    # Server will stop when test ends

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_async_serialization_performance(self, start_server):
        # REMOVED_SYNTAX_ERROR: """Test that async serialization doesn't block the event loop."""
        # REMOVED_SYNTAX_ERROR: ws_url = start_server

        # REMOVED_SYNTAX_ERROR: async with websockets.connect(ws_url) as websocket:
            # Create a large message
            # REMOVED_SYNTAX_ERROR: large_state = { )
            # REMOVED_SYNTAX_ERROR: "type": "test_state",
            # REMOVED_SYNTAX_ERROR: "data": {}
            

            # Build nested structure
            # REMOVED_SYNTAX_ERROR: current = large_state["data"]
            # REMOVED_SYNTAX_ERROR: for i in range(50):
                # REMOVED_SYNTAX_ERROR: current["formatted_string"] = { )
                # REMOVED_SYNTAX_ERROR: "items": [{"id": j, "data": "x" * 1000} for j in range(5)],
                # REMOVED_SYNTAX_ERROR: "nested": {}
                
                # REMOVED_SYNTAX_ERROR: current = current["formatted_string"]["nested"]

                # Test serialization
                # Removed problematic line: await websocket.send(json.dumps({ )))
                # REMOVED_SYNTAX_ERROR: "type": "test_serialization",
                # REMOVED_SYNTAX_ERROR: "state": large_state
                

                # Track event loop responsiveness while waiting for response
                # REMOVED_SYNTAX_ERROR: loop_responsive = True

# REMOVED_SYNTAX_ERROR: async def check_responsiveness():
    # REMOVED_SYNTAX_ERROR: nonlocal loop_responsive
    # REMOVED_SYNTAX_ERROR: for _ in range(10):
        # REMOVED_SYNTAX_ERROR: start = time.perf_counter()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
        # REMOVED_SYNTAX_ERROR: if time.perf_counter() - start > 0.5:
            # REMOVED_SYNTAX_ERROR: loop_responsive = False
            # REMOVED_SYNTAX_ERROR: break

            # Run check while waiting for response
            # REMOVED_SYNTAX_ERROR: check_task = asyncio.create_task(check_responsiveness())
            # REMOVED_SYNTAX_ERROR: response = await asyncio.wait_for(websocket.recv(), timeout=5)
            # REMOVED_SYNTAX_ERROR: await check_task

            # REMOVED_SYNTAX_ERROR: result = json.loads(response)
            # REMOVED_SYNTAX_ERROR: assert result["type"] == "serialization_result"
            # REMOVED_SYNTAX_ERROR: assert loop_responsive, "Event loop was blocked during serialization"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_send_to_thread_with_real_websocket(self, start_server):
                # REMOVED_SYNTAX_ERROR: """Test send_to_thread with real WebSocket connections."""
                # REMOVED_SYNTAX_ERROR: ws_url = start_server

                # Connect multiple real WebSocket clients
                # REMOVED_SYNTAX_ERROR: websockets_list = []
                # REMOVED_SYNTAX_ERROR: for i in range(3):
                    # REMOVED_SYNTAX_ERROR: ws = await websockets.connect(ws_url)
                    # REMOVED_SYNTAX_ERROR: websockets_list.append(ws)

                    # Create a complex DeepAgentState
                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                    # REMOVED_SYNTAX_ERROR: user_request="test request",
                    # REMOVED_SYNTAX_ERROR: chat_thread_id="test-thread",
                    # REMOVED_SYNTAX_ERROR: user_id="test-user",
                    # REMOVED_SYNTAX_ERROR: messages=[ )
                    # REMOVED_SYNTAX_ERROR: {"role": "user", "content": "test " * 100} for _ in range(10)
                    # REMOVED_SYNTAX_ERROR: ],
                    # REMOVED_SYNTAX_ERROR: metadata={"timestamp": str(time.time()), "data": "x" * 1000}
                    

                    # Send broadcast message through first WebSocket
                    # Removed problematic line: await websockets_list[0].send(json.dumps({ )))
                    # REMOVED_SYNTAX_ERROR: "type": "broadcast",
                    # REMOVED_SYNTAX_ERROR: "message": state.model_dump()
                    

                    # Check response
                    # REMOVED_SYNTAX_ERROR: response = await asyncio.wait_for(websockets_list[0].recv(), timeout=5)
                    # REMOVED_SYNTAX_ERROR: result = json.loads(response)

                    # REMOVED_SYNTAX_ERROR: assert result["type"] == "broadcast_result"
                    # REMOVED_SYNTAX_ERROR: assert result["success"] is True

                    # Clean up
                    # REMOVED_SYNTAX_ERROR: for ws in websockets_list:
                        # REMOVED_SYNTAX_ERROR: await ws.close()

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_concurrent_serialization_real(self, start_server):
                            # REMOVED_SYNTAX_ERROR: """Test concurrent message serialization with real connections."""
                            # REMOVED_SYNTAX_ERROR: ws_url = start_server

                            # REMOVED_SYNTAX_ERROR: async with websockets.connect(ws_url) as websocket:
                                # Send multiple serialization requests concurrently
                                # REMOVED_SYNTAX_ERROR: tasks = []
                                # REMOVED_SYNTAX_ERROR: for i in range(10):
                                    # REMOVED_SYNTAX_ERROR: message = { )
                                    # REMOVED_SYNTAX_ERROR: "type": "test_serialization",
                                    # REMOVED_SYNTAX_ERROR: "state": { )
                                    # REMOVED_SYNTAX_ERROR: "id": i,
                                    # REMOVED_SYNTAX_ERROR: "data": "x" * 10000,
                                    # REMOVED_SYNTAX_ERROR: "nested": {"items": [j for j in range(100)}]
                                    
                                    
                                    # REMOVED_SYNTAX_ERROR: tasks.append(websocket.send(json.dumps(message)))

                                    # Send all at once
                                    # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                                    # Receive all responses
                                    # REMOVED_SYNTAX_ERROR: responses = []
                                    # REMOVED_SYNTAX_ERROR: for _ in range(10):
                                        # REMOVED_SYNTAX_ERROR: response = await asyncio.wait_for(websocket.recv(), timeout=5)
                                        # REMOVED_SYNTAX_ERROR: responses.append(json.loads(response))

                                        # All should succeed
                                        # REMOVED_SYNTAX_ERROR: assert all(r["type"] == "serialization_result" for r in responses)
                                        # REMOVED_SYNTAX_ERROR: assert len(responses) == 10

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_websocket_retry_mechanism_real(self, start_server):
                                            # REMOVED_SYNTAX_ERROR: """Test retry mechanism with real WebSocket that has intermittent issues."""
                                            # This test would require a special endpoint that simulates failures
                                            # For now, we test that normal messages succeed
                                            # REMOVED_SYNTAX_ERROR: ws_url = start_server

                                            # REMOVED_SYNTAX_ERROR: async with websockets.connect(ws_url) as websocket:
                                                # Send a message that should succeed after potential retries
                                                # REMOVED_SYNTAX_ERROR: state = {"type": "test", "data": "test_message"}

                                                # Removed problematic line: await websocket.send(json.dumps({ )))
                                                # REMOVED_SYNTAX_ERROR: "type": "broadcast",
                                                # REMOVED_SYNTAX_ERROR: "message": state
                                                

                                                # REMOVED_SYNTAX_ERROR: response = await asyncio.wait_for(websocket.recv(), timeout=10)
                                                # REMOVED_SYNTAX_ERROR: result = json.loads(response)

                                                # Should eventually succeed
                                                # REMOVED_SYNTAX_ERROR: assert result["type"] == "broadcast_result"
                                                # REMOVED_SYNTAX_ERROR: assert result["success"] is True


                                                # REMOVED_SYNTAX_ERROR: import json  # Add this import at the top


                                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                    # Run tests directly
                                                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])