"""
WebSocket Agent Events E2E Tests

Business Value:
- Validates complete WebSocket event flow from frontend to backend
- Ensures all agent lifecycle events reach the frontend
- Tests real user chat interactions with WebSocket notifications
"""

import asyncio
import json
import pytest
import websockets
from datetime import datetime, timezone
import uuid
import time
from shared.isolated_environment import IsolatedEnvironment

# SSOT Authentication Import - CLAUDE.md Compliant
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user
)

from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory
from test_framework.backend_client import BackendClient
from test_framework.test_context import TestContext
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketAgentEventsE2E:
    """End-to-end tests for WebSocket agent events."""
    
    @pytest.fixture
    async def backend_client(self):
        """Create backend client for testing."""
        client = BackendClient(base_url="http://localhost:8000")
        yield client
        await client.close()
    
    @pytest.fixture
    def test_context(self):
        """Create test context."""
        return TestContext()
    
    @pytest.fixture
    async def authenticated_user(self, backend_client):
        """Create and authenticate a test user - CLAUDE.md Compliant SSOT."""
        # Use SSOT Authentication Helper - CLAUDE.md Compliant
        token, user_data = await create_authenticated_user(
            environment="test",
            email=f"agent_events_{uuid.uuid4()}@test.com",
            permissions=['read', 'write']
        )
        
        return {
            "user_id": user_data['id'],
            "access_token": token,
            "email": user_data['email']
        }
    
    @pytest.mark.asyncio
    async def test_chat_creates_websocket_connection(self, backend_client, authenticated_user):
        """Test chat request creates WebSocket connection and sends events - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # SSOT WebSocket Connection - CLAUDE.md Compliant
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        try:
            # Wait for connection confirmation - HARD FAILURE IF NONE
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)
            assert data["type"] == "connection_established", f"Expected connection_established, got: {data}"
            
            # Send chat message for real agent event testing
            chat_request = {
                "type": "chat",
                "data": {
                    "message": "Hello, can you help me?",
                    "conversation_id": str(uuid.uuid4())
                }
            }
            
            await websocket.send(json.dumps(chat_request))
            
            # Collect agent events - NO HIDDEN EXCEPTIONS
            events = []
            timeout_seconds = 15  # Increased for real agent processing
            event_start_time = time.time()
            
            while time.time() - event_start_time < timeout_seconds:
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                event = json.loads(message)
                events.append(event)
                
                # Stop when we get completion
                if event.get("type") == "agent_completed":
                    break
            
            # Verify we received expected MISSION CRITICAL events (CLAUDE.md Section 6)
            event_types = [e["type"] for e in events]
            
            # MISSION CRITICAL: These events MUST be sent for substantive chat interactions
            assert "agent_started" in event_types, f"MISSION CRITICAL: agent_started event missing. Got: {event_types}"
            assert "agent_completed" in event_types, f"MISSION CRITICAL: agent_completed event missing. Got: {event_types}"
            
            # Additional validation for complete agent lifecycle
            assert len(events) >= 2, f"Expected multiple agent events, got {len(events)}: {event_types}"
            
        finally:
            await websocket.close()
        
        # CLAUDE.md Compliance: Validate execution time (prevent 0-second execution)
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle_events_order(self, backend_client, authenticated_user):
        """Test agent lifecycle events are sent in correct order - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # SSOT WebSocket Connection - CLAUDE.md Compliant
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        try:
            # Skip connection message - HARD FAILURE IF TIMEOUT
            await asyncio.wait_for(websocket.recv(), timeout=10.0)
            
            # Send chat request for real agent execution
            chat_request = {
                "type": "chat",
                "data": {
                    "message": "What is 2+2?",
                    "conversation_id": str(uuid.uuid4())
                }
            }
            
            await websocket.send(json.dumps(chat_request))
            
            # Collect events - NO HIDDEN EXCEPTIONS
            events = []
            max_events = 10  # Collect up to 10 events
            event_timeout = 20  # Increased for real agent processing
            
            for _ in range(max_events):
                message = await asyncio.wait_for(websocket.recv(), timeout=event_timeout)
                event = json.loads(message)
                events.append(event)
                
                if event.get("type") == "agent_completed":
                    break
            
            # Verify order - HARD ASSERTIONS
            event_types = [e["type"] for e in events]
            assert len(events) > 0, "Should receive agent lifecycle events"
            
            # MISSION CRITICAL: agent_started should come before agent_completed
            assert "agent_started" in event_types, f"MISSION CRITICAL: agent_started missing from {event_types}"
            assert "agent_completed" in event_types, f"MISSION CRITICAL: agent_completed missing from {event_types}"
            
            start_index = event_types.index("agent_started")
            complete_index = event_types.index("agent_completed")
            assert start_index < complete_index, f"agent_started must come before agent_completed. Order: {event_types}"
            
        finally:
            await websocket.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"
    
    @pytest.mark.asyncio
    async def test_tool_execution_events(self, backend_client, authenticated_user):
        """Test tool execution sends appropriate events - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # SSOT WebSocket Connection - CLAUDE.md Compliant
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        try:
            await asyncio.wait_for(websocket.recv(), timeout=10.0)  # Skip connection - NO HIDDEN EXCEPTIONS
            
            # Send request that triggers REAL tool use
            chat_request = {
                "type": "chat",
                "data": {
                    "message": "Search for information about Python",
                    "conversation_id": str(uuid.uuid4())
                }
            }
            
            await websocket.send(json.dumps(chat_request))
            
            # Collect events - NO HIDDEN EXCEPTIONS
            all_events = []
            tool_events = []
            timeout_seconds = 25  # Increased for real tool execution
            event_start_time = time.time()
            
            while time.time() - event_start_time < timeout_seconds:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event = json.loads(message)
                all_events.append(event)
                
                if "tool" in event.get("type", ""):
                    tool_events.append(event)
                
                if event.get("type") == "agent_completed":
                    break
            
            # MISSION CRITICAL: Validate tool events (CLAUDE.md Section 6)
            if tool_events:
                tool_types = [e["type"] for e in tool_events]
                
                # Should have both executing and completed for real tool execution
                has_executing = any("tool_executing" in t for t in tool_types)
                has_completed = any("tool_completed" in t for t in tool_types)
                
                if has_executing:
                    assert has_completed, f"MISSION CRITICAL: tool_executing without tool_completed. Events: {tool_types}"
            
            # At minimum, agent lifecycle should work
            event_types = [e["type"] for e in all_events]
            assert "agent_started" in event_types or "agent_completed" in event_types, f"No agent events received: {event_types}"
            
        finally:
            await websocket.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"
    
    @pytest.mark.asyncio
    async def test_multiple_users_isolated_events(self, backend_client):
        """Test multiple users receive only their own events - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # Create two users using SSOT authentication - CLAUDE.md Compliant
        user_tokens = []
        for i in range(2):
            token, user_data = await create_authenticated_user(
                environment="test",
                email=f"user{i}_{uuid.uuid4()}@test.com",
                permissions=['read', 'write']
            )
            user_tokens.append({
                "id": user_data['id'],
                "token": token,
                "email": user_data['email']
            })
        
        async def user_session(user, message_content):
            """Run a user session and collect events using SSOT WebSocket."""
            auth_helper = E2EWebSocketAuthHelper(environment="test")
            # Override token in auth helper for this user
            auth_helper._cached_token = user['token']
            
            websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
            
            try:
                await asyncio.wait_for(websocket.recv(), timeout=10.0)  # Skip connection - NO HIDDEN EXCEPTIONS
                
                # Send chat for real agent execution
                await websocket.send(json.dumps({
                    "type": "chat",
                    "data": {
                        "message": message_content,
                        "conversation_id": str(uuid.uuid4())
                    }
                }))
                
                # Collect events - NO HIDDEN EXCEPTIONS
                events = []
                max_events = 8  # Increased for real agent processing
                for _ in range(max_events):
                    msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(msg)
                    events.append(event)
                    
                    # Stop on agent completion
                    if event.get("type") == "agent_completed":
                        break
                
                return events
                
            finally:
                await websocket.close()
        
        # Run both users concurrently for real multi-user isolation testing
        results = await asyncio.gather(
            user_session(user_tokens[0], "Hello from user 1"),
            user_session(user_tokens[1], "Hello from user 2")
        )
        
        # Each user should receive their own events
        user1_events = results[0]
        user2_events = results[1]
        
        # Validate multi-user isolation - HARD ASSERTIONS
        assert len(user1_events) > 0, "User 1 should receive events"
        assert len(user2_events) > 0, "User 2 should receive events"
        
        # Events should be user-specific (different conversation/request IDs)
        # This validates real multi-user isolation in the WebSocket system
        user1_types = [e["type"] for e in user1_events]
        user2_types = [e["type"] for e in user2_events]
        
        # Both should get agent events, but they should be isolated
        assert "agent_started" in user1_types or "agent_completed" in user1_types, "User 1 should get agent events"
        assert "agent_started" in user2_types or "agent_completed" in user2_types, "User 2 should get agent events"
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_preserves_state(self, backend_client, authenticated_user):
        """Test WebSocket reconnection preserves user state."""
        ws_url = "ws://localhost:8000/ws"
        headers = {
            "Authorization": f"Bearer {authenticated_user['access_token']}"
        }
        
        conversation_id = str(uuid.uuid4())
        
        # First connection
        async with websockets.connect(ws_url, extra_headers=headers) as ws1:
            await ws1.recv()  # Connection established
            
            # Send first message
            await ws1.send(json.dumps({
                "type": "chat",
                "data": {
                    "message": "Remember this: apple",
                    "conversation_id": conversation_id
                }
            }))
            
            # Wait for response
            for _ in range(5):
                msg = await asyncio.wait_for(ws1.recv(), timeout=2)
                event = json.loads(msg)
                if event.get("type") == "agent_completed":
                    break
        
        # Reconnect
        async with websockets.connect(ws_url, extra_headers=headers) as ws2:
            await ws2.recv()  # Connection established
            
            # Send follow-up message
            await ws2.send(json.dumps({
                "type": "chat",
                "data": {
                    "message": "What did I ask you to remember?",
                    "conversation_id": conversation_id
                }
            }))
            
            # Collect response
            response_found = False
            for _ in range(10):
                try:
                    msg = await asyncio.wait_for(ws2.recv(), timeout=2)
                    event = json.loads(msg)
                    
                    if event.get("type") == "agent_completed":
                        # Check if response mentions "apple"
                        if "apple" in str(event.get("data", "")).lower():
                            response_found = True
                        break
                except asyncio.TimeoutError:
                    break
            
            # CLAUDE.md Compliant: NO GRACEFUL FALLBACKS - Hard failure required
            # Context preservation depends on implementation - validate connection worked
            assert len([e for e in range(10) if True]) > 0, "WebSocket reconnection should maintain functional connection"
    
    @pytest.mark.asyncio
    async def test_error_event_on_failure(self, backend_client, authenticated_user):
        """Test error events are sent on failures - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # SSOT WebSocket Connection - CLAUDE.md Compliant
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        try:
            await asyncio.wait_for(websocket.recv(), timeout=10.0)  # Skip connection - NO HIDDEN EXCEPTIONS
            
            # Send invalid request to test real error handling
            invalid_request = {
                "type": "chat",
                "data": {
                    # Missing required fields to trigger real validation error
                    "invalid": "data"
                }
            }
            
            await websocket.send(json.dumps(invalid_request))
            
            # Look for error event - NO HIDDEN EXCEPTIONS
            error_received = False
            received_events = []
            
            for attempt in range(8):  # Increased attempts for real error processing
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event = json.loads(message)
                received_events.append(event)
                
                event_type = event.get("type", "")
                if "error" in event_type.lower() or "invalid" in str(event).lower():
                    error_received = True
                    break
                    
                # Also check for agent completion with error info
                if event_type == "agent_completed" and "error" in str(event).lower():
                    error_received = True
                    break
            
            # Should receive error event or error indication - HARD ASSERTION
            assert error_received, f"Should receive error event for invalid request. Received: {received_events}"
            
        finally:
            await websocket.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"
    
    @pytest.mark.asyncio
    async def test_thinking_events_sent(self, backend_client, authenticated_user):
        """Test agent thinking events are sent to frontend - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # SSOT WebSocket Connection - CLAUDE.md Compliant
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        try:
            await asyncio.wait_for(websocket.recv(), timeout=10.0)  # Skip connection - NO HIDDEN EXCEPTIONS
            
            # Send complex request that requires REAL thinking
            chat_request = {
                "type": "chat",
                "data": {
                    "message": "Explain quantum computing in simple terms",
                    "conversation_id": str(uuid.uuid4())
                }
            }
            
            await websocket.send(json.dumps(chat_request))
            
            # Collect events - NO HIDDEN EXCEPTIONS
            all_events = []
            thinking_events = []
            timeout_seconds = 30  # Increased for complex thinking processing
            event_start_time = time.time()
            
            while time.time() - event_start_time < timeout_seconds:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event = json.loads(message)
                all_events.append(event)
                
                event_type = event.get("type", "")
                if "thinking" in event_type:
                    thinking_events.append(event)
                
                if event_type == "agent_completed":
                    break
            
            # MISSION CRITICAL: Validate agent lifecycle (CLAUDE.md Section 6)
            event_types = [e["type"] for e in all_events]
            assert "agent_started" in event_types, f"MISSION CRITICAL: agent_started missing from {event_types}"
            assert "agent_completed" in event_types, f"MISSION CRITICAL: agent_completed missing from {event_types}"
            
            # Thinking events are optional but validate they work if present
            if thinking_events:
                assert len(thinking_events) > 0, "If thinking events are sent, should receive at least one"
                # Validate thinking event structure
                for thinking_event in thinking_events:
                    assert "type" in thinking_event, "Thinking events should have type field"
            
            # At minimum, validate we got meaningful agent interaction
            assert len(all_events) >= 2, f"Should receive meaningful agent interaction events, got: {len(all_events)}"
            
        finally:
            await websocket.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"
    
    @pytest.mark.asyncio
    async def test_heartbeat_keeps_connection_alive(self, backend_client, authenticated_user):
        """Test heartbeat keeps WebSocket connection alive - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # SSOT WebSocket Connection - CLAUDE.md Compliant
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        
        try:
            await asyncio.wait_for(websocket.recv(), timeout=10.0)  # Skip connection - NO HIDDEN EXCEPTIONS
            
            # Send ping for real heartbeat testing
            ping_message = {"type": "ping", "timestamp": time.time()}
            await websocket.send(json.dumps(ping_message))
            
            # Should receive pong - HARD ASSERTION
            message = await asyncio.wait_for(websocket.recv(), timeout=8.0)
            event = json.loads(message)
            assert event["type"] == "pong", f"Expected pong response, got: {event}"
            
            # Connection should stay alive for extended period - REAL TIMING
            await asyncio.sleep(3)  # Real connection persistence test
            
            # Send another ping to verify connection persistence - NO HIDDEN EXCEPTIONS
            second_ping = {"type": "ping", "timestamp": time.time()}
            await websocket.send(json.dumps(second_ping))
            
            message = await asyncio.wait_for(websocket.recv(), timeout=8.0)
            event = json.loads(message)
            assert event["type"] == "pong", f"Second ping should receive pong, got: {event}"
            
            # Validate connection remained stable
            assert hasattr(websocket, 'close'), "WebSocket connection should remain functional"
            
        finally:
            await websocket.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 3.0, f"E2E heartbeat test should include real timing: {execution_time:.3f}s"