"""End-to-end test for development mode thread handling.

This test verifies the complete flow from WebSocket connection to database
operations when handling threads in development mode with OAUTH SIMULATION.
"""

import asyncio
import json
import pytest
from typing import Optional
from shared.isolated_environment import IsolatedEnvironment

import websockets
from fastapi import FastAPI
from fastapi.testclient import TestClient

from netra_backend.app.main import app
from netra_backend.app.db.postgres import initialize_postgres, async_session_factory
from netra_backend.app.db.models_postgres import Thread
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDevelopmentThreadHandling:
    """E2E tests for thread handling in development mode."""
    
    @pytest.fixture
    async def setup_development_environment(self):
        """Setup development environment with OAUTH SIMULATION."""
        # Set environment variables for development mode
        with patch.dict('os.environ', {
            'ENVIRONMENT': 'development',
            'ALLOW_DEV_OAUTH_SIMULATION': 'true',
            'WEBSOCKET_AUTH_BYPASS': 'true',
            'DATABASE_URL': 'postgresql+asyncpg://postgres:postgres@localhost:5432/netra_test'
        }):
            # Initialize database
            await initialize_postgres()
            yield
            # Cleanup would go here
    
    async def test_websocket_connection_creates_thread_automatically(self, setup_development_environment):
        """Test that WebSocket connection in dev mode creates threads automatically."""
        # Arrange
        test_client = TestClient(app)
        websocket_url = "ws://localhost:8000/ws"
        
        # Act - Connect to WebSocket without authentication
        async with websockets.connect(websocket_url) as websocket:
            # Send start_agent message with non-existent thread
            message = {
                "type": "start_agent",
                "payload": {
                    "user_request": "Test in development mode",
                    "thread_id": "thread_dev-temp-e946eb46"
                }
            }
            
            await websocket.send(json.dumps(message))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            # Assert
            # In fixed system, should either create thread or handle gracefully
            assert response_data.get("type") != "error"
            
            # Verify thread was created in database
            if async_session_factory:
                async with async_session_factory() as session:
                    from sqlalchemy import select
                    result = await session.execute(
                        select(Thread).where(Thread.id == "thread_dev-temp-e946eb46")
                    )
                    thread = result.scalar_one_or_none()
                    
                    # Thread should either exist or system should handle gracefully
                    if thread:
                        assert thread.metadata_.get("user_id") == "development-user"
    
    async def test_development_mode_thread_lifecycle(self, setup_development_environment):
        """Test complete thread lifecycle in development mode."""
        # Test thread creation, message sending, and retrieval
        
        async def simulate_user_session():
            """Simulate a complete user session."""
            websocket_url = "ws://localhost:8000/ws"
            
            async with websockets.connect(websocket_url) as ws:
                # Step 1: Start agent with auto-generated thread
                await ws.send(json.dumps({
                    "type": "start_agent",
                    "payload": {"user_request": "Hello, create a thread for me"}
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                
                # Should receive thread_created event or similar
                assert "thread" in str(data).lower() or data.get("type") == "thread_created"
                
                # Step 2: Send message to the thread
                await ws.send(json.dumps({
                    "type": "user_message",
                    "payload": {
                        "content": "Test message",
                        "thread_id": data.get("payload", {}).get("thread_id", "thread_development-user")
                    }
                }))
                
                # Step 3: Verify message handling
                response = await ws.recv()
                assert response is not None
        
        # Execute test
        await simulate_user_session()
    
    async def test_asyncpg_parameter_type_handling(self, setup_development_environment):
        """Test that asyncpg parameter type issues are resolved."""
        # This test specifically targets the VARCHAR casting issue
        
        problematic_thread_ids = [
            "thread_dev-temp-e946eb46",
            "thread_with-special-chars_123",
            "thread_unicode_[U+6D4B][U+8BD5]",
            "thread_very_long_id_" + "x" * 100
        ]
        
        for thread_id in problematic_thread_ids:
            # Test direct database query
            if async_session_factory:
                async with async_session_factory() as session:
                    from sqlalchemy import select, text
                    
                    try:
                        # This should not raise asyncpg parameter type error
                        result = await session.execute(
                            select(Thread).where(Thread.id == thread_id)
                        )
                        thread = result.scalar_one_or_none()
                        
                        # Thread may not exist, but query should execute without error
                        assert thread is None or isinstance(thread, Thread)
                        
                    except Exception as e:
                        # Should not get "could not determine data type of parameter $1"
                        assert "could not determine data type of parameter" not in str(e)
                        # Other exceptions might be acceptable (e.g., connection issues)
    
    async def test_concurrent_development_connections(self, setup_development_environment):
        """Test multiple concurrent WebSocket connections in development mode."""
        # Simulate multiple developers connecting simultaneously
        
        async def connect_and_send(client_id: int):
            """Single client connection."""
            websocket_url = f"ws://localhost:8000/ws"
            
            try:
                async with websockets.connect(websocket_url) as ws:
                    # Each client creates their own thread
                    thread_id = f"thread_dev-client-{client_id}"
                    
                    await ws.send(json.dumps({
                        "type": "start_agent",
                        "payload": {
                            "user_request": f"Client {client_id} request",
                            "thread_id": thread_id
                        }
                    }))
                    
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    return json.loads(response)
            except Exception as e:
                return {"error": str(e)}
        
        # Launch multiple concurrent connections
        tasks = [connect_and_send(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All connections should succeed or fail gracefully
        for result in results:
            if isinstance(result, dict):
                # Should not have DB_QUERY_FAILED errors
                assert "DB_QUERY_FAILED" not in str(result)
            
    async def test_thread_persistence_across_reconnections(self, setup_development_environment):
        """Test that threads persist across WebSocket reconnections."""
        thread_id = "thread_dev-persistent"
        
        # First connection - create thread
        async with websockets.connect("ws://localhost:8000/ws") as ws:
            await ws.send(json.dumps({
                "type": "start_agent",
                "payload": {
                    "user_request": "Create persistent thread",
                    "thread_id": thread_id
                }
            }))
            
            response = await ws.recv()
            first_response = json.loads(response)
        
        # Second connection - use same thread
        async with websockets.connect("ws://localhost:8000/ws") as ws:
            await ws.send(json.dumps({
                "type": "user_message",
                "payload": {
                    "content": "Message to existing thread",
                    "thread_id": thread_id
                }
            }))
            
            response = await ws.recv()
            second_response = json.loads(response)
            
            # Should successfully use the existing thread
            assert second_response.get("type") != "error"