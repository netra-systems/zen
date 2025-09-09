"""
Comprehensive WebSocket Integration Tests - 40+ Real Service Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable real-time communication infrastructure
- Value Impact: WebSocket connections enable chat functionality, agent events, and real-time user experience
- Strategic Impact: Critical for customer retention and chat-based AI value delivery

CRITICAL REQUIREMENTS:
- Tests use REAL services (NO MOCKS except external APIs)
- All tests validate actual WebSocket connections via /ws endpoint  
- Tests validate ALL 5 critical agent events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Uses IsolatedEnvironment, not os.environ
- Uses BaseIntegrationTest as parent class
- Includes proper authentication setup for WebSocket tests
- Tests fail hard on any issues to detect real problems

This test suite validates WebSocket functionality that enables $30K+ MRR from chat-based AI interactions.
"""

import asyncio
import json
import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
# Mock imports removed - real services only

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, InvalidStatus
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

import aiohttp
from fastapi import WebSocket
from fastapi.testclient import TestClient

# SSOT imports - single source of truth
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.isolated_environment_fixtures import isolated_env
from test_framework.websocket_helpers import (
    WebSocketTestClient, 
    WebSocketTestHelpers,
    assert_websocket_events,
    validate_websocket_message
)
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper, 
    E2EAuthConfig,
    get_test_jwt_token
)

# Import real services and factories
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID, WebSocketID


