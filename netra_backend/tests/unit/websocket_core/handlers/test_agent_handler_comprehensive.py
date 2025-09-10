"""
Comprehensive Unit Tests for AgentHandler Message Routing - Golden Path Requirements

Business Value Justification:
- Segment: Platform/Critical Infrastructure  
- Business Goal: Chat functionality delivers 90% of platform value
- Value Impact: Ensures user messages are correctly routed to agents for processing
- Strategic Impact: Critical component for $500K+ ARR chat functionality reliability

CRITICAL MISSION: Get Golden Path working - users login and get AI responses back.

This test suite covers:
1. Message type detection and routing (START_AGENT, USER_MESSAGE, CHAT)
2. Agent selection based on message content  
3. User context propagation and session management
4. WebSocket event emission for business-critical agent events
5. Error handling and recovery scenarios
6. Invalid message handling and validation
7. Rate limiting and throttling
8. Concurrent message processing
9. V2 legacy and V3 clean pattern validation
10. Multi-user isolation testing

REQUIREMENTS:
- 100% method coverage for AgentHandler
- Focus on business value - routing messages correctly
- Use SSOT test patterns from test_framework
- Mock external dependencies appropriately  
- Test all critical message routing scenarios
- Validate WebSocket events are emitted correctly
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

# Import SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import AgentHandler and dependencies
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.dependencies import RequestScopedContext

# Import ID generation
from shared.id_generation import UnifiedIdGenerator


class TestAgentHandlerComprehensive(SSotAsyncTestCase):
    """
    Comprehensive test suite for AgentHandler message routing.
    
    Tests all critical message routing scenarios that are essential 
    for the golden path user flow where users login and get AI responses.
    """

    async def async_setup_method(self, method=None):
        """Setup method for each test."""
        await super().async_setup_method(method)
        
        # Set test environment variables
        self.set_env_var("USE_WEBSOCKET_SUPERVISOR_V3", "true")
        self.set_env_var("TESTING", "true")
        
        # Setup common test data
        self.test_user_id = "test_user_123"
        self.test_thread_id = "thread_456"
        self.test_run_id = "run_789"
        self.test_connection_id = "conn_abc"
        
        # Create mock dependencies
        self.mock_websocket = AsyncMock(spec=WebSocket)
        self.mock_websocket.scope = {
            'app': MagicMock(),
            'type': 'websocket'
        }
        self.mock_websocket.scope['app'].state = MagicMock()
        
        self.mock_db_session = AsyncMock(spec=AsyncSession)
        self.mock_message_handler_service = AsyncMock(spec=MessageHandlerService)
        
        # Create AgentHandler instance
        self.agent_handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )
        
        # Mock WebSocket manager
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.get_connection_id_by_websocket.return_value = self.test_connection_id
        self.mock_websocket_manager.update_connection_thread = AsyncMock()
        self.mock_websocket_manager.send_error = AsyncMock()
        
        # Mock user execution context
        self.mock_user_context = Mock(spec=UserExecutionContext)
        self.mock_user_context.user_id = self.test_user_id
        self.mock_user_context.thread_id = self.test_thread_id
        self.mock_user_context.run_id = self.test_run_id
        self.mock_user_context.request_id = "req_123"
        self.mock_user_context.websocket_connection_id = self.test_connection_id
        
        # Mock WebSocket context  
        self.mock_websocket_context = Mock(spec=WebSocketContext)
        self.mock_websocket_context.user_id = self.test_user_id
        self.mock_websocket_context.thread_id = self.test_thread_id
        self.mock_websocket_context.run_id = self.test_run_id
        self.mock_websocket_context.connection_id = self.test_connection_id
        self.mock_websocket_context.update_activity = Mock()
        self.mock_websocket_context.validate_for_message_processing = Mock()

    async def create_test_message(self, 
                                message_type: MessageType, 
                                payload: Dict[str, Any],
                                thread_id: Optional[str] = None,
                                user_id: Optional[str] = None) -> WebSocketMessage:
        """Helper to create test WebSocket messages."""
        return WebSocketMessage(
            type=message_type,
            payload=payload,
            thread_id=thread_id or self.test_thread_id,
            user_id=user_id or self.test_user_id,
            timestamp=time.time(),
            message_id=f"msg_{uuid.uuid4().hex[:8]}"
        )

    # ========================================================================
    # CORE MESSAGE ROUTING TESTS (Tests 1-10)
    # ========================================================================

    async def test_01_handle_message_v3_clean_pattern_start_agent(self):
        """
        Test 1: V3 clean pattern handles START_AGENT messages correctly.
        
        Business Impact: Ensures agents can be started through WebSocket.
        Golden Path: Critical for user message → agent execution flow.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Start analysis agent", "thread_id": self.test_thread_id}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            # Create new message handler for this supervisor
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify success
                                assert result is True
                                
                                # Verify WebSocket context was created correctly
                                mock_ws_context_class.create_for_user.assert_called_once()
                                call_args = mock_ws_context_class.create_for_user.call_args
                                assert call_args[1]['user_id'] == self.test_user_id
                                assert call_args[1]['websocket'] == self.mock_websocket
                                
                                # Verify message handler was called
                                mock_mhs_instance.handle_start_agent.assert_called_once()
                                call_args = mock_mhs_instance.handle_start_agent.call_args
                                assert call_args[1]['user_id'] == self.test_user_id
                                assert call_args[1]['payload'] == message.payload
                                assert call_args[1]['websocket'] == self.mock_websocket
                                
                                # Verify WebSocket manager operations
                                self.mock_websocket_manager.get_connection_id_by_websocket.assert_called_with(self.mock_websocket)
                                self.mock_websocket_manager.update_connection_thread.assert_called_with(
                                    self.test_connection_id, self.test_thread_id
                                )
                                
                                # Verify processing stats updated
                                stats = self.agent_handler.get_stats()
                                assert stats["messages_processed"] >= 1
                                assert stats["start_agent_requests"] >= 1

    async def test_02_handle_message_v3_clean_pattern_user_message(self):
        """
        Test 2: V3 clean pattern handles USER_MESSAGE correctly.
        
        Business Impact: Core chat functionality for user interaction.
        Golden Path: Essential for user chat messages → AI responses.
        """
        message = await self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "Hello, I need help with analysis", "thread_id": self.test_thread_id}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify success
                                assert result is True
                                
                                # Verify correct handler method called for user message
                                mock_mhs_instance.handle_user_message.assert_called_once()
                                call_args = mock_mhs_instance.handle_user_message.call_args
                                assert call_args[1]['user_id'] == self.test_user_id
                                assert call_args[1]['payload'] == message.payload
                                
                                # Verify processing stats updated
                                stats = self.agent_handler.get_stats()
                                assert stats["user_messages"] >= 1

    async def test_03_handle_message_v3_clean_pattern_chat_message(self):
        """
        Test 3: V3 clean pattern handles CHAT messages correctly.
        
        Business Impact: Alternative chat interface compatibility.
        Golden Path: Supports multiple chat message formats.
        """
        message = await self.create_test_message(
            MessageType.CHAT,
            {"content": "Can you help me optimize this process?"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify success
                                assert result is True
                                
                                # Verify CHAT messages use handle_user_message
                                mock_mhs_instance.handle_user_message.assert_called_once()
                                
                                # Verify processing stats updated
                                stats = self.agent_handler.get_stats()
                                assert stats["chat_messages"] >= 1

    async def test_04_handle_message_v2_legacy_pattern_compatibility(self):
        """
        Test 4: V2 legacy pattern still works when feature flag disabled.
        
        Business Impact: Backward compatibility during gradual rollout.
        Golden Path: Ensures no disruption during V3 deployment.
        """
        # Disable V3 pattern
        self.set_env_var("USE_WEBSOCKET_SUPERVISOR_V3", "false")
        
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Legacy pattern test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor') as mock_get_supervisor:
                        with patch('fastapi.Request') as mock_request_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_request = Mock()
                            mock_request_class.return_value = mock_request
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify success
                                assert result is True
                                
                                # Verify V2 pattern used (mock Request created)
                                mock_request_class.assert_called_once()
                                
                                # Verify message handled
                                mock_mhs_instance.handle_start_agent.assert_called_once()

    async def test_05_message_type_routing_validation(self):
        """
        Test 5: Verify all supported message types route correctly.
        
        Business Impact: Comprehensive message type support.
        Golden Path: All message types work properly.
        """
        test_cases = [
            (MessageType.START_AGENT, {"user_request": "Start agent"}, "handle_start_agent"),
            (MessageType.USER_MESSAGE, {"message": "User message"}, "handle_user_message"),
            (MessageType.CHAT, {"content": "Chat message"}, "handle_user_message"),
        ]
        
        for message_type, payload, expected_handler in test_cases:
            with self.subTest(message_type=message_type):
                message = await self.create_test_message(message_type, payload)
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                    with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                                with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                    
                                    # Setup mocks
                                    mock_get_context.return_value = self.mock_user_context
                                    mock_create_ws.return_value = self.mock_websocket_manager
                                    
                                    async def db_generator():
                                        yield self.mock_db_session
                                    mock_get_db.return_value = db_generator()
                                    
                                    mock_supervisor = AsyncMock()
                                    mock_get_supervisor.return_value = mock_supervisor
                                    
                                    mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                    
                                    with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                        mock_mhs_instance = AsyncMock()
                                        mock_mhs_class.return_value = mock_mhs_instance
                                        
                                        # Execute test
                                        result = await self.agent_handler.handle_message(
                                            self.test_user_id, self.mock_websocket, message
                                        )
                                        
                                        # Verify success
                                        assert result is True
                                        
                                        # Verify correct handler called
                                        handler_method = getattr(mock_mhs_instance, expected_handler)
                                        handler_method.assert_called_once()

    async def test_06_user_context_propagation(self):
        """
        Test 6: Verify user context is properly propagated through the system.
        
        Business Impact: Ensures user isolation and session continuity.
        Golden Path: Critical for multi-user system integrity.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Context test", "thread_id": self.test_thread_id, "run_id": self.test_run_id}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify user context was created with correct parameters
                                mock_get_context.assert_called()
                                call_args = mock_get_context.call_args
                                assert call_args[1]['user_id'] == self.test_user_id
                                assert call_args[1]['thread_id'] == self.test_thread_id
                                assert call_args[1]['run_id'] == self.test_run_id
                                
                                # Verify WebSocket context created with user context data
                                mock_ws_context_class.create_for_user.assert_called()
                                ws_call_args = mock_ws_context_class.create_for_user.call_args
                                assert ws_call_args[1]['user_id'] == self.test_user_id
                                assert ws_call_args[1]['thread_id'] == self.mock_user_context.thread_id

    async def test_07_websocket_manager_integration(self):
        """
        Test 7: Verify WebSocket manager integration and connection management.
        
        Business Impact: Ensures WebSocket events reach correct users.
        Golden Path: Critical for real-time chat updates.
        """
        message = await self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "WebSocket integration test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify WebSocket manager was created
                                mock_create_ws.assert_called_with(self.mock_user_context)
                                
                                # Verify connection ID was retrieved
                                self.mock_websocket_manager.get_connection_id_by_websocket.assert_called_with(self.mock_websocket)
                                
                                # Verify thread association was updated
                                self.mock_websocket_manager.update_connection_thread.assert_called_with(
                                    self.test_connection_id, self.test_thread_id
                                )

    async def test_08_session_continuity_with_existing_ids(self):
        """
        Test 8: Verify session continuity when existing thread/run IDs provided.
        
        Business Impact: Maintains conversation context across messages.
        Golden Path: Essential for coherent multi-turn conversations.
        """
        existing_thread_id = "existing_thread_999"
        existing_run_id = "existing_run_888"
        
        message = await self.create_test_message(
            MessageType.USER_MESSAGE,
            {
                "message": "Continue conversation", 
                "thread_id": existing_thread_id,
                "run_id": existing_run_id
            },
            thread_id=existing_thread_id
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify existing IDs were passed to context
                                mock_get_context.assert_called()
                                call_args = mock_get_context.call_args
                                assert call_args[1]['thread_id'] == existing_thread_id
                                assert call_args[1]['run_id'] == existing_run_id

    async def test_09_new_session_creation_without_ids(self):
        """
        Test 9: Verify new session creation when no thread/run IDs provided.
        
        Business Impact: Allows users to start new conversations.
        Golden Path: Essential for new user interactions.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Start new conversation"},
            thread_id=None
        )
        message.thread_id = None  # Explicitly no thread ID
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify context creation allows None values for new sessions
                                mock_get_context.assert_called()
                                call_args = mock_get_context.call_args
                                assert call_args[1]['user_id'] == self.test_user_id
                                # Thread ID and run ID should be None or handled by session manager

    async def test_10_processing_statistics_tracking(self):
        """
        Test 10: Verify processing statistics are correctly tracked.
        
        Business Impact: Enables monitoring and performance optimization.
        Golden Path: Supports operational visibility.
        """
        messages = [
            await self.create_test_message(MessageType.START_AGENT, {"user_request": "Start 1"}),
            await self.create_test_message(MessageType.USER_MESSAGE, {"message": "Message 1"}),
            await self.create_test_message(MessageType.CHAT, {"content": "Chat 1"}),
            await self.create_test_message(MessageType.USER_MESSAGE, {"message": "Message 2"}),
        ]
        
        initial_stats = self.agent_handler.get_stats()
        
        for message in messages:
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                            with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                
                                # Setup mocks
                                mock_get_context.return_value = self.mock_user_context
                                mock_create_ws.return_value = self.mock_websocket_manager
                                
                                async def db_generator():
                                    yield self.mock_db_session
                                mock_get_db.return_value = db_generator()
                                
                                mock_supervisor = AsyncMock()
                                mock_get_supervisor.return_value = mock_supervisor
                                
                                mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                
                                with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                    mock_mhs_instance = AsyncMock()
                                    mock_mhs_class.return_value = mock_mhs_instance
                                    
                                    # Execute test
                                    await self.agent_handler.handle_message(
                                        self.test_user_id, self.mock_websocket, message
                                    )
        
        # Verify statistics were updated
        final_stats = self.agent_handler.get_stats()
        assert final_stats["messages_processed"] == initial_stats["messages_processed"] + 4
        assert final_stats["start_agent_requests"] == initial_stats["start_agent_requests"] + 1
        assert final_stats["user_messages"] == initial_stats["user_messages"] + 2
        assert final_stats["chat_messages"] == initial_stats["chat_messages"] + 1
        assert final_stats["last_processed_time"] is not None

    # ========================================================================
    # PAYLOAD VALIDATION TESTS (Tests 11-15)
    # ========================================================================

    async def test_11_start_agent_payload_validation_success(self):
        """
        Test 11: Verify START_AGENT payload validation for valid payloads.
        
        Business Impact: Ensures only valid agent requests are processed.
        Golden Path: Prevents malformed agent startup requests.
        """
        valid_payloads = [
            {"user_request": "Simple request"},
            {"user_request": "Request with context", "context": {"key": "value"}},
            {"user_request": "Request with thread", "thread_id": "thread_123"},
            {"user_request": "Full payload", "thread_id": "thread_123", "run_id": "run_456", "context": {"test": True}},
        ]
        
        for payload in valid_payloads:
            with self.subTest(payload=payload):
                message = await self.create_test_message(MessageType.START_AGENT, payload)
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                    with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                                with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                    
                                    # Setup mocks
                                    mock_get_context.return_value = self.mock_user_context
                                    mock_create_ws.return_value = self.mock_websocket_manager
                                    
                                    async def db_generator():
                                        yield self.mock_db_session
                                    mock_get_db.return_value = db_generator()
                                    
                                    mock_supervisor = AsyncMock()
                                    mock_get_supervisor.return_value = mock_supervisor
                                    
                                    mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                    
                                    with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                        mock_mhs_instance = AsyncMock()
                                        mock_mhs_class.return_value = mock_mhs_instance
                                        
                                        # Execute test
                                        result = await self.agent_handler.handle_message(
                                            self.test_user_id, self.mock_websocket, message
                                        )
                                        
                                        # Verify success for valid payload
                                        assert result is True
                                        mock_mhs_instance.handle_start_agent.assert_called_once()

    async def test_12_start_agent_payload_validation_failure(self):
        """
        Test 12: Verify START_AGENT payload validation for invalid payloads.
        
        Business Impact: Prevents processing of malformed requests.
        Golden Path: Ensures system stability with invalid input.
        """
        invalid_payloads = [
            {},  # Empty payload
            {"thread_id": "thread_123"},  # Missing user_request
            {"user_request": ""},  # Empty user_request
            {"user_request": None},  # Null user_request
            {"user_request": "   "},  # Whitespace-only user_request
        ]
        
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                message = await self.create_test_message(MessageType.START_AGENT, payload)
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                    with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                                with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                    
                                    # Setup mocks
                                    mock_get_context.return_value = self.mock_user_context
                                    mock_create_ws.return_value = self.mock_websocket_manager
                                    
                                    async def db_generator():
                                        yield self.mock_db_session
                                    mock_get_db.return_value = db_generator()
                                    
                                    mock_supervisor = AsyncMock()
                                    mock_get_supervisor.return_value = mock_supervisor
                                    
                                    mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                    
                                    with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                        mock_mhs_instance = AsyncMock()
                                        mock_mhs_class.return_value = mock_mhs_instance
                                        
                                        # Execute test
                                        result = await self.agent_handler.handle_message(
                                            self.test_user_id, self.mock_websocket, message
                                        )
                                        
                                        # Verify failure for invalid payload
                                        assert result is False
                                        mock_mhs_instance.handle_start_agent.assert_not_called()

    async def test_13_user_message_payload_validation_success(self):
        """
        Test 13: Verify USER_MESSAGE/CHAT payload validation for valid payloads.
        
        Business Impact: Ensures user messages are properly processed.
        Golden Path: Core chat functionality validation.
        """
        valid_payloads = [
            {"message": "Hello world"},
            {"content": "Content field"},
            {"text": "Text field"},
            {"message": "Priority", "content": "Lower", "text": "Lowest"},  # Field precedence
            {"message": "Message with extras", "extra_field": "allowed"},
        ]
        
        for message_type in [MessageType.USER_MESSAGE, MessageType.CHAT]:
            for payload in valid_payloads:
                with self.subTest(message_type=message_type, payload=payload):
                    message = await self.create_test_message(message_type, payload)
                    
                    with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                                    with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                        
                                        # Setup mocks
                                        mock_get_context.return_value = self.mock_user_context
                                        mock_create_ws.return_value = self.mock_websocket_manager
                                        
                                        async def db_generator():
                                            yield self.mock_db_session
                                        mock_get_db.return_value = db_generator()
                                        
                                        mock_supervisor = AsyncMock()
                                        mock_get_supervisor.return_value = mock_supervisor
                                        
                                        mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                        
                                        with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                            mock_mhs_instance = AsyncMock()
                                            mock_mhs_class.return_value = mock_mhs_instance
                                            
                                            # Execute test
                                            result = await self.agent_handler.handle_message(
                                                self.test_user_id, self.mock_websocket, message
                                            )
                                            
                                            # Verify success for valid payload
                                            assert result is True
                                            mock_mhs_instance.handle_user_message.assert_called_once()

    async def test_14_user_message_payload_validation_failure(self):
        """
        Test 14: Verify USER_MESSAGE/CHAT payload validation for invalid payloads.
        
        Business Impact: Prevents processing of empty or malformed messages.
        Golden Path: Maintains chat quality by rejecting invalid input.
        """
        invalid_payloads = [
            {},  # Empty payload
            {"extra_field": "no_content"},  # No content fields
            {"message": "", "content": "", "text": ""},  # All empty
            {"message": None, "content": None, "text": None},  # All null
            {"message": "   ", "content": "  ", "text": "   "},  # All whitespace
        ]
        
        for message_type in [MessageType.USER_MESSAGE, MessageType.CHAT]:
            for payload in invalid_payloads:
                with self.subTest(message_type=message_type, payload=payload):
                    message = await self.create_test_message(message_type, payload)
                    
                    with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                        with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                                    with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                        
                                        # Setup mocks
                                        mock_get_context.return_value = self.mock_user_context
                                        mock_create_ws.return_value = self.mock_websocket_manager
                                        
                                        async def db_generator():
                                            yield self.mock_db_session
                                        mock_get_db.return_value = db_generator()
                                        
                                        mock_supervisor = AsyncMock()
                                        mock_get_supervisor.return_value = mock_supervisor
                                        
                                        mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                        
                                        with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                            mock_mhs_instance = AsyncMock()
                                            mock_mhs_class.return_value = mock_mhs_instance
                                            
                                            # Execute test
                                            result = await self.agent_handler.handle_message(
                                                self.test_user_id, self.mock_websocket, message
                                            )
                                            
                                            # Verify failure for invalid payload
                                            assert result is False
                                            mock_mhs_instance.handle_user_message.assert_not_called()

    async def test_15_message_field_precedence_validation(self):
        """
        Test 15: Verify message field precedence (message > content > text).
        
        Business Impact: Ensures consistent content extraction logic.
        Golden Path: Reliable message processing regardless of field name.
        """
        test_cases = [
            ({"message": "Message field"}, "message"),
            ({"content": "Content field"}, "content"),
            ({"text": "Text field"}, "text"),
            ({"message": "Priority", "content": "Secondary"}, "message"),
            ({"content": "Primary", "text": "Secondary"}, "content"),
            ({"message": "", "content": "Fallback"}, "content"),
        ]
        
        for payload, expected_field in test_cases:
            with self.subTest(payload=payload, expected_field=expected_field):
                message = await self.create_test_message(MessageType.USER_MESSAGE, payload)
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                    with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                                with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                    
                                    # Setup mocks
                                    mock_get_context.return_value = self.mock_user_context
                                    mock_create_ws.return_value = self.mock_websocket_manager
                                    
                                    async def db_generator():
                                        yield self.mock_db_session
                                    mock_get_db.return_value = db_generator()
                                    
                                    mock_supervisor = AsyncMock()
                                    mock_get_supervisor.return_value = mock_supervisor
                                    
                                    mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                    
                                    with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                        mock_mhs_instance = AsyncMock()
                                        mock_mhs_class.return_value = mock_mhs_instance
                                        
                                        # Execute test
                                        result = await self.agent_handler.handle_message(
                                            self.test_user_id, self.mock_websocket, message
                                        )
                                        
                                        # Verify success and that correct payload was passed
                                        assert result is True
                                        mock_mhs_instance.handle_user_message.assert_called_once()
                                        
                                        # Verify the original payload was passed (precedence handled in handler)
                                        call_args = mock_mhs_instance.handle_user_message.call_args
                                        assert call_args[1]['payload'] == payload

    # ========================================================================
    # ERROR HANDLING AND RECOVERY TESTS (Tests 16-20)
    # ========================================================================

    async def test_16_handle_message_handler_service_error(self):
        """
        Test 16: Verify error handling when MessageHandlerService raises exception.
        
        Business Impact: Ensures system stability during processing errors.
        Golden Path: Graceful degradation when agent processing fails.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "This will cause an error"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_instance.handle_start_agent.side_effect = Exception("Processing error")
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify error handling
                                assert result is False
                                
                                # Verify error stats updated
                                stats = self.agent_handler.get_stats()
                                assert stats["errors"] >= 1
                                
                                # Verify error notification attempted
                                self.mock_websocket_manager.send_error.assert_called_once()
                                error_call = self.mock_websocket_manager.send_error.call_args
                                assert error_call[0][0] == self.test_user_id
                                assert "Failed to process" in error_call[0][1]

    async def test_17_handle_database_session_error(self):
        """
        Test 17: Verify error handling when database session fails.
        
        Business Impact: Maintains service availability during DB issues.
        Golden Path: Graceful degradation when database unavailable.
        """
        message = await self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "Database test message"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    
                    # Setup mocks
                    mock_get_context.return_value = self.mock_user_context
                    mock_create_ws.return_value = self.mock_websocket_manager
                    
                    # Make database session fail
                    async def failing_db_generator():
                        raise Exception("Database connection failed")
                        yield  # This yield is never reached
                    mock_get_db.return_value = failing_db_generator()
                    
                    # Execute test
                    result = await self.agent_handler.handle_message(
                        self.test_user_id, self.mock_websocket, message
                    )
                    
                    # Verify error handling
                    assert result is False
                    
                    # Verify error stats updated
                    stats = self.agent_handler.get_stats()
                    assert stats["errors"] >= 1

    async def test_18_handle_websocket_manager_creation_error(self):
        """
        Test 18: Verify error handling when WebSocket manager creation fails.
        
        Business Impact: Handles WebSocket infrastructure failures gracefully.
        Golden Path: System stability when WebSocket services unavailable.
        """
        message = await self.create_test_message(
            MessageType.CHAT,
            {"content": "WebSocket manager test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                
                # Setup mocks
                mock_get_context.return_value = self.mock_user_context
                mock_create_ws.side_effect = Exception("WebSocket manager creation failed")
                
                # Execute test
                result = await self.agent_handler.handle_message(
                    self.test_user_id, self.mock_websocket, message
                )
                
                # Verify error handling
                assert result is False
                
                # Verify error stats updated
                stats = self.agent_handler.get_stats()
                assert stats["errors"] >= 1

    async def test_19_handle_supervisor_creation_error(self):
        """
        Test 19: Verify error handling when supervisor creation fails.
        
        Business Impact: Graceful degradation when agent supervisor unavailable.
        Golden Path: System stability when core agent services fail.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Supervisor creation test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            # Make supervisor creation fail
                            mock_get_supervisor.side_effect = Exception("Supervisor creation failed")
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            # Execute test
                            result = await self.agent_handler.handle_message(
                                self.test_user_id, self.mock_websocket, message
                            )
                            
                            # Verify error handling
                            assert result is False
                            
                            # Verify error stats updated
                            stats = self.agent_handler.get_stats()
                            assert stats["errors"] >= 1

    async def test_20_handle_websocket_error_notification_failure(self):
        """
        Test 20: Verify graceful handling when error notification fails.
        
        Business Impact: Prevents cascade failures in error scenarios.
        Golden Path: System stability when even error reporting fails.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Error notification test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            # Make both message handling and error notification fail
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_instance.handle_start_agent.side_effect = Exception("Primary error")
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                self.mock_websocket_manager.send_error.side_effect = Exception("Notification failed")
                                
                                # Execute test - should not raise exception despite both failures
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify error handling doesn't cascade
                                assert result is False
                                
                                # Verify error stats updated for primary error
                                stats = self.agent_handler.get_stats()
                                assert stats["errors"] >= 1

    # ========================================================================
    # CONCURRENT PROCESSING AND EDGE CASES (Tests 21-25)
    # ========================================================================

    async def test_21_concurrent_message_processing_isolation(self):
        """
        Test 21: Verify isolation between concurrent message processing.
        
        Business Impact: Multi-user system integrity under load.
        Golden Path: Ensures users don't interfere with each other.
        """
        user1_id = "user_1"
        user2_id = "user_2"
        
        message1 = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "User 1 request"},
            user_id=user1_id
        )
        message2 = await self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "User 2 message"},
            user_id=user2_id
        )
        
        # Create separate contexts for each user
        mock_user_context_1 = Mock(spec=UserExecutionContext)
        mock_user_context_1.user_id = user1_id
        mock_user_context_1.thread_id = "thread_1"
        mock_user_context_1.run_id = "run_1"
        
        mock_user_context_2 = Mock(spec=UserExecutionContext)
        mock_user_context_2.user_id = user2_id
        mock_user_context_2.thread_id = "thread_2"
        mock_user_context_2.run_id = "run_2"
        
        # Track which user context is returned based on user_id
        def get_context_by_user(user_id, **kwargs):
            return mock_user_context_1 if user_id == user1_id else mock_user_context_2
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.side_effect = get_context_by_user
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            # Create separate WebSocket contexts for each user
                            mock_ws_context_1 = Mock(spec=WebSocketContext)
                            mock_ws_context_1.user_id = user1_id
                            mock_ws_context_1.update_activity = Mock()
                            mock_ws_context_1.validate_for_message_processing = Mock()
                            
                            mock_ws_context_2 = Mock(spec=WebSocketContext)
                            mock_ws_context_2.user_id = user2_id
                            mock_ws_context_2.update_activity = Mock()
                            mock_ws_context_2.validate_for_message_processing = Mock()
                            
                            def create_ws_context_by_user(websocket, user_id, **kwargs):
                                return mock_ws_context_1 if user_id == user1_id else mock_ws_context_2
                                
                            mock_ws_context_class.create_for_user.side_effect = create_ws_context_by_user
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Process both messages concurrently
                                results = await asyncio.gather(
                                    self.agent_handler.handle_message(user1_id, self.mock_websocket, message1),
                                    self.agent_handler.handle_message(user2_id, self.mock_websocket, message2),
                                    return_exceptions=True
                                )
                                
                                # Verify both processed successfully
                                assert results[0] is True
                                assert results[1] is True
                                
                                # Verify correct handlers called for each message type
                                assert mock_mhs_instance.handle_start_agent.call_count >= 1
                                assert mock_mhs_instance.handle_user_message.call_count >= 1
                                
                                # Verify isolation by checking user contexts were called correctly
                                context_calls = mock_get_context.call_args_list
                                user_ids_called = [call[1]['user_id'] for call in context_calls]
                                assert user1_id in user_ids_called
                                assert user2_id in user_ids_called

    async def test_22_unsupported_message_type_handling(self):
        """
        Test 22: Verify handling of unsupported message types.
        
        Business Impact: System stability with unknown message types.
        Golden Path: Graceful handling of protocol extensions.
        """
        # Create message with unsupported type (we'll manually set it)
        message = await self.create_test_message(
            MessageType.HEARTBEAT,  # Not supported by AgentHandler
            {"heartbeat": "ping"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify unsupported message type is rejected gracefully
                                assert result is False
                                
                                # Verify no handler methods were called
                                mock_mhs_instance.handle_start_agent.assert_not_called()
                                mock_mhs_instance.handle_user_message.assert_not_called()

    async def test_23_connection_id_fallback_generation(self):
        """
        Test 23: Verify connection ID fallback generation when not found.
        
        Business Impact: Resilience when WebSocket connection tracking fails.
        Golden Path: System continues working even with connection ID issues.
        """
        message = await self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "Connection ID fallback test"}
        )
        
        # Mock WebSocket manager that can't find connection ID
        mock_websocket_manager_no_conn = AsyncMock()
        mock_websocket_manager_no_conn.get_connection_id_by_websocket.return_value = None
        mock_websocket_manager_no_conn.update_connection_thread = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            with patch('shared.id_generation.UnifiedIdGenerator.generate_websocket_connection_id') as mock_generate_id:
                                
                                # Setup mocks
                                mock_get_context.return_value = self.mock_user_context
                                mock_create_ws.return_value = mock_websocket_manager_no_conn
                                
                                async def db_generator():
                                    yield self.mock_db_session
                                mock_get_db.return_value = db_generator()
                                
                                mock_supervisor = AsyncMock()
                                mock_get_supervisor.return_value = mock_supervisor
                                
                                mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                
                                fallback_connection_id = "fallback_conn_123"
                                mock_generate_id.return_value = fallback_connection_id
                                
                                with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                    mock_mhs_instance = AsyncMock()
                                    mock_mhs_class.return_value = mock_mhs_instance
                                    
                                    # Execute test
                                    result = await self.agent_handler.handle_message(
                                        self.test_user_id, self.mock_websocket, message
                                    )
                                    
                                    # Verify success despite missing connection ID
                                    assert result is True
                                    
                                    # Verify fallback connection ID was generated
                                    mock_generate_id.assert_called_with(self.test_user_id)
                                    
                                    # Verify no update_connection_thread called (no connection ID found)
                                    mock_websocket_manager_no_conn.update_connection_thread.assert_not_called()

    async def test_24_large_payload_handling(self):
        """
        Test 24: Verify handling of large message payloads.
        
        Business Impact: System stability with complex user requests.
        Golden Path: Supports rich user interactions and complex agent requests.
        """
        # Create large payload with complex data structures
        large_payload = {
            "user_request": "Analyze this large dataset",
            "context": {
                "data": list(range(1000)),  # Large list
                "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},  # Large dict
                "nested": {
                    "deep": {
                        "structure": {
                            "with": "complex data",
                            "arrays": [{"id": i, "value": f"item_{i}"} for i in range(50)]
                        }
                    }
                }
            },
            "settings": {
                "processing_options": ["option_" + str(i) for i in range(50)],
                "parameters": {f"param_{i}": i * 2.5 for i in range(100)}
            }
        }
        
        message = await self.create_test_message(MessageType.START_AGENT, large_payload)
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                result = await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify large payload handled successfully
                                assert result is True
                                
                                # Verify handler was called with complete payload
                                mock_mhs_instance.handle_start_agent.assert_called_once()
                                call_args = mock_mhs_instance.handle_start_agent.call_args
                                passed_payload = call_args[1]['payload']
                                assert passed_payload == large_payload
                                assert len(passed_payload["context"]["data"]) == 1000

    async def test_25_unicode_and_special_characters_handling(self):
        """
        Test 25: Verify handling of Unicode and special characters in messages.
        
        Business Impact: International user support and diverse content.
        Golden Path: System works globally with all character sets.
        """
        unicode_payloads = [
            {"message": "Hello 世界! 🌍 Testing émojis and ñoñó special chars"},
            {"user_request": "Análisis con acentos y ñ, plus some 中文 characters"},
            {"content": "Сообщение на русском языке with مرحبا Arabic"},
            {"text": "Japanese: こんにちは, Korean: 안녕하세요, Thai: สวัสดี"},
            {"message": "Special symbols: ∆≈∞℠™®©¿¡‰"},
            {"user_request": "Code with special chars: function(λ) { return α + β; }"},
        ]
        
        for payload in unicode_payloads:
            with self.subTest(payload=payload):
                message_type = MessageType.START_AGENT if "user_request" in payload else MessageType.USER_MESSAGE
                message = await self.create_test_message(message_type, payload)
                
                with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
                    with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                                with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                                    
                                    # Setup mocks
                                    mock_get_context.return_value = self.mock_user_context
                                    mock_create_ws.return_value = self.mock_websocket_manager
                                    
                                    async def db_generator():
                                        yield self.mock_db_session
                                    mock_get_db.return_value = db_generator()
                                    
                                    mock_supervisor = AsyncMock()
                                    mock_get_supervisor.return_value = mock_supervisor
                                    
                                    mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                    
                                    with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                        mock_mhs_instance = AsyncMock()
                                        mock_mhs_class.return_value = mock_mhs_instance
                                        
                                        # Execute test
                                        result = await self.agent_handler.handle_message(
                                            self.test_user_id, self.mock_websocket, message
                                        )
                                        
                                        # Verify Unicode payload handled successfully
                                        assert result is True
                                        
                                        # Verify correct handler called
                                        if message_type == MessageType.START_AGENT:
                                            mock_mhs_instance.handle_start_agent.assert_called_once()
                                        else:
                                            mock_mhs_instance.handle_user_message.assert_called_once()

    # ========================================================================
    # WEBSOCKET EVENT EMISSION TESTS (Tests 26-30)
    # ========================================================================

    async def test_26_websocket_context_validation_before_processing(self):
        """
        Test 26: Verify WebSocket context validation before message processing.
        
        Business Impact: Ensures context integrity before agent execution.
        Golden Path: Validates user session is ready for processing.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Context validation test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify context validation methods were called
                                self.mock_websocket_context.update_activity.assert_called_once()
                                self.mock_websocket_context.validate_for_message_processing.assert_called_once()

    async def test_27_websocket_thread_association_update(self):
        """
        Test 27: Verify WebSocket thread association is updated correctly.
        
        Business Impact: Ensures agent events route to correct user sessions.
        Golden Path: Critical for routing agent responses to right conversations.
        """
        thread_id = "specific_thread_456"
        message = await self.create_test_message(
            MessageType.USER_MESSAGE,
            {"message": "Thread association test", "thread_id": thread_id},
            thread_id=thread_id
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify thread association was updated
                                self.mock_websocket_manager.update_connection_thread.assert_called_with(
                                    self.test_connection_id, thread_id
                                )

    async def test_28_websocket_manager_factory_integration(self):
        """
        Test 28: Verify WebSocket manager factory integration.
        
        Business Impact: Ensures proper WebSocket manager lifecycle.
        Golden Path: WebSocket services are properly initialized per user.
        """
        message = await self.create_test_message(
            MessageType.CHAT,
            {"content": "Manager factory test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify WebSocket manager was created with correct context
                                mock_create_ws.assert_called_once_with(self.mock_user_context)

    async def test_29_supervisor_factory_integration_v3_pattern(self):
        """
        Test 29: Verify supervisor factory integration for V3 clean pattern.
        
        Business Impact: Ensures proper agent supervisor initialization.
        Golden Path: Agent execution environment is correctly established.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {"user_request": "Supervisor factory test"}
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            
                            # Setup mocks
                            mock_get_context.return_value = self.mock_user_context
                            mock_create_ws.return_value = self.mock_websocket_manager
                            
                            async def db_generator():
                                yield self.mock_db_session
                            mock_get_db.return_value = db_generator()
                            
                            mock_supervisor = AsyncMock()
                            mock_get_supervisor.return_value = mock_supervisor
                            
                            mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                            
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                mock_mhs_instance = AsyncMock()
                                mock_mhs_class.return_value = mock_mhs_instance
                                
                                # Execute test
                                await self.agent_handler.handle_message(
                                    self.test_user_id, self.mock_websocket, message
                                )
                                
                                # Verify V3 supervisor factory was called
                                mock_get_supervisor.assert_called_once()
                                call_args = mock_get_supervisor.call_args
                                assert call_args[1]['context'] == self.mock_websocket_context
                                assert call_args[1]['db_session'] == self.mock_db_session
                                assert 'app_state' in call_args[1]  # App state passed for bridge access

    async def test_30_comprehensive_integration_golden_path(self):
        """
        Test 30: Comprehensive integration test for complete golden path flow.
        
        Business Impact: End-to-end validation of critical user flow.
        Golden Path: Validates complete user message → agent execution pipeline.
        """
        message = await self.create_test_message(
            MessageType.START_AGENT,
            {
                "user_request": "Perform comprehensive analysis of business metrics",
                "thread_id": "golden_path_thread",
                "run_id": "golden_path_run",
                "context": {
                    "priority": "high",
                    "department": "analytics",
                    "user_role": "manager"
                }
            },
            thread_id="golden_path_thread"
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_ws:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        with patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
                            with patch('netra_backend.app.websocket_core.agent_handler.ThreadService') as mock_thread_service_class:
                                
                                # Setup mocks
                                mock_get_context.return_value = self.mock_user_context
                                mock_create_ws.return_value = self.mock_websocket_manager
                                
                                async def db_generator():
                                    yield self.mock_db_session
                                mock_get_db.return_value = db_generator()
                                
                                mock_supervisor = AsyncMock()
                                mock_get_supervisor.return_value = mock_supervisor
                                
                                mock_ws_context_class.create_for_user.return_value = self.mock_websocket_context
                                
                                mock_thread_service = Mock()
                                mock_thread_service_class.return_value = mock_thread_service
                                
                                with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_mhs_class:
                                    mock_mhs_instance = AsyncMock()
                                    mock_mhs_class.return_value = mock_mhs_instance
                                    
                                    # Execute test
                                    result = await self.agent_handler.handle_message(
                                        self.test_user_id, self.mock_websocket, message
                                    )
                                    
                                    # COMPREHENSIVE GOLDEN PATH VALIDATIONS
                                    
                                    # 1. Overall success
                                    assert result is True, "Golden path should succeed"
                                    
                                    # 2. User context created with session continuity
                                    mock_get_context.assert_called_once()
                                    context_call = mock_get_context.call_args
                                    assert context_call[1]['user_id'] == self.test_user_id
                                    assert context_call[1]['thread_id'] == "golden_path_thread"
                                    assert context_call[1]['run_id'] == "golden_path_run"
                                    
                                    # 3. WebSocket manager created for user
                                    mock_create_ws.assert_called_once_with(self.mock_user_context)
                                    
                                    # 4. Connection ID retrieved and thread association updated
                                    self.mock_websocket_manager.get_connection_id_by_websocket.assert_called_with(self.mock_websocket)
                                    self.mock_websocket_manager.update_connection_thread.assert_called_with(
                                        self.test_connection_id, "golden_path_thread"
                                    )
                                    
                                    # 5. WebSocket context created properly
                                    mock_ws_context_class.create_for_user.assert_called_once()
                                    ws_context_call = mock_ws_context_class.create_for_user.call_args
                                    assert ws_context_call[1]['websocket'] == self.mock_websocket
                                    assert ws_context_call[1]['user_id'] == self.test_user_id
                                    assert ws_context_call[1]['thread_id'] == self.mock_user_context.thread_id
                                    assert ws_context_call[1]['run_id'] == self.mock_user_context.run_id
                                    
                                    # 6. WebSocket context validation performed
                                    self.mock_websocket_context.update_activity.assert_called_once()
                                    self.mock_websocket_context.validate_for_message_processing.assert_called_once()
                                    
                                    # 7. Database session acquired properly
                                    mock_get_db.assert_called_once()
                                    
                                    # 8. Supervisor created with correct context
                                    mock_get_supervisor.assert_called_once()
                                    supervisor_call = mock_get_supervisor.call_args
                                    assert supervisor_call[1]['context'] == self.mock_websocket_context
                                    assert supervisor_call[1]['db_session'] == self.mock_db_session
                                    assert 'app_state' in supervisor_call[1]
                                    
                                    # 9. Thread service initialized
                                    mock_thread_service_class.assert_called_once()
                                    
                                    # 10. Message handler service created with supervisor and thread service
                                    mock_mhs_class.assert_called_once()
                                    mhs_call = mock_mhs_class.call_args
                                    assert mhs_call[0][0] == mock_supervisor  # supervisor
                                    assert mhs_call[0][1] == mock_thread_service  # thread_service
                                    
                                    # 11. Agent handler called with correct parameters
                                    mock_mhs_instance.handle_start_agent.assert_called_once()
                                    handler_call = mock_mhs_instance.handle_start_agent.call_args
                                    assert handler_call[1]['user_id'] == self.test_user_id
                                    assert handler_call[1]['payload'] == message.payload
                                    assert handler_call[1]['db_session'] == self.mock_db_session
                                    assert handler_call[1]['websocket'] == self.mock_websocket
                                    
                                    # 12. Processing statistics updated
                                    stats = self.agent_handler.get_stats()
                                    assert stats["messages_processed"] >= 1
                                    assert stats["start_agent_requests"] >= 1
                                    assert stats["last_processed_time"] is not None
                                    
                                    # 13. No errors recorded
                                    initial_errors = stats.get("errors", 0)
                                    assert initial_errors == 0, "Golden path should not record errors"

    # ========================================================================
    # HELPER METHODS AND UTILITIES
    # ========================================================================
    
    def create_mock_websocket_context(self, user_id: str, thread_id: str, run_id: str) -> Mock:
        """Helper to create mock WebSocket context."""
        context = Mock(spec=WebSocketContext)
        context.user_id = user_id
        context.thread_id = thread_id  
        context.run_id = run_id
        context.connection_id = f"conn_{user_id}"
        context.update_activity = Mock()
        context.validate_for_message_processing = Mock()
        return context
    
    def create_mock_user_context(self, user_id: str, thread_id: str, run_id: str) -> Mock:
        """Helper to create mock user execution context."""
        context = Mock(spec=UserExecutionContext)
        context.user_id = user_id
        context.thread_id = thread_id
        context.run_id = run_id
        context.request_id = f"req_{user_id}"
        context.websocket_connection_id = f"conn_{user_id}"
        return context
    
    async def verify_websocket_event_emission(self, expected_events: List[str]):
        """Helper to verify WebSocket events were emitted."""
        # This would integrate with actual WebSocket event verification
        # For now, we verify through manager calls
        self.mock_websocket_manager.send_error.assert_not_called()
        
    def assert_processing_stats_incremented(self, 
                                          expected_total: int = 1,
                                          expected_start_agent: int = 0,
                                          expected_user_messages: int = 0,
                                          expected_chat_messages: int = 0):
        """Helper to assert processing statistics."""
        stats = self.agent_handler.get_stats()
        assert stats["messages_processed"] >= expected_total
        
        if expected_start_agent > 0:
            assert stats["start_agent_requests"] >= expected_start_agent
        if expected_user_messages > 0:
            assert stats["user_messages"] >= expected_user_messages
        if expected_chat_messages > 0:
            assert stats["chat_messages"] >= expected_chat_messages

# ============================================================================
# TEST CONFIGURATION AND MARKERS
# ============================================================================

# Mark all tests as unit tests
pytestmark = pytest.mark.unit

# Test class configuration
TestAgentHandlerComprehensive.__test__ = True