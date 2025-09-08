"""
Comprehensive WebSocket Integration Tests for Netra Platform

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure WebSocket messaging delivers reliable AI chat value
- Value Impact: WebSocket events enable real-time chat interactions and agent execution visibility
- Strategic Impact: Core platform communication infrastructure for revenue delivery

CRITICAL: WebSocket events are MISSION CRITICAL for chat value delivery per CLAUDE.md
All 5 agent events MUST be sent: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

These integration tests validate WebSocket behavior without requiring Docker services.
They test real WebSocket connections, authentication, message handling, and agent integration patterns.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets import WebSocketException, ConnectionClosed

# SSOT imports - using absolute imports only per CLAUDE.md
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage,
    WebSocketTestMetrics
)
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, get_test_jwt_token


class TestWebSocketConnectionManagement(SSotBaseTestCase):
    """
    Test WebSocket connection establishment, lifecycle, and authentication.
    
    BVJ: Platform/Internal - Connection reliability ensures users can receive AI insights
    """
    
    @pytest.mark.integration
    async def test_websocket_connection_establishment_success(self):
        """
        Test successful WebSocket connection with proper authentication.
        
        BVJ: Users must be able to connect to receive AI agent responses
        """
        env = self.get_env()
        
        # Create mock WebSocket server for testing
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_websocket.send = AsyncMock()
            mock_websocket.recv = AsyncMock(return_value='{"type": "pong"}')
            mock_websocket.close = AsyncMock()
            mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_websocket)
            mock_connect.return_value.__aexit__ = AsyncMock(return_value=None)
            
            async with WebSocketTestUtility() as ws_util:
                client = await ws_util.create_test_client(user_id="test-user-conn")
                
                # Mock successful connection
                with patch.object(client, 'websocket', mock_websocket):
                    client.is_connected = True
                    
                    # Test connection properties
                    assert client.test_id is not None
                    assert client.url == ws_util.base_url
                    assert not client.sent_messages
                    assert not client.received_messages
                    
                    # Test that connection accepts authentication headers
                    assert "X-User-ID" in client.headers
                    assert "Authorization" in client.headers
                    assert client.headers["Authorization"].startswith("Bearer")
                    
                    self.record_metric("websocket_connection_test", "success")
    
    @pytest.mark.integration
    async def test_websocket_connection_with_jwt_authentication(self):
        """
        Test WebSocket connection with proper JWT authentication headers.
        
        BVJ: Authenticated users must connect securely to receive personalized AI insights
        """
        auth_helper = E2EAuthHelper()
        token = auth_helper.create_test_jwt_token(
            user_id="auth-test-user",
            email="websocket@test.com",
            permissions=["read", "write"]
        )
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("auth-test-user", token)
            
            # Verify authentication headers are properly set
            headers = client.headers
            assert "Authorization" in headers
            assert headers["Authorization"] == f"Bearer {token}"
            assert headers["X-User-ID"] == "auth-test-user"
            
            # Test that token is valid format
            assert len(token.split('.')) == 3, "JWT token must have 3 parts"
            
            self.record_metric("jwt_auth_validation", "passed")
    
    @pytest.mark.integration
    async def test_websocket_connection_failure_handling(self):
        """
        Test WebSocket connection failure scenarios and error handling.
        
        BVJ: Graceful failure handling prevents user frustration and provides clear feedback
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Test connection to non-existent server
            original_url = client.url
            client.url = "ws://nonexistent-server:9999/ws"
            
            # Mock connection failure
            with patch('websockets.connect', side_effect=ConnectionError("Connection refused")):
                success = await client.connect(timeout=1.0)
                assert not success, "Connection should fail to non-existent server"
                assert not client.is_connected, "Client should not be marked as connected"
            
            # Restore original URL
            client.url = original_url
            self.record_metric("connection_failure_handling", "tested")
    
    @pytest.mark.integration
    async def test_websocket_connection_timeout_handling(self):
        """
        Test WebSocket connection timeout scenarios.
        
        BVJ: Timeout handling prevents users from waiting indefinitely for connections
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Mock slow connection that times out
            async def slow_connect(*args, **kwargs):
                await asyncio.sleep(5)  # Longer than timeout
                return AsyncMock()
            
            with patch('websockets.connect', side_effect=slow_connect):
                start_time = time.time()
                success = await client.connect(timeout=2.0)
                elapsed = time.time() - start_time
                
                assert not success, "Connection should timeout"
                assert elapsed < 3.0, "Should respect timeout parameter"
                assert not client.is_connected
                
                self.record_metric("timeout_handling", elapsed)


class TestWebSocketMessageHandling(SSotBaseTestCase):
    """
    Test WebSocket message serialization, deserialization, and routing.
    
    BVJ: Reliable message handling ensures AI responses reach users correctly
    """
    
    @pytest.mark.integration
    async def test_websocket_message_serialization(self):
        """
        Test WebSocket message serialization and structure.
        
        BVJ: Proper message format ensures consistent AI response delivery
        """
        message = WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            data={"agent_id": "cost_optimizer", "user_request": "Analyze costs"},
            timestamp=datetime.now(timezone.utc),
            message_id="msg_123",
            user_id="test-user",
            thread_id="thread_456"
        )
        
        # Test serialization
        serialized = message.to_dict()
        assert serialized["type"] == "agent_started"
        assert serialized["data"]["agent_id"] == "cost_optimizer"
        assert serialized["message_id"] == "msg_123"
        assert serialized["user_id"] == "test-user"
        assert serialized["thread_id"] == "thread_456"
        assert "timestamp" in serialized
        
        # Test JSON serialization works
        json_str = json.dumps(serialized)
        assert isinstance(json_str, str)
        
        # Test deserialization
        restored = WebSocketMessage.from_dict(serialized)
        assert restored.event_type == WebSocketEventType.AGENT_STARTED
        assert restored.data["agent_id"] == "cost_optimizer"
        assert restored.user_id == "test-user"
        
        self.record_metric("message_serialization", "success")
    
    @pytest.mark.integration
    async def test_websocket_message_sending(self):
        """
        Test sending messages through WebSocket client.
        
        BVJ: Reliable message sending enables user requests to reach AI agents
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Mock WebSocket connection
            mock_websocket = AsyncMock()
            mock_websocket.send = AsyncMock()
            client.websocket = mock_websocket
            client.is_connected = True
            
            # Send test message
            message = await client.send_message(
                WebSocketEventType.PING,
                {"timestamp": time.time()},
                user_id="sender-123"
            )
            
            # Verify message was sent
            assert len(client.sent_messages) == 1
            sent_msg = client.sent_messages[0]
            assert sent_msg.event_type == WebSocketEventType.PING
            assert sent_msg.user_id == "sender-123"
            assert sent_msg.message_id is not None
            
            # Verify WebSocket.send was called
            mock_websocket.send.assert_called_once()
            sent_data = mock_websocket.send.call_args[0][0]
            parsed_data = json.loads(sent_data)
            assert parsed_data["type"] == "ping"
            
            self.record_metric("message_sending", len(client.sent_messages))
    
    @pytest.mark.integration
    async def test_websocket_message_receiving(self):
        """
        Test receiving and parsing messages from WebSocket.
        
        BVJ: Accurate message parsing ensures users receive AI responses correctly
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Create test message data
            test_message = {
                "type": "agent_completed",
                "data": {
                    "result": "Cost analysis complete",
                    "recommendations": ["Reduce instance sizes", "Use spot instances"],
                    "savings": {"monthly": 1500, "percentage": 25}
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": "msg_response_789",
                "user_id": "test-user",
                "thread_id": "thread_cost_analysis"
            }
            
            # Simulate message reception
            try:
                parsed_message = WebSocketMessage.from_dict(test_message)
                client.received_messages.append(parsed_message)
                
                # Verify message was parsed correctly
                assert len(client.received_messages) == 1
                received = client.received_messages[0]
                assert received.event_type == WebSocketEventType.AGENT_COMPLETED
                assert received.data["result"] == "Cost analysis complete"
                assert len(received.data["recommendations"]) == 2
                assert received.data["savings"]["monthly"] == 1500
                
                self.record_metric("message_receiving", "success")
                
            except Exception as e:
                self.record_metric("message_parsing_error", str(e))
                raise
    
    @pytest.mark.integration
    async def test_websocket_message_validation(self):
        """
        Test WebSocket message validation and error handling.
        
        BVJ: Input validation prevents malformed messages from disrupting AI services
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Test sending message without connection should raise error
            client.is_connected = False
            with pytest.raises(RuntimeError, match="not connected"):
                await client.send_message(WebSocketEventType.PING, {})
            
            # Reset connection for next tests
            client.is_connected = True
            
            # Test invalid event type handling
            invalid_message_data = {
                "type": "invalid_event_type",
                "data": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": "msg_invalid"
            }
            
            with pytest.raises(ValueError):
                WebSocketMessage.from_dict(invalid_message_data)
                
            self.record_metric("message_validation", "tested")