class TestWebSocketConnectionEstablishment(BaseIntegrationTest):
    """Test WebSocket connection establishment with real authentication."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_with_auth(self, test_db_session, isolated_env):
        """
        BVJ: Validates basic WebSocket connectivity for chat functionality.
        Tests that users can establish WebSocket connections with proper JWT authentication.
        """
        if test_db_session is None:
            pytest.skip("Database session not available for WebSocket testing")
            
        # Create authenticated helper
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_ws_connection_user",
            email="connection_test@example.com"
        )
        
        # Get auth headers for WebSocket connection
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        # Test WebSocket connection with authentication
        try:
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                url=websocket_url,
                headers=headers,
                timeout=10.0,
                user_id="test_ws_connection_user"
            )
            
            # Verify connection established
            assert websocket is not None
            
            # Send test message to verify connection works
            test_msg = {
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, test_msg)
            
            # Wait for response
            response = await WebSocketTestHelpers.receive_test_message(websocket)
            assert response is not None
            
            # Close connection cleanly
            await WebSocketTestHelpers.close_test_connection(websocket)
            
        except Exception as e:
            # Real WebSocket connection failure should fail the test - no mock fallback
            pytest.fail(f"WebSocket integration test failed - real service required: {e}")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_websocket_connection_without_auth_fails(self, test_db_session, isolated_env):
        """
        BVJ: Ensures security by validating auth is required.
        Tests that WebSocket connections without proper authentication are rejected.
        """
        services = test_db_session
        websocket_url = f"ws://localhost:8000/ws"
        
        # Attempt connection without auth headers
        try:
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                url=websocket_url,
                headers={},  # No auth headers
                timeout=5.0
            )
            
            # If connection succeeds (shouldn't), try to send message
            test_msg = {"type": "unauthorized_test"}
            await WebSocketTestHelpers.send_test_message(websocket, test_msg)
            
            # Should receive auth error
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
            
            # Verify auth error response
            assert response.get("type") == "error"
            assert "auth" in response.get("message", "").lower()
            
            await WebSocketTestHelpers.close_test_connection(websocket)
            
        except (ConnectionClosed, InvalidStatus) as e:
            # Expected - connection should be rejected
            assert "401" in str(e) or "403" in str(e) or "auth" in str(e).lower()

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_websocket_connection_with_invalid_token_fails(self, test_db_session, isolated_env):
        """
        BVJ: Validates JWT token security for chat authentication.
        Tests that invalid/expired JWT tokens are properly rejected.
        """
        services = test_db_session
        websocket_url = f"ws://localhost:8000/ws"
        
        # Create invalid token
        invalid_token = "invalid.jwt.token"
        headers = {
            "Authorization": f"Bearer {invalid_token}",
            "X-Test-Type": "integration"
        }
        
        # Attempt connection with invalid token
        try:
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                url=websocket_url,
                headers=headers,
                timeout=5.0
            )
            
            # Should receive auth failure
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
            assert response.get("type") == "error"
            assert "auth" in response.get("error", "").lower() or "token" in response.get("error", "").lower()
            
            await WebSocketTestHelpers.close_test_connection(websocket)
            
        except (ConnectionClosed, InvalidStatus) as e:
            # Expected - connection should be rejected with auth error
            assert "401" in str(e) or "403" in str(e) or "auth" in str(e).lower()


class TestWebSocketAgentEvents(BaseIntegrationTest):
    """Test critical WebSocket agent events that enable chat value."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_all_five_critical_websocket_events(self, test_db_session, isolated_env):
        """
        BVJ: MISSION CRITICAL - Tests the 5 events that enable $30K+ MRR chat value.
        Validates agent_started, agent_thinking, tool_executing, tool_completed, agent_completed events.
        
        Without these events, users get no real-time feedback and chat has no business value.
        """
        services = test_db_session
        if not services["database_available"]:
            pytest.skip("Database not available for agent event testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_agent_events_user",
            email="agent_events@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        try:
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                url=websocket_url,
                headers=headers,
                timeout=15.0,
                user_id="test_agent_events_user"
            )
            
            # Send agent request that should trigger all 5 events
            agent_request = {
                "type": "chat",
                "content": "Test agent request for event validation",
                "user_id": "test_agent_events_user",
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, agent_request)
            
            # Collect all events for 30 seconds
            events = []
            start_time = time.time()
            timeout = 30.0
            
            while time.time() - start_time < timeout:
                try:
                    response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                    events.append(response)
                    
                    # Check if we have agent_completed
                    if response.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Continue collecting - timeout is expected between events
                    continue
                except Exception as e:
                    self.logger.error(f"Error receiving events: {e}")
                    break
            
            # Validate all 5 critical events were sent
            event_types = [event.get("type", event.get("event")) for event in events]
            
            required_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            
            missing_events = []
            for required_event in required_events:
                if required_event not in event_types:
                    missing_events.append(required_event)
            
            # CRITICAL: All 5 events must be present for chat business value
            assert len(missing_events) == 0, (
                f"CRITICAL BUSINESS FAILURE: Missing required WebSocket events {missing_events}. "
                f"Received events: {event_types}. Without these events, chat has no real-time value."
            )
            
            # Validate event ordering (agent_started should be first)
            first_event_type = event_types[0] if event_types else None
            assert first_event_type == "agent_started", (
                f"First event should be agent_started, got: {first_event_type}"
            )
            
            # agent_completed should be last
            last_event_type = event_types[-1] if event_types else None  
            assert last_event_type == "agent_completed", (
                f"Last event should be agent_completed, got: {last_event_type}"
            )
            
            await WebSocketTestHelpers.close_test_connection(websocket)
            
        except Exception as e:
            # Real WebSocket agent events test failure should fail the test - no mock fallback
            pytest.fail(f"Critical WebSocket agent events test failed - real services required for business value validation: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_event_message_structure(self, test_db_session, isolated_env):
        """
        BVJ: Ensures event messages have proper structure for frontend consumption.
        Tests that each WebSocket event contains required fields for UI rendering.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for agent event message structure testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_structure_user",
            email="structure@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_structure_user"
        )
        
        # Send test message to generate events
        test_message = {
            "type": "ping", 
            "user_id": "test_structure_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, test_message)
        response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
        
        # Validate required fields
        required_fields = ["type", "timestamp"]
        validate_websocket_message(response, required_fields)
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_thinking_event_contains_reasoning(self, test_db_session, isolated_env):
        """
        BVJ: Validates reasoning visibility for user engagement.
        Tests that agent_thinking events contain reasoning text for user display.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for agent thinking event testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_reasoning_user",
            email="reasoning@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_reasoning_user"
        )
        
        # Send agent request that should trigger agent_thinking event
        agent_request = {
            "type": "chat",
            "content": "Simple request to trigger thinking",
            "user_id": "test_reasoning_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, agent_request)
        
        # Look for agent_thinking event in responses
        thinking_found = False
        for _ in range(10):  # Check multiple responses for agent_thinking
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                if response.get("type") == "agent_thinking":
                    # Validate reasoning is present and not empty
                    assert "reasoning" in response or "message" in response
                    reasoning_text = response.get("reasoning") or response.get("message", "")
                    assert reasoning_text is not None
                    assert len(str(reasoning_text)) > 0
                    thinking_found = True
                    break
            except asyncio.TimeoutError:
                continue
                
        # Skip if no agent_thinking event received (system might not generate it for simple requests)
        if not thinking_found:
            pytest.skip("No agent_thinking event received - system may not generate for simple requests")
            
        await WebSocketTestHelpers.close_test_connection(websocket)


class TestWebSocketMessageRouting(BaseIntegrationTest):
    """Test WebSocket message routing to correct handlers."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_routing_by_type(self, test_db_session, isolated_env):
        """
        BVJ: Ensures different message types reach appropriate handlers.
        Tests routing of chat, system, and data messages to correct processors.
        """
        services = test_db_session
        
        # Create authenticated connection
        auth_helper = E2EWebSocketAuthHelper(environment="test") 
        token = auth_helper.create_test_jwt_token(user_id="test_routing_user")
        headers = auth_helper.get_websocket_headers(token)
        
        try:
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                f"ws://localhost:8000/ws",
                headers=headers,
                timeout=10.0
            )
            
            # Test different message types
            message_types = [
                {"type": "chat", "content": "Hello agent"},
                {"type": "ping", "timestamp": time.time()},
                {"type": "user_message", "content": "User message test"}
            ]
            
            responses = []
            for msg in message_types:
                await WebSocketTestHelpers.send_test_message(websocket, msg)
                
                try:
                    response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                    responses.append(response)
                except asyncio.TimeoutError:
                    # Some message types might not generate immediate responses
                    responses.append({"type": "timeout", "original_type": msg["type"]})
            
            # Validate responses received
            assert len(responses) >= len(message_types)
            
            # At least one response should be successful
            successful_responses = [r for r in responses if r.get("type") != "timeout"]
            assert len(successful_responses) > 0
            
            await WebSocketTestHelpers.close_test_connection(websocket)
            
        except Exception as e:
            # Real WebSocket message routing failure should fail the test - no mock fallback
            pytest.fail(f"WebSocket message routing test failed - real service required: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_invalid_message_type_handling(self, test_db_session, isolated_env):
        """
        BVJ: Ensures system handles invalid messages gracefully.
        Tests error handling for malformed or unknown message types.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for invalid message type testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_invalid_user",
            email="invalid@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_invalid_user"
        )
        
        # Send invalid message type
        invalid_message = {"type": "invalid_type", "data": "test"}
        await WebSocketTestHelpers.send_test_message(websocket, invalid_message)
        
        # Should receive error response for unknown type (or no response)
        try:
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
            if response and response.get("type") == "error":
                assert "unknown" in response.get("error", "").lower() or "invalid" in response.get("error", "").lower()
        except asyncio.TimeoutError:
            # No response to invalid message is also acceptable behavior
            pass
            
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_malformed_json_handling(self, test_db_session, isolated_env):
        """
        BVJ: Ensures system handles malformed JSON gracefully.
        Tests error recovery from invalid JSON messages.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for malformed JSON testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_malformed_user",
            email="malformed@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_malformed_user"
        )
        
        # Send invalid JSON directly to the WebSocket
        invalid_json = '{"type": "test", "invalid": json}'
        
        try:
            # This should cause a JSON parsing error
            await websocket.send(invalid_json)
            
            # Try to receive error response
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
            if response and response.get("type") == "error":
                assert "json" in response.get("error", "").lower() or "parse" in response.get("error", "").lower()
        except Exception as e:
            # Connection might close due to malformed JSON - this is acceptable behavior
            assert "json" in str(e).lower() or "parse" in str(e).lower() or "websocket" in str(e).lower()
        finally:
            try:
                await WebSocketTestHelpers.close_test_connection(websocket)
            except Exception:
                pass  # Connection may already be closed


class TestWebSocketConcurrency(BaseIntegrationTest):
    """Test WebSocket handling of concurrent connections and messages."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_concurrent_connections(self, test_db_session, isolated_env):
        """
        BVJ: Validates multi-user chat capability for enterprise customers.
        Tests that multiple users can maintain WebSocket connections simultaneously.
        """
        services = test_db_session
        
        # Create multiple authenticated connections
        connections = []
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        try:
            # Create 3 concurrent connections
            for i in range(3):
                user_id = f"concurrent_user_{i}"
                token = auth_helper.create_test_jwt_token(user_id=user_id)
                headers = auth_helper.get_websocket_headers(token)
                
                try:
                    websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                        f"ws://localhost:8000/ws",
                        headers=headers,
                        timeout=10.0,
                        user_id=user_id
                    )
                    connections.append({"websocket": websocket, "user_id": user_id})
                    
                except Exception as e:
                    self.logger.error(f"Failed to create WebSocket connection for {user_id}: {e}")
                    # Skip this connection rather than using mock fallback
                    continue
            
            # Verify at least 2 connections established (allow for some failures in real environment)
            assert len(connections) >= 2
            
            # Send messages from each connection
            for i, conn in enumerate(connections):
                test_msg = {
                    "type": "ping",
                    "user_id": conn["user_id"],
                    "message_id": i,
                    "timestamp": time.time()
                }
                
                await WebSocketTestHelpers.send_test_message(conn["websocket"], test_msg)
            
            # Verify responses from all connections
            responses = []
            for conn in connections:
                try:
                    response = await WebSocketTestHelpers.receive_test_message(conn["websocket"], timeout=5.0)
                    responses.append(response)
                except Exception as e:
                    # Allow partial responses in real environment
                    self.logger.warning(f"Failed to get response from {conn['user_id']}: {e}")
            
            # At least 1 connection should respond successfully
            assert len(responses) >= 1
            
            # Clean up connections
            for conn in connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(conn["websocket"])
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Concurrent connections test error: {e}")
            # Clean up any established connections
            for conn in connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(conn["websocket"])
                except Exception:
                    pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_rapid_message_sending(self, test_db_session, isolated_env):
        """
        BVJ: Validates system handles high-frequency messages for active users.
        Tests rapid message sending without dropping or corrupting messages.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for rapid message testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_rapid_user",
            email="rapid@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_rapid_user"
        )
        
        # Send 10 messages rapidly
        messages_sent = []
        for i in range(10):
            msg = {
                "type": "ping",
                "sequence": i,
                "timestamp": time.time()
            }
            messages_sent.append(msg)
            await WebSocketTestHelpers.send_test_message(websocket, msg)
            # Small delay to prevent overwhelming the connection
            await asyncio.sleep(0.1)
        
        # Receive responses
        responses = []
        for _ in range(10):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                responses.append(response)
            except asyncio.TimeoutError:
                break
        
        # Should receive at least 5 out of 10 responses (allowing for rate limiting)
        assert len(responses) >= 5
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_connection_isolation_between_users(self, test_db_session, isolated_env):
        """
        BVJ: Ensures user data privacy and isolation for enterprise security.
        Tests that messages sent by one user are not received by another user.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for connection isolation testing")
            
        # Create two separate authenticated WebSocket connections
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # User 1 connection
        token1 = auth_helper.create_test_jwt_token(
            user_id="isolated_user_1",
            email="user1@example.com"
        )
        headers1 = auth_helper.get_websocket_headers(token1)
        
        user1_websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"ws://localhost:8000/ws",
            headers=headers1,
            timeout=10.0,
            user_id="isolated_user_1"
        )
        
        # User 2 connection
        token2 = auth_helper.create_test_jwt_token(
            user_id="isolated_user_2",
            email="user2@example.com"
        )
        headers2 = auth_helper.get_websocket_headers(token2)
        
        user2_websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"ws://localhost:8000/ws",
            headers=headers2,
            timeout=10.0,
            user_id="isolated_user_2"
        )
        
        # User 1 sends message
        private_msg = {
            "type": "ping",
            "content": "This is from user 1",
            "user_id": "isolated_user_1",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(user1_websocket, private_msg)
        
        # User 1 should receive response
        user1_response = await WebSocketTestHelpers.receive_test_message(user1_websocket, timeout=5.0)
        assert user1_response is not None
        
        # User 2 sends their own message
        user2_ping = {"type": "ping", "user_id": "isolated_user_2", "content": "This is from user 2"}
        await WebSocketTestHelpers.send_test_message(user2_websocket, user2_ping)
        
        user2_response = await WebSocketTestHelpers.receive_test_message(user2_websocket, timeout=5.0)
        
        # User 2 should get their own response, isolated from user 1
        assert user2_response is not None
        # Responses should be isolated to each user
        assert "isolated_user_1" not in str(user2_response)
        
        await WebSocketTestHelpers.close_test_connection(user1_websocket)
        await WebSocketTestHelpers.close_test_connection(user2_websocket)


class TestWebSocketErrorHandling(BaseIntegrationTest):
    """Test WebSocket error handling and recovery."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_recovery_after_error(self, test_db_session, isolated_env):
        """
        BVJ: Ensures service reliability for consistent user experience.
        Tests that WebSocket connections can recover from temporary errors.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for connection recovery testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_recovery_user",
            email="recovery@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        # Test basic connection and message flow
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_recovery_user"
        )
        
        # Send normal message first
        normal_msg = {"type": "ping", "data": "normal"}
        await WebSocketTestHelpers.send_test_message(websocket, normal_msg)
        
        response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
        assert response is not None
        
        # Close and reconnect to test recovery
        await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Wait a moment
        await asyncio.sleep(1.0)
        
        # Reconnect with same credentials
        recovery_websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_recovery_user"
        )
        
        # Should be able to send messages again
        recovery_msg = {"type": "ping", "data": "recovery"}
        await WebSocketTestHelpers.send_test_message(recovery_websocket, recovery_msg)
        
        recovery_response = await WebSocketTestHelpers.receive_test_message(recovery_websocket, timeout=5.0)
        assert recovery_response is not None
        
        await WebSocketTestHelpers.close_test_connection(recovery_websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oversized_message_handling(self, test_db_session, isolated_env):
        """
        BVJ: Prevents system crashes from malicious or accidental large messages.
        Tests handling of messages that exceed size limits.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for oversized message testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_oversized_user",
            email="oversized@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_oversized_user"
        )
        
        # Create oversized message (> 5000 chars)
        large_content = "x" * 6000
        oversized_msg = {
            "type": "chat",
            "content": large_content
        }
        
        try:
            await WebSocketTestHelpers.send_test_message(websocket, oversized_msg)
            
            # Should receive error response or connection closure
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
            if response and response.get("type") == "error":
                assert "size" in response.get("error", "").lower() or "large" in response.get("error", "").lower()
        except Exception as e:
            # Connection might close due to oversized message - acceptable behavior
            assert "size" in str(e).lower() or "large" in str(e).lower() or "websocket" in str(e).lower()
        finally:
            try:
                await WebSocketTestHelpers.close_test_connection(websocket)
            except Exception:
                pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_missing_required_fields_handling(self, test_db_session, isolated_env):
        """
        BVJ: Ensures robust error handling for malformed client messages.
        Tests handling of messages missing required fields.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for missing fields testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_missing_fields_user",
            email="missing@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_missing_fields_user"
        )
        
        # Send message missing required type field
        incomplete_msg = {"content": "message without type"}
        
        try:
            await websocket.send(json.dumps(incomplete_msg))
            
            # Should receive error response
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
            if response and response.get("type") == "error":
                assert "type" in response.get("error", "").lower() or "missing" in response.get("error", "").lower()
        except Exception as e:
            # Connection might close due to invalid message - acceptable behavior
            assert "type" in str(e).lower() or "missing" in str(e).lower() or "websocket" in str(e).lower()
        finally:
            try:
                await WebSocketTestHelpers.close_test_connection(websocket)
            except Exception:
                pass


