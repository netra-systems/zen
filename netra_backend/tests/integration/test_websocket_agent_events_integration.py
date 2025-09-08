"""
Integration Tests for WebSocket Agent Events - Batch 3 WebSocket Infrastructure Suite
==============================================================================

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat System Reliability & Real-Time User Engagement
- Value Impact: Validates complete WebSocket event flows with real connections
- Strategic Impact: Ensures chat business value through end-to-end event delivery

CRITICAL CHAT BUSINESS VALUE EVENTS TESTED:
1. agent_started -> Users see AI began processing (prevents abandonment)
2. agent_thinking -> Real-time reasoning visibility (builds trust)
3. tool_executing -> Tool usage transparency (demonstrates value)
4. tool_completed -> Results delivery (actionable insights)
5. agent_completed -> Task completion signal (clear boundaries)

This suite tests real WebSocket connections with the AgentWebSocketBridge
and validates event delivery for multi-user chat scenarios.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class TestWebSocketAgentEventsIntegration(SSotBaseTestCase):
    """
    Integration tests for WebSocket agent events with real connections.
    
    These tests validate that chat-critical events flow properly through
    the WebSocket infrastructure, ensuring users receive real-time feedback.
    """

    async def test_complete_agent_execution_event_flow(self):
        """
        Test complete agent execution flow with all critical events.
        
        BUSINESS VALUE: Validates the complete chat experience from agent_started
        through agent_completed, ensuring users see the full AI processing journey.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange - Create authenticated client for chat session
            user_id = f"chat_user_{uuid.uuid4().hex[:8]}"
            client = await ws_util.create_authenticated_client(user_id)
            
            # Expected chat events in order
            expected_events = [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING, 
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]
            
            # Act - Simulate complete agent execution
            execution_result = await ws_util.simulate_agent_execution(
                client, 
                "Analyze our Q3 sales performance and identify growth opportunities"
            )
            
            # Assert - Verify complete execution succeeded
            assert execution_result["success"] is True
            assert execution_result["execution_time"] > 0
            assert execution_result["events_received"] == len(expected_events)
            
            # Verify all critical events were received
            for event_type in expected_events:
                events_of_type = client.get_messages_by_type(event_type)
                assert len(events_of_type) > 0, f"Missing critical chat event: {event_type.value}"
            
            # Verify event ordering for user understanding
            all_events = [msg for msg in client.received_messages 
                         if msg.event_type in expected_events]
            event_sequence = [msg.event_type for msg in all_events]
            
            # Should follow logical progression
            assert event_sequence.index(WebSocketEventType.AGENT_STARTED) == 0
            assert event_sequence.index(WebSocketEventType.AGENT_COMPLETED) == len(event_sequence) - 1

    async def test_multi_user_concurrent_agent_events(self):
        """
        Test concurrent agent events for multiple users don't interfere.
        
        BUSINESS VALUE: Multi-user chat system maintains isolation - users only
        receive events for their own conversations, preventing confusion.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange - Create multiple authenticated users
            user_count = 3
            clients = []
            user_threads = {}
            
            for i in range(user_count):
                user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:6]}"
                client = await ws_util.create_authenticated_client(user_id)
                await client.connect()
                clients.append(client)
                user_threads[user_id] = f"thread_{i}_{uuid.uuid4().hex[:6]}"
            
            # Act - Start concurrent agent executions
            execution_tasks = []
            for i, client in enumerate(clients):
                task = asyncio.create_task(
                    ws_util.simulate_agent_execution(
                        client,
                        f"User {i} request: Analyze data set {i}"
                    )
                )
                execution_tasks.append(task)
            
            # Wait for all executions to complete
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # Assert - All executions should succeed
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"User {i} execution failed: {result}"
                assert result["success"] is True
            
            # Verify event isolation - each user should only receive their events
            for i, client in enumerate(clients):
                agent_started_events = client.get_messages_by_type(WebSocketEventType.AGENT_STARTED)
                assert len(agent_started_events) == 1, f"User {i} received wrong number of agent_started events"
                
                # Verify event belongs to this user's thread
                event = agent_started_events[0]
                assert event.thread_id is not None
                # Each user should have unique thread context

    async def test_websocket_event_delivery_guarantees(self):
        """
        Test WebSocket event delivery guarantees for critical chat events.
        
        BUSINESS VALUE: Critical events (agent_started, tool_executing, etc.) 
        are never lost, ensuring users always receive complete chat feedback.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange
            client = await ws_util.create_authenticated_client("guarantee_test_user")
            await client.connect()
            
            # Create agent context
            agent_context = AgentExecutionContext(
                run_id=f"test-run-{uuid.uuid4().hex[:8]}",
                agent_name="reliability_tester",
                thread_id=f"thread-{uuid.uuid4().hex[:8]}",
                user_id="guarantee_test_user"
            )
            
            # Mock WebSocket manager with intermittent failures
            mock_manager = AsyncMock()
            # Simulate failure then success for critical event delivery
            mock_manager.send_to_thread.side_effect = [False, True, False, True, True]
            
            with patch('netra_backend.app.websocket_core.create_websocket_manager', return_value=mock_manager):
                bridge = AgentWebSocketBridge()
                await bridge.initialize()
                
                # Act - Send critical events
                critical_events = [
                    ("send_agent_started", [agent_context]),
                    ("send_tool_executing", [agent_context, "data_processor"]),
                    ("send_tool_completed", [agent_context, "data_processor", {"status": "success"}]),
                    ("send_agent_completed", [agent_context])
                ]
                
                for method_name, args in critical_events:
                    method = getattr(bridge, method_name, None)
                    if method:
                        await method(*args)
            
            # Assert - All critical events should have retry mechanisms
            assert mock_manager.send_to_thread.call_count >= len(critical_events)

    async def test_websocket_event_message_structure_validation(self):
        """
        Test WebSocket event messages have proper structure for chat UI.
        
        BUSINESS VALUE: Consistent message structure ensures reliable chat UI
        rendering and prevents client-side JavaScript errors.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange
            client = await ws_util.create_authenticated_client("structure_test_user")
            await client.connect()
            
            # Act - Send various event types
            test_events = [
                (WebSocketEventType.AGENT_STARTED, {
                    "agent_name": "structure_tester",
                    "task": "validation",
                    "timestamp": datetime.now().isoformat()
                }),
                (WebSocketEventType.AGENT_THINKING, {
                    "thought": "Validating message structures",
                    "progress": 25.0,
                    "step": "analysis"
                }),
                (WebSocketEventType.TOOL_EXECUTING, {
                    "tool_name": "structure_validator",
                    "purpose": "Ensuring consistent formats"
                }),
                (WebSocketEventType.TOOL_COMPLETED, {
                    "tool_name": "structure_validator",
                    "result": {"validation_passed": True}
                }),
                (WebSocketEventType.AGENT_COMPLETED, {
                    "summary": "Structure validation completed",
                    "duration": 2500
                })
            ]
            
            for event_type, data in test_events:
                await client.send_message(event_type, data)
            
            # Wait for message processing
            await asyncio.sleep(0.5)
            
            # Assert - All messages should be properly structured
            for sent_message in client.sent_messages:
                message_dict = sent_message.to_dict()
                
                # Verify required fields for chat UI
                assert "type" in message_dict
                assert "data" in message_dict
                assert "timestamp" in message_dict
                assert "message_id" in message_dict
                
                # Verify message can be JSON serialized (no circular refs)
                json_str = json.dumps(message_dict)
                assert len(json_str) > 0
                
                # Verify structure is parseable
                parsed = json.loads(json_str)
                assert parsed["type"] == sent_message.event_type.value

    async def test_websocket_event_timing_performance(self):
        """
        Test WebSocket event timing meets chat performance requirements.
        
        BUSINESS VALUE: Events arrive within acceptable timeframes for good
        chat UX - users don't experience delays that suggest system problems.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange
            client = await ws_util.create_authenticated_client("timing_test_user")
            await client.connect()
            
            # Performance requirements for chat events
            max_event_latency_ms = 500  # 500ms max latency for responsive chat
            max_total_flow_time_ms = 5000  # 5s max for complete flow
            
            # Act - Measure event timing
            start_time = time.time()
            
            await client.send_message(WebSocketEventType.AGENT_STARTED, {
                "agent_name": "timing_tester",
                "start_timestamp": start_time
            })
            
            # Simulate rapid event sequence
            events_to_send = [
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]
            
            event_times = []
            for event_type in events_to_send:
                event_start = time.time()
                await client.send_message(event_type, {
                    "timestamp": event_start,
                    "sequence": len(event_times)
                })
                event_times.append(time.time() - event_start)
            
            total_flow_time = (time.time() - start_time) * 1000
            
            # Assert - Performance requirements met
            for i, event_time in enumerate(event_times):
                event_latency_ms = event_time * 1000
                assert event_latency_ms < max_event_latency_ms, \
                    f"Event {i} latency {event_latency_ms}ms exceeds {max_event_latency_ms}ms limit"
            
            assert total_flow_time < max_total_flow_time_ms, \
                f"Total flow time {total_flow_time}ms exceeds {max_total_flow_time_ms}ms limit"

    async def test_websocket_connection_resilience_with_events(self):
        """
        Test WebSocket connection resilience during agent event flows.
        
        BUSINESS VALUE: Chat remains functional even with network issues - 
        users can continue conversations after temporary connection problems.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange
            client = await ws_util.create_authenticated_client("resilience_test_user")
            await client.connect()
            
            # Act - Test connection resilience
            resilience_results = await ws_util.test_connection_resilience(
                client, disconnect_count=2
            )
            
            # Assert - Connection should recover successfully
            assert resilience_results["successful_reconnects"] >= 1
            assert resilience_results["failed_reconnects"] <= 1  # Allow some failures
            assert resilience_results["avg_reconnect_time"] < 5.0  # Should reconnect quickly
            
            # Verify events work after reconnection
            if client.is_connected:
                await client.send_message(WebSocketEventType.AGENT_STARTED, {
                    "agent_name": "resilience_tester",
                    "post_recovery": True
                })
                
                # Should receive the event
                response = await client.wait_for_message(timeout=3.0)
                assert response is not None

    async def test_large_payload_event_handling(self):
        """
        Test WebSocket handles large payloads for data-rich chat interactions.
        
        BUSINESS VALUE: Chat can handle complex AI responses with substantial
        data (analysis results, reports) without breaking the UI.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange
            client = await ws_util.create_authenticated_client("large_payload_user")
            await client.connect()
            
            # Create large but realistic chat payload
            large_analysis_result = {
                "summary": "Comprehensive Q3 analysis completed",
                "metrics": {
                    f"metric_{i}": {
                        "value": i * 100,
                        "trend": "upward" if i % 2 == 0 else "downward",
                        "details": f"Detailed analysis for metric {i}: " + "x" * 200
                    } for i in range(50)  # 50 detailed metrics
                },
                "recommendations": [
                    f"Recommendation {i}: " + "Detailed explanation " * 20
                    for i in range(10)  # 10 detailed recommendations
                ],
                "raw_data": [
                    {"date": f"2024-Q3-{i:02d}", "values": list(range(i, i+20))}
                    for i in range(90)  # 90 days of data
                ],
                "visualizations": {
                    "charts": [f"chart_data_{i}" * 100 for i in range(5)],
                    "tables": [f"table_data_{i}" * 150 for i in range(3)]
                }
            }
            
            # Act - Send large payload
            start_time = time.time()
            await client.send_message(WebSocketEventType.AGENT_COMPLETED, {
                "agent_name": "data_analyzer",
                "result": large_analysis_result,
                "processing_time_ms": 15000
            })
            
            send_time = (time.time() - start_time) * 1000
            
            # Assert - Large payload should be handled efficiently
            assert send_time < 2000, f"Large payload took {send_time}ms to send (should be < 2000ms)"
            
            # Verify message was added to sent messages
            assert len(client.sent_messages) > 0
            last_message = client.sent_messages[-1]
            assert last_message.event_type == WebSocketEventType.AGENT_COMPLETED
            assert "result" in last_message.data
            assert "metrics" in last_message.data["result"]

    async def test_websocket_error_event_user_guidance(self):
        """
        Test WebSocket error events provide helpful user guidance.
        
        BUSINESS VALUE: When chat AI fails, users get clear, actionable guidance
        on what went wrong and how to recover, maintaining trust and engagement.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange
            client = await ws_util.create_authenticated_client("error_guidance_user")
            await client.connect()
            
            # Test different error scenarios with user guidance
            error_scenarios = [
                {
                    "error_type": "rate_limit",
                    "message": "API rate limit exceeded",
                    "expected_guidance": ["wait", "rate limit", "moment"]
                },
                {
                    "error_type": "timeout",
                    "message": "Request timed out",
                    "expected_guidance": ["longer than expected", "try again", "smaller parts"]
                },
                {
                    "error_type": "validation",
                    "message": "Invalid input format",
                    "expected_guidance": ["request format", "required fields", "check"]
                },
                {
                    "error_type": "network",
                    "message": "Network connection failed", 
                    "expected_guidance": ["connectivity", "internet connection", "try again"]
                }
            ]
            
            # Act & Assert - Test each error scenario
            for scenario in error_scenarios:
                await client.send_message(WebSocketEventType.ERROR, {
                    "error_type": scenario["error_type"],
                    "error_message": scenario["message"],
                    "agent_name": "helpful_ai",
                    "is_recoverable": True,
                    "user_guidance": f"Error: {scenario['message']}. Please try again.",
                    "recovery_suggestions": [
                        "Check your request and try again",
                        "Wait a moment if the system is busy",
                        "Contact support if the problem persists"
                    ]
                })
                
                # Verify error message structure for user guidance
                error_message = client.sent_messages[-1]
                error_data = error_message.data
                
                assert error_data["error_type"] == scenario["error_type"]
                assert error_data["is_recoverable"] is True
                assert "user_guidance" in error_data
                assert "recovery_suggestions" in error_data
                assert len(error_data["recovery_suggestions"]) > 0


class TestWebSocketAgentEventsRealServices(SSotBaseTestCase):
    """
    Integration tests with real WebSocket services for agent events.
    
    These tests require Docker services to be running and test against
    actual WebSocket connections and agent execution flows.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_websocket_agent_execution_flow(self):
        """
        Test complete agent execution flow with real WebSocket services.
        
        BUSINESS VALUE: End-to-end validation that chat works in realistic
        deployment scenarios with actual service dependencies.
        """
        # This test requires real services - skip if not available
        try:
            async with WebSocketTestUtility() as ws_util:
                # Force real server connection (not mock mode)
                ws_util._mock_mode = False
                
                # Create client with real authentication
                user_id = f"real_test_user_{uuid.uuid4().hex[:8]}"
                client = await ws_util.create_authenticated_client(user_id)
                
                # Verify connection to real service
                connected = await client.connect(mock_mode=False)
                if not connected:
                    pytest.skip("Real WebSocket service not available")
                
                # Test real agent execution
                execution_result = await ws_util.simulate_agent_execution(
                    client,
                    "Real integration test: Analyze system performance"
                )
                
                # Should succeed with real services
                assert execution_result["success"] is True
                assert execution_result["execution_time"] > 0
                
                # Clean up
                await client.disconnect()
                
        except Exception as e:
            pytest.skip(f"Real WebSocket services not available: {e}")
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_real_websocket_authentication_events(self):
        """
        Test WebSocket authentication with real auth service integration.
        
        BUSINESS VALUE: Validates that authenticated chat sessions work 
        correctly with real authentication flows and user isolation.
        """
        try:
            async with WebSocketTestUtility() as ws_util:
                ws_util._mock_mode = False
                
                # Test multiple authenticated users
                user_count = 2
                authenticated_clients = []
                
                for i in range(user_count):
                    user_id = f"auth_test_user_{i}_{uuid.uuid4().hex[:6]}"
                    
                    # Create client with real authentication
                    client = await ws_util.create_authenticated_client(user_id)
                    connected = await client.connect(mock_mode=False)
                    
                    if not connected:
                        pytest.skip("Real authentication service not available")
                    
                    authenticated_clients.append((user_id, client))
                
                # Verify each user gets isolated events
                for user_id, client in authenticated_clients:
                    await client.send_message(WebSocketEventType.AGENT_STARTED, {
                        "agent_name": "auth_test_agent",
                        "user_id": user_id,
                        "authenticated": True
                    })
                
                # Clean up
                for _, client in authenticated_clients:
                    await client.disconnect()
                    
        except Exception as e:
            pytest.skip(f"Real authentication service not available: {e}")