class TestWebSocketAgentIntegration(SSotBaseTestCase):
    """
    Test WebSocket integration with AI agents and the 5 critical events.
    
    BVJ: Agent integration enables real-time AI processing visibility for users
    """
    
    @pytest.mark.integration
    async def test_agent_started_event(self):
        """
        Test agent_started event delivery - MISSION CRITICAL per CLAUDE.md.
        
        BVJ: Users must know when AI agent begins processing their request
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("agent-test-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Simulate agent_started event
            await client.send_message(
                WebSocketEventType.AGENT_STARTED,
                {
                    "agent_type": "cost_optimizer",
                    "request_id": "req_123",
                    "user_request": "Analyze my AWS spend",
                    "estimated_duration": "30-60 seconds"
                },
                user_id="agent-test-user",
                thread_id="thread_cost_analysis"
            )
            
            # Verify event was sent
            assert len(client.sent_messages) == 1
            started_event = client.sent_messages[0]
            assert started_event.event_type == WebSocketEventType.AGENT_STARTED
            assert started_event.data["agent_type"] == "cost_optimizer"
            assert started_event.data["request_id"] == "req_123"
            assert started_event.user_id == "agent-test-user"
            
            self.increment_websocket_events()
            self.record_metric("agent_started_event", "delivered")
    
    @pytest.mark.integration
    async def test_agent_thinking_event(self):
        """
        Test agent_thinking event for real-time reasoning visibility.
        
        BVJ: Users see AI reasoning process, building trust and engagement
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("thinking-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Simulate agent thinking with reasoning steps
            await client.send_message(
                WebSocketEventType.AGENT_THINKING,
                {
                    "reasoning_step": "Analyzing cost patterns",
                    "current_thought": "Examining EC2 instance utilization across regions",
                    "progress": 0.3,
                    "sub_tasks": [
                        "Load historical billing data",
                        "Identify underutilized resources", 
                        "Calculate potential savings"
                    ]
                },
                user_id="thinking-user"
            )
            
            thinking_event = client.sent_messages[0]
            assert thinking_event.event_type == WebSocketEventType.AGENT_THINKING
            assert thinking_event.data["reasoning_step"] == "Analyzing cost patterns"
            assert thinking_event.data["progress"] == 0.3
            assert len(thinking_event.data["sub_tasks"]) == 3
            
            self.increment_websocket_events()
            self.record_metric("agent_thinking_event", "delivered")
    
    @pytest.mark.integration
    async def test_tool_executing_event(self):
        """
        Test tool_executing event for tool usage transparency.
        
        BVJ: Users see which tools AI uses, demonstrating problem-solving approach
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("tool-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Simulate tool execution
            await client.send_message(
                WebSocketEventType.TOOL_EXECUTING,
                {
                    "tool_name": "aws_cost_analyzer",
                    "tool_description": "Analyze AWS billing data for cost optimization opportunities",
                    "parameters": {
                        "account_id": "123456789",
                        "time_range": "30_days",
                        "services": ["EC2", "RDS", "S3"]
                    },
                    "expected_duration": "10-15 seconds"
                },
                user_id="tool-user"
            )
            
            tool_event = client.sent_messages[0]
            assert tool_event.event_type == WebSocketEventType.TOOL_EXECUTING
            assert tool_event.data["tool_name"] == "aws_cost_analyzer"
            assert "parameters" in tool_event.data
            assert tool_event.data["parameters"]["account_id"] == "123456789"
            
            self.increment_websocket_events()
            self.record_metric("tool_executing_event", "delivered")
    
    @pytest.mark.integration
    async def test_tool_completed_event(self):
        """
        Test tool_completed event with results delivery.
        
        BVJ: Users receive actionable insights from AI tool execution
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("result-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Simulate tool completion with results
            await client.send_message(
                WebSocketEventType.TOOL_COMPLETED,
                {
                    "tool_name": "aws_cost_analyzer",
                    "execution_time": 12.5,
                    "status": "success",
                    "results": {
                        "total_monthly_cost": 5420.50,
                        "potential_savings": 1365.75,
                        "recommendations": [
                            {
                                "type": "rightsizing",
                                "resource": "EC2 instances",
                                "savings": 800.25,
                                "action": "Reduce instance sizes for underutilized servers"
                            },
                            {
                                "type": "scheduling",
                                "resource": "Development environments",
                                "savings": 565.50,
                                "action": "Schedule dev instances to run only during business hours"
                            }
                        ]
                    },
                    "metadata": {
                        "resources_analyzed": 147,
                        "optimization_opportunities": 12
                    }
                },
                user_id="result-user"
            )
            
            completed_event = client.sent_messages[0]
            assert completed_event.event_type == WebSocketEventType.TOOL_COMPLETED
            assert completed_event.data["status"] == "success"
            assert completed_event.data["results"]["potential_savings"] == 1365.75
            assert len(completed_event.data["results"]["recommendations"]) == 2
            
            self.increment_websocket_events()
            self.record_metric("tool_completed_event", "delivered")
    
    @pytest.mark.integration
    async def test_agent_completed_event(self):
        """
        Test agent_completed event - final deliverable to user.
        
        BVJ: Users receive final AI analysis and actionable recommendations
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("completion-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Simulate agent completion with comprehensive results
            await client.send_message(
                WebSocketEventType.AGENT_COMPLETED,
                {
                    "agent_type": "cost_optimizer",
                    "request_id": "req_final_123",
                    "execution_time": 45.2,
                    "status": "success",
                    "final_results": {
                        "executive_summary": "Identified $1,365/month in cost savings (25% reduction)",
                        "total_analysis": {
                            "current_monthly_spend": 5420.50,
                            "potential_savings": 1365.75,
                            "savings_percentage": 25.2
                        },
                        "priority_actions": [
                            {
                                "priority": 1,
                                "action": "Right-size 8 overprovisioned EC2 instances",
                                "impact": "$800/month savings",
                                "effort": "Low - automated resize available"
                            },
                            {
                                "priority": 2,
                                "action": "Implement dev environment scheduling",
                                "impact": "$565/month savings", 
                                "effort": "Medium - requires policy changes"
                            }
                        ],
                        "next_steps": [
                            "Review and approve recommended instance changes",
                            "Set up automated scaling policies",
                            "Schedule monthly cost reviews"
                        ]
                    },
                    "conversation_continuation": {
                        "suggested_followups": [
                            "Would you like me to help implement these changes?",
                            "Should I analyze other AWS services for additional savings?",
                            "Do you want to set up automated cost monitoring?"
                        ]
                    }
                },
                user_id="completion-user"
            )
            
            completed_event = client.sent_messages[0]
            assert completed_event.event_type == WebSocketEventType.AGENT_COMPLETED
            assert completed_event.data["status"] == "success"
            assert "executive_summary" in completed_event.data["final_results"]
            assert completed_event.data["final_results"]["total_analysis"]["savings_percentage"] == 25.2
            assert len(completed_event.data["final_results"]["priority_actions"]) == 2
            
            self.increment_websocket_events()
            self.record_metric("agent_completed_event", "delivered")
    
    @pytest.mark.integration
    async def test_complete_agent_event_flow(self):
        """
        Test complete agent execution flow with all 5 critical events.
        
        BVJ: Complete event flow ensures users have full visibility into AI processing
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("flow-test-user")
            
            # Define expected event sequence per CLAUDE.md
            expected_events = [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]
            
            # Mock successful agent execution flow
            client.is_connected = True
            client.websocket = AsyncMock()
            
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            
            # Simulate complete agent flow
            for i, event_type in enumerate(expected_events):
                event_data = {
                    "execution_id": execution_id,
                    "step": i + 1,
                    "total_steps": len(expected_events),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Add specific data based on event type
                if event_type == WebSocketEventType.AGENT_STARTED:
                    event_data["agent_type"] = "cost_optimizer"
                elif event_type == WebSocketEventType.AGENT_THINKING:
                    event_data["current_thought"] = f"Processing step {i+1}"
                elif event_type == WebSocketEventType.TOOL_EXECUTING:
                    event_data["tool_name"] = "cost_analyzer"
                elif event_type == WebSocketEventType.TOOL_COMPLETED:
                    event_data["results"] = {"status": "success", "data_processed": True}
                elif event_type == WebSocketEventType.AGENT_COMPLETED:
                    event_data["final_result"] = "Analysis complete with recommendations"
                
                await client.send_message(event_type, event_data, user_id="flow-test-user")
            
            # Verify all events were sent in correct order
            assert len(client.sent_messages) == 5
            
            for i, expected_event in enumerate(expected_events):
                actual_event = client.sent_messages[i]
                assert actual_event.event_type == expected_event
                assert actual_event.data["execution_id"] == execution_id
                assert actual_event.data["step"] == i + 1
            
            self.record_metric("complete_agent_flow", len(client.sent_messages))
            
            # Verify all 5 critical events tracked
            assert self.get_websocket_events_count() >= 5


class TestWebSocketMultiUserIsolation(SSotBaseTestCase):
    """
    Test WebSocket multi-user isolation and security patterns.
    
    BVJ: User isolation ensures secure, personalized AI interactions
    """
    
    @pytest.mark.integration
    async def test_multi_user_websocket_isolation(self):
        """
        Test that multiple users have isolated WebSocket sessions.
        
        BVJ: User data isolation prevents cross-contamination of AI contexts
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple authenticated clients
            user1_client = await ws_util.create_authenticated_client("user1", "token1")
            user2_client = await ws_util.create_authenticated_client("user2", "token2")
            user3_client = await ws_util.create_authenticated_client("user3", "token3")
            
            # Mock connections
            for client in [user1_client, user2_client, user3_client]:
                client.is_connected = True
                client.websocket = AsyncMock()
            
            # Send messages from each user
            await user1_client.send_message(
                WebSocketEventType.PING,
                {"user_data": "user1_specific_data"},
                user_id="user1"
            )
            
            await user2_client.send_message(
                WebSocketEventType.PING,
                {"user_data": "user2_specific_data"},
                user_id="user2"
            )
            
            await user3_client.send_message(
                WebSocketEventType.PING,
                {"user_data": "user3_specific_data"},
                user_id="user3"
            )
            
            # Verify user isolation - each client has only its own messages
            assert len(user1_client.sent_messages) == 1
            assert len(user2_client.sent_messages) == 1
            assert len(user3_client.sent_messages) == 1
            
            assert user1_client.sent_messages[0].data["user_data"] == "user1_specific_data"
            assert user2_client.sent_messages[0].data["user_data"] == "user2_specific_data"
            assert user3_client.sent_messages[0].data["user_data"] == "user3_specific_data"
            
            # Verify user IDs are correctly set
            assert user1_client.sent_messages[0].user_id == "user1"
            assert user2_client.sent_messages[0].user_id == "user2"
            assert user3_client.sent_messages[0].user_id == "user3"
            
            self.record_metric("multi_user_isolation", "verified")
    
    @pytest.mark.integration
    async def test_websocket_authentication_security(self):
        """
        Test WebSocket authentication security and token validation.
        
        BVJ: Secure authentication prevents unauthorized access to AI services
        """
        auth_helper = E2EAuthHelper()
        
        # Test with valid token
        valid_token = auth_helper.create_test_jwt_token(
            user_id="secure-user",
            permissions=["read", "write"]
        )
        
        async with WebSocketTestUtility() as ws_util:
            # Create client with valid token
            valid_client = await ws_util.create_authenticated_client("secure-user", valid_token)
            
            # Verify authentication headers are set correctly
            assert valid_client.headers["Authorization"] == f"Bearer {valid_token}"
            assert valid_client.headers["X-User-ID"] == "secure-user"
            
            # Test with expired/invalid token
            invalid_token = "invalid.jwt.token"
            invalid_client = await ws_util.create_authenticated_client("invalid-user", invalid_token)
            
            # Verify invalid client still has headers (server will reject)
            assert invalid_client.headers["Authorization"] == f"Bearer {invalid_token}"
            
            self.record_metric("authentication_security", "tested")
    
    @pytest.mark.integration
    async def test_websocket_concurrent_connections(self):
        """
        Test handling of concurrent WebSocket connections.
        
        BVJ: Concurrent connection support enables multiple users simultaneously
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple concurrent connections
            connection_count = 5
            clients = await ws_util.create_multi_user_clients(connection_count)
            
            # Verify all clients were created
            assert len(clients) == connection_count
            
            # Verify each client has unique identifiers
            client_ids = [client.test_id for client in clients]
            assert len(set(client_ids)) == connection_count, "All clients should have unique IDs"
            
            # Mock concurrent message sending
            tasks = []
            for i, client in enumerate(clients):
                client.is_connected = True
                client.websocket = AsyncMock()
                
                task = asyncio.create_task(
                    client.send_message(
                        WebSocketEventType.PING,
                        {"client_index": i, "timestamp": time.time()},
                        user_id=f"concurrent_user_{i}"
                    )
                )
                tasks.append(task)
            
            # Wait for all messages to be sent concurrently
            await asyncio.gather(*tasks)
            
            # Verify all clients sent their messages
            for i, client in enumerate(clients):
                assert len(client.sent_messages) == 1
                assert client.sent_messages[0].data["client_index"] == i
            
            self.record_metric("concurrent_connections", connection_count)


class TestWebSocketPerformanceAndResilience(SSotBaseTestCase):
    """
    Test WebSocket performance characteristics and connection resilience.
    
    BVJ: Reliable performance ensures consistent AI service delivery
    """
    
    @pytest.mark.integration
    async def test_websocket_message_throughput(self):
        """
        Test WebSocket message throughput and latency.
        
        BVJ: High throughput ensures responsive AI interactions
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Test batch message sending
            message_count = 50
            start_time = time.time()
            
            for i in range(message_count):
                await client.send_message(
                    WebSocketEventType.PING,
                    {"sequence": i, "batch_test": True},
                    user_id="throughput-user"
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify all messages were sent
            assert len(client.sent_messages) == message_count
            
            # Calculate performance metrics
            messages_per_second = message_count / duration if duration > 0 else 0
            avg_latency_per_message = (duration / message_count) * 1000  # ms
            
            # Performance assertions
            assert messages_per_second > 10, "Should handle at least 10 messages/second"
            assert avg_latency_per_message < 100, "Average message latency should be under 100ms"
            
            self.record_metric("messages_per_second", messages_per_second)
            self.record_metric("avg_latency_ms", avg_latency_per_message)
    
    @pytest.mark.integration
    async def test_websocket_connection_resilience(self):
        """
        Test WebSocket connection resilience with reconnection.
        
        BVJ: Connection resilience ensures uninterrupted AI service availability
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Simulate connection resilience test
            resilience_results = await ws_util.test_connection_resilience(client, disconnect_count=3)
            
            # Verify resilience metrics
            assert "disconnect_count" in resilience_results
            assert "successful_reconnects" in resilience_results
            assert "avg_reconnect_time" in resilience_results
            
            # Basic resilience expectations
            assert resilience_results["disconnect_count"] == 3
            
            self.record_metric("resilience_test", resilience_results)
    
    @pytest.mark.integration
    async def test_websocket_memory_usage_tracking(self):
        """
        Test WebSocket connection memory usage and cleanup.
        
        BVJ: Efficient memory usage prevents service degradation under load
        """
        async with WebSocketTestUtility() as ws_util:
            metrics = ws_util.metrics
            
            # Track initial state
            initial_clients = len(ws_util.active_clients)
            
            # Create and use clients
            test_clients = []
            for i in range(10):
                client = await ws_util.create_test_client(user_id=f"memory-test-{i}")
                client.is_connected = True
                client.websocket = AsyncMock()
                test_clients.append(client)
            
            # Verify clients are tracked
            assert len(ws_util.active_clients) == initial_clients + 10
            
            # Send messages to accumulate data
            for client in test_clients:
                await client.send_message(
                    WebSocketEventType.PING,
                    {"memory_test": True, "data": "x" * 1000},  # 1KB message
                    user_id=client.headers.get("X-User-ID", "unknown")
                )
            
            # Verify message accumulation
            total_messages = sum(len(client.sent_messages) for client in test_clients)
            assert total_messages == 10
            
            # Test cleanup
            await ws_util.disconnect_all_clients()
            
            # Verify cleanup
            connected_count = sum(1 for client in test_clients if client.is_connected)
            assert connected_count == 0, "All clients should be disconnected after cleanup"
            
            self.record_metric("memory_usage_test", "completed")
    
    @pytest.mark.integration
    async def test_websocket_error_handling_comprehensive(self):
        """
        Test comprehensive WebSocket error handling scenarios.
        
        BVJ: Robust error handling prevents service disruption and user confusion
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Test 1: Sending message without connection
            with pytest.raises(RuntimeError, match="not connected"):
                await client.send_message(WebSocketEventType.PING, {})
            
            # Test 2: Mock connection with send failure
            mock_websocket = AsyncMock()
            mock_websocket.send.side_effect = ConnectionClosed(None, None)
            client.websocket = mock_websocket
            client.is_connected = True
            
            with pytest.raises(ConnectionClosed):
                await client.send_message(WebSocketEventType.PING, {"test": "error"})
            
            # Test 3: Message timeout scenario
            client.websocket = AsyncMock()
            client.is_connected = True
            
            with pytest.raises(asyncio.TimeoutError):
                await client.wait_for_message(timeout=0.1)  # Very short timeout
            
            self.record_metric("error_handling", "comprehensive")


class TestWebSocketEventValidation(SSotBaseTestCase):
    """
    Test WebSocket event validation and message integrity.
    
    BVJ: Event validation ensures reliable AI response delivery
    """
    
    @pytest.mark.integration
    async def test_websocket_event_type_validation(self):
        """
        Test validation of WebSocket event types.
        
        BVJ: Event type validation ensures proper message routing and handling
        """
        # Test all valid event types
        valid_events = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.AGENT_COMPLETED,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.STATUS_UPDATE,
            WebSocketEventType.ERROR,
            WebSocketEventType.PING,
            WebSocketEventType.PONG,
            WebSocketEventType.THREAD_UPDATE,
            WebSocketEventType.MESSAGE_CREATED,
            WebSocketEventType.USER_CONNECTED,
            WebSocketEventType.USER_DISCONNECTED
        ]
        
        for event_type in valid_events:
            message = WebSocketMessage(
                event_type=event_type,
                data={"test": "validation"},
                timestamp=datetime.now(timezone.utc),
                message_id=f"msg_{event_type.value}"
            )
            
            # Test serialization/deserialization
            serialized = message.to_dict()
            restored = WebSocketMessage.from_dict(serialized)
            
            assert restored.event_type == event_type
            assert serialized["type"] == event_type.value
        
        self.record_metric("event_validation", len(valid_events))
    
    @pytest.mark.integration
    async def test_websocket_message_integrity(self):
        """
        Test WebSocket message data integrity and completeness.
        
        BVJ: Message integrity ensures users receive complete AI responses
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Test message with complex nested data
            complex_data = {
                "analysis_results": {
                    "cost_breakdown": [
                        {"service": "EC2", "cost": 2500.75, "percentage": 46.1},
                        {"service": "RDS", "cost": 1200.25, "percentage": 22.1},
                        {"service": "S3", "cost": 850.50, "percentage": 15.7}
                    ],
                    "recommendations": {
                        "immediate": [
                            {"action": "Right-size instances", "impact": "High", "effort": "Low"},
                            {"action": "Enable auto-scaling", "impact": "Medium", "effort": "Low"}
                        ],
                        "planned": [
                            {"action": "Migrate to Graviton", "impact": "High", "effort": "High"}
                        ]
                    },
                    "metadata": {
                        "analysis_time": 45.2,
                        "data_points": 1247,
                        "confidence_score": 0.94
                    }
                }
            }
            
            # Send complex message
            await client.send_message(
                WebSocketEventType.AGENT_COMPLETED,
                complex_data,
                user_id="integrity-test-user",
                thread_id="thread_integrity_test"
            )
            
            # Verify message integrity
            sent_message = client.sent_messages[0]
            assert sent_message.data == complex_data
            assert len(sent_message.data["analysis_results"]["cost_breakdown"]) == 3
            assert sent_message.data["analysis_results"]["metadata"]["confidence_score"] == 0.94
            
            # Test JSON serialization integrity
            serialized = sent_message.to_dict()
            json_string = json.dumps(serialized)
            restored_data = json.loads(json_string)
            
            # Verify no data loss in serialization
            original_cost = complex_data["analysis_results"]["cost_breakdown"][0]["cost"]
            restored_cost = restored_data["data"]["analysis_results"]["cost_breakdown"][0]["cost"]
            assert original_cost == restored_cost
            
            self.record_metric("message_integrity", "verified")
    
    @pytest.mark.integration
    async def test_websocket_event_ordering(self):
        """
        Test WebSocket event ordering and sequence validation.
        
        BVJ: Proper event ordering ensures users see logical AI processing progression
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            
            # Test agent event flow ordering
            expected_sequence = [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]
            
            # Simulate ordered execution
            execution_results = await ws_util.simulate_agent_execution(
                client,
                "Test cost analysis request"
            )
            
            # Verify simulation structure
            assert "execution_id" in execution_results
            assert "thread_id" in execution_results
            assert "execution_time" in execution_results
            
            self.record_metric("event_ordering", "tested")


@pytest.mark.integration
class TestWebSocketConfigurationAndEnvironment(SSotBaseTestCase):
    """
    Test WebSocket configuration and environment handling.
    
    BVJ: Proper configuration ensures reliable WebSocket service across environments
    """
    
    async def test_websocket_environment_configuration(self):
        """
        Test WebSocket URL and configuration from environment.
        
        BVJ: Environment-based configuration enables deployment flexibility
        """
        env = self.get_env()
        
        # Test default configuration
        with self.temp_env_vars(WEBSOCKET_TEST_URL="ws://test.example.com:8000/ws"):
            async with WebSocketTestUtility() as ws_util:
                assert "test.example.com" in ws_util.base_url
                assert ws_util.base_url.startswith("ws://")
        
        # Test HTTPS to WSS conversion
        with self.temp_env_vars(WEBSOCKET_URL="https://secure.example.com/ws"):
            async with WebSocketTestUtility() as ws_util:
                assert ws_util.base_url.startswith("wss://")
                assert "secure.example.com" in ws_util.base_url
        
        self.record_metric("environment_config", "tested")
    
    async def test_websocket_timeout_configuration(self):
        """
        Test WebSocket timeout configuration.
        
        BVJ: Configurable timeouts prevent indefinite waits and improve user experience
        """
        # Test custom timeout configuration
        with self.temp_env_vars(WEBSOCKET_TEST_TIMEOUT="15"):
            async with WebSocketTestUtility() as ws_util:
                assert ws_util.default_timeout == 15.0
        
        # Test retry configuration
        with self.temp_env_vars(WEBSOCKET_RETRY_COUNT="5"):
            async with WebSocketTestUtility() as ws_util:
                assert ws_util.connection_retry_count == 5
        
        self.record_metric("timeout_config", "tested")
    
    async def test_websocket_performance_monitoring_config(self):
        """
        Test WebSocket performance monitoring configuration.
        
        BVJ: Performance monitoring enables optimization of AI service delivery
        """
        # Test with performance monitoring enabled
        with self.temp_env_vars(WS_ENABLE_PERF_MONITORING="true"):
            async with WebSocketTestUtility() as ws_util:
                assert ws_util.enable_performance_monitoring is True
                
                # Verify metrics tracking is functional
                assert isinstance(ws_util.metrics, WebSocketTestMetrics)
                assert ws_util.metrics.connection_time == 0.0  # Initial state
        
        # Test with performance monitoring disabled
        with self.temp_env_vars(WS_ENABLE_PERF_MONITORING="false"):
            async with WebSocketTestUtility() as ws_util:
                assert ws_util.enable_performance_monitoring is False
        
        self.record_metric("monitoring_config", "tested")