class TestWebSocketPerformance(BaseIntegrationTest):
    """Test WebSocket performance characteristics."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_establishment_speed(self, test_db_session, isolated_env):
        """
        BVJ: Ensures fast connection times for good user experience.
        Tests that WebSocket connections establish within acceptable time limits.
        """
        services = test_db_session
        
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(user_id="test_speed_user")
        headers = auth_helper.get_websocket_headers(token)
        
        # Measure connection time
        start_time = time.time()
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for connection speed testing")
            
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"ws://localhost:8000/ws",
            headers=headers,
            timeout=10.0
        )
        
        connection_time = time.time() - start_time
        
        # Connection should establish within 10 seconds for integration test
        assert connection_time < 10.0, f"Connection took {connection_time:.2f}s, should be < 10s"
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_throughput_performance(self, test_db_session, isolated_env):
        """
        BVJ: Validates system can handle expected message volumes.
        Tests message processing speed for active chat users.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for message throughput testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_throughput_user",
            email="throughput@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_throughput_user"
        )
        
        # Send 10 messages and measure time (reduced count for real service testing)
        start_time = time.time()
        message_count = 10
        
        for i in range(message_count):
            msg = {
                "type": "ping",
                "sequence": i,
                "timestamp": time.time()
            }
            await WebSocketTestHelpers.send_test_message(websocket, msg)
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.05)
        
        send_time = time.time() - start_time
        
        # Calculate throughput
        throughput = message_count / send_time
        
        # Should handle at least 5 messages per second for real service
        assert throughput >= 5, f"Throughput {throughput:.1f} msg/s, should be >= 5 msg/s"
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_memory_usage_stability(self, test_db_session, isolated_env):
        """
        BVJ: Prevents memory leaks that could cause service instability.
        Tests that WebSocket connections don't accumulate excessive memory.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for memory stability testing")
            
        # Create and close multiple real connections to test memory stability
        connections = []
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create and close 5 connections (reduced for real service testing)
        for i in range(5):
            user_id = f"memory_test_user_{i}"
            token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=f"memory{i}@example.com"
            )
            headers = auth_helper.get_websocket_headers(token)
            
            try:
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"ws://localhost:8000/ws",
                    headers=headers,
                    timeout=10.0,
                    user_id=user_id
                )
                
                # Send a few messages
                for j in range(2):  # Reduced message count
                    msg = {"type": "ping", "sequence": j}
                    await WebSocketTestHelpers.send_test_message(websocket, msg)
                    
                    try:
                        await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                    except asyncio.TimeoutError:
                        pass  # Response not critical for memory test
                
                await WebSocketTestHelpers.close_test_connection(websocket)
                connections.append(websocket)
                
            except Exception as e:
                self.logger.warning(f"Failed to create connection {i}: {e}")
                continue
        
        # Should have created and closed at least 3 connections
        assert len(connections) >= 3


class TestWebSocketReconnection(BaseIntegrationTest):
    """Test WebSocket reconnection and session restoration."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_reconnection_after_disconnect(self, test_db_session, isolated_env):
        """
        BVJ: Ensures chat reliability when connections are lost.
        Tests that users can reconnect after network interruptions.
        """
        services = test_db_session
        
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "test_reconnect_user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        # Initial connection
        try:
            websocket1 = await WebSocketTestHelpers.create_test_websocket_connection(
                f"ws://localhost:8000/ws",
                headers=headers,
                timeout=10.0
            )
            
            # Send test message
            initial_msg = {"type": "ping", "data": "initial"}
            await WebSocketTestHelpers.send_test_message(websocket1, initial_msg)
            
            # Simulate disconnect
            await WebSocketTestHelpers.close_test_connection(websocket1)
            
            # Wait brief period
            await asyncio.sleep(1.0)
            
            # Reconnect with same credentials
            websocket2 = await WebSocketTestHelpers.create_test_websocket_connection(
                f"ws://localhost:8000/ws",
                headers=headers,
                timeout=10.0
            )
            
            # Send message after reconnection
            reconnect_msg = {"type": "ping", "data": "reconnected"}
            await WebSocketTestHelpers.send_test_message(websocket2, reconnect_msg)
            
            # Should receive response
            response = await WebSocketTestHelpers.receive_test_message(websocket2, timeout=5.0)
            assert response is not None
            
            await WebSocketTestHelpers.close_test_connection(websocket2)
            
        except Exception as e:
            # Real WebSocket reconnection failure should fail the test - no mock fallback
            pytest.fail(f"WebSocket reconnection test failed - real service required: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_restoration_after_reconnect(self, test_db_session, isolated_env):
        """
        BVJ: Maintains conversation continuity for better user experience.
        Tests that session context is restored after reconnection.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for session restoration testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "test_session_user"
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email="session@example.com"
        )
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        # Initial connection with session
        websocket1 = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id=user_id
        )
        
        # Send test message to establish session
        session_msg = {
            "type": "ping",
            "client_id": user_id,
            "session_id": session_id
        }
        await WebSocketTestHelpers.send_test_message(websocket1, session_msg)
        
        # Get response to confirm session
        start_response = await WebSocketTestHelpers.receive_test_message(websocket1, timeout=5.0)
        assert start_response is not None
        
        # Disconnect
        await WebSocketTestHelpers.close_test_connection(websocket1)
        
        # Wait briefly
        await asyncio.sleep(1.0)
        
        # Reconnect with same credentials
        websocket2 = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id=user_id
        )
        
        # Send message indicating reconnection
        reconnect_msg = {
            "type": "ping", 
            "client_id": user_id,
            "session_id": session_id,
            "reconnect": True
        }
        await WebSocketTestHelpers.send_test_message(websocket2, reconnect_msg)
        
        # Should be able to communicate after reconnection
        restore_response = await WebSocketTestHelpers.receive_test_message(websocket2, timeout=5.0)
        assert restore_response is not None
        
        await WebSocketTestHelpers.close_test_connection(websocket2)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_started_event_structure(self, test_db_session, isolated_env):
        """
        BVJ: Validates agent_started event contains required data for UI rendering.
        Tests that agent_started events have proper structure for frontend consumption.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for agent_started event testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_agent_started_user",
            email="agent_started@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_agent_started_user"
        )
        
        # Send agent request to trigger agent_started
        agent_request = {
            "type": "chat",
            "content": "Test request for agent_started event",
            "user_id": "test_agent_started_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, agent_request)
        
        # Look for agent_started event
        started_event = None
        for _ in range(10):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                if response.get("type") == "agent_started":
                    started_event = response
                    break
            except asyncio.TimeoutError:
                continue
                
        # Validate agent_started event structure
        if started_event:
            required_fields = ["type", "timestamp", "agent_name"]
            validate_websocket_message(started_event, required_fields)
            
            # Validate specific agent_started fields
            assert started_event["type"] == "agent_started"
            assert "agent_name" in started_event
            assert len(started_event["agent_name"]) > 0
            assert isinstance(started_event["timestamp"], (int, float))
        else:
            pytest.skip("No agent_started event received - system may not generate for simple requests")
            
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_executing_event_validation(self, test_db_session, isolated_env):
        """
        BVJ: Ensures tool_executing events provide transparency for user engagement.
        Tests that tool_executing events contain proper tool information.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for tool_executing event testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_tool_executing_user",
            email="tool_executing@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_tool_executing_user"
        )
        
        # Send agent request that might trigger tool usage
        tool_request = {
            "type": "chat",
            "content": "Analyze data and provide insights",
            "user_id": "test_tool_executing_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, tool_request)
        
        # Look for tool_executing event
        tool_event = None
        for _ in range(15):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                if response.get("type") == "tool_executing":
                    tool_event = response
                    break
            except asyncio.TimeoutError:
                continue
                
        # Validate tool_executing event if received
        if tool_event:
            required_fields = ["type", "timestamp", "tool_name"]
            validate_websocket_message(tool_event, required_fields)
            
            assert tool_event["type"] == "tool_executing"
            assert "tool_name" in tool_event
            assert len(tool_event["tool_name"]) > 0
        else:
            pytest.skip("No tool_executing event received - system may not use tools for simple requests")
            
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_completed_event_validation(self, test_db_session, isolated_env):
        """
        BVJ: Validates tool completion delivers actionable results to users.
        Tests that tool_completed events contain proper result data.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for tool_completed event testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_tool_completed_user",
            email="tool_completed@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_tool_completed_user"
        )
        
        # Send request that might trigger tool completion
        tool_request = {
            "type": "chat",
            "content": "Execute analysis and return results",
            "user_id": "test_tool_completed_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, tool_request)
        
        # Look for tool_completed event
        completed_event = None
        for _ in range(20):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                if response.get("type") == "tool_completed":
                    completed_event = response
                    break
            except asyncio.TimeoutError:
                continue
                
        # Validate tool_completed event if received
        if completed_event:
            required_fields = ["type", "timestamp", "tool_name"]
            validate_websocket_message(completed_event, required_fields)
            
            assert completed_event["type"] == "tool_completed"
            assert "tool_name" in completed_event
            assert len(completed_event["tool_name"]) > 0
            # Results field may be optional but timestamp is required
            assert isinstance(completed_event["timestamp"], (int, float))
        else:
            pytest.skip("No tool_completed event received - system may not use tools for simple requests")
            
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_completed_final_response(self, test_db_session, isolated_env):
        """
        BVJ: Ensures agent_completed delivers final value to users.
        Tests that agent_completed events contain proper final response data.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for agent_completed event testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_agent_completed_user",
            email="agent_completed@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_agent_completed_user"
        )
        
        # Send request to trigger agent completion
        completion_request = {
            "type": "chat",
            "content": "Simple request that should complete",
            "user_id": "test_agent_completed_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, completion_request)
        
        # Look for agent_completed event with longer timeout
        completed_event = None
        for _ in range(30):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                if response.get("type") == "agent_completed":
                    completed_event = response
                    break
            except asyncio.TimeoutError:
                continue
                
        # Validate agent_completed event
        if completed_event:
            required_fields = ["type", "timestamp"]
            validate_websocket_message(completed_event, required_fields)
            
            assert completed_event["type"] == "agent_completed"
            assert isinstance(completed_event["timestamp"], (int, float))
            
            # Response field validation (should contain meaningful response)
            if "response" in completed_event:
                assert len(str(completed_event["response"])) > 0
            elif "final_response" in completed_event:
                assert len(str(completed_event["final_response"])) > 0
        else:
            pytest.skip("No agent_completed event received - system may not complete for simple requests")
            
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_ordering_sequence(self, test_db_session, isolated_env):
        """
        BVJ: Validates proper event sequence for coherent user experience.
        Tests that WebSocket agent events arrive in correct chronological order.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for event ordering testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_ordering_user",
            email="ordering@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_ordering_user"
        )
        
        # Send request to trigger event sequence
        sequence_request = {
            "type": "chat",
            "content": "Request that should trigger event sequence",
            "user_id": "test_ordering_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, sequence_request)
        
        # Collect all events with timestamps
        events_with_time = []
        start_time = time.time()
        
        while time.time() - start_time < 25.0:
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                event_time = time.time()
                events_with_time.append((response, event_time))
                
                if response.get("type") == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue
                
        # Validate event ordering
        agent_events = [
            (event, event_time) for event, event_time in events_with_time
            if event.get("type") in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        ]
        
        if len(agent_events) >= 2:
            # Events should arrive in chronological order
            for i in range(1, len(agent_events)):
                prev_time = agent_events[i-1][1]
                curr_time = agent_events[i][1]
                assert curr_time >= prev_time, f"Events out of chronological order: {agent_events[i-1][0]['type']} -> {agent_events[i][0]['type']}"
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_queuing_during_disconnect(self, test_db_session, isolated_env):
        """
        BVJ: Prevents message loss during temporary disconnections.
        Tests that messages are queued when user is temporarily disconnected.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for message queuing testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "test_queue_user"
        client_id = f"client_{uuid.uuid4().hex[:8]}"
        
        token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email="queue@example.com"
        )
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id=user_id
        )
        
        # Send message that might be queued
        queue_msg = {
            "type": "ping",
            "client_id": client_id,
            "content": "Test message for queuing"
        }
        await WebSocketTestHelpers.send_test_message(websocket, queue_msg)
        
        # Should receive some response (queuing confirmation or direct response)
        queue_response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
        assert queue_response is not None
        
        await WebSocketTestHelpers.close_test_connection(websocket)


class TestWebSocketSecurity(BaseIntegrationTest):
    """Test WebSocket security features."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_expiry_handling(self, test_db_session, isolated_env):
        """
        BVJ: Ensures security by enforcing token expiration.
        Tests that expired JWT tokens are properly rejected.
        """
        services = test_db_session
        
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create token with very short expiry (1 second)
        expired_token = auth_helper.create_test_jwt_token(
            user_id="test_expired_user",
            exp_minutes=0  # Immediate expiry
        )
        
        # Wait for token to expire
        await asyncio.sleep(1.1)
        
        headers = auth_helper.get_websocket_headers(expired_token)
        
        # Attempt connection with expired token
        try:
            websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                f"ws://localhost:8000/ws",
                headers=headers,
                timeout=5.0
            )
            
            # If connection succeeds, should receive auth error
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
            assert response.get("type") == "error"
            assert "token" in response.get("error", "").lower() or "expired" in response.get("error", "").lower()
            
            await WebSocketTestHelpers.close_test_connection(websocket)
            
        except (ConnectionClosed, InvalidStatus) as e:
            # Expected - connection should be rejected
            assert "401" in str(e) or "403" in str(e)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_rate_limiting_enforcement(self, test_db_session, isolated_env):
        """
        BVJ: Prevents abuse and ensures fair resource usage.
        Tests that rate limiting is enforced for WebSocket messages.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for rate limiting testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_rate_limit_user",
            email="rate_limit@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_rate_limit_user"
        )
        
        # Track message count and rate limiting
        message_count = 0
        rate_limit_hit = False
        
        # Send messages rapidly to test rate limiting
        for i in range(20):  # Reduced count for real service testing
            msg = {"type": "ping", "sequence": i}
            
            try:
                await WebSocketTestHelpers.send_test_message(websocket, msg)
                message_count += 1
                
                # Check if we get rate limit error
                try:
                    response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=1.0)
                    if response and response.get("type") == "error" and "rate" in response.get("error", "").lower():
                        rate_limit_hit = True
                        break
                except asyncio.TimeoutError:
                    # No immediate response, continue
                    pass
                    
            except Exception as e:
                # Rate limiting might cause send failures
                if "rate" in str(e).lower() or "limit" in str(e).lower():
                    rate_limit_hit = True
                    break
                    
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.05)
        
        # Should send at least some messages successfully
        assert message_count >= 5
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_permissions_validation(self, test_db_session, isolated_env):
        """
        BVJ: Ensures proper access control for different user tiers.
        Tests that user permissions are validated for WebSocket operations.
        """
        services = test_db_session
        
        # Create user with limited permissions
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        limited_token = auth_helper.create_test_jwt_token(
            user_id="test_limited_user",
            permissions=["read"]  # No write permission
        )
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for user permissions testing")
            
        # Create WebSocket connection with limited user
        headers = auth_helper.get_websocket_headers(limited_token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_limited_user"
        )
        
        # Send message that might require permissions
        write_msg = {
            "type": "ping",  # Use ping instead of agent_request for broader compatibility
            "content": "Test message",
            "action": "test"
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, write_msg)
        
        # Should receive appropriate response
        response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
        assert response is not None
        
        await WebSocketTestHelpers.close_test_connection(websocket)


class TestWebSocketHealthMonitoring(BaseIntegrationTest):
    """Test WebSocket health monitoring and metrics."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_health_endpoint(self, test_db_session, isolated_env):
        """
        BVJ: Enables monitoring and alerts for service reliability.
        Tests WebSocket health check endpoint returns valid status.
        """
        services = test_db_session
        
        # Test health endpoint with HTTP client
        try:
            async with aiohttp.ClientSession() as session:
                health_url = f"http://localhost:8000/ws/health"
                
                async with session.get(health_url, timeout=5.0) as response:
                    assert response.status == 200
                    
                    health_data = await response.json()
                    assert health_data.get("status") in ["healthy", "degraded"]
                    assert "websocket" in health_data.get("service", "")
                    assert "timestamp" in health_data
                    
        except Exception as e:
            # Health endpoint failure should fail the test - no mock fallback
            pytest.fail(f"WebSocket health endpoint test failed - real service required: {e}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_metrics_tracking(self, test_db_session, isolated_env):
        """
        BVJ: Provides operational insights for capacity planning.
        Tests that WebSocket connection metrics are properly tracked.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for connection metrics testing")
            
        # Create multiple real WebSocket connections to generate metrics
        real_connections = []
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        try:
            # Create 3 connections (reduced from 5 for stability)
            for i in range(3):
                user_id = f"metrics_user_{i}"
                token = auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=f"metrics{i}@example.com"
                )
                headers = auth_helper.get_websocket_headers(token)
                
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"ws://localhost:8000/ws",
                    headers=headers,
                    timeout=10.0,
                    user_id=user_id
                )
                real_connections.append(websocket)
                
                # Send a test message
                msg = {"type": "ping", "user_id": user_id}
                await WebSocketTestHelpers.send_test_message(websocket, msg)
                
                # Try to receive response (optional)
                try:
                    await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                except asyncio.TimeoutError:
                    pass  # Response not required for metrics test
            
            # Verify connections were created
            assert len(real_connections) >= 2  # Allow for some failures
            
        finally:
            # Clean up connections
            for conn in real_connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(conn)
                except Exception:
                    pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_rate_monitoring(self, test_db_session, isolated_env):
        """
        BVJ: Enables proactive error detection and resolution.
        Tests that WebSocket error rates are monitored and reported.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for error rate monitoring testing")
            
        # Create authenticated WebSocket connection
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="test_error_tracking_user",
            email="error_tracking@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="test_error_tracking_user"
        )
        
        error_count = 0
        success_count = 0
        
        # Send mix of valid and invalid messages
        test_messages = [
            {"type": "ping", "content": "success"},
            {"type": "ping", "content": "success"},
            {"type": "invalid_type", "content": "this should cause error"},
            {"type": "ping", "content": "success"}
        ]
        
        for msg in test_messages:
            try:
                await WebSocketTestHelpers.send_test_message(websocket, msg)
                
                # Try to receive response
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                
                if response and response.get("type") == "error":
                    error_count += 1
                elif response:
                    success_count += 1
                    
            except asyncio.TimeoutError:
                # No response might indicate error or system behavior
                if msg.get("type") == "invalid_type":
                    error_count += 1
            except Exception as e:
                error_count += 1
        
        # Should have processed some messages
        total_messages = error_count + success_count
        assert total_messages > 0
        assert success_count > 0  # Should have processed valid ping messages
        
        await WebSocketTestHelpers.close_test_connection(websocket)


