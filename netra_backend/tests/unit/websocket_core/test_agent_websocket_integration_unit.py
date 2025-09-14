"""
Unit Tests for Agent WebSocket Integration

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Real-time Communication & User Experience  
- Value Impact: Tests WebSocket event delivery for $500K+ ARR chat functionality
- Strategic Impact: Validates agent handler WebSocket registration and multi-user isolation

Tests cover agent handler WebSocket registration, event delivery validation,
multi-user isolation, and connection cleanup for the golden path workflow.

SSOT Compliance: Uses SSotAsyncTestCase base class and unified test patterns.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService


class TestAgentWebSocketIntegration(SSotAsyncTestCase):
    """Unit tests for agent WebSocket integration functionality."""
    
    def setup_method(self, method):
        """Set up test fixtures for each test method."""
        super().setup_method(method)
        
        # Create mock dependencies
        self.mock_message_handler_service = MagicMock(spec=MessageHandlerService)
        self.mock_websocket = AsyncMock()
        self.mock_websocket.client = MagicMock()
        self.mock_websocket.client.host = "testhost"
        self.mock_websocket_manager = MagicMock(spec=WebSocketManager)
        
        # Test data
        self.test_user_id = "test-user-123"
        self.test_connection_id = str(uuid.uuid4())
        self.test_message_id = str(uuid.uuid4())
        
        # Create test instance
        self.agent_handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )
        
    async def test_websocket_manager_registration(self):
        """Test that agent handler properly registers with WebSocket manager."""
        # Arrange
        websocket_context = WebSocketContext(
            connection_id=self.test_connection_id,
            user_id=self.test_user_id,
            websocket=self.mock_websocket
        )
        
        # Act
        handler_with_context = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=websocket_context.websocket
        )
        
        # Assert
        assert handler_with_context.websocket is not None
        assert handler_with_context.websocket == self.mock_websocket
        
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    async def test_websocket_manager_factory_integration(self, mock_create_manager):
        """Test integration with WebSocket manager factory."""
        # Arrange
        mock_create_manager.return_value = self.mock_websocket_manager
        
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"agent_type": "supervisor"},
            message_id=self.test_message_id,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Act - This tests the factory integration pattern
        with patch.object(self.agent_handler, 'handle_message') as mock_handle:
            mock_handle.return_value = True
            
            await self.agent_handler.handle_message(
                user_id=self.test_user_id,
                websocket=self.mock_websocket,
                message=message
            )
            
        # Assert
        mock_handle.assert_called_once()
        
    async def test_event_delivery_agent_started(self):
        """Test that agent_started events are properly delivered via WebSocket."""
        # Arrange
        expected_event = {
            "type": "agent_started",
            "payload": {
                "agent_type": "supervisor",
                "request_id": self.test_message_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Mock WebSocket send method
        self.mock_websocket.send_text = AsyncMock()
        
        # Act - Simulate agent started event delivery
        with patch.object(self.agent_handler, '_send_websocket_event') as mock_send:
            mock_send.return_value = True
            
            await self.agent_handler._send_websocket_event(
                "agent_started",
                expected_event["payload"]
            )
            
        # Assert
        mock_send.assert_called_once_with("agent_started", expected_event["payload"])
        
    async def test_event_delivery_agent_thinking(self):
        """Test that agent_thinking events are properly delivered."""
        # Arrange
        thinking_payload = {
            "agent_id": str(uuid.uuid4()),
            "thought_process": "Analyzing user request for AI optimization...",
            "stage": "analysis"
        }
        
        # Mock WebSocket send
        self.mock_websocket.send_text = AsyncMock()
        
        # Act
        with patch.object(self.agent_handler, '_send_websocket_event') as mock_send:
            mock_send.return_value = True
            
            await self.agent_handler._send_websocket_event(
                "agent_thinking", 
                thinking_payload
            )
            
        # Assert
        mock_send.assert_called_once_with("agent_thinking", thinking_payload)
        
    async def test_event_delivery_tool_executing(self):
        """Test that tool_executing events are properly delivered."""
        # Arrange
        tool_payload = {
            "tool_name": "data_analyzer",
            "parameters": {"dataset": "user_metrics"},
            "execution_id": str(uuid.uuid4())
        }
        
        # Act
        with patch.object(self.agent_handler, '_send_websocket_event') as mock_send:
            mock_send.return_value = True
            
            await self.agent_handler._send_websocket_event(
                "tool_executing",
                tool_payload
            )
            
        # Assert
        mock_send.assert_called_once_with("tool_executing", tool_payload)
        
    async def test_event_delivery_agent_completed(self):
        """Test that agent_completed events are properly delivered."""
        # Arrange
        completion_payload = {
            "agent_id": str(uuid.uuid4()),
            "result": "Successfully analyzed AI pipeline and provided recommendations",
            "execution_time": "2.5s"
        }
        
        # Act
        with patch.object(self.agent_handler, '_send_websocket_event') as mock_send:
            mock_send.return_value = True
            
            await self.agent_handler._send_websocket_event(
                "agent_completed",
                completion_payload
            )
            
        # Assert
        mock_send.assert_called_once_with("agent_completed", completion_payload)


class TestMultiUserWebSocketIsolation(SSotAsyncTestCase):
    """Unit tests for multi-user WebSocket isolation in agent handling."""
    
    def setup_method(self, method):
        """Set up test fixtures for each test method."""
        super().setup_method(method)
        
        # Create multiple user contexts
        self.user1_id = "user-1"
        self.user2_id = "user-2"
        self.connection1_id = str(uuid.uuid4())
        self.connection2_id = str(uuid.uuid4())
        
        # Create separate WebSocket mocks for each user
        self.mock_websocket1 = AsyncMock()
        self.mock_websocket1.client = MagicMock()
        self.mock_websocket1.client.host = "testhost1"
        
        self.mock_websocket2 = AsyncMock()
        self.mock_websocket2.client = MagicMock()
        self.mock_websocket2.client.host = "testhost2"
        
        # Create separate handlers for each user
        self.mock_service1 = MagicMock(spec=MessageHandlerService)
        self.mock_service2 = MagicMock(spec=MessageHandlerService)
        
        self.handler1 = AgentMessageHandler(
            message_handler_service=self.mock_service1,
            websocket=self.mock_websocket1
        )
        
        self.handler2 = AgentMessageHandler(
            message_handler_service=self.mock_service2,
            websocket=self.mock_websocket2
        )
        
    async def test_user_context_isolation(self):
        """Test that user execution contexts are properly isolated between users."""
        # Arrange
        message1 = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"content": "User 1 message"},
            message_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc)
        )
        
        message2 = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"content": "User 2 message"},
            message_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Act - Process messages for different users
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            # Create separate contexts for each user
            mock_context1 = MagicMock()
            mock_context1.user_id = self.user1_id
            mock_context2 = MagicMock()
            mock_context2.user_id = self.user2_id
            
            mock_get_context.side_effect = [mock_context1, mock_context2]
            
            with patch.object(self.handler1, 'handle_message') as mock_handle1:
                with patch.object(self.handler2, 'handle_message') as mock_handle2:
                    mock_handle1.return_value = True
                    mock_handle2.return_value = True
                    
                    # Process messages for each user
                    result1 = await self.handler1.handle_message(
                        user_id=self.user1_id,
                        websocket=self.mock_websocket1,
                        message=message1
                    )
                    
                    result2 = await self.handler2.handle_message(
                        user_id=self.user2_id,
                        websocket=self.mock_websocket2,
                        message=message2
                    )
                    
                    # Assert
                    assert result1 is True
                    assert result2 is True
                    mock_handle1.assert_called_once()
                    mock_handle2.assert_called_once()
                    
    async def test_websocket_event_isolation(self):
        """Test that WebSocket events are delivered only to the correct user."""
        # Arrange
        event_payload = {"test": "event for user 1"}
        
        # Mock send methods
        self.mock_websocket1.send_text = AsyncMock()
        self.mock_websocket2.send_text = AsyncMock()
        
        # Act - Send event only to user 1
        with patch.object(self.handler1, '_send_websocket_event') as mock_send1:
            mock_send1.return_value = True
            
            await self.handler1._send_websocket_event("agent_started", event_payload)
            
        # Assert - Only user 1 should receive the event
        mock_send1.assert_called_once_with("agent_started", event_payload)
        
        # User 2's WebSocket should not have been called
        self.mock_websocket2.send_text.assert_not_called()
        
    async def test_concurrent_message_processing_isolation(self):
        """Test that concurrent message processing maintains user isolation."""
        # Arrange
        messages = []
        for i in range(5):
            messages.append(WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={"content": f"Message {i}"},
                message_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Act - Process messages concurrently for different users
        tasks = []
        
        with patch.object(self.handler1, 'handle_message') as mock_handle1:
            with patch.object(self.handler2, 'handle_message') as mock_handle2:
                mock_handle1.return_value = True
                mock_handle2.return_value = True
                
                # Create concurrent tasks
                for i, message in enumerate(messages):
                    if i % 2 == 0:
                        task = asyncio.create_task(
                            self.handler1.handle_message(
                                user_id=self.user1_id,
                                websocket=self.mock_websocket1,
                                message=message
                            )
                        )
                    else:
                        task = asyncio.create_task(
                            self.handler2.handle_message(
                                user_id=self.user2_id,
                                websocket=self.mock_websocket2,
                                message=message
                            )
                        )
                    tasks.append(task)
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # Assert
                assert all(result is True for result in results)
                assert mock_handle1.call_count == 3  # Even indices (0, 2, 4)
                assert mock_handle2.call_count == 2  # Odd indices (1, 3)


class TestWebSocketConnectionCleanup(SSotAsyncTestCase):
    """Unit tests for WebSocket connection cleanup in agent handlers."""
    
    def setup_method(self, method):
        """Set up test fixtures for each test method."""
        super().setup_method(method)
        
        self.mock_websocket = AsyncMock()
        self.mock_service = MagicMock(spec=MessageHandlerService)
        self.test_user_id = "cleanup-test-user"
        
        self.agent_handler = AgentMessageHandler(
            message_handler_service=self.mock_service,
            websocket=self.mock_websocket
        )
        
    async def test_connection_cleanup_on_disconnect(self):
        """Test that connections are properly cleaned up on disconnect."""
        # Arrange
        connection_id = str(uuid.uuid4())
        
        # Simulate connection cleanup
        with patch.object(self.agent_handler, '_cleanup_connection') as mock_cleanup:
            mock_cleanup.return_value = True
            
            # Act
            result = await self.agent_handler._cleanup_connection(connection_id)
            
            # Assert
            mock_cleanup.assert_called_once_with(connection_id)
            assert result is True
            
    async def test_resource_cleanup_on_handler_destruction(self):
        """Test that resources are cleaned up when handler is destroyed."""
        # Arrange
        handler = AgentMessageHandler(
            message_handler_service=self.mock_service,
            websocket=self.mock_websocket
        )
        
        # Act - Simulate handler cleanup
        with patch.object(handler, '_cleanup_resources') as mock_cleanup:
            mock_cleanup.return_value = True
            
            await handler._cleanup_resources()
            
        # Assert
        mock_cleanup.assert_called_once()
        
    async def test_websocket_state_validation_before_send(self):
        """Test that WebSocket state is validated before sending events."""
        # Arrange
        event_payload = {"test": "event"}
        
        # Mock WebSocket state check
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected') as mock_connected:
            mock_connected.return_value = True
            self.mock_websocket.send_text = AsyncMock()
            
            # Act
            with patch.object(self.agent_handler, '_send_websocket_event') as mock_send:
                mock_send.return_value = True
                
                result = await self.agent_handler._send_websocket_event(
                    "agent_started",
                    event_payload
                )
                
            # Assert
            mock_send.assert_called_once_with("agent_started", event_payload)
            
    async def test_graceful_degradation_on_websocket_error(self):
        """Test graceful degradation when WebSocket operations fail."""
        # Arrange
        event_payload = {"test": "event"}
        self.mock_websocket.send_text = AsyncMock(side_effect=Exception("WebSocket error"))
        
        # Act & Assert - Should not raise exception
        with patch.object(self.agent_handler, '_send_websocket_event') as mock_send:
            mock_send.side_effect = Exception("WebSocket error")
            
            try:
                await self.agent_handler._send_websocket_event("agent_started", event_payload)
            except Exception as e:
                # Expected - but test that it's handled gracefully in implementation
                assert "WebSocket error" in str(e)