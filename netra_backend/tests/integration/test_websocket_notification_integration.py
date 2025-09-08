"""
Test WebSocket Notification System Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable real-time agent communication and chat value delivery
- Value Impact: WebSocket events are mission-critical for delivering AI insights to users in real-time
- Strategic Impact: Core chat functionality - without WebSocket events, the platform has no user-facing value

This test suite validates the WebSocket notification system integration:
1. Agent execution WebSocket events (all 5 critical events)
2. Real-time message broadcasting with user isolation
3. WebSocket connection management and reconnection handling
4. Error handling and graceful degradation
"""

import asyncio
import uuid
import pytest
import json
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, WebSocketID,
    WebSocketEventType, WebSocketMessage, WebSocketConnectionInfo,
    ConnectionState, ensure_user_id, ensure_thread_id
)

# WebSocket core components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketProtocol
from netra_backend.app.websocket_core.unified_emitter import UnifiedEventEmitter
from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

# Agent and execution components
from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, websocket_id: WebSocketID, user_id: UserID):
        self.websocket_id = websocket_id
        self.user_id = user_id
        self.messages_sent = []
        self.is_connected = True
        self.connection_state = ConnectionState.CONNECTED
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock sending JSON data to WebSocket."""
        if not self.is_connected:
            raise ConnectionError("WebSocket is not connected")
        self.messages_sent.append(data)
    
    async def close(self) -> None:
        """Mock closing WebSocket connection."""
        self.is_connected = False
        self.connection_state = ConnectionState.DISCONNECTED


class TestWebSocketNotificationIntegration(BaseIntegrationTest):
    """Test WebSocket notification system with real message routing and user isolation."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_events_all_five_critical_events(self, real_services_fixture, isolated_env):
        """Test all 5 critical WebSocket events are sent during agent execution."""
        
        # Create test user and connection
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket_id = WebSocketID(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        request_id = RequestID(str(uuid.uuid4()))
        
        # Setup mock WebSocket connection
        mock_connection = MockWebSocketConnection(websocket_id, user_id)
        
        # Create WebSocket manager with real routing logic
        websocket_manager = UnifiedWebSocketManager()
        
        # Mock the connection registry to return our test connection
        with patch.object(websocket_manager, '_get_user_connections', 
                         return_value=[mock_connection]):
            
            # Send all 5 critical WebSocket events
            events_to_send = [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]
            
            event_data = {
                "agent_id": "test_agent",
                "execution_id": str(uuid.uuid4()),
                "message": "Processing user request"
            }
            
            # Send each event and verify it's properly routed
            for event_type in events_to_send:
                websocket_message = WebSocketMessage(
                    event_type=event_type,
                    user_id=user_id,
                    thread_id=thread_id,
                    request_id=request_id,
                    data=event_data,
                    timestamp=datetime.utcnow()
                )
                
                # Send the message through the WebSocket system
                await websocket_manager.broadcast_to_user(
                    user_id=user_id,
                    message=websocket_message.dict()
                )
            
            # Verify all 5 events were sent to the connection
            assert len(mock_connection.messages_sent) == 5
            
            sent_event_types = [msg.get("event_type") for msg in mock_connection.messages_sent]
            expected_events = [event.value for event in events_to_send]
            
            for expected_event in expected_events:
                assert expected_event in sent_event_types, f"Missing critical event: {expected_event}"
            
            # Verify events contain proper metadata
            for message in mock_connection.messages_sent:
                assert message.get("user_id") == str(user_id)
                assert message.get("thread_id") == str(thread_id)
                assert message.get("request_id") == str(request_id)
                assert "timestamp" in message
                assert message.get("data", {}).get("agent_id") == "test_agent"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_user_isolation_concurrent_sessions(self, real_services_fixture, isolated_env):
        """Test WebSocket message isolation between concurrent user sessions."""
        
        # Create two separate users with different WebSocket connections
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        
        websocket1_id = WebSocketID(str(uuid.uuid4()))
        websocket2_id = WebSocketID(str(uuid.uuid4()))
        
        thread1_id = ensure_thread_id(str(uuid.uuid4()))
        thread2_id = ensure_thread_id(str(uuid.uuid4()))
        
        # Create separate connections for each user
        connection1 = MockWebSocketConnection(websocket1_id, user1_id)
        connection2 = MockWebSocketConnection(websocket2_id, user2_id)
        
        websocket_manager = UnifiedWebSocketManager()
        
        # Mock connection registry to return appropriate connections per user
        def mock_get_user_connections(user_id: UserID):
            if user_id == user1_id:
                return [connection1]
            elif user_id == user2_id:
                return [connection2]
            return []
        
        with patch.object(websocket_manager, '_get_user_connections', 
                         side_effect=mock_get_user_connections):
            
            # Send messages to each user concurrently
            message1 = WebSocketMessage(
                event_type=WebSocketEventType.AGENT_STARTED,
                user_id=user1_id,
                thread_id=thread1_id,
                request_id=RequestID(str(uuid.uuid4())),
                data={"message": "User 1 agent started"}
            )
            
            message2 = WebSocketMessage(
                event_type=WebSocketEventType.AGENT_STARTED,
                user_id=user2_id,
                thread_id=thread2_id,
                request_id=RequestID(str(uuid.uuid4())),
                data={"message": "User 2 agent started"}
            )
            
            # Send messages concurrently
            await asyncio.gather(
                websocket_manager.broadcast_to_user(user1_id, message1.dict()),
                websocket_manager.broadcast_to_user(user2_id, message2.dict())
            )
            
            # Verify message isolation
            assert len(connection1.messages_sent) == 1
            assert len(connection2.messages_sent) == 1
            
            # Verify each user only received their own message
            user1_message = connection1.messages_sent[0]
            user2_message = connection2.messages_sent[0]
            
            assert user1_message["data"]["message"] == "User 1 agent started"
            assert user2_message["data"]["message"] == "User 2 agent started"
            
            # Verify user IDs are properly isolated
            assert user1_message["user_id"] == str(user1_id)
            assert user2_message["user_id"] == str(user2_id)
            
            # Verify thread IDs are separate
            assert user1_message["thread_id"] == str(thread1_id)
            assert user2_message["thread_id"] == str(thread2_id)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_error_handling(self, real_services_fixture, isolated_env):
        """Test WebSocket error handling and graceful degradation."""
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket_id = WebSocketID(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        # Create a connection that fails to send messages
        class FailingWebSocketConnection:
            def __init__(self, websocket_id: WebSocketID, user_id: UserID):
                self.websocket_id = websocket_id
                self.user_id = user_id
                self.send_attempts = 0
                self.error_count = 0
            
            async def send_json(self, data: Dict[str, Any]) -> None:
                self.send_attempts += 1
                if self.send_attempts <= 2:  # Fail first 2 attempts
                    self.error_count += 1
                    raise ConnectionError("WebSocket send failed")
                # Succeed on subsequent attempts
        
        failing_connection = FailingWebSocketConnection(websocket_id, user_id)
        websocket_manager = UnifiedWebSocketManager()
        
        # Mock connection registry
        with patch.object(websocket_manager, '_get_user_connections', 
                         return_value=[failing_connection]):
            
            # Mock error handling to track retry attempts
            retry_count = 0
            original_broadcast = websocket_manager.broadcast_to_user
            
            async def mock_broadcast_with_retry(user_id: UserID, message: Dict[str, Any]):
                nonlocal retry_count
                try:
                    return await original_broadcast(user_id, message)
                except Exception as e:
                    retry_count += 1
                    if retry_count < 3:
                        # Simulate retry logic
                        await asyncio.sleep(0.1)
                        return await original_broadcast(user_id, message)
                    raise e
            
            with patch.object(websocket_manager, 'broadcast_to_user', 
                             side_effect=mock_broadcast_with_retry):
                
                message = WebSocketMessage(
                    event_type=WebSocketEventType.AGENT_STARTED,
                    user_id=user_id,
                    thread_id=thread_id,
                    request_id=RequestID(str(uuid.uuid4())),
                    data={"test": "error_handling"}
                )
                
                # This should eventually succeed after retries
                try:
                    await websocket_manager.broadcast_to_user(user_id, message.dict())
                except Exception as e:
                    # Error handling should have been attempted
                    pass
                
                # Verify retry attempts were made
                assert failing_connection.send_attempts >= 2
                assert failing_connection.error_count >= 2

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_quality_message_router_integration(self, real_services_fixture, isolated_env):
        """Test QualityMessageRouter integration with WebSocket notifications."""
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        websocket_id = WebSocketID(str(uuid.uuid4()))
        
        # Create mock connection
        mock_connection = MockWebSocketConnection(websocket_id, user_id)
        
        # Initialize quality message router
        message_router = QualityMessageRouter()
        websocket_manager = UnifiedWebSocketManager()
        
        with patch.object(websocket_manager, '_get_user_connections', 
                         return_value=[mock_connection]):
            
            # Route quality-related messages through the system
            quality_events = [
                {
                    "type": "quality_alert",
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "data": {
                        "alert_type": "performance_degradation",
                        "metric": "response_time",
                        "threshold_exceeded": True
                    }
                },
                {
                    "type": "quality_report",
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "data": {
                        "overall_score": 0.85,
                        "metrics": {
                            "accuracy": 0.92,
                            "relevance": 0.88,
                            "completeness": 0.79
                        }
                    }
                }
            ]
            
            # Process each quality event through the router
            for event in quality_events:
                await message_router.route_message(event, websocket_manager)
            
            # Verify quality messages were properly routed to WebSocket
            assert len(mock_connection.messages_sent) == 2
            
            # Check quality alert message
            quality_alert = mock_connection.messages_sent[0]
            assert quality_alert["type"] == "quality_alert"
            assert quality_alert["data"]["alert_type"] == "performance_degradation"
            
            # Check quality report message
            quality_report = mock_connection.messages_sent[1]
            assert quality_report["type"] == "quality_report"
            assert quality_report["data"]["overall_score"] == 0.85

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_ordering_and_timing(self, real_services_fixture, isolated_env):
        """Test WebSocket events are delivered in correct order with proper timing."""
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        websocket_id = WebSocketID(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        request_id = RequestID(str(uuid.uuid4()))
        
        # Create connection that tracks message timing
        class TimingTrackingConnection:
            def __init__(self, websocket_id: WebSocketID, user_id: UserID):
                self.websocket_id = websocket_id
                self.user_id = user_id
                self.messages_with_timing = []
            
            async def send_json(self, data: Dict[str, Any]) -> None:
                self.messages_with_timing.append({
                    "message": data,
                    "received_at": datetime.utcnow()
                })
        
        timing_connection = TimingTrackingConnection(websocket_id, user_id)
        websocket_manager = UnifiedWebSocketManager()
        
        with patch.object(websocket_manager, '_get_user_connections', 
                         return_value=[timing_connection]):
            
            # Send events in specific order with small delays
            event_sequence = [
                (WebSocketEventType.AGENT_STARTED, "Agent initialization complete"),
                (WebSocketEventType.AGENT_THINKING, "Analyzing user request"),
                (WebSocketEventType.TOOL_EXECUTING, "Executing data retrieval tool"),
                (WebSocketEventType.TOOL_COMPLETED, "Data retrieval completed"),
                (WebSocketEventType.AGENT_COMPLETED, "Final response generated")
            ]
            
            for i, (event_type, description) in enumerate(event_sequence):
                message = WebSocketMessage(
                    event_type=event_type,
                    user_id=user_id,
                    thread_id=thread_id,
                    request_id=request_id,
                    data={
                        "sequence_number": i,
                        "description": description,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                await websocket_manager.broadcast_to_user(user_id, message.dict())
                await asyncio.sleep(0.01)  # Small delay to ensure ordering
            
            # Verify all events were received
            assert len(timing_connection.messages_with_timing) == 5
            
            # Verify correct event ordering
            for i, event_with_timing in enumerate(timing_connection.messages_with_timing):
                message = event_with_timing["message"]
                assert message["data"]["sequence_number"] == i
                
                expected_event_type = event_sequence[i][0].value
                assert message["event_type"] == expected_event_type
            
            # Verify timing progression (each message should be received after the previous)
            for i in range(1, len(timing_connection.messages_with_timing)):
                current_time = timing_connection.messages_with_timing[i]["received_at"]
                previous_time = timing_connection.messages_with_timing[i-1]["received_at"]
                assert current_time >= previous_time, "Events received out of chronological order"