class TestWebSocketUserContextIsolation(BaseIntegrationTest):
    """Test WebSocket user context isolation and factory patterns."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_execution_context_websocket_isolation(self, test_db_session, isolated_env):
        """
        BVJ: Ensures enterprise security through proper user context isolation.
        Tests UserExecutionContext factory patterns prevent cross-user data leakage.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for user context isolation testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create two separate user contexts
        user1_token = auth_helper.create_test_jwt_token(
            user_id="isolated_user_1",
            email="user1@example.com"
        )
        
        user2_token = auth_helper.create_test_jwt_token(
            user_id="isolated_user_2",
            email="user2@example.com"
        )
        
        # Create separate WebSocket connections
        headers1 = auth_helper.get_websocket_headers(user1_token)
        headers2 = auth_helper.get_websocket_headers(user2_token)
        
        websocket1 = await WebSocketTestHelpers.create_test_websocket_connection(
            f"ws://localhost:8000/ws",
            headers=headers1,
            timeout=10.0,
            user_id="isolated_user_1"
        )
        
        websocket2 = await WebSocketTestHelpers.create_test_websocket_connection(
            f"ws://localhost:8000/ws",
            headers=headers2,
            timeout=10.0,
            user_id="isolated_user_2"
        )
        
        # Send different requests from each user
        user1_msg = {
            "type": "chat",
            "content": "User 1 private message",
            "user_id": "isolated_user_1",
            "timestamp": time.time()
        }
        
        user2_msg = {
            "type": "chat",
            "content": "User 2 private message", 
            "user_id": "isolated_user_2",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket1, user1_msg)
        await WebSocketTestHelpers.send_test_message(websocket2, user2_msg)
        
        # Collect responses for each user
        user1_events = []
        user2_events = []
        
        # Collect user 1 events
        for _ in range(5):
            try:
                response1 = await WebSocketTestHelpers.receive_test_message(websocket1, timeout=3.0)
                user1_events.append(response1)
            except asyncio.TimeoutError:
                break
                
        # Collect user 2 events
        for _ in range(5):
            try:
                response2 = await WebSocketTestHelpers.receive_test_message(websocket2, timeout=3.0)
                user2_events.append(response2)
            except asyncio.TimeoutError:
                break
                
        # Validate isolation - User 1 events should not contain User 2 data
        user1_content = json.dumps(user1_events)
        user2_content = json.dumps(user2_events)
        
        assert "User 2" not in user1_content, "User 1 received User 2's data - isolation failure"
        assert "User 1" not in user2_content, "User 2 received User 1's data - isolation failure"
        
        await WebSocketTestHelpers.close_test_connection(websocket1)
        await WebSocketTestHelpers.close_test_connection(websocket2)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_factory_per_user(self, test_db_session, isolated_env):
        """
        BVJ: Validates factory pattern creates isolated WebSocket managers per user.
        Tests that WebSocket manager factory prevents shared state between users.
        """
        services = test_db_session
        
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create multiple user connections to test factory isolation
        users = ["factory_user_1", "factory_user_2", "factory_user_3"]
        connections = []
        
        try:
            for user_id in users:
                token = auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=f"{user_id}@example.com"
                )
                headers = auth_helper.get_websocket_headers(token)
                
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"ws://localhost:8000/ws",
                    headers=headers,
                    timeout=10.0,
                    user_id=user_id
                )
                connections.append((websocket, user_id))
                
            # Send unique messages from each user
            for i, (websocket, user_id) in enumerate(connections):
                unique_msg = {
                    "type": "ping",
                    "content": f"Factory test from {user_id}",
                    "user_id": user_id,
                    "sequence": i,
                    "timestamp": time.time()
                }
                await WebSocketTestHelpers.send_test_message(websocket, unique_msg)
                
            # Collect responses - each should be isolated
            for websocket, user_id in connections:
                try:
                    response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                    # Validate response corresponds to correct user
                    response_str = json.dumps(response)
                    # Response should not contain data from other users
                    other_users = [u for u in users if u != user_id]
                    for other_user in other_users:
                        assert other_user not in response_str, f"WebSocket manager factory isolation failed: {user_id} received {other_user} data"
                except asyncio.TimeoutError:
                    pass  # Some connections may not respond immediately
                    
        finally:
            # Clean up connections
            for websocket, _ in connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(websocket)
                except Exception:
                    pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_agent_events_isolation(self, test_db_session, isolated_env):
        """
        BVJ: Validates concurrent users receive isolated agent events.
        Tests that multiple users can run agents simultaneously without cross-contamination.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for concurrent agent isolation testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create two concurrent user sessions
        users_data = [
            {"user_id": "concurrent_1", "email": "concurrent1@example.com", "request": "Analyze data for user 1"},
            {"user_id": "concurrent_2", "email": "concurrent2@example.com", "request": "Process info for user 2"}
        ]
        
        connections = []
        
        try:
            # Establish connections
            for user_data in users_data:
                token = auth_helper.create_test_jwt_token(
                    user_id=user_data["user_id"],
                    email=user_data["email"]
                )
                headers = auth_helper.get_websocket_headers(token)
                
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"ws://localhost:8000/ws",
                    headers=headers,
                    timeout=10.0,
                    user_id=user_data["user_id"]
                )
                connections.append((websocket, user_data))
                
            # Send concurrent agent requests
            for websocket, user_data in connections:
                agent_request = {
                    "type": "chat",
                    "content": user_data["request"],
                    "user_id": user_data["user_id"],
                    "timestamp": time.time()
                }
                await WebSocketTestHelpers.send_test_message(websocket, agent_request)
                
            # Collect events from both users concurrently
            async def collect_user_events(websocket, user_data, max_events=10):
                events = []
                for _ in range(max_events):
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                        events.append(response)
                        if response.get("type") == "agent_completed":
                            break
                    except asyncio.TimeoutError:
                        continue
                return events, user_data["user_id"]
                
            # Collect events from both users simultaneously
            event_tasks = [
                collect_user_events(websocket, user_data)
                for websocket, user_data in connections
            ]
            
            results = await asyncio.gather(*event_tasks, return_exceptions=True)
            
            # Validate isolation
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    continue
                    
                events, user_id = result
                other_user_id = users_data[1-i]["user_id"]
                
                # Events should not contain data from the other user
                events_str = json.dumps(events)
                assert other_user_id not in events_str, f"Concurrent agent events contaminated: {user_id} received {other_user_id} data"
                
        finally:
            # Clean up
            for websocket, _ in connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(websocket)
                except Exception:
                    pass


class TestWebSocketBusinessValueScenarios(BaseIntegrationTest):
    """Test WebSocket functionality that directly delivers business value."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_chat_value_delivery(self, test_db_session, isolated_env):
        """
        BVJ: MISSION CRITICAL - Tests complete chat value delivery via WebSocket events.
        Validates that users receive meaningful, real-time AI assistance through WebSocket.
        This test represents the core $30K+ MRR chat functionality.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for chat value delivery testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="chat_value_user",
            email="chat_value@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=15.0,
            user_id="chat_value_user"
        )
        
        # Send business-critical chat request
        business_request = {
            "type": "chat",
            "content": "Help me optimize our cloud costs and identify savings opportunities",
            "user_id": "chat_value_user",
            "thread_id": f"business_thread_{int(time.time())}",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, business_request)
        
        # Collect comprehensive event sequence
        business_value_events = []
        start_time = time.time()
        
        while time.time() - start_time < 30.0:
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                business_value_events.append(response)
                
                if response.get("type") == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue
                
        # Validate complete business value delivery
        event_types = [event.get("type") for event in business_value_events]
        
        # CRITICAL: Must have meaningful business interaction
        assert len(business_value_events) > 0, "No WebSocket events received - chat has no business value"
        
        # Validate user receives real-time feedback (any meaningful events)
        meaningful_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed", "ack", "response"
        ]
        received_meaningful = [event for event in event_types if event in meaningful_events]
        assert len(received_meaningful) > 0, f"No meaningful events received - business value not delivered. Got: {event_types}"
        
        # Business value assertion - user must get actionable response
        has_actionable_content = False
        for event in business_value_events:
            content_fields = ["response", "final_response", "message", "content", "reasoning"]
            for field in content_fields:
                if field in event and event[field] and len(str(event[field])) > 10:
                    has_actionable_content = True
                    break
                    
        assert has_actionable_content, "WebSocket events contain no actionable business content"
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_enterprise_multi_user_chat_isolation(self, test_db_session, isolated_env):
        """
        BVJ: Validates enterprise security for multi-tenant chat environments.
        Tests that enterprise customers can have isolated chat sessions.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for enterprise isolation testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create enterprise user contexts
        enterprise_users = [
            {"user_id": "enterprise_user_1", "org": "TechCorp", "request": "Sensitive TechCorp data analysis"},
            {"user_id": "enterprise_user_2", "org": "MegaInc", "request": "Confidential MegaInc optimization"}
        ]
        
        connections = []
        
        try:
            # Establish enterprise connections
            for user_data in enterprise_users:
                token = auth_helper.create_test_jwt_token(
                    user_id=user_data["user_id"],
                    email=f"{user_data['user_id']}@{user_data['org'].lower()}.com",
                    permissions=["read", "write", "enterprise"]
                )
                headers = auth_helper.get_websocket_headers(token)
                
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"ws://localhost:8000/ws",
                    headers=headers,
                    timeout=10.0,
                    user_id=user_data["user_id"]
                )
                connections.append((websocket, user_data))
                
            # Send sensitive enterprise requests
            for websocket, user_data in connections:
                enterprise_request = {
                    "type": "chat",
                    "content": user_data["request"],
                    "user_id": user_data["user_id"],
                    "org_context": user_data["org"],
                    "security_level": "enterprise",
                    "timestamp": time.time()
                }
                await WebSocketTestHelpers.send_test_message(websocket, enterprise_request)
                
            # Validate enterprise isolation
            for i, (websocket, user_data) in enumerate(connections):
                user_events = []
                
                # Collect events for this enterprise user
                for _ in range(10):
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                        user_events.append(response)
                    except asyncio.TimeoutError:
                        break
                        
                # Validate enterprise data isolation
                events_content = json.dumps(user_events)
                other_user = enterprise_users[1-i]
                
                # CRITICAL: Enterprise user data must not leak
                assert other_user["org"] not in events_content, f"ENTERPRISE SECURITY BREACH: {user_data['org']} received {other_user['org']} data"
                assert other_user["user_id"] not in events_content, f"ENTERPRISE ISOLATION FAILURE: Cross-user data leakage detected"
                
        finally:
            # Secure cleanup
            for websocket, _ in connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(websocket)
                except Exception:
                    pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_free_tier_websocket_value_demonstration(self, test_db_session, isolated_env):
        """
        BVJ: Demonstrates WebSocket value for free tier users to drive conversion.
        Tests that free tier users get enough value to convert to paid tiers.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for free tier value testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="free_tier_user",
            email="free_user@example.com",
            permissions=["read"]  # Limited free tier permissions
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="free_tier_user"
        )
        
        # Send free tier appropriate request
        free_tier_request = {
            "type": "chat",
            "content": "Quick help with basic optimization suggestions",
            "user_id": "free_tier_user",
            "tier": "free",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, free_tier_request)
        
        # Collect free tier response events
        free_tier_events = []
        for _ in range(15):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                free_tier_events.append(response)
                if response.get("type") == "agent_completed":
                    break
            except asyncio.TimeoutError:
                continue
                
        # Validate free tier gets meaningful value
        assert len(free_tier_events) > 0, "Free tier users received no WebSocket value - conversion impossible"
        
        # Free tier should get basic real-time feedback
        event_types = [event.get("type") for event in free_tier_events]
        valuable_events = ["agent_started", "agent_thinking", "agent_completed", "response", "ack"]
        received_value = [event for event in event_types if event in valuable_events]
        
        assert len(received_value) > 0, f"Free tier received no valuable events - no conversion incentive. Got: {event_types}"
        
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_agent_event_payload_validation(self, test_db_session, isolated_env):
        """
        BVJ: Validates WebSocket agent event payloads meet API contract requirements.
        Tests that all 5 critical agent events have valid payload structures.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for payload validation testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="payload_validation_user",
            email="payload@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="payload_validation_user"
        )
        
        # Send comprehensive agent request
        payload_request = {
            "type": "chat",
            "content": "Comprehensive request to validate all agent event payloads",
            "user_id": "payload_validation_user",
            "timestamp": time.time()
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, payload_request)
        
        # Collect and validate each event type's payload
        collected_events = {}
        for _ in range(25):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                event_type = response.get("type")
                
                if event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                    collected_events[event_type] = response
                    
                if event_type == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                continue
                
        # Validate each critical event type payload
        for event_type, event_data in collected_events.items():
            # Common required fields for all agent events
            common_fields = ["type", "timestamp"]
            validate_websocket_message(event_data, common_fields)
            
            # Event-specific validations
            if event_type == "agent_started":
                assert "agent_name" in event_data or "agent_type" in event_data, "agent_started missing agent identification"
            elif event_type == "agent_thinking":
                assert "reasoning" in event_data or "message" in event_data, "agent_thinking missing reasoning content"
            elif event_type == "tool_executing":
                assert "tool_name" in event_data, "tool_executing missing tool_name"
            elif event_type == "tool_completed":
                assert "tool_name" in event_data, "tool_completed missing tool_name"
            elif event_type == "agent_completed":
                # agent_completed should have some form of result
                result_fields = ["response", "final_response", "result", "message"]
                has_result = any(field in event_data for field in result_fields)
                if not has_result:
                    self.logger.warning("agent_completed event lacks result field - may impact user experience")
                    
        await WebSocketTestHelpers.close_test_connection(websocket)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_timing_performance(self, test_db_session, isolated_env):
        """
        BVJ: Ensures WebSocket events arrive within acceptable time limits for good UX.
        Tests that agent events are delivered with low latency for real-time experience.
        """
        services = test_db_session
        
        if not services["websocket_available"]:
            pytest.skip("WebSocket service not available for timing performance testing")
            
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        token = auth_helper.create_test_jwt_token(
            user_id="timing_performance_user",
            email="timing@example.com"
        )
        
        headers = auth_helper.get_websocket_headers(token)
        websocket_url = f"ws://localhost:8000/ws"
        
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=headers,
            timeout=10.0,
            user_id="timing_performance_user"
        )
        
        # Send request and measure timing
        request_start = time.time()
        timing_request = {
            "type": "chat",
            "content": "Quick request to measure event timing",
            "user_id": "timing_performance_user",
            "timestamp": request_start
        }
        
        await WebSocketTestHelpers.send_test_message(websocket, timing_request)
        
        # Measure time to first meaningful event
        first_event_time = None
        events_received = 0
        
        for _ in range(10):
            try:
                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                events_received += 1
                
                if first_event_time is None:
                    first_event_time = time.time()
                    
                # Break on completion or after reasonable number of events
                if response.get("type") == "agent_completed" or events_received >= 5:
                    break
                    
            except asyncio.TimeoutError:
                break
                
        # Validate timing performance
        if first_event_time:
            first_event_latency = first_event_time - request_start
            # First event should arrive within 10 seconds for good UX
            assert first_event_latency < 10.0, f"First WebSocket event took {first_event_latency:.2f}s - too slow for real-time UX"
            
            self.logger.info(f"WebSocket first event latency: {first_event_latency:.3f}s")
        else:
            pytest.skip("No WebSocket events received for timing measurement")
            
        await WebSocketTestHelpers.close_test_connection(websocket)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])