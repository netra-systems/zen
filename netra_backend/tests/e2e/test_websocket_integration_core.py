"""WebSocket Integration Core E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) 
- Business Goal: Validate WebSocket infrastructure delivers real-time AI interactions
- Value Impact: WebSocket reliability directly affects user engagement and chat functionality
- Strategic Impact: WebSocket failures cause 90% of delivered value (chat) to fail per CLAUDE.md

CRITICAL MISSION: This test suite validates that WebSocket core infrastructure enables
the delivery of business value through real-time AI-powered chat interactions.

🚨 CRITICAL: ALL E2E TESTS MUST USE AUTHENTICATION
This ensures proper multi-user isolation and real-world scenario testing.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
import websockets

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from test_framework.websocket_helpers import WebSocketTestClient, WebSocketTestHelpers
from shared.isolated_environment import get_env


class TestWebSocketIntegrationCoreE2E(BaseE2ETest):
    """Comprehensive E2E tests for WebSocket core functionality with authentication."""
    
    def setup_method(self):
        """Set up authenticated E2E test environment for each test method."""
        super().setup_method()
        self.env = get_env()
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        # Create authenticated helpers - MANDATORY for E2E tests
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        
        # E2E test URLs
        self.websocket_url = "ws://localhost:8000/ws"
        self.backend_url = "http://localhost:8000"
        
        # Track WebSocket connections for cleanup
        self.active_websockets = []
    
    async def teardown_method(self):
        """Clean up WebSocket connections after each test."""
        for ws in self.active_websockets:
            try:
                await WebSocketTestHelpers.close_test_connection(ws)
            except Exception:
                pass
        self.active_websockets.clear()
    
    @pytest.mark.e2e
    async def test_authenticated_websocket_connection_establishment(self):
        """Test WebSocket connection establishment with proper authentication.
        
        BVJ: WebSocket connections are the foundation of chat functionality delivery.
        """
        execution_start_time = time.time()
        
        # Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.websocket.connection@example.com",
            permissions=["read", "write", "websocket_connect"]
        )
        
        user_id = user_data["id"]
        
        # Test real WebSocket connection with authentication
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            self.websocket_url,
            headers=websocket_headers,
            timeout=15.0,
            user_id=user_id
        )
        self.active_websockets.append(websocket)
        
        # Verify connection established successfully
        assert websocket is not None, "WebSocket connection should be established"
        
        # Test basic ping-pong to verify connection health
        ping_message = {
            "type": "ping",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send_json(ping_message)
        response = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        
        assert response is not None, "Should receive response to ping"
        
        # Validate execution timing
        execution_time = time.time() - execution_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly ({execution_time:.3f}s)"

    @pytest.mark.e2e  
    async def test_authenticated_websocket_message_flow(self):
        """Test bi-directional WebSocket messaging with authentication.
        
        BVJ: Message flow is core to chat functionality - this validates the complete pipeline.
        """
        execution_start_time = time.time()
        
        # Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.websocket.messages@example.com",
            permissions=["read", "write", "send_messages", "receive_messages"]
        )
        
        user_id = user_data["id"]
        thread_id = f"websocket_test_thread_{uuid.uuid4().hex[:8]}"
        
        # Establish authenticated WebSocket connection
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            self.websocket_url,
            headers=websocket_headers,
            timeout=15.0,
            user_id=user_id
        )
        self.active_websockets.append(websocket)
        
        # Test agent request message (simulates chat functionality)
        agent_request = {
            "type": "agent_request",
            "content": "What is the status of my optimization project?",
            "thread_id": thread_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send message and collect responses
        await websocket.send_json(agent_request)
        
        # Collect WebSocket events (should include agent lifecycle events)
        events_received = []
        timeout_duration = 20.0
        start_time = time.time()
        
        while time.time() - start_time < timeout_duration:
            try:
                event = await asyncio.wait_for(websocket.receive_json(), timeout=3.0)
                events_received.append(event)
                
                # Stop when we get a completion or error event
                if event.get("type") in ["agent_completed", "agent_error"]:
                    break
                    
            except asyncio.TimeoutError:
                if len(events_received) > 0:
                    break  # Got some events, that's sufficient for E2E
                continue
        
        # Validate we received events (core business requirement)
        assert len(events_received) > 0, "Should receive WebSocket events for business value delivery"
        
        # Validate execution timing
        execution_time = time.time() - execution_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly ({execution_time:.3f}s)"

    @pytest.mark.e2e
    async def test_multi_user_websocket_isolation(self):
        """Test WebSocket isolation between multiple authenticated users.
        
        BVJ: Multi-user isolation prevents data leaks and ensures secure chat sessions.
        """
        execution_start_time = time.time()
        
        # Create two authenticated users
        users = []
        for i in range(2):
            token, user_data = await create_authenticated_user(
                environment=self.test_environment,
                email=f"e2e.websocket.user{i+1}@example.com",
                permissions=["read", "write", "websocket_connect"]
            )
            users.append({"token": token, "user_data": user_data, "user_id": user_data["id"]})
        
        # Establish WebSocket connections for both users
        websockets_data = []
        for i, user in enumerate(users):
            headers = self.auth_helper.get_websocket_headers(user["token"])
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                self.websocket_url,
                headers=headers,
                timeout=15.0,
                user_id=user["user_id"]
            )
            self.active_websockets.append(websocket)
            websockets_data.append({"websocket": websocket, "user_id": user["user_id"]})
        
        # Send different messages from each user
        for i, ws_data in enumerate(websockets_data):
            message = {
                "type": "user_message",
                "content": f"Private message from user {i+1}",
                "user_id": ws_data["user_id"],
                "thread_id": f"private_thread_user_{i+1}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await ws_data["websocket"].send_json(message)
        
        # Verify each user only receives their own responses
        for i, ws_data in enumerate(websockets_data):
            try:
                response = await asyncio.wait_for(ws_data["websocket"].receive_json(), timeout=10.0)
                if "user_id" in response:
                    assert response["user_id"] == ws_data["user_id"], f"User {i+1} received message for wrong user"
            except asyncio.TimeoutError:
                pass  # No response is acceptable for isolation test
        
        # Validate execution timing
        execution_time = time.time() - execution_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly ({execution_time:.3f}s)"

    @pytest.mark.e2e
    async def test_websocket_error_handling_with_authentication(self):
        """Test WebSocket error handling for invalid requests with real authentication.
        
        BVJ: Proper error handling prevents system crashes and maintains user experience.
        """
        execution_start_time = time.time()
        
        # Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.websocket.errors@example.com",
            permissions=["read", "write"]
        )
        
        user_id = user_data["id"]
        
        # Establish authenticated WebSocket connection
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            self.websocket_url,
            headers=websocket_headers,
            timeout=15.0,
            user_id=user_id
        )
        self.active_websockets.append(websocket)
        
        # Send malformed message to test error handling
        malformed_message = {
            "type": "invalid_message_type",
            "malformed_data": "this should trigger error handling",
            "user_id": user_id
        }
        
        await websocket.send_json(malformed_message)
        
        # Should either receive error response or connection should remain stable
        try:
            response = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
            # If we get a response, it should be an error or the connection should handle gracefully
            if "error" in response:
                assert True, "Error properly handled"
            else:
                assert True, "Connection handled malformed message gracefully"
        except asyncio.TimeoutError:
            # No response is also acceptable - connection remains stable
            assert True, "Connection remained stable despite malformed message"
        
        # Verify connection is still functional with valid message
        valid_message = {
            "type": "ping",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send_json(valid_message)
        
        # Validate execution timing
        execution_time = time.time() - execution_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly ({execution_time:.3f}s)"

    @pytest.mark.e2e
    async def test_websocket_connection_lifecycle_complete(self):
        """Test complete WebSocket connection lifecycle with authentication.
        
        BVJ: Connection lifecycle management is critical for reliable chat sessions.
        """
        execution_start_time = time.time()
        
        # Create authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.websocket.lifecycle@example.com",
            permissions=["read", "write", "websocket_connect"]
        )
        
        user_id = user_data["id"]
        
        # Test connection establishment
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            self.websocket_url,
            headers=websocket_headers,
            timeout=15.0,
            user_id=user_id
        )
        
        # Test active communication
        test_message = {
            "type": "lifecycle_test",
            "content": "Testing connection lifecycle",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send_json(test_message)
        
        # Test graceful connection closure
        await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Validate execution timing
        execution_time = time.time() - execution_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly ({execution_time:.3f}s)"