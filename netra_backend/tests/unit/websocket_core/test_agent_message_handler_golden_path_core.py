"""
Unit Tests for Agent Message Handler Golden Path Core Logic - Issue #861 Phase 1

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Quality Assurance
- Value Impact: Comprehensive test coverage for 500K+ ARR agent golden path functionality
- Strategic Impact: Prevents regressions in core agent-WebSocket message handling

Test Coverage Focus:
- Agent message handler core initialization and configuration
- Message type routing (START_AGENT, USER_MESSAGE, CHAT) 
- WebSocket context creation and validation
- Database session management in WebSocket flows
- Error handling and recovery patterns
- Processing statistics and metrics tracking

REQUIREMENTS per CLAUDE.md:
- Use SSotBaseTestCase for unified test infrastructure
- No forbidden mocks - use real service patterns where possible
- Focus on business-critical golden path functionality
- Test actual message processing logic, not just API contracts
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import WebSocket

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import IsolatedEnvironment


class AgentMessageHandlerCoreTests(SSotAsyncTestCase):
    """Test suite for core AgentMessageHandler functionality."""

    def setup_method(self, method):
        """Set up test fixtures and mocks."""
        super().setup_method(method)
        
        # Create test environment
        self.env = IsolatedEnvironment()
        self.test_user_id = "test_user_" + str(uuid.uuid4())[:8]
        self.test_thread_id = "thread_" + str(uuid.uuid4())[:8]
        self.test_run_id = "run_" + str(uuid.uuid4())[:8]
        
        # Create mock WebSocket with proper spec
        self.mock_websocket = MagicMock(spec=WebSocket)
        self.mock_websocket.scope = {
            'app': MagicMock(),
            'client': ('127.0.0.1', 12345),
            'path': '/ws',
            'type': 'websocket'
        }
        self.mock_websocket.scope['app'].state = MagicMock()
        
        # Create mock message handler service
        self.mock_message_handler_service = MagicMock(spec=MessageHandlerService)
        self.mock_message_handler_service.handle_start_agent = AsyncMock(return_value=True)
        self.mock_message_handler_service.handle_user_message = AsyncMock(return_value=True)
        
        # Create handler instance
        self.handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )
        
        # Track created contexts for cleanup
        self.created_contexts = []

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
        
        # Clean up any created contexts
        for context in self.created_contexts:
            if hasattr(context, 'cleanup'):
                try:
                    context.cleanup()
                except:
                    pass

    def create_test_message(self, message_type: MessageType, payload: Dict[str, Any]) -> WebSocketMessage:
        """Create a test WebSocket message with proper structure."""
        return WebSocketMessage(
            type=message_type,
            payload=payload,
            timestamp=time.time(),
            message_id=f"msg_{uuid.uuid4()}",
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        )

    # Test 1: Handler Initialization and Configuration
    async def test_handler_initialization_with_valid_service(self):
        """Test proper handler initialization with valid message handler service.
        
        Business Impact: Ensures handler can be properly configured for message processing.
        Golden Path Impact: Core initialization must work for any agent processing to succeed.
        """
        # Verify handler is properly initialized
        assert self.handler.message_handler_service is self.mock_message_handler_service
        assert self.handler.websocket is self.mock_websocket
        assert isinstance(self.handler.processing_stats, dict)
        
        # Verify supported message types
        expected_types = [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]
        assert set(self.handler.supported_types) == set(expected_types)
        
        # Verify initial statistics
        assert self.handler.processing_stats["messages_processed"] == 0
        assert self.handler.processing_stats["errors"] == 0

    async def test_handler_initialization_without_websocket(self):
        """Test handler can initialize without websocket parameter.
        
        Business Impact: Allows flexible handler creation patterns.
        """
        handler = AgentMessageHandler(self.mock_message_handler_service)
        assert handler.message_handler_service is self.mock_message_handler_service
        assert handler.websocket is None

    async def test_can_handle_supported_message_types(self):
        """Test handler correctly identifies supported message types.
        
        Business Impact: Ensures proper message routing in the WebSocket system.
        """
        # Test supported types
        assert self.handler.can_handle(MessageType.START_AGENT)
        assert self.handler.can_handle(MessageType.USER_MESSAGE) 
        assert self.handler.can_handle(MessageType.CHAT)
        
        # Test unsupported types
        assert not self.handler.can_handle(MessageType.PING)
        assert not self.handler.can_handle(MessageType.CONNECT)
        assert not self.handler.can_handle(MessageType.ERROR_MESSAGE)

    # Test 2: START_AGENT Message Processing
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    @patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor')
    async def test_start_agent_message_processing_success(self, mock_supervisor, mock_db_session, 
                                                         mock_ws_manager, mock_context):
        """Test successful START_AGENT message processing.
        
        Business Impact: Core agent startup functionality - must work for agent execution.
        Golden Path Impact: This is the primary entry point for agent conversations.
        """
        # Setup mocks
        mock_context_instance = MagicMock()
        mock_context_instance.thread_id = self.test_thread_id
        mock_context_instance.run_id = self.test_run_id
        mock_context.return_value = mock_context_instance
        
        mock_ws_manager_instance = AsyncMock()
        mock_ws_manager_instance.get_connection_id_by_websocket.return_value = "conn_123"
        mock_ws_manager.return_value = mock_ws_manager_instance
        
        # Setup database session generator
        async def mock_db_generator():
            yield MagicMock()
        mock_db_session.return_value = mock_db_generator()
        
        mock_supervisor.return_value = MagicMock()
        
        # Create START_AGENT message
        message = self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Help me analyze data"}
        )
        
        # Process message
        with patch('netra_backend.app.services.thread_service.ThreadService'):
            with patch('netra_backend.app.services.message_handlers.MessageHandlerService') as MockMHS:
                mock_handler_instance = AsyncMock()
                MockMHS.return_value = mock_handler_instance
                
                result = await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify success
        assert result is True
        
        # Verify context was created
        mock_context.assert_called_once_with(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=None  # Not provided in message payload
        )
        
        # Verify WebSocket manager was created
        mock_ws_manager.assert_called_once_with(mock_context_instance)
        
        # Verify statistics were updated
        assert self.handler.processing_stats["messages_processed"] == 1
        assert self.handler.processing_stats["start_agent_requests"] == 1

    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_start_agent_message_missing_user_request(self, mock_context):
        """Test START_AGENT message handling with missing user_request.
        
        Business Impact: Validates input validation prevents processing invalid requests.
        """
        # Setup context
        mock_context.return_value = MagicMock()
        
        # Create message without user_request
        message = self.create_test_message(
            MessageType.START_AGENT,
            {"other_field": "value"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                result = await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Should fail due to missing user_request
        assert result is False
        assert self.handler.processing_stats["errors"] == 1

    # Test 3: USER_MESSAGE Processing
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    @patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor')
    async def test_user_message_processing_success(self, mock_supervisor, mock_db_session,
                                                  mock_ws_manager, mock_context):
        """Test successful USER_MESSAGE processing.
        
        Business Impact: Core user message handling for ongoing conversations.
        """
        # Setup mocks similar to START_AGENT test
        mock_context_instance = MagicMock()
        mock_context_instance.thread_id = self.test_thread_id
        mock_context_instance.run_id = self.test_run_id
        mock_context.return_value = mock_context_instance
        
        mock_ws_manager.return_value = AsyncMock()
        
        async def mock_db_generator():
            yield MagicMock()
        mock_db_session.return_value = mock_db_generator()
        mock_supervisor.return_value = MagicMock()
        
        # Create USER_MESSAGE
        message = self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "Follow up question"}
        )
        
        with patch('netra_backend.app.services.thread_service.ThreadService'):
            with patch('netra_backend.app.services.message_handlers.MessageHandlerService') as MockMHS:
                mock_handler_instance = AsyncMock()
                MockMHS.return_value = mock_handler_instance
                
                result = await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify success and statistics
        assert result is True
        assert self.handler.processing_stats["user_messages"] == 1

    # Test 4: CHAT Message Processing
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    @patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor')
    async def test_chat_message_processing_success(self, mock_supervisor, mock_db_session,
                                                  mock_ws_manager, mock_context):
        """Test successful CHAT message processing.
        
        Business Impact: Modern chat interface compatibility.
        """
        # Setup mocks
        mock_context_instance = MagicMock()
        mock_context_instance.thread_id = self.test_thread_id
        mock_context_instance.run_id = self.test_run_id
        mock_context.return_value = mock_context_instance
        
        mock_ws_manager.return_value = AsyncMock()
        
        async def mock_db_generator():
            yield MagicMock()
        mock_db_session.return_value = mock_db_generator()
        mock_supervisor.return_value = MagicMock()
        
        # Create CHAT message with different content field names
        for content_field in ["message", "content", "text"]:
            message = self.create_test_message(
                MessageType.CHAT,
                {content_field: f"Chat message via {content_field}"}
            )
            
            with patch('netra_backend.app.services.thread_service.ThreadService'):
                with patch('netra_backend.app.services.message_handlers.MessageHandlerService') as MockMHS:
                    mock_handler_instance = AsyncMock()
                    MockMHS.return_value = mock_handler_instance
                    
                    result = await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
            
            assert result is True
        
        # Verify chat messages were counted
        assert self.handler.processing_stats["chat_messages"] == 3

    # Test 5: Error Handling and Recovery
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_context_creation_failure_handling(self, mock_context):
        """Test handling when user execution context creation fails.
        
        Business Impact: Graceful degradation when infrastructure components fail.
        """
        # Make context creation fail
        mock_context.side_effect = Exception("Context creation failed")
        
        message = self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Test request"}
        )
        
        result = await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Should handle error gracefully
        assert result is False
        assert self.handler.processing_stats["errors"] == 1

    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    async def test_websocket_manager_creation_failure(self, mock_ws_manager, mock_context):
        """Test handling when WebSocket manager creation fails."""
        mock_context.return_value = MagicMock()
        mock_ws_manager.side_effect = Exception("WebSocket manager creation failed")
        
        message = self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "Test message"}
        )
        
        result = await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        assert result is False
        assert self.handler.processing_stats["errors"] == 1

    # Test 6: Processing Statistics Tracking
    async def test_processing_statistics_tracking(self):
        """Test that processing statistics are properly tracked.
        
        Business Impact: Monitoring and observability of agent message processing.
        """
        initial_stats = self.handler.get_stats()
        assert initial_stats["messages_processed"] == 0
        
        # Manually update stats to test tracking
        self.handler._update_processing_stats(MessageType.START_AGENT)
        self.handler._update_processing_stats(MessageType.USER_MESSAGE)
        self.handler._update_processing_stats(MessageType.CHAT)
        
        stats = self.handler.get_stats()
        assert stats["messages_processed"] == 3
        assert stats["start_agent_requests"] == 1
        assert stats["user_messages"] == 1
        assert stats["chat_messages"] == 1
        assert stats["last_processed_time"] is not None

    # Test 7: WebSocket Context Validation
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    async def test_websocket_context_creation_and_validation(self, mock_ws_manager, mock_context):
        """Test WebSocket context creation and validation in message processing.
        
        Business Impact: Ensures proper context isolation for multi-user scenarios.
        """
        # Setup mocks
        mock_execution_context = MagicMock()
        mock_execution_context.thread_id = self.test_thread_id
        mock_execution_context.run_id = self.test_run_id
        mock_context.return_value = mock_execution_context
        
        mock_manager = AsyncMock()
        mock_manager.get_connection_id_by_websocket.return_value = "test_connection_123"
        mock_ws_manager.return_value = mock_manager
        
        # Mock the WebSocketContext creation
        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as MockWSContext:
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                mock_ws_context = MagicMock()
                mock_ws_context.user_id = self.test_user_id
                mock_ws_context.thread_id = self.test_thread_id
                mock_ws_context.run_id = self.test_run_id
                MockWSContext.create_for_user.return_value = mock_ws_context
                
                message = self.create_test_message(
                    MessageType.START_AGENT,
                    {"user_request": "Test context validation"}
                )
                
                # Should create context properly even if processing fails downstream
                try:
                    await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
                except:
                    pass  # We only care about context creation here
                
                # Verify context was created with correct parameters
                MockWSContext.create_for_user.assert_called_once_with(
                    websocket=self.mock_websocket,
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,  # From execution context
                    run_id=self.test_run_id,  # From execution context
                    connection_id="test_connection_123"
                )

    # Test 8: Thread ID and Run ID Handling
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_thread_and_run_id_extraction_from_message(self, mock_context):
        """Test proper extraction of thread_id and run_id from messages.
        
        Business Impact: Session continuity and proper conversation threading.
        """
        # Test with IDs in payload
        mock_execution_context = MagicMock()
        mock_execution_context.thread_id = "extracted_thread"
        mock_execution_context.run_id = "extracted_run"
        mock_context.return_value = mock_execution_context
        
        message = self.create_test_message(
            MessageType.USER_MESSAGE,
            {
                "message": "Test with IDs",
                "thread_id": "payload_thread",
                "run_id": "payload_run"
            }
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager'):
            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session'):
                try:
                    await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
                except:
                    pass  # We only care about context creation parameters
        
        # Verify get_user_execution_context was called with payload IDs
        mock_context.assert_called_once_with(
            user_id=self.test_user_id,
            thread_id="payload_thread",  # From message payload
            run_id="payload_run"  # From message payload
        )

    # Test 9: Database Session Management
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    async def test_database_session_lifecycle_management(self, mock_db_session, mock_ws_manager, mock_context):
        """Test proper database session lifecycle management.
        
        Business Impact: Prevents database connection leaks in WebSocket handlers.
        """
        # Setup mocks
        mock_context.return_value = MagicMock()
        mock_ws_manager.return_value = AsyncMock()
        
        # Create a mock session that tracks if it's properly closed
        mock_session = MagicMock()
        session_closed = False
        
        async def mock_db_generator():
            nonlocal session_closed
            try:
                yield mock_session
            finally:
                session_closed = True
        
        mock_db_session.return_value = mock_db_generator()
        
        message = self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Test database session"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor'):
            with patch('netra_backend.app.services.thread_service.ThreadService'):
                with patch('netra_backend.app.services.message_handlers.MessageHandlerService'):
                    await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify session was properly closed
        assert session_closed is True

    # Test 10: Concurrent Message Processing
    async def test_concurrent_message_processing_isolation(self):
        """Test that concurrent message processing maintains proper isolation.
        
        Business Impact: Ensures multi-user scenarios don't interfere with each other.
        """
        # Create multiple handlers for concurrent testing
        handler1 = AgentMessageHandler(self.mock_message_handler_service)
        handler2 = AgentMessageHandler(self.mock_message_handler_service)
        
        # Track processing order
        processing_order = []
        
        async def slow_processing(user_id, websocket, message):
            processing_order.append(f"start_{user_id}")
            await asyncio.sleep(0.01)  # Small delay
            processing_order.append(f"end_{user_id}")
            return True
        
        # Mock the internal processing to track order
        with patch.object(handler1, '_handle_message_v3_clean', side_effect=slow_processing):
            with patch.object(handler2, '_handle_message_v3_clean', side_effect=slow_processing):
                
                message1 = self.create_test_message(MessageType.USER_MESSAGE, {"message": "User 1"})
                message2 = self.create_test_message(MessageType.USER_MESSAGE, {"message": "User 2"})
                
                # Process messages concurrently
                await asyncio.gather(
                    handler1.handle_message("user1", self.mock_websocket, message1),
                    handler2.handle_message("user2", self.mock_websocket, message2)
                )
        
        # Verify both processors ran (order may vary due to concurrency)
        assert "start_user1" in processing_order
        assert "end_user1" in processing_order
        assert "start_user2" in processing_order
        assert "end_user2" in processing_order