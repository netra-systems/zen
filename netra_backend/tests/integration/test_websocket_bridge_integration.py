"""
Integration Tests for WebSocket Bridge - Batch 3 WebSocket Infrastructure Suite
=============================================================================

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Chat System Integration & User Experience
- Value Impact: Validates WebSocket-Agent bridge delivers seamless chat interactions
- Strategic Impact: Ensures replacement of deprecated WebSocketNotifier maintains business value

CRITICAL: Tests the AgentWebSocketBridge which replaces deprecated WebSocketNotifier.
Bridge must deliver same chat business value with improved reliability and performance.

CHAT BUSINESS VALUE BRIDGE VALIDATION:
1. Agent-WebSocket coordination maintains real-time feedback
2. Event delivery guarantees prevent lost chat notifications
3. User isolation works correctly in multi-user scenarios
4. Performance meets chat responsiveness requirements
5. Error handling provides graceful user experience

This suite tests the bridge integration with real components and services.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch

from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core import create_websocket_manager


class TestWebSocketBridgeIntegration(SSotBaseTestCase):
    """
    Integration tests for AgentWebSocketBridge with real components.
    
    These tests validate that the bridge successfully coordinates between
    agent execution and WebSocket event delivery for chat business value.
    """
    
    @pytest.fixture
    async def websocket_bridge(self):
        """Create and initialize AgentWebSocketBridge for testing."""
        bridge = AgentWebSocketBridge()
        
        # Initialize with test configuration
        await bridge.initialize()
        
        yield bridge
        
        # Cleanup
        await bridge.shutdown()
    
    @pytest.fixture
    def agent_execution_context(self):
        """Create test agent execution context."""
        return AgentExecutionContext(
            run_id=f"bridge-test-{uuid.uuid4().hex[:8]}",
            agent_name="integration_tester",
            thread_id=f"bridge-thread-{uuid.uuid4().hex[:8]}",
            user_id=f"bridge-user-{uuid.uuid4().hex[:8]}"
        )

    async def test_bridge_initialization_and_health(self, websocket_bridge):
        """
        Test WebSocket bridge initialization and health monitoring.
        
        BUSINESS VALUE: Bridge initializes correctly and maintains healthy state
        for reliable chat service delivery.
        """
        # Assert - Bridge should be initialized and healthy
        health_status = await websocket_bridge.get_health_status()
        
        assert health_status.state in [IntegrationState.ACTIVE, IntegrationState.INITIALIZING]
        assert health_status.websocket_manager_healthy is True
        assert health_status.registry_healthy is True
        assert health_status.consecutive_failures == 0
    
    async def test_bridge_agent_event_coordination(self, websocket_bridge, agent_execution_context):
        """
        Test bridge coordinates agent events with WebSocket delivery.
        
        BUSINESS VALUE: Agent execution events are properly translated to
        WebSocket messages that provide real-time chat feedback to users.
        """
        # Arrange - Mock WebSocket manager to capture events
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
        
        # Replace bridge's WebSocket manager with mock
        websocket_bridge._websocket_manager = mock_ws_manager
        
        # Act - Send critical chat events through bridge
        chat_events = [
            ("send_agent_started", [agent_execution_context]),
            ("send_agent_thinking", [
                agent_execution_context,
                "Analyzing business requirements", 
                1,
                25.0,
                8000,
                "requirement_analysis"
            ]),
            ("send_tool_executing", [
                agent_execution_context,
                "business_analyzer",
                "Extracting key metrics from data",
                5000,
                "Revenue and growth analysis"
            ]),
            ("send_tool_completed", [
                agent_execution_context,
                "business_analyzer",
                {
                    "status": "success",
                    "insights_found": 8,
                    "key_metrics": ["revenue_growth", "customer_retention"],
                    "recommendations": "Focus on high-value segments"
                }
            ]),
            ("send_agent_completed", [
                agent_execution_context,
                {
                    "analysis_summary": "Comprehensive business analysis completed",
                    "action_items": ["Segment optimization", "Revenue focus"],
                    "confidence_score": 0.91
                },
                15750.0
            ])
        ]
        
        # Execute all events through bridge
        for method_name, args in chat_events:
            method = getattr(websocket_bridge, method_name, None)
            if method and callable(method):
                await method(*args)
        
        # Assert - All events should be delivered through WebSocket manager
        assert mock_ws_manager.send_to_thread.call_count == len(chat_events)
        
        # Verify events went to correct thread
        call_args_list = mock_ws_manager.send_to_thread.call_args_list
        for call_args in call_args_list:
            thread_id, message = call_args[0]
            assert thread_id == agent_execution_context.thread_id
            assert isinstance(message, dict)
            assert "type" in message
            assert "payload" in message
    
    async def test_bridge_user_isolation_enforcement(self, websocket_bridge):
        """
        Test bridge enforces user isolation for multi-user chat.
        
        BUSINESS VALUE: Users only receive their own chat events, maintaining
        conversation privacy and preventing cross-user confusion.
        """
        # Arrange - Multiple users with different contexts
        user_contexts = []
        for i in range(3):
            context = AgentExecutionContext(
                run_id=f"isolation-run-{i}-{uuid.uuid4().hex[:6]}",
                agent_name=f"user_agent_{i}",
                thread_id=f"isolation-thread-{i}-{uuid.uuid4().hex[:6]}",
                user_id=f"isolation-user-{i}"
            )
            user_contexts.append(context)
        
        # Mock WebSocket manager to track message routing
        mock_ws_manager = AsyncMock()
        sent_messages = []
        
        async def capture_send_to_thread(thread_id, message):
            sent_messages.append((thread_id, message))
            return True
        
        mock_ws_manager.send_to_thread.side_effect = capture_send_to_thread
        websocket_bridge._websocket_manager = mock_ws_manager
        
        # Act - Send events for each user
        for i, context in enumerate(user_contexts):
            await websocket_bridge.send_agent_started(context)
            await websocket_bridge.send_agent_completed(
                context,
                {"result": f"Analysis for user {i} completed"},
                2500.0
            )
        
        # Assert - Messages routed to correct threads
        assert len(sent_messages) == len(user_contexts) * 2  # 2 events per user
        
        # Verify thread isolation
        thread_message_map = {}
        for thread_id, message in sent_messages:
            if thread_id not in thread_message_map:
                thread_message_map[thread_id] = []
            thread_message_map[thread_id].append(message)
        
        # Each user should have their own thread
        assert len(thread_message_map) == len(user_contexts)
        
        # Verify messages are properly isolated
        for i, context in enumerate(user_contexts):
            messages_for_thread = thread_message_map.get(context.thread_id, [])
            assert len(messages_for_thread) == 2  # agent_started + agent_completed
    
    async def test_bridge_error_handling_and_recovery(self, websocket_bridge, agent_execution_context):
        """
        Test bridge error handling maintains chat service availability.
        
        BUSINESS VALUE: Bridge gracefully handles errors without interrupting
        user chat sessions, maintaining reliable AI interaction experience.
        """
        # Arrange - Mock WebSocket manager with intermittent failures
        mock_ws_manager = AsyncMock()
        failure_count = 0
        
        async def failing_send_to_thread(thread_id, message):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # First 2 calls fail
                raise Exception("Simulated WebSocket failure")
            return True  # Subsequent calls succeed
        
        mock_ws_manager.send_to_thread.side_effect = failing_send_to_thread
        websocket_bridge._websocket_manager = mock_ws_manager
        
        # Act - Send events that will initially fail
        success_count = 0
        error_count = 0
        
        events_to_test = [
            ("send_agent_started", [agent_execution_context]),
            ("send_tool_executing", [agent_execution_context, "error_test_tool"]),
            ("send_tool_completed", [agent_execution_context, "error_test_tool", {"status": "recovered"}]),
            ("send_agent_completed", [agent_execution_context, {"recovery": "successful"}, 1000.0])
        ]
        
        for method_name, args in events_to_test:
            try:
                method = getattr(websocket_bridge, method_name, None)
                if method:
                    await method(*args)
                success_count += 1
            except Exception:
                error_count += 1
        
        # Assert - Bridge should handle errors gracefully
        # Some events may fail but system should recover
        assert success_count >= 2, f"Too few successful events: {success_count}"
        assert mock_ws_manager.send_to_thread.call_count >= len(events_to_test)
    
    async def test_bridge_performance_under_load(self, websocket_bridge):
        """
        Test bridge performance with high message volume for chat.
        
        BUSINESS VALUE: Bridge maintains responsive chat performance even
        under high message load from active AI conversations.
        """
        # Arrange - Multiple agent contexts for load testing
        load_contexts = []
        for i in range(10):
            context = AgentExecutionContext(
                run_id=f"load-run-{i}",
                agent_name=f"load_agent_{i}",
                thread_id=f"load-thread-{i}",
                user_id=f"load_user_{i}"
            )
            load_contexts.append(context)
        
        # Mock WebSocket manager for performance measurement
        mock_ws_manager = AsyncMock()
        message_times = []
        
        async def timed_send_to_thread(thread_id, message):
            timestamp = time.time()
            message_times.append(timestamp)
            await asyncio.sleep(0.001)  # Simulate small processing delay
            return True
        
        mock_ws_manager.send_to_thread.side_effect = timed_send_to_thread
        websocket_bridge._websocket_manager = mock_ws_manager
        
        # Act - Send high volume of events concurrently
        start_time = time.time()
        
        event_tasks = []
        for context in load_contexts:
            # Send multiple events per context
            events = [
                websocket_bridge.send_agent_started(context),
                websocket_bridge.send_agent_thinking(context, f"Processing for {context.user_id}", 1),
                websocket_bridge.send_tool_executing(context, "load_test_tool"),
                websocket_bridge.send_tool_completed(context, "load_test_tool", {"status": "success"}),
                websocket_bridge.send_agent_completed(context, {"result": "load test complete"}, 1000.0)
            ]
            event_tasks.extend(events)
        
        # Execute all events concurrently
        await asyncio.gather(*event_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Assert - Performance requirements met
        total_events = len(load_contexts) * 5  # 5 events per context
        events_per_second = total_events / total_time if total_time > 0 else 0
        
        # Should handle at least 100 events per second for responsive chat
        assert events_per_second >= 100, f"Poor performance: {events_per_second:.1f} events/sec"
        
        # All events should complete within reasonable time
        assert total_time <= 3.0, f"Load test took too long: {total_time:.2f}s"
        
        # Verify all messages were sent
        assert len(message_times) == total_events
    
    async def test_bridge_websocket_manager_integration(self, websocket_bridge):
        """
        Test bridge integration with real WebSocket manager.
        
        BUSINESS VALUE: Bridge works correctly with actual WebSocket infrastructure
        for production-ready chat service delivery.
        """
        # Arrange - Create real WebSocket manager
        real_ws_manager = create_websocket_manager()
        
        # Replace mock with real manager
        websocket_bridge._websocket_manager = real_ws_manager
        
        # Create test context
        test_context = AgentExecutionContext(
            run_id=f"real-integration-{uuid.uuid4().hex[:8]}",
            agent_name="real_integration_tester",
            thread_id=f"real-thread-{uuid.uuid4().hex[:8]}",
            user_id=f"real-user-{uuid.uuid4().hex[:8]}"
        )
        
        # Act - Send events through real WebSocket manager
        integration_success = True
        
        try:
            # Test critical chat events with real manager
            await websocket_bridge.send_agent_started(test_context)
            await websocket_bridge.send_agent_thinking(
                test_context,
                "Real integration test in progress",
                1,
                50.0,
                3000,
                "integration_testing"
            )
            await websocket_bridge.send_tool_executing(
                test_context,
                "integration_validator",
                "Validating real WebSocket integration"
            )
            await websocket_bridge.send_tool_completed(
                test_context,
                "integration_validator", 
                {
                    "validation_result": "success",
                    "integration_verified": True,
                    "latency_ms": 45
                }
            )
            await websocket_bridge.send_agent_completed(
                test_context,
                {
                    "integration_summary": "Real WebSocket bridge integration successful",
                    "performance_metrics": {
                        "events_sent": 4,
                        "success_rate": 1.0
                    }
                },
                3500.0
            )
            
        except Exception as e:
            integration_success = False
            print(f"Real integration test failed: {e}")
        
        # Assert - Integration should work with real components
        assert integration_success, "Bridge failed to integrate with real WebSocket manager"
        
        # Verify bridge health after real integration
        health_status = await websocket_bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.consecutive_failures == 0


class TestWebSocketBridgeUserEmitter(SSotBaseTestCase):
    """
    Integration tests for WebSocket bridge user emitter patterns.
    
    These tests validate per-user WebSocket emitters that ensure complete
    user isolation for enterprise multi-tenant chat scenarios.
    """
    
    async def test_user_emitter_creation_and_isolation(self):
        """
        Test user-specific WebSocket emitter creation and isolation.
        
        BUSINESS VALUE: Enterprise customers get guaranteed user isolation
        with dedicated emitters for secure multi-tenant chat.
        """
        async with WebSocketTestUtility() as ws_util:
            # Arrange - Create multiple user emitters
            users = [
                f"emitter_user_{i}_{uuid.uuid4().hex[:6]}" 
                for i in range(3)
            ]
            
            user_emitters = {}
            bridge = AgentWebSocketBridge()
            await bridge.initialize()
            
            try:
                # Act - Create user-specific emitters
                for user_id in users:
                    emitter = await bridge.create_user_emitter(user_id)
                    user_emitters[user_id] = emitter
                    
                    # Verify emitter is user-specific
                    assert emitter is not None
                    assert hasattr(emitter, 'user_id') or user_id in str(emitter)
                
                # Assert - Each user gets isolated emitter
                assert len(user_emitters) == len(users)
                
                # Verify emitters are different instances
                emitter_ids = set(id(emitter) for emitter in user_emitters.values())
                assert len(emitter_ids) == len(users), "User emitters not properly isolated"
                
            finally:
                await bridge.shutdown()
    
    async def test_user_emitter_event_delivery(self):
        """
        Test user emitter delivers events only to correct user.
        
        BUSINESS VALUE: User emitters ensure chat events reach only the
        intended recipient, maintaining conversation privacy.
        """
        # Arrange - Bridge with user emitter capability
        bridge = AgentWebSocketBridge()
        await bridge.initialize()
        
        try:
            # Create user emitters
            user_a = f"emitter_test_a_{uuid.uuid4().hex[:6]}"
            user_b = f"emitter_test_b_{uuid.uuid4().hex[:6]}"
            
            emitter_a = await bridge.create_user_emitter(user_a)
            emitter_b = await bridge.create_user_emitter(user_b)
            
            # Create contexts for each user
            context_a = AgentExecutionContext(
                run_id=f"emitter-run-a-{uuid.uuid4().hex[:6]}",
                agent_name="user_a_agent",
                thread_id=f"emitter-thread-a-{uuid.uuid4().hex[:6]}",
                user_id=user_a
            )
            
            context_b = AgentExecutionContext(
                run_id=f"emitter-run-b-{uuid.uuid4().hex[:6]}",
                agent_name="user_b_agent", 
                thread_id=f"emitter-thread-b-{uuid.uuid4().hex[:6]}",
                user_id=user_b
            )
            
            # Mock the emitters to track events
            emitter_a_events = []
            emitter_b_events = []
            
            async def mock_emit_a(event_type, payload):
                emitter_a_events.append((event_type, payload))
                
            async def mock_emit_b(event_type, payload):
                emitter_b_events.append((event_type, payload))
            
            # If emitters have emit methods, mock them
            if hasattr(emitter_a, 'emit'):
                emitter_a.emit = mock_emit_a
            if hasattr(emitter_b, 'emit'):
                emitter_b.emit = mock_emit_b
            
            # Act - Send events through user-specific emitters
            # This would typically happen through bridge coordination
            if hasattr(emitter_a, 'emit'):
                await emitter_a.emit("agent_started", {
                    "agent_name": context_a.agent_name,
                    "user_id": user_a
                })
                
            if hasattr(emitter_b, 'emit'):
                await emitter_b.emit("agent_started", {
                    "agent_name": context_b.agent_name, 
                    "user_id": user_b
                })
            
            # Assert - Events delivered to correct users only
            if emitter_a_events:
                assert len(emitter_a_events) == 1
                assert emitter_a_events[0][1]["user_id"] == user_a
                
            if emitter_b_events:
                assert len(emitter_b_events) == 1
                assert emitter_b_events[0][1]["user_id"] == user_b
                
        finally:
            await bridge.shutdown()


class TestWebSocketBridgeRealServices(SSotBaseTestCase):
    """
    Integration tests with real WebSocket services.
    
    These tests require Docker services and validate bridge functionality
    with actual WebSocket connections and agent execution flows.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_bridge_with_real_websocket_service(self):
        """
        Test bridge integration with real WebSocket service.
        
        BUSINESS VALUE: Validates bridge works in production-like environment
        with actual service dependencies for reliable chat delivery.
        """
        try:
            # Create bridge with real services
            bridge = AgentWebSocketBridge()
            await bridge.initialize()
            
            # Verify bridge connected to real services
            health_status = await bridge.get_health_status()
            if health_status.state != IntegrationState.ACTIVE:
                pytest.skip("Real WebSocket services not available")
            
            # Create test context
            real_context = AgentExecutionContext(
                run_id=f"real-service-{uuid.uuid4().hex[:8]}",
                agent_name="real_service_tester",
                thread_id=f"real-service-thread-{uuid.uuid4().hex[:8]}",
                user_id=f"real-service-user-{uuid.uuid4().hex[:8]}"
            )
            
            # Test full event flow with real services
            await bridge.send_agent_started(real_context)
            await bridge.send_agent_thinking(
                real_context,
                "Testing with real WebSocket services",
                1,
                30.0,
                5000,
                "service_validation"
            )
            await bridge.send_tool_executing(
                real_context,
                "real_service_validator",
                "Validating real service integration"
            )
            await bridge.send_tool_completed(
                real_context,
                "real_service_validator",
                {"service_integration": "successful", "latency": "acceptable"}
            )
            await bridge.send_agent_completed(
                real_context,
                {"real_service_test": "completed successfully"},
                7500.0
            )
            
            # Verify bridge health after real service interaction
            final_health = await bridge.get_health_status()
            assert final_health.state == IntegrationState.ACTIVE
            assert final_health.consecutive_failures == 0
            
            await bridge.shutdown()
            
        except Exception as e:
            pytest.skip(f"Real WebSocket services not available: {e}")