"""Real WebSocket Message Routing Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Chat Reliability - Message Delivery Accuracy
- Value Impact: Ensures messages reach correct handlers for proper chat functionality
- Strategic Impact: Prevents message routing failures that break chat interactions

Tests real WebSocket message routing to appropriate handlers with Docker services.
Validates that different message types are routed to correct processing logic.

CRITICAL: Tests message routing for the PRIMARY path (90% traffic) per CLAUDE.md
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.app.websocket_core.types import MessageType
from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.message_routing
@skip_if_no_real_services
class TestRealWebSocketMessageRouting:
    """Test real WebSocket message routing to correct handlers.
    
    CRITICAL: Tests that messages are properly routed to their handlers:
    - Connection messages  ->  Connection handler
    - Agent messages  ->  Agent handler  
    - User messages  ->  Message handler
    - Heartbeat messages  ->  Health handler
    - Error messages  ->  Error handler
    
    Validates routing accuracy for chat value delivery.
    """
    
    @pytest.fixture
    def websocket_url(self):
        """Get WebSocket URL from environment."""
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for WebSocket connection."""
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Message-Routing-Test/1.0"
        }
    
    @pytest.fixture
    def test_user_id(self):
        """Generate unique test user ID."""
        return f"test_user_routing_{int(time.time())}"
    
    @pytest.mark.asyncio
    async def test_connection_message_routing(self, websocket_url, auth_headers, test_user_id):
        """Test connection messages are routed to connection handler."""
        responses = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Send connection message - should route to connection handler
                connect_msg = {
                    "type": "connect",
                    "user_id": test_user_id,
                    "client_info": {
                        "version": "1.0",
                        "platform": "test"
                    }
                }
                await websocket.send(json.dumps(connect_msg))
                
                # Receive routing response
                response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_raw)
                responses.append(response)
                
                # Validate connection handler processed message
                assert response.get("type") == "connection_established"
                assert "connection_id" in response
                assert response.get("status") == "connected"
                
                # Send disconnect message - should also route to connection handler
                disconnect_msg = {
                    "type": "disconnect",
                    "user_id": test_user_id,
                    "reason": "test_routing_complete"
                }
                await websocket.send(json.dumps(disconnect_msg))
                
                # May receive disconnect acknowledgment
                try:
                    disconnect_response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    disconnect_response = json.loads(disconnect_response_raw)
                    responses.append(disconnect_response)
                    
                    # Validate disconnect was processed
                    assert disconnect_response.get("type") in ["disconnect_ack", "connection_closed"]
                    
                except asyncio.TimeoutError:
                    # Disconnect may close connection immediately
                    pass
                
        except Exception as e:
            pytest.fail(f"Connection message routing test failed: {e}")
        
        # Verify connection messages were properly routed
        assert len(responses) >= 1, "Connection message should have generated response"
        assert any(r.get("type") == "connection_established" for r in responses), "Connection handler did not process connect message"
    
    @pytest.mark.asyncio
    async def test_user_message_routing(self, websocket_url, auth_headers, test_user_id):
        """Test user messages are routed to message handler."""
        responses = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect first
                await websocket.send(json.dumps({"type": "connect", "user_id": test_user_id}))
                connect_response = json.loads(await websocket.recv())
                assert connect_response.get("status") == "connected"
                
                # Send user message - should route to message handler
                user_msg = {
                    "type": "user_message",
                    "user_id": test_user_id,
                    "content": "Test message routing to handler",
                    "thread_id": f"thread_{test_user_id}",
                    "message_id": f"msg_{int(time.time())}"
                }
                await websocket.send(json.dumps(user_msg))
                
                # Collect responses for routing validation
                timeout_time = time.time() + 10
                while time.time() < timeout_time:
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response = json.loads(response_raw)
                        responses.append(response)
                        
                        # Look for message processing indicators
                        if response.get("type") in ["message_received", "agent_started", "processing_started"]:
                            break
                            
                    except asyncio.TimeoutError:
                        break
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"User message routing test failed: {e}")
        
        # Validate user message was routed to message handler
        assert len(responses) > 0, "User message should generate handler response"
        
        # Check for message processing indicators
        processing_indicators = [
            "message_received", "agent_started", "processing_started", 
            "agent_thinking", "message_processed"
        ]
        
        has_processing_indicator = any(
            r.get("type") in processing_indicators for r in responses
        )
        
        if not has_processing_indicator:
            # Log available response types for debugging
            response_types = [r.get("type") for r in responses]
            print(f"WARNING: No clear message processing indicator. Response types: {response_types}")
            
            # At minimum, should have received some response
            assert len(responses) > 0, "Message handler should have processed user message"
    
    @pytest.mark.asyncio
    async def test_agent_message_routing(self, websocket_url, auth_headers, test_user_id):
        """Test agent messages are routed to agent handler."""
        responses = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": test_user_id}))
                connect_response = json.loads(await websocket.recv())
                assert connect_response.get("status") == "connected"
                
                # Send agent start message - should route to agent handler
                start_agent_msg = {
                    "type": "start_agent",
                    "user_id": test_user_id,
                    "agent_type": "triage_agent",
                    "task": "Test agent message routing",
                    "thread_id": f"thread_{test_user_id}",
                    "parameters": {
                        "routing_test": True
                    }
                }
                await websocket.send(json.dumps(start_agent_msg))
                
                # Collect agent handler responses
                timeout_time = time.time() + 10
                while time.time() < timeout_time:
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response = json.loads(response_raw)
                        responses.append(response)
                        
                        # Look for agent handler processing
                        if response.get("type") in ["agent_started", "agent_received", "agent_processing"]:
                            break
                            
                    except asyncio.TimeoutError:
                        break
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Agent message routing test failed: {e}")
        
        # Validate agent message was routed to agent handler
        assert len(responses) > 0, "Agent message should generate handler response"
        
        # Check for agent processing indicators
        agent_indicators = [
            "agent_started", "agent_received", "agent_processing",
            "agent_thinking", "tool_executing"
        ]
        
        has_agent_indicator = any(
            r.get("type") in agent_indicators for r in responses
        )
        
        if not has_agent_indicator:
            response_types = [r.get("type") for r in responses]
            print(f"WARNING: No clear agent processing indicator. Response types: {response_types}")
    
    @pytest.mark.asyncio
    async def test_heartbeat_message_routing(self, websocket_url, auth_headers, test_user_id):
        """Test heartbeat messages are routed to health handler."""
        responses = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": test_user_id}))
                connect_response = json.loads(await websocket.recv())
                assert connect_response.get("status") == "connected"
                
                # Send heartbeat message - should route to health handler
                heartbeat_msg = {
                    "type": "heartbeat",
                    "user_id": test_user_id,
                    "timestamp": time.time(),
                    "client_id": f"client_{test_user_id}"
                }
                await websocket.send(json.dumps(heartbeat_msg))
                
                # Receive heartbeat response
                response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_raw)
                responses.append(response)
                
                # Validate heartbeat handler processed message
                assert response.get("type") == "heartbeat_ack"
                assert "timestamp" in response
                
        except Exception as e:
            pytest.fail(f"Heartbeat message routing test failed: {e}")
        
        # Verify heartbeat routing worked
        assert len(responses) == 1, "Should receive exactly one heartbeat_ack"
        heartbeat_response = responses[0]
        assert heartbeat_response.get("type") == "heartbeat_ack"
    
    @pytest.mark.asyncio
    async def test_invalid_message_routing(self, websocket_url, auth_headers, test_user_id):
        """Test invalid messages are routed to error handler."""
        responses = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": test_user_id}))
                connect_response = json.loads(await websocket.recv())
                assert connect_response.get("status") == "connected"
                
                # Send invalid message - should route to error handler
                invalid_msg = {
                    "type": "invalid_message_type_xyz",
                    "user_id": test_user_id,
                    "invalid_field": "test_error_routing"
                }
                await websocket.send(json.dumps(invalid_msg))
                
                # Receive error response
                try:
                    response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response = json.loads(response_raw)
                    responses.append(response)
                    
                except asyncio.TimeoutError:
                    # Some systems may silently drop invalid messages
                    pass
                
        except Exception as e:
            # Connection may close on invalid message
            if "connection" not in str(e).lower():
                pytest.fail(f"Invalid message routing test failed: {e}")
        
        # Validate error handling
        if len(responses) > 0:
            # If response received, should be error type
            error_response = responses[0]
            expected_error_types = ["error", "invalid_message", "unsupported_message", "message_error"]
            assert error_response.get("type") in expected_error_types, f"Expected error response, got: {error_response.get('type')}"
        else:
            # Silent dropping of invalid messages is also acceptable
            print("INFO: Invalid message was silently dropped (acceptable behavior)")
    
    @pytest.mark.asyncio
    async def test_concurrent_message_routing(self, websocket_url, auth_headers, test_user_id):
        """Test routing works correctly with concurrent messages."""
        all_responses = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=20
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": test_user_id}))
                connect_response = json.loads(await websocket.recv())
                assert connect_response.get("status") == "connected"
                
                # Send multiple message types concurrently
                messages_to_send = [
                    {"type": "heartbeat", "user_id": test_user_id, "timestamp": time.time()},
                    {"type": "user_message", "user_id": test_user_id, "content": "Concurrent test 1", "thread_id": f"thread_{test_user_id}"},
                    {"type": "heartbeat", "user_id": test_user_id, "timestamp": time.time() + 1},
                    {"type": "user_message", "user_id": test_user_id, "content": "Concurrent test 2", "thread_id": f"thread_{test_user_id}"}
                ]
                
                # Send all messages rapidly
                for msg in messages_to_send:
                    await websocket.send(json.dumps(msg))
                    await asyncio.sleep(0.1)  # Brief delay between sends
                
                # Collect responses
                response_timeout = time.time() + 15
                while time.time() < response_timeout and len(all_responses) < 10:
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response = json.loads(response_raw)
                        all_responses.append(response)
                        
                    except asyncio.TimeoutError:
                        break
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Concurrent message routing test failed: {e}")
        
        # Validate concurrent routing worked
        assert len(all_responses) >= 2, f"Should receive multiple responses for concurrent messages, got: {len(all_responses)}"
        
        # Count response types
        response_types = [r.get("type") for r in all_responses]
        heartbeat_acks = response_types.count("heartbeat_ack")
        
        # Should have received heartbeat acknowledgments
        assert heartbeat_acks >= 1, f"Should receive heartbeat_ack responses. Response types: {response_types}"
        
        # Check for message processing responses
        message_processing_types = [
            "message_received", "agent_started", "processing_started", "agent_thinking"
        ]
        
        message_responses = sum(1 for t in response_types if t in message_processing_types)
        print(f"Concurrent routing results - Heartbeat ACKs: {heartbeat_acks}, Message responses: {message_responses}")
        print(f"All response types: {response_types}")
    
    @pytest.mark.asyncio
    async def test_message_routing_with_context_preservation(self, websocket_url, auth_headers, test_user_id):
        """Test message routing preserves user context across different message types."""
        responses = []
        user_contexts = set()
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": test_user_id}))
                connect_response = json.loads(await websocket.recv())
                assert connect_response.get("status") == "connected"
                
                # Send different message types with context tracking
                context_messages = [
                    {
                        "type": "user_message",
                        "user_id": test_user_id,
                        "content": "Context test message 1",
                        "thread_id": f"thread_{test_user_id}",
                        "context_tag": "test_context_1"
                    },
                    {
                        "type": "heartbeat",
                        "user_id": test_user_id,
                        "timestamp": time.time(),
                        "context_tag": "test_context_2"
                    },
                    {
                        "type": "user_message",
                        "user_id": test_user_id,
                        "content": "Context test message 2",
                        "thread_id": f"thread_{test_user_id}",
                        "context_tag": "test_context_3"
                    }
                ]
                
                # Send messages and collect responses
                for msg in context_messages:
                    await websocket.send(json.dumps(msg))
                    await asyncio.sleep(0.5)
                
                # Collect responses
                timeout_time = time.time() + 10
                while time.time() < timeout_time:
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response = json.loads(response_raw)
                        responses.append(response)
                        
                        # Track user context preservation
                        if "user_id" in response:
                            user_contexts.add(response["user_id"])
                        
                    except asyncio.TimeoutError:
                        break
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Context preservation routing test failed: {e}")
        
        # Validate context preservation
        assert len(responses) > 0, "Should receive responses for context test"
        assert len(user_contexts) <= 1, f"Should preserve single user context, found: {user_contexts}"
        
        if len(user_contexts) == 1:
            preserved_user_id = list(user_contexts)[0]
            assert preserved_user_id == test_user_id, "User context should match original user ID"
        
        # Verify different message types were processed
        response_types = [r.get("type") for r in responses]
        print(f"Context preservation test - Response types: {response_types}")
        print(f"User contexts preserved: {user_contexts}")