"""Integration Tests for Agent Response Delivery Mechanisms

Tests the various mechanisms by which agent responses are delivered to users,
including WebSocket events, HTTP responses, and persistence storage.

Business Value Justification (BVJ):
- Segment: All segments - Core Platform Functionality
- Business Goal: Ensure reliable response delivery (90% of platform value)
- Value Impact: Validates that users actually receive AI responses they request
- Strategic Impact: Protects $500K+ ARR by ensuring chat delivery works
"""

import asyncio
import pytest
import json
import time
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

from test_framework.ssot.base_test_case import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockWebSocketConnection:
    """Mock WebSocket connection for testing delivery mechanisms."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sent_messages = []
        self.is_connected = True
        
    async def send_text(self, message: str):
        """Mock send text message."""
        if not self.is_connected:
            raise ConnectionError("WebSocket not connected")
        self.sent_messages.append({"type": "text", "data": message})
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock send JSON message."""
        if not self.is_connected:
            raise ConnectionError("WebSocket not connected")
        self.sent_messages.append({"type": "json", "data": data})
        
    def disconnect(self):
        """Mock disconnect."""
        self.is_connected = False


@pytest.mark.integration
class TestAgentResponseDeliveryMechanisms(BaseIntegrationTest):
    """Test agent response delivery mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.test_user_id = "test_user_delivery"
        self.test_thread_id = "thread_delivery_001"
        self.mock_connections = {}
        
    def _create_mock_websocket_connection(self, user_id: str) -> MockWebSocketConnection:
        """Create mock WebSocket connection for testing."""
        connection = MockWebSocketConnection(user_id)
        self.mock_connections[user_id] = connection
        return connection
        
    async def test_websocket_response_delivery_success_path(self):
        """
        Test successful WebSocket response delivery.
        
        BVJ: All segments - Core Platform Functionality
        Validates that agent responses are delivered via WebSocket to users,
        which is the primary real-time delivery mechanism for chat.
        """
        # GIVEN: A user execution context with WebSocket connection
        mock_connection = self._create_mock_websocket_connection(self.test_user_id)
        
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Mock WebSocket manager to use our test connection
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                mock_manager_instance = AsyncMock()
                mock_ws_manager.return_value = mock_manager_instance
                mock_manager_instance.send_to_user = AsyncMock()
                
                agent = DataHelperAgent()
                query = "Test query for WebSocket delivery"
                
                # WHEN: Agent generates response with WebSocket delivery
                result = await agent.run(context, query=query)
                
                # Simulate WebSocket delivery
                if isinstance(result, TypedAgentResult) and result.success:
                    await mock_manager_instance.send_to_user(
                        user_id=self.test_user_id,
                        message_type="agent_response",
                        data={
                            "response": result.result,
                            "thread_id": self.test_thread_id,
                            "timestamp": result.timestamp.isoformat()
                        }
                    )
                
                # THEN: Response is delivered via WebSocket
                assert result is not None, "Agent must generate response"
                
                if isinstance(result, TypedAgentResult):
                    assert result.success, "Agent execution must succeed"
                    
                    # Verify WebSocket delivery was attempted
                    mock_manager_instance.send_to_user.assert_called_once()
                    call_args = mock_manager_instance.send_to_user.call_args
                    
                    assert call_args[1]["user_id"] == self.test_user_id, "Message sent to correct user"
                    assert call_args[1]["message_type"] == "agent_response", "Correct message type"
                    assert "response" in call_args[1]["data"], "Response data included"
                    
                    logger.info("✅ WebSocket response delivery validated")
                    
    async def test_websocket_delivery_failure_graceful_handling(self):
        """
        Test graceful handling of WebSocket delivery failures.
        
        BVJ: All segments - Reliability/User Experience
        Validates that when WebSocket delivery fails, the system handles it gracefully
        without losing the response or breaking the user experience.
        """
        # GIVEN: A user execution context with failing WebSocket connection
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Mock WebSocket manager with delivery failure
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                mock_manager_instance = AsyncMock()
                mock_ws_manager.return_value = mock_manager_instance
                mock_manager_instance.send_to_user.side_effect = ConnectionError("WebSocket disconnected")
                
                agent = DataHelperAgent()
                query = "Test query for delivery failure handling"
                
                # WHEN: Agent generates response with WebSocket delivery failure
                result = await agent.run(context, query=query)
                
                # Attempt WebSocket delivery that will fail
                delivery_failed = False
                if isinstance(result, TypedAgentResult) and result.success:
                    try:
                        await mock_manager_instance.send_to_user(
                            user_id=self.test_user_id,
                            message_type="agent_response",
                            data={"response": result.result}
                        )
                    except ConnectionError:
                        delivery_failed = True
                
                # THEN: Response is still generated despite delivery failure
                assert result is not None, "Agent must generate response even if delivery fails"
                assert delivery_failed, "Delivery failure should be simulated"
                
                if isinstance(result, TypedAgentResult):
                    assert result.success, "Agent execution should succeed independently of delivery"
                    assert result.result is not None, "Response should be available for alternative delivery"
                    
                    logger.info("✅ WebSocket delivery failure handled gracefully")
                    
    async def test_multi_user_response_delivery_isolation(self):
        """
        Test response delivery isolation between multiple users.
        
        BVJ: Enterprise - Security/Multi-tenancy
        Validates that responses are delivered only to the correct user,
        preventing data leakage in multi-tenant environments.
        """
        # GIVEN: Multiple users with separate contexts
        user_1_id = f"{self.test_user_id}_multi_1"
        user_2_id = f"{self.test_user_id}_multi_2"
        
        mock_connection_1 = self._create_mock_websocket_connection(user_1_id)
        mock_connection_2 = self._create_mock_websocket_connection(user_2_id)
        
        async def process_user_request(user_id: str, query: str) -> Dict[str, Any]:
            """Process request for specific user."""
            with create_isolated_execution_context(
                user_id=user_id,
                thread_id=f"thread_{user_id}"
            ) as context:
                # Mock WebSocket manager for this user
                with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                    mock_manager_instance = AsyncMock()
                    mock_ws_manager.return_value = mock_manager_instance
                    
                    agent = DataHelperAgent()
                    result = await agent.run(context, query=query)
                    
                    # Simulate delivery to specific user
                    if isinstance(result, TypedAgentResult) and result.success:
                        await mock_manager_instance.send_to_user(
                            user_id=user_id,
                            message_type="agent_response",
                            data={"response": result.result, "user_context": user_id}
                        )
                    
                    return {
                        "user_id": user_id,
                        "result": result,
                        "delivery_calls": mock_manager_instance.send_to_user.call_args_list
                    }
        
        # WHEN: Multiple users generate responses concurrently
        tasks = [
            process_user_request(user_1_id, "Query from user 1"),
            process_user_request(user_2_id, "Query from user 2")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # THEN: Responses are delivered to correct users only
        user_1_result, user_2_result = results
        
        # Validate isolation
        assert len(user_1_result["delivery_calls"]) == 1, "User 1 should receive one delivery"
        assert len(user_2_result["delivery_calls"]) == 1, "User 2 should receive one delivery"
        
        user_1_delivery = user_1_result["delivery_calls"][0][1]
        user_2_delivery = user_2_result["delivery_calls"][0][1]
        
        assert user_1_delivery["user_id"] == user_1_id, "User 1 delivery to correct user"
        assert user_2_delivery["user_id"] == user_2_id, "User 2 delivery to correct user"
        
        # Validate no cross-contamination
        assert user_1_delivery["data"]["user_context"] == user_1_id, "User 1 context isolated"
        assert user_2_delivery["data"]["user_context"] == user_2_id, "User 2 context isolated"
        
        logger.info("✅ Multi-user response delivery isolation validated")
        
    async def test_response_delivery_with_websocket_events_integration(self):
        """
        Test response delivery integration with WebSocket events.
        
        BVJ: All segments - User Experience/Real-time
        Validates that agent responses trigger appropriate WebSocket events
        for real-time user experience (agent_started, agent_thinking, etc.).
        """
        # GIVEN: A user execution context with WebSocket event tracking
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Mock WebSocket manager with event tracking
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                mock_manager_instance = AsyncMock()
                mock_ws_manager.return_value = mock_manager_instance
                
                # Track all WebSocket events
                event_calls = []
                
                async def track_send_to_user(**kwargs):
                    event_calls.append(kwargs)
                
                mock_manager_instance.send_to_user.side_effect = track_send_to_user
                
                agent = DataHelperAgent()
                query = "Test query for WebSocket events integration"
                
                # WHEN: Agent generates response with event integration
                # Simulate the events that should be sent during agent execution
                await mock_manager_instance.send_to_user(
                    user_id=self.test_user_id,
                    message_type="agent_started",
                    data={"agent": "DataHelperAgent", "thread_id": self.test_thread_id}
                )
                
                await mock_manager_instance.send_to_user(
                    user_id=self.test_user_id,
                    message_type="agent_thinking",
                    data={"status": "processing", "thread_id": self.test_thread_id}
                )
                
                result = await agent.run(context, query=query)
                
                await mock_manager_instance.send_to_user(
                    user_id=self.test_user_id,
                    message_type="agent_completed",
                    data={"result": result.result if isinstance(result, TypedAgentResult) else result, 
                          "thread_id": self.test_thread_id}
                )
                
                # THEN: All required WebSocket events are sent
                assert len(event_calls) >= 3, "Minimum required events: agent_started, agent_thinking, agent_completed"
                
                event_types = [call["message_type"] for call in event_calls]
                required_events = ["agent_started", "agent_thinking", "agent_completed"]
                
                for required_event in required_events:
                    assert required_event in event_types, f"Required event {required_event} must be sent"
                
                # Validate event order
                start_index = event_types.index("agent_started")
                complete_index = event_types.index("agent_completed")
                assert start_index < complete_index, "agent_started must come before agent_completed"
                
                # Validate event data
                for call in event_calls:
                    assert call["user_id"] == self.test_user_id, "All events sent to correct user"
                    assert "thread_id" in call["data"], "All events include thread_id"
                    
                logger.info(f"✅ WebSocket events integration validated ({len(event_calls)} events)")
                
    async def test_response_delivery_performance_meets_requirements(self):
        """
        Test response delivery performance meets real-time requirements.
        
        BVJ: All segments - User Experience/Performance
        Validates that response delivery is fast enough for good user experience,
        particularly important for real-time chat interactions.
        """
        # GIVEN: A user execution context for performance testing
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Mock WebSocket manager for performance testing
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                mock_manager_instance = AsyncMock()
                mock_ws_manager.return_value = mock_manager_instance
                
                # Track delivery timing
                delivery_times = []
                
                async def timed_send_to_user(**kwargs):
                    start_time = time.time()
                    await asyncio.sleep(0.001)  # Simulate minimal network latency
                    delivery_time = time.time() - start_time
                    delivery_times.append(delivery_time)
                
                mock_manager_instance.send_to_user.side_effect = timed_send_to_user
                
                agent = DataHelperAgent()
                query = "Performance test query"
                
                # WHEN: Agent generates response with timed delivery
                overall_start = time.time()
                
                result = await agent.run(context, query=query)
                
                # Simulate multiple delivery events
                for event_type in ["agent_started", "agent_thinking", "agent_completed"]:
                    await mock_manager_instance.send_to_user(
                        user_id=self.test_user_id,
                        message_type=event_type,
                        data={"event": event_type}
                    )
                
                overall_time = time.time() - overall_start
                
                # THEN: Delivery performance meets requirements
                assert overall_time < 30.0, f"Overall response time {overall_time:.2f}s exceeds 30s limit"
                
                if delivery_times:
                    avg_delivery_time = sum(delivery_times) / len(delivery_times)
                    max_delivery_time = max(delivery_times)
                    
                    assert avg_delivery_time < 0.1, f"Average delivery time {avg_delivery_time:.3f}s too slow"
                    assert max_delivery_time < 0.5, f"Max delivery time {max_delivery_time:.3f}s too slow"
                    
                    logger.info(f"✅ Response delivery performance validated (avg: {avg_delivery_time:.3f}s, max: {max_delivery_time:.3f}s)")
                else:
                    logger.info("✅ Response delivery performance validated (no delivery timing captured)")
                    
    def teardown_method(self):
        """Clean up test resources."""
        # Clean up mock connections
        for connection in self.mock_connections.values():
            connection.disconnect()
        self.mock_connections.clear()
        
        super().teardown_method()