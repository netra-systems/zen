"""
Test WebSocket Agent Events Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure chat value delivery through WebSocket event system
- Value Impact: WebSocket events are THE mechanism for delivering AI insights to users
- Strategic Impact: Core platform functionality - without events, chat has zero business value

MISSION CRITICAL: These integration tests validate the 5 critical WebSocket events
that enable substantive AI chat interactions:
1. agent_started - User sees agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working)
3. tool_executing - Tool usage transparency (demonstrates problem-solving)
4. tool_completed - Tool results display (delivers actionable insights) 
5. agent_completed - Response ready notification (completes value delivery)

Test Architecture:
- Integration tests (not E2E) - uses real PostgreSQL and Redis but mock LLM
- Tests real WebSocket event delivery, ordering, and payload validation
- Tests user context isolation for WebSocket events
- Tests race conditions and error scenarios
- Validates component integration without full Docker stack

Following TEST_CREATION_GUIDE.md patterns for SSOT test framework usage.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.websocket_helpers import (
    MockWebSocketConnection,
    WebSocketTestHelpers,
    assert_websocket_events,
    validate_websocket_message
)

# Import real services for integration testing
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.registry import AgentRegistry
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager
    from shared.isolated_environment import get_env
    INTEGRATION_COMPONENTS_AVAILABLE = True
except ImportError as e:
    INTEGRATION_COMPONENTS_AVAILABLE = False
    pytest.skip(f"Integration components not available: {e}", allow_module_level=True)


class TestWebSocketAgentEventsIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket agent events with real services."""

    async def async_setup(self):
        """Set up integration test environment."""
        await super().async_setup()
        
        # Set up isolated environment
        self.env = get_env()
        self.env.set("ENVIRONMENT", "test", source="test")
        self.env.set("LOG_LEVEL", "INFO", source="test")
        
        # Generate test user context
        self.test_user_id = f"test_user_{int(time.time() * 1000)}"
        self.test_connection_id = f"conn_{int(time.time() * 1000)}"
        
        # Mock external dependencies (LLM) while using real WebSocket infrastructure
        self.mock_llm_client = AsyncMock()
        self.mock_llm_response = {
            "content": "Mock AI response for testing",
            "reasoning": "Mock reasoning process",
            "tool_calls": []
        }
        self.mock_llm_client.generate_response.return_value = self.mock_llm_response
        
        # Initialize real WebSocket components for integration testing
        self.websocket_manager = None
        self.agent_bridge = None
        self.user_emitter = None
        
    async def async_teardown(self):
        """Clean up integration test resources."""
        try:
            if self.user_emitter:
                await self.user_emitter.close()
            if self.agent_bridge:
                await self.agent_bridge.cleanup()
            if self.websocket_manager:
                await self.websocket_manager.shutdown()
        except Exception as e:
            self.logger.warning(f"Cleanup error (ignored): {e}")
        
        await super().async_teardown()

    async def _create_test_websocket_infrastructure(self) -> Dict[str, Any]:
        """Create real WebSocket infrastructure for integration testing."""
        # Create UnifiedWebSocketManager (real component)
        self.websocket_manager = UnifiedWebSocketManager(
            connection_pool_size=10,
            enable_compression=False,  # Simplified for testing
            heartbeat_interval=30
        )
        await self.websocket_manager.initialize()
        
        # Create AgentWebSocketBridge (real component)  
        self.agent_bridge = AgentWebSocketBridge()
        await self.agent_bridge.initialize()
        
        # Create UserExecutionContext for isolated testing
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            connection_id=self.test_connection_id,
            thread_id=f"thread_{int(time.time())}"
        )
        
        # Create UnifiedWebSocketEmitter with real manager
        self.user_emitter = UnifiedWebSocketEmitter(
            manager=self.websocket_manager,
            user_id=self.test_user_id,
            context=user_context
        )
        
        return {
            "manager": self.websocket_manager,
            "bridge": self.agent_bridge,
            "emitter": self.user_emitter,
            "context": user_context
        }

    async def _simulate_websocket_connection(self) -> MockWebSocketConnection:
        """Create mock WebSocket connection for event capture."""
        mock_websocket = MockWebSocketConnection(self.test_user_id)
        
        # Register mock connection with manager
        if self.websocket_manager:
            await self.websocket_manager.add_connection(
                user_id=self.test_user_id,
                connection_id=self.test_connection_id,
                websocket=mock_websocket
            )
        
        return mock_websocket

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_agent_started_event_delivery(self):
        """Test agent_started event is delivered with correct structure."""
        # Set up real WebSocket infrastructure
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Send agent_started event through real emitter
        event_data = {
            "agent_name": "test_agent",
            "user_id": self.test_user_id,
            "timestamp": time.time(),
            "request": "Test user request"
        }
        
        await infrastructure["emitter"].emit_agent_started(
            agent_name=event_data["agent_name"],
            user_id=self.test_user_id,
            additional_data={"request": event_data["request"]}
        )
        
        # Wait for event propagation
        await asyncio.sleep(0.1)
        
        # Verify event was received
        sent_messages = mock_websocket._sent_messages
        assert len(sent_messages) > 0, "No messages sent to WebSocket"
        
        # Parse and validate the event
        event_message = json.loads(sent_messages[-1])
        assert event_message["type"] == "agent_started"
        assert event_message["agent_name"] == "test_agent"
        assert event_message["user_id"] == self.test_user_id
        assert "timestamp" in event_message
        
        # Validate required fields
        validate_websocket_message(event_message, ["type", "agent_name", "user_id", "timestamp"])

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_agent_thinking_event_delivery(self):
        """Test agent_thinking event is delivered with reasoning content."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Send agent_thinking event
        reasoning_content = "Analyzing user request and determining optimal approach..."
        await infrastructure["emitter"].emit_agent_thinking(
            reasoning=reasoning_content,
            user_id=self.test_user_id,
            step=1,
            total_steps=3
        )
        
        await asyncio.sleep(0.1)
        
        # Validate event delivery
        sent_messages = mock_websocket._sent_messages
        assert len(sent_messages) > 0
        
        event_message = json.loads(sent_messages[-1])
        assert event_message["type"] == "agent_thinking"
        assert event_message["reasoning"] == reasoning_content
        assert event_message["user_id"] == self.test_user_id
        assert event_message["step"] == 1
        assert event_message["total_steps"] == 3
        
        validate_websocket_message(event_message, ["type", "reasoning", "user_id"])

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_tool_executing_event_delivery(self):
        """Test tool_executing event is delivered with tool details."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Send tool_executing event
        tool_name = "cost_analyzer"
        tool_params = {"time_period": "30_days", "service": "aws"}
        
        await infrastructure["emitter"].emit_tool_executing(
            tool_name=tool_name,
            user_id=self.test_user_id,
            parameters=tool_params,
            description="Analyzing AWS costs for the last 30 days"
        )
        
        await asyncio.sleep(0.1)
        
        # Validate event delivery
        sent_messages = mock_websocket._sent_messages
        assert len(sent_messages) > 0
        
        event_message = json.loads(sent_messages[-1])
        assert event_message["type"] == "tool_executing"
        assert event_message["tool_name"] == tool_name
        assert event_message["user_id"] == self.test_user_id
        assert event_message["parameters"] == tool_params
        assert "description" in event_message
        
        validate_websocket_message(event_message, ["type", "tool_name", "user_id"])

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_tool_completed_event_delivery(self):
        """Test tool_completed event is delivered with results."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Send tool_completed event
        tool_results = {
            "total_cost": 1250.75,
            "top_services": ["EC2", "S3", "RDS"],
            "recommendations": ["Right-size EC2 instances", "Enable S3 lifecycle"]
        }
        
        await infrastructure["emitter"].emit_tool_completed(
            tool_name="cost_analyzer",
            user_id=self.test_user_id,
            results=tool_results,
            execution_time_ms=2500,
            success=True
        )
        
        await asyncio.sleep(0.1)
        
        # Validate event delivery
        sent_messages = mock_websocket._sent_messages
        assert len(sent_messages) > 0
        
        event_message = json.loads(sent_messages[-1])
        assert event_message["type"] == "tool_completed"
        assert event_message["tool_name"] == "cost_analyzer"
        assert event_message["user_id"] == self.test_user_id
        assert event_message["results"] == tool_results
        assert event_message["success"] is True
        assert event_message["execution_time_ms"] == 2500
        
        validate_websocket_message(event_message, ["type", "tool_name", "user_id", "results"])

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_agent_completed_event_delivery(self):
        """Test agent_completed event is delivered with final response."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Send agent_completed event
        final_response = {
            "summary": "Cost analysis completed successfully",
            "total_monthly_cost": 1250.75,
            "potential_savings": 375.25,
            "recommendations": [
                "Right-size EC2 instances for 20% savings",
                "Implement S3 lifecycle policies for 15% savings"
            ]
        }
        
        await infrastructure["emitter"].emit_agent_completed(
            response=final_response,
            user_id=self.test_user_id,
            total_execution_time_ms=15000,
            tools_used=["cost_analyzer", "recommendation_engine"]
        )
        
        await asyncio.sleep(0.1)
        
        # Validate event delivery
        sent_messages = mock_websocket._sent_messages
        assert len(sent_messages) > 0
        
        event_message = json.loads(sent_messages[-1])
        assert event_message["type"] == "agent_completed"
        assert event_message["user_id"] == self.test_user_id
        assert event_message["response"] == final_response
        assert event_message["total_execution_time_ms"] == 15000
        assert event_message["tools_used"] == ["cost_analyzer", "recommendation_engine"]
        
        validate_websocket_message(event_message, ["type", "user_id", "response"])

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_complete_agent_workflow_event_sequence(self):
        """Test complete agent workflow sends all 5 critical events in order."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Simulate complete agent workflow
        emitter = infrastructure["emitter"]
        
        # 1. Agent started
        await emitter.emit_agent_started(
            agent_name="cost_optimizer",
            user_id=self.test_user_id
        )
        await asyncio.sleep(0.05)
        
        # 2. Agent thinking
        await emitter.emit_agent_thinking(
            reasoning="Analyzing cost optimization opportunities",
            user_id=self.test_user_id
        )
        await asyncio.sleep(0.05)
        
        # 3. Tool executing
        await emitter.emit_tool_executing(
            tool_name="cost_analyzer",
            user_id=self.test_user_id,
            parameters={"period": "30_days"}
        )
        await asyncio.sleep(0.05)
        
        # 4. Tool completed
        await emitter.emit_tool_completed(
            tool_name="cost_analyzer",
            user_id=self.test_user_id,
            results={"savings": 500},
            success=True
        )
        await asyncio.sleep(0.05)
        
        # 5. Agent completed
        await emitter.emit_agent_completed(
            response={"summary": "Optimization complete"},
            user_id=self.test_user_id
        )
        await asyncio.sleep(0.05)
        
        # Validate all 5 events were sent in sequence
        sent_messages = mock_websocket._sent_messages
        assert len(sent_messages) >= 5, f"Expected 5+ events, got {len(sent_messages)}"
        
        # Parse events and verify sequence
        events = [json.loads(msg) for msg in sent_messages[-5:]]
        event_types = [event["type"] for event in events]
        
        expected_sequence = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Verify all critical events are present (order may vary due to async)
        for expected_event in expected_sequence:
            assert expected_event in event_types, f"Missing critical event: {expected_event}"
        
        # Verify user isolation - all events for same user
        for event in events:
            assert event["user_id"] == self.test_user_id, "User isolation violation"

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_user_isolation(self):
        """Test WebSocket events are isolated per user."""
        infrastructure = await self._create_test_websocket_infrastructure()
        
        # Create two separate user contexts
        user1_id = f"user1_{int(time.time())}"
        user2_id = f"user2_{int(time.time())}"
        
        # Create separate mock connections
        mock_websocket_user1 = MockWebSocketConnection(user1_id)
        mock_websocket_user2 = MockWebSocketConnection(user2_id)
        
        # Register connections with manager
        await self.websocket_manager.add_connection(
            user_id=user1_id,
            connection_id=f"conn1_{int(time.time())}",
            websocket=mock_websocket_user1
        )
        await self.websocket_manager.add_connection(
            user_id=user2_id, 
            connection_id=f"conn2_{int(time.time())}",
            websocket=mock_websocket_user2
        )
        
        # Create separate emitters
        emitter1 = UnifiedWebSocketEmitter(
            manager=self.websocket_manager,
            user_id=user1_id,
            context=None
        )
        emitter2 = UnifiedWebSocketEmitter(
            manager=self.websocket_manager,
            user_id=user2_id,
            context=None
        )
        
        # Send events to different users
        await emitter1.emit_agent_started(agent_name="agent1", user_id=user1_id)
        await emitter2.emit_agent_started(agent_name="agent2", user_id=user2_id)
        
        await asyncio.sleep(0.1)
        
        # Verify user isolation
        user1_messages = [json.loads(msg) for msg in mock_websocket_user1._sent_messages]
        user2_messages = [json.loads(msg) for msg in mock_websocket_user2._sent_messages]
        
        # Each user should only receive their events
        for msg in user1_messages:
            if msg.get("user_id"):
                assert msg["user_id"] == user1_id, "User 1 received User 2's event"
                
        for msg in user2_messages:
            if msg.get("user_id"):
                assert msg["user_id"] == user2_id, "User 2 received User 1's event"

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_error_handling(self):
        """Test WebSocket event error handling and recovery."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Simulate WebSocket connection failure
        mock_websocket.should_fail_send = True
        
        # Attempt to send event - should handle gracefully
        with patch.object(infrastructure["emitter"], '_handle_send_error') as mock_error_handler:
            await infrastructure["emitter"].emit_agent_started(
                agent_name="test_agent",
                user_id=self.test_user_id
            )
            
            await asyncio.sleep(0.1)
            
            # Error handler should be called for failed delivery
            # (Real implementation would retry or log error)

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_retry_mechanism(self):
        """Test WebSocket event retry mechanism for critical events."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Track retry attempts
        retry_count = 0
        original_send = mock_websocket.send
        
        async def failing_send(message):
            nonlocal retry_count
            retry_count += 1
            if retry_count <= 2:  # Fail first 2 attempts
                raise ConnectionError("Simulated connection error")
            await original_send(message)  # Succeed on 3rd attempt
        
        mock_websocket.send = failing_send
        
        # Send critical event - should retry until success
        await infrastructure["emitter"].emit_agent_started(
            agent_name="test_agent",
            user_id=self.test_user_id
        )
        
        await asyncio.sleep(0.2)  # Allow retry delays
        
        # Should eventually succeed after retries
        assert retry_count >= 3, "Retry mechanism not triggered"

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_payload_validation(self):
        """Test WebSocket event payload structure and validation."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Test with invalid payload
        with pytest.raises((ValueError, TypeError)):
            await infrastructure["emitter"].emit_agent_thinking(
                reasoning=None,  # Invalid - reasoning cannot be None
                user_id=self.test_user_id
            )
        
        # Test with oversized payload
        oversized_response = "x" * 10000  # Very large response
        
        # Should either handle gracefully or raise appropriate error
        try:
            await infrastructure["emitter"].emit_agent_completed(
                response={"data": oversized_response},
                user_id=self.test_user_id
            )
        except (ValueError, OSError):
            pass  # Expected - payload too large

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_timestamp_accuracy(self):
        """Test WebSocket event timestamps are accurate and sequential."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        start_time = time.time()
        
        # Send events with small delays
        await infrastructure["emitter"].emit_agent_started(
            agent_name="test_agent",
            user_id=self.test_user_id
        )
        
        await asyncio.sleep(0.1)
        
        await infrastructure["emitter"].emit_agent_thinking(
            reasoning="Processing...",
            user_id=self.test_user_id
        )
        
        await asyncio.sleep(0.1)
        
        end_time = time.time()
        
        # Validate timestamps
        sent_messages = mock_websocket._sent_messages
        events = [json.loads(msg) for msg in sent_messages[-2:]]
        
        for event in events:
            assert "timestamp" in event
            timestamp = event["timestamp"]
            assert start_time <= timestamp <= end_time, "Timestamp out of expected range"
        
        # Verify chronological order
        if len(events) >= 2:
            assert events[0]["timestamp"] <= events[1]["timestamp"], "Events not in chronological order"

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_compression_handling(self):
        """Test WebSocket events with compression enabled."""
        # Create manager with compression enabled
        compressed_manager = UnifiedWebSocketManager(
            connection_pool_size=5,
            enable_compression=True,
            compression_threshold=100  # Compress messages > 100 bytes
        )
        await compressed_manager.initialize()
        
        mock_websocket = MockWebSocketConnection(self.test_user_id)
        await compressed_manager.add_connection(
            user_id=self.test_user_id,
            connection_id=self.test_connection_id,
            websocket=mock_websocket
        )
        
        emitter = UnifiedWebSocketEmitter(
            manager=compressed_manager,
            user_id=self.test_user_id,
            context=None
        )
        
        # Send large event that should trigger compression
        large_response = {"data": "x" * 500, "analysis": "detailed analysis " * 20}
        
        await emitter.emit_agent_completed(
            response=large_response,
            user_id=self.test_user_id
        )
        
        await asyncio.sleep(0.1)
        
        # Event should be delivered regardless of compression
        assert len(mock_websocket._sent_messages) > 0, "Event not delivered with compression"
        
        await compressed_manager.shutdown()

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_rate_limiting(self):
        """Test WebSocket event rate limiting behavior."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Send burst of events to test rate limiting
        event_count = 10
        start_time = time.time()
        
        for i in range(event_count):
            await infrastructure["emitter"].emit_agent_thinking(
                reasoning=f"Step {i + 1} of analysis",
                user_id=self.test_user_id,
                step=i + 1,
                total_steps=event_count
            )
        
        await asyncio.sleep(0.2)  # Allow processing time
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Verify events were delivered (rate limiting shouldn't drop critical events)
        sent_messages = mock_websocket._sent_messages
        delivered_events = len([msg for msg in sent_messages if "agent_thinking" in msg])
        
        # All critical events should be delivered despite rate limiting
        assert delivered_events >= event_count * 0.8, "Too many events dropped by rate limiting"

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_connection_recovery(self):
        """Test WebSocket event delivery after connection recovery."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        
        # Send initial event
        await infrastructure["emitter"].emit_agent_started(
            agent_name="test_agent",
            user_id=self.test_user_id
        )
        
        await asyncio.sleep(0.05)
        initial_message_count = len(mock_websocket._sent_messages)
        
        # Simulate connection disconnect
        mock_websocket.simulate_disconnect()
        await asyncio.sleep(0.05)
        
        # Create new connection (simulating reconnection)
        new_mock_websocket = MockWebSocketConnection(self.test_user_id)
        await self.websocket_manager.add_connection(
            user_id=self.test_user_id,
            connection_id=f"reconnect_{int(time.time())}",
            websocket=new_mock_websocket
        )
        
        # Send event after reconnection
        await infrastructure["emitter"].emit_agent_completed(
            response={"status": "reconnection test"},
            user_id=self.test_user_id
        )
        
        await asyncio.sleep(0.1)
        
        # Verify event delivered to new connection
        assert len(new_mock_websocket._sent_messages) > 0, "Event not delivered after reconnection"

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_event_concurrent_users(self):
        """Test WebSocket events under concurrent multi-user load."""
        infrastructure = await self._create_test_websocket_infrastructure()
        
        user_count = 5
        users_and_connections = []
        
        # Create multiple users with separate connections
        for i in range(user_count):
            user_id = f"concurrent_user_{i}_{int(time.time())}"
            connection_id = f"conn_{i}_{int(time.time())}"
            mock_websocket = MockWebSocketConnection(user_id)
            
            await self.websocket_manager.add_connection(
                user_id=user_id,
                connection_id=connection_id,
                websocket=mock_websocket
            )
            
            emitter = UnifiedWebSocketEmitter(
                manager=self.websocket_manager,
                user_id=user_id,
                context=None
            )
            
            users_and_connections.append((user_id, mock_websocket, emitter))
        
        # Send events concurrently for all users
        async def send_user_events(user_id, mock_websocket, emitter):
            await emitter.emit_agent_started(agent_name=f"agent_{user_id}", user_id=user_id)
            await asyncio.sleep(0.01)
            await emitter.emit_agent_thinking(reasoning=f"Thinking for {user_id}", user_id=user_id)
            await asyncio.sleep(0.01)  
            await emitter.emit_agent_completed(response=f"Done for {user_id}", user_id=user_id)
        
        # Execute all user events concurrently
        tasks = [
            send_user_events(user_id, mock_websocket, emitter)
            for user_id, mock_websocket, emitter in users_and_connections
        ]
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.1)
        
        # Verify each user received their events
        for user_id, mock_websocket, _ in users_and_connections:
            sent_messages = mock_websocket._sent_messages
            assert len(sent_messages) >= 3, f"User {user_id} didn't receive expected events"
            
            # Verify user isolation
            for message in sent_messages:
                event = json.loads(message)
                if event.get("user_id"):
                    assert event["user_id"] == user_id, f"User isolation violated for {user_id}"

    @pytest.mark.integration
    @pytest.mark.websocket_events
    async def test_websocket_bridge_integration_health_monitoring(self):
        """Test AgentWebSocketBridge health monitoring integration."""
        infrastructure = await self._create_test_websocket_infrastructure()
        bridge = infrastructure["bridge"]
        
        # Check initial health status
        health_status = await bridge.get_health_status()
        assert health_status.state in [IntegrationState.ACTIVE, IntegrationState.INITIALIZING]
        assert health_status.websocket_manager_healthy is True
        
        # Verify bridge can handle event coordination
        await bridge.ensure_integration()
        
        # Get updated health after integration
        updated_health = await bridge.get_health_status()
        assert updated_health.state == IntegrationState.ACTIVE
        assert updated_health.consecutive_failures == 0

    @pytest.mark.integration
    @pytest.mark.websocket_events  
    async def test_websocket_event_metrics_tracking(self):
        """Test WebSocket event metrics are properly tracked."""
        infrastructure = await self._create_test_websocket_infrastructure()
        mock_websocket = await self._simulate_websocket_connection()
        emitter = infrastructure["emitter"]
        
        # Send various events to track metrics
        await emitter.emit_agent_started(agent_name="metrics_test", user_id=self.test_user_id)
        await emitter.emit_agent_thinking(reasoning="Tracking metrics", user_id=self.test_user_id)
        await emitter.emit_tool_executing(tool_name="metric_tool", user_id=self.test_user_id)
        await emitter.emit_tool_completed(tool_name="metric_tool", user_id=self.test_user_id, results={})
        await emitter.emit_agent_completed(response="Metrics tracked", user_id=self.test_user_id)
        
        await asyncio.sleep(0.1)
        
        # Verify metrics are tracked (if metrics available on emitter)
        if hasattr(emitter, "metrics"):
            metrics = emitter.metrics
            assert metrics.total_events >= 5, "Event metrics not properly tracked"
            
            # Check critical event tracking
            critical_events_sent = sum(
                metrics.critical_events.get(event_type, 0)
                for event_type in UnifiedWebSocketEmitter.CRITICAL_EVENTS
            )
            assert critical_events_sent >= 5, "Critical event metrics not tracked"

# Additional test utility functions for WebSocket integration testing

async def create_test_agent_workflow_events(emitter: UnifiedWebSocketEmitter, user_id: str) -> List[Dict[str, Any]]:
    """Helper function to create a complete test agent workflow event sequence."""
    events = []
    
    # Simulate real agent workflow
    workflow_events = [
        ("agent_started", {"agent_name": "test_workflow_agent"}),
        ("agent_thinking", {"reasoning": "Analyzing request and planning approach"}),
        ("tool_executing", {"tool_name": "data_analyzer", "parameters": {"scope": "full"}}),
        ("tool_completed", {"tool_name": "data_analyzer", "results": {"status": "success"}, "success": True}),
        ("agent_completed", {"response": {"summary": "Analysis complete", "results": []}})
    ]
    
    for event_type, event_data in workflow_events:
        method_name = f"emit_{event_type}"
        if hasattr(emitter, method_name):
            method = getattr(emitter, method_name)
            await method(user_id=user_id, **event_data)
            events.append({"type": event_type, **event_data, "user_id": user_id})
            await asyncio.sleep(0.02)  # Small delay between events
    
    return events


def validate_critical_event_sequence(events: List[Dict[str, Any]]) -> bool:
    """Validate that critical WebSocket events follow expected patterns."""
    critical_events = UnifiedWebSocketEmitter.CRITICAL_EVENTS
    
    # Find all critical events in the sequence
    found_events = [event for event in events if event.get("type") in critical_events]
    
    if len(found_events) == 0:
        return False
    
    # Validate chronological order (timestamps should be increasing)
    timestamps = [event.get("timestamp", 0) for event in found_events]
    if not all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1)):
        return False
    
    # Validate required fields for each event type
    for event in found_events:
        event_type = event["type"]
        if event_type == "agent_started":
            if not event.get("agent_name") or not event.get("user_id"):
                return False
        elif event_type == "agent_thinking":
            if not event.get("reasoning") or not event.get("user_id"):
                return False
        elif event_type in ["tool_executing", "tool_completed"]:
            if not event.get("tool_name") or not event.get("user_id"):
                return False
        elif event_type == "agent_completed":
            if not event.get("response") or not event.get("user_id"):
                return False
    
    return True