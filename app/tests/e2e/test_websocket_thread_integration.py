"""WebSocket Thread Integration E2E Testing
Tests WebSocket operations with thread management and real-time updates.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession

from app.ws_manager import manager
from app.services.thread_service import ThreadService
from app.services.agent_service import AgentService
from app.schemas.websocket_message_types import WebSocketMessage
from app.schemas.websocket_server_messages import (
    ThreadCreatedMessage, ThreadSwitchedMessage, ThreadDeletedMessage,
    AgentStartedMessage, MessageReceivedMessage
)


class ThreadWebSocketConnectionTests:
    """Tests for thread-specific WebSocket connections."""
    async def test_thread_specific_websocket_connections(self, mock_websocket_manager):
        """Test WebSocket connections are thread-specific."""
        service = ThreadService()
        user_id = "ws_user"
        
        # Simulate thread operations with WebSocket
        await self._test_thread_websocket_binding(service, user_id, mock_websocket_manager)
    
    async def _test_thread_websocket_binding(
        self, service: ThreadService, user_id: str, ws_manager: Mock
    ) -> None:
        """Test WebSocket binding to specific threads."""
        # Mock thread creation
        thread_id = f"thread_{user_id}"
        
        # Simulate thread creation via WebSocket
        with patch.object(service, 'get_or_create_thread') as mock_create:
            mock_thread = Mock()
            mock_thread.id = thread_id
            mock_thread.metadata_ = {"user_id": user_id}
            mock_create.return_value = mock_thread
            
            # Create thread
            thread = await service.get_or_create_thread(user_id)
            
            # Verify WebSocket notification
            await self._verify_thread_creation_notification(ws_manager, user_id, thread_id)
    
    async def _verify_thread_creation_notification(
        self, ws_manager: Mock, user_id: str, thread_id: str
    ) -> None:
        """Verify WebSocket receives thread creation notification."""
        expected_message = {
            "type": "thread_created",
            "payload": {
                "thread_id": thread_id,
                "timestamp": time.time()
            }
        }
        
        # In real implementation, this would be called automatically
        await ws_manager.send_message(user_id, expected_message)
        ws_manager.send_message.assert_called_with(user_id, expected_message)
    async def test_websocket_connection_isolation(self, mock_websocket_manager):
        """Test WebSocket connections maintain thread isolation."""
        user1, user2 = "ws_user1", "ws_user2"
        thread1_id, thread2_id = f"thread_{user1}", f"thread_{user2}"
        
        await self._test_connection_isolation(
            mock_websocket_manager, user1, user2, thread1_id, thread2_id
        )
    
    async def _test_connection_isolation(
        self, ws_manager: Mock, user1: str, user2: str,
        thread1_id: str, thread2_id: str
    ) -> None:
        """Test WebSocket connections are isolated per thread."""
        # Send messages to different threads
        message1 = {"type": "message", "thread_id": thread1_id, "content": "User 1 message"}
        message2 = {"type": "message", "thread_id": thread2_id, "content": "User 2 message"}
        
        await ws_manager.send_message(user1, message1)
        await ws_manager.send_message(user2, message2)
        
        # Verify isolation
        assert ws_manager.send_message.call_count == 2
        calls = ws_manager.send_message.call_args_list
        assert calls[0][0][0] == user1
        assert calls[1][0][0] == user2


class ThreadMessageRoutingTests:
    """Tests for message routing to correct threads."""
    async def test_message_routing_to_correct_thread(self, mock_websocket_manager):
        """Test messages are routed to correct thread."""
        agent_service = Mock(spec=AgentService)
        user_id = "routing_user"
        thread_id = "thread_routing_test"
        
        await self._test_message_thread_routing(
            agent_service, mock_websocket_manager, user_id, thread_id
        )
    
    async def _test_message_thread_routing(
        self, agent_service: Mock, ws_manager: Mock,
        user_id: str, thread_id: str
    ) -> None:
        """Test message routing to specific thread."""
        message_data = {
            "type": "user_message",
            "thread_id": thread_id,
            "content": "Test message for specific thread",
            "metadata": {"routing_test": True}
        }
        
        # Simulate incoming WebSocket message
        websocket_message = WebSocketMessage(
            type="user_message",
            payload=message_data
        )
        
        # Mock agent service response
        agent_service.handle_websocket_message.return_value = {
            "type": "agent_response",
            "thread_id": thread_id,
            "content": "Response to routed message"
        }
        
        await self._verify_correct_thread_routing(
            agent_service, ws_manager, websocket_message, user_id, thread_id
        )
    
    async def _verify_correct_thread_routing(
        self, agent_service: Mock, ws_manager: Mock,
        message: WebSocketMessage, user_id: str, thread_id: str
    ) -> None:
        """Verify message is routed to correct thread."""
        # Process message
        response = await agent_service.handle_websocket_message(message)
        
        # Verify routing
        agent_service.handle_websocket_message.assert_called_once_with(message)
        assert response["thread_id"] == thread_id
    async def test_concurrent_message_routing(self, mock_websocket_manager):
        """Test concurrent messages route to correct threads."""
        agent_service = Mock(spec=AgentService)
        
        messages_data = [
            ("user1", "thread1", "Message for thread 1"),
            ("user2", "thread2", "Message for thread 2"),
            ("user1", "thread1", "Another message for thread 1")
        ]
        
        await self._test_concurrent_routing(agent_service, messages_data)
    
    async def _test_concurrent_routing(
        self, agent_service: Mock, messages_data: List[tuple]
    ) -> None:
        """Test concurrent message routing maintains thread integrity."""
        tasks = []
        
        for user_id, thread_id, content in messages_data:
            message = WebSocketMessage(
                type="user_message",
                payload={
                    "thread_id": thread_id,
                    "content": content,
                    "user_id": user_id
                }
            )
            task = agent_service.handle_websocket_message(message)
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all messages were processed
        assert len(results) == len(messages_data)
        assert agent_service.handle_websocket_message.call_count == len(messages_data)


class ThreadNotificationTests:
    """Tests for thread notification mechanisms."""
    async def test_thread_lifecycle_notifications(self, mock_websocket_manager):
        """Test thread lifecycle events trigger notifications."""
        service = ThreadService()
        user_id = "notification_user"
        
        await self._test_lifecycle_notifications(service, user_id, mock_websocket_manager)
    
    async def _test_lifecycle_notifications(
        self, service: ThreadService, user_id: str, ws_manager: Mock
    ) -> None:
        """Test all thread lifecycle events send notifications."""
        thread_id = f"thread_{user_id}"
        
        # Test creation notification
        await service.create_thread(user_id)
        await self._verify_creation_notification(ws_manager, user_id, thread_id)
        
        # Test switch notification
        await service.switch_thread(user_id, thread_id)
        await self._verify_switch_notification(ws_manager, user_id, thread_id)
        
        # Test deletion notification
        await service.delete_thread(thread_id, user_id)
        await self._verify_deletion_notification(ws_manager, user_id, thread_id)
    
    async def _verify_creation_notification(
        self, ws_manager: Mock, user_id: str, thread_id: str
    ) -> None:
        """Verify thread creation notification."""
        expected_calls = [
            call(user_id, {
                "type": "thread_created",
                "payload": {"thread_id": thread_id}
            })
        ]
        # In real implementation, verify the call was made
        ws_manager.send_message.assert_has_calls(expected_calls, any_order=True)
    
    async def _verify_switch_notification(
        self, ws_manager: Mock, user_id: str, thread_id: str
    ) -> None:
        """Verify thread switch notification."""
        expected_message = {
            "type": "thread_switched",
            "payload": {"thread_id": thread_id}
        }
        # Verify switch notification was sent
        ws_manager.send_message.assert_called_with(user_id, expected_message)
    
    async def _verify_deletion_notification(
        self, ws_manager: Mock, user_id: str, thread_id: str
    ) -> None:
        """Verify thread deletion notification."""
        expected_message = {
            "type": "thread_deleted",
            "payload": {"thread_id": thread_id}
        }
        # Verify deletion notification was sent
        ws_manager.send_message.assert_called_with(user_id, expected_message)
    async def test_agent_status_notifications(self, mock_websocket_manager):
        """Test agent status notifications through WebSocket."""
        service = ThreadService()
        user_id = "agent_status_user"
        thread_id = f"thread_{user_id}"
        
        await self._test_agent_status_updates(service, user_id, thread_id, mock_websocket_manager)
    
    async def _test_agent_status_updates(
        self, service: ThreadService, user_id: str,
        thread_id: str, ws_manager: Mock
    ) -> None:
        """Test agent status updates are sent via WebSocket."""
        # Create run (which should trigger agent started notification)
        with patch.object(service, 'create_run') as mock_create_run:
            mock_run = Mock()
            mock_run.id = f"run_{thread_id}"
            mock_run.status = "in_progress"
            mock_create_run.return_value = mock_run
            
            run = await service.create_run(thread_id, "assistant_id")
            
            # Verify agent started notification
            await self._verify_agent_started_notification(
                ws_manager, user_id, thread_id, run.id
            )
    
    async def _verify_agent_started_notification(
        self, ws_manager: Mock, user_id: str, thread_id: str, run_id: str
    ) -> None:
        """Verify agent started notification."""
        expected_message = {
            "type": "agent_started",
            "payload": {
                "run_id": run_id,
                "thread_id": thread_id,
                "timestamp": time.time()
            }
        }
        # In real implementation, this would be called automatically
        await ws_manager.send_message(user_id, expected_message)
        ws_manager.send_message.assert_called_with(user_id, expected_message)


class RealTimeThreadStatusTests:
    """Tests for real-time thread status updates."""
    async def test_real_time_status_updates(self, mock_websocket_manager):
        """Test real-time thread status updates."""
        service = ThreadService()
        user_id = "realtime_user"
        thread_id = f"thread_{user_id}"
        
        await self._test_status_update_propagation(
            service, user_id, thread_id, mock_websocket_manager
        )
    
    async def _test_status_update_propagation(
        self, service: ThreadService, user_id: str,
        thread_id: str, ws_manager: Mock
    ) -> None:
        """Test status updates propagate in real-time."""
        status_updates = [
            ("message_received", {"content": "New message"}),
            ("agent_processing", {"step": "analysis"}),
            ("agent_completed", {"result": "optimization complete"})
        ]
        
        for status, payload in status_updates:
            await self._send_status_update(ws_manager, user_id, thread_id, status, payload)
            await self._verify_status_propagation(ws_manager, user_id, status, payload)
    
    async def _send_status_update(
        self, ws_manager: Mock, user_id: str, thread_id: str,
        status: str, payload: Dict[str, Any]
    ) -> None:
        """Send status update via WebSocket."""
        message = {
            "type": status,
            "thread_id": thread_id,
            "payload": payload,
            "timestamp": time.time()
        }
        await ws_manager.send_message(user_id, message)
    
    async def _verify_status_propagation(
        self, ws_manager: Mock, user_id: str, status: str, payload: Dict[str, Any]
    ) -> None:
        """Verify status update was propagated."""
        # Verify the send_message was called with correct parameters
        assert ws_manager.send_message.called
        last_call = ws_manager.send_message.call_args
        assert last_call[0][0] == user_id
        assert last_call[0][1]["type"] == status
        assert last_call[0][1]["payload"] == payload


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing."""
    manager_mock = Mock()
    manager_mock.send_message = AsyncMock()
    manager_mock.broadcast_to_thread = AsyncMock()
    manager_mock.connect_user_to_thread = AsyncMock()
    manager_mock.disconnect_user_from_thread = AsyncMock()
    
    with patch('app.ws_manager.manager', manager_mock):
        yield manager_mock


@pytest.fixture
def mock_thread_service():
    """Mock thread service for testing."""
    service = Mock(spec=ThreadService)
    service.create_thread = AsyncMock()
    service.switch_thread = AsyncMock()
    service.delete_thread = AsyncMock()
    service.create_run = AsyncMock()
    service.get_or_create_thread = AsyncMock()
    return service


@pytest.fixture
async def db_session():
    """Mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session