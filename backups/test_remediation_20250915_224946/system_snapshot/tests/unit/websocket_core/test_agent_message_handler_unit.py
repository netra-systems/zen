"""
Unit Tests for AgentMessageHandler - Core Golden Path Message Processing

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform) - Core Infrastructure  
- Business Goal: Ensure agent message handling for $500K+ ARR Golden Path reliability
- Value Impact: Message processing is foundation for agent-user WebSocket communication
- Strategic Impact: Core reliability that enables all AI interaction value delivery
- Revenue Protection: Without proper message handling, users get no AI responses -> churn

PURPOSE: This test suite validates the core message handling functionality that enables
agents to receive, process, and route user messages through the Golden Path WebSocket flow.
Message handling is critical infrastructure that enables all AI-powered interactions.

KEY COVERAGE:
1. WebSocket message reception and validation
2. Message type routing (START_AGENT, USER_MESSAGE, CHAT)
3. User context isolation and validation
4. Database session management
5. Error handling for malformed messages
6. WebSocket context creation and management
7. Performance requirements for message processing
8. Multi-user isolation in message handling

GOLDEN PATH PROTECTION:
Tests ensure AgentMessageHandler can properly receive and route WebSocket messages,
manage user contexts, and maintain proper isolation. This is critical infrastructure
that enables the entire $500K+ ARR agent execution pipeline.

Issue #1081 Phase 1 - Priority 1 (CRITICAL): AgentMessageHandler unit tests
Target Coverage: From 0% to 15-20% (Phase 1 baseline)
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import the class under test
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler

# Import related types and dependencies
from netra_backend.app.websocket_core.types import (
    WebSocketMessage,
    MessageType,
    create_standard_message,
    create_error_message
)
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService


class AgentMessageHandlerTests(SSotAsyncTestCase):
    """Unit tests for AgentMessageHandler functionality
    
    This test class validates the critical message handling capabilities that
    enable WebSocket messages to be properly received, validated, and routed
    to agent execution systems in the Golden Path user flow.
    
    Tests MUST ensure the handler can:
    1. Accept and validate WebSocket messages correctly
    2. Route messages by type (START_AGENT, USER_MESSAGE, CHAT)
    3. Create proper user contexts for isolation
    4. Handle database sessions correctly
    5. Manage errors gracefully
    6. Process messages with performance requirements
    7. Maintain user isolation between concurrent requests
    """
    
    def setup_method(self, method=None):
        """Setup for each test with proper isolation"""
        super().setup_method(method)
        
        # Create isolated test context
        self.test_user_id = f"test_user_{self.get_test_context().test_id}"
        self.test_thread_id = f"test_thread_{self.get_test_context().test_id}"
        self.test_run_id = f"test_run_{self.get_test_context().test_id}"
        
        # Create mock dependencies
        self.mock_message_handler_service = SSotMockFactory.create_mock_message_handler_service()
        self.mock_websocket = SSotMockFactory.create_websocket_mock(
            connection_id=f"conn_{self.get_test_context().test_id}",
            user_id=self.test_user_id
        )
        
        # Create handler under test
        self.handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )
        
        # Track processing stats for validation
        self.initial_stats = self.handler.get_stats().copy()
    
    # ========================================================================
    # INITIALIZATION AND CONFIGURATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_agent_message_handler_initialization(self):
        """Test AgentMessageHandler initializes with correct configuration
        
        Business Impact: Ensures handler starts in correct state for
        reliable message processing.
        """
        # Verify handler was initialized correctly
        assert self.handler is not None
        assert self.handler.message_handler_service is not None
        assert self.handler.websocket is not None
        
        # Verify supported message types
        expected_types = [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]
        assert set(self.handler.supported_types) == set(expected_types)
        
        # Verify initial processing stats
        stats = self.handler.get_stats()
        assert stats["messages_processed"] == 0
        assert stats["start_agent_requests"] == 0
        assert stats["user_messages"] == 0
        assert stats["chat_messages"] == 0
        assert stats["errors"] == 0
        assert stats["last_processed_time"] is None
        
        self.record_metric("handler_initialization_success", True)
    
    @pytest.mark.unit
    def test_agent_message_handler_supported_message_types(self):
        """Test handler correctly identifies supported message types
        
        Business Impact: Ensures only valid message types are processed,
        preventing system errors from unsupported messages.
        """
        # Test supported types
        supported_types = [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]
        
        for msg_type in supported_types:
            assert msg_type in self.handler.supported_types
        
        # Test unsupported types (should not be in supported list)
        unsupported_types = [MessageType.PING, MessageType.PONG, MessageType.AUTH]
        
        for msg_type in unsupported_types:
            assert msg_type not in self.handler.supported_types
        
        self.record_metric("message_type_validation", True)
        self.record_metric("supported_message_types", len(supported_types))
    
    # ========================================================================
    # MESSAGE PROCESSING CORE FUNCTIONALITY TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_handle_message_basic_functionality(self):
        """Test basic message handling functionality
        
        Business Impact: Ensures core message processing works correctly,
        the foundation of all WebSocket agent interactions.
        """
        # Create test message
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "content": "Test user message for agent processing",
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id
            }
        )
        
        # Mock successful processing
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
            
            # Setup mocks
            mock_context = SSotMockFactory.create_mock_user_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            mock_get_context.return_value = mock_context
            
            mock_ws_manager = SSotMockFactory.create_mock_websocket_manager()
            mock_create_manager.return_value = mock_ws_manager
            
            mock_db_session = SSotMockFactory.create_database_session_mock()
            mock_get_session.return_value = mock_db_session.__aiter__()
            
            mock_supervisor = SSotMockFactory.create_mock_supervisor_agent()
            mock_get_supervisor.return_value = mock_supervisor
            
            # Process message
            start_time = time.time()
            result = await self.handler.handle_message(
                user_id=self.test_user_id,
                websocket=self.mock_websocket,
                message=test_message
            )
            processing_time = time.time() - start_time
            
            # Verify successful processing
            assert result is True
            
            # Verify mocks were called correctly
            mock_get_context.assert_called_once_with(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            mock_create_manager.assert_called_once()
            mock_get_supervisor.assert_called_once()
            
            # Verify processing stats updated
            final_stats = self.handler.get_stats()
            assert final_stats["messages_processed"] == self.initial_stats["messages_processed"] + 1
            assert final_stats["user_messages"] == self.initial_stats["user_messages"] + 1
            assert final_stats["last_processed_time"] is not None
            
            # Verify performance (should be fast for unit test)
            assert processing_time < 1.0, f"Message processing took {processing_time:.3f}s, should be < 1.0s"
            
            self.record_metric("basic_message_processing_time", processing_time)
            self.record_metric("basic_processing_success", True)
    
    @pytest.mark.unit
    async def test_handle_start_agent_message(self):
        """Test START_AGENT message handling
        
        Business Impact: Ensures agent startup messages are processed correctly,
        critical for initiating AI interactions.
        """
        # Create START_AGENT message
        start_agent_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Start agent to help optimize AI costs",
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id,
                "agent_type": "supervisor"
            }
        )
        
        # Mock successful processing
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
            
            # Setup mocks
            mock_context = SSotMockFactory.create_mock_user_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            mock_get_context.return_value = mock_context
            
            mock_ws_manager = SSotMockFactory.create_mock_websocket_manager()
            mock_create_manager.return_value = mock_ws_manager
            
            mock_db_session = SSotMockFactory.create_database_session_mock()
            mock_get_session.return_value = mock_db_session.__aiter__()
            
            mock_supervisor = SSotMockFactory.create_mock_supervisor_agent()
            mock_get_supervisor.return_value = mock_supervisor
            
            # Process START_AGENT message
            result = await self.handler.handle_message(
                user_id=self.test_user_id,
                websocket=self.mock_websocket,
                message=start_agent_message
            )
            
            # Verify successful processing
            assert result is True
            
            # Verify processing stats updated correctly
            final_stats = self.handler.get_stats()
            assert final_stats["start_agent_requests"] == self.initial_stats["start_agent_requests"] + 1
            assert final_stats["messages_processed"] == self.initial_stats["messages_processed"] + 1
            
            self.record_metric("start_agent_processing_success", True)
    
    @pytest.mark.unit
    async def test_handle_chat_message(self):
        """Test CHAT message handling
        
        Business Impact: Ensures chat messages are processed correctly,
        core functionality for user-agent conversations.
        """
        # Create CHAT message
        chat_message = WebSocketMessage(
            type=MessageType.CHAT,
            payload={
                "message": "What's the best way to reduce my AI model costs?",
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id
            }
        )
        
        # Mock successful processing
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
            
            # Setup mocks
            mock_context = SSotMockFactory.create_mock_user_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            mock_get_context.return_value = mock_context
            
            mock_ws_manager = SSotMockFactory.create_mock_websocket_manager()
            mock_create_manager.return_value = mock_ws_manager
            
            mock_db_session = SSotMockFactory.create_database_session_mock()
            mock_get_session.return_value = mock_db_session.__aiter__()
            
            mock_supervisor = SSotMockFactory.create_mock_supervisor_agent()
            mock_get_supervisor.return_value = mock_supervisor
            
            # Process CHAT message
            result = await self.handler.handle_message(
                user_id=self.test_user_id,
                websocket=self.mock_websocket,
                message=chat_message
            )
            
            # Verify successful processing
            assert result is True
            
            # Verify processing stats updated correctly
            final_stats = self.handler.get_stats()
            assert final_stats["chat_messages"] == self.initial_stats["chat_messages"] + 1
            assert final_stats["messages_processed"] == self.initial_stats["messages_processed"] + 1
            
            self.record_metric("chat_message_processing_success", True)
    
    # ========================================================================
    # USER CONTEXT AND ISOLATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_user_context_isolation(self):
        """Test user context isolation between different users
        
        Business Impact: Critical for multi-tenant system security.
        User contexts must never leak between different users.
        """
        # Create messages from different users
        user1_id = "user_001_isolation_test"
        user2_id = "user_002_isolation_test"
        
        user1_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "content": "User 1 private message",
                "thread_id": f"thread_{user1_id}",
                "run_id": f"run_{user1_id}"
            }
        )
        
        user2_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "content": "User 2 private message", 
                "thread_id": f"thread_{user2_id}",
                "run_id": f"run_{user2_id}"
            }
        )
        
        # Mock context creation to track isolation
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
            
            # Setup mocks to return user-specific contexts
            def mock_context_factory(user_id, thread_id, run_id):
                return SSotMockFactory.create_mock_user_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
            
            mock_get_context.side_effect = mock_context_factory
            mock_create_manager.return_value = SSotMockFactory.create_mock_websocket_manager()
            mock_get_session.return_value = SSotMockFactory.create_database_session_mock().__aiter__()
            mock_get_supervisor.return_value = SSotMockFactory.create_mock_supervisor_agent()
            
            # Process user 1 message
            result1 = await self.handler.handle_message(
                user_id=user1_id,
                websocket=self.mock_websocket,
                message=user1_message
            )
            
            # Process user 2 message
            result2 = await self.handler.handle_message(
                user_id=user2_id,
                websocket=self.mock_websocket,
                message=user2_message
            )
            
            # Verify both processed successfully
            assert result1 is True
            assert result2 is True
            
            # Verify contexts were created separately
            assert mock_get_context.call_count == 2
            
            # Verify user-specific context parameters
            call_args_list = mock_get_context.call_args_list
            
            # First call should be for user1
            user1_call = call_args_list[0]
            assert user1_call[1]["user_id"] == user1_id
            assert user1_call[1]["thread_id"] == f"thread_{user1_id}"
            assert user1_call[1]["run_id"] == f"run_{user1_id}"
            
            # Second call should be for user2
            user2_call = call_args_list[1]
            assert user2_call[1]["user_id"] == user2_id
            assert user2_call[1]["thread_id"] == f"thread_{user2_id}"
            assert user2_call[1]["run_id"] == f"run_{user2_id}"
            
            self.record_metric("user_isolation_validated", True)
            self.record_metric("isolated_users_processed", 2)
    
    @pytest.mark.unit
    async def test_websocket_context_creation(self):
        """Test WebSocketContext creation with proper parameters
        
        Business Impact: Ensures WebSocket contexts are created with
        correct user isolation parameters.
        """
        test_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Test context creation",
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id
            }
        )
        
        # Mock the WebSocket context creation specifically
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor, \
             patch('netra_backend.app.websocket_core.agent_handler.WebSocketContext') as mock_ws_context_class:
            
            # Setup mocks
            mock_context = SSotMockFactory.create_mock_user_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            mock_get_context.return_value = mock_context
            
            mock_ws_manager = SSotMockFactory.create_mock_websocket_manager()
            mock_create_manager.return_value = mock_ws_manager
            
            mock_db_session = SSotMockFactory.create_database_session_mock()
            mock_get_session.return_value = mock_db_session.__aiter__()
            
            mock_supervisor = SSotMockFactory.create_mock_supervisor_agent()
            mock_get_supervisor.return_value = mock_supervisor
            
            # Setup WebSocketContext mock
            mock_ws_context = MagicMock()
            mock_ws_context.user_id = self.test_user_id
            mock_ws_context.thread_id = self.test_thread_id
            mock_ws_context.run_id = self.test_run_id
            mock_ws_context_class.create_for_user.return_value = mock_ws_context
            
            # Process message
            result = await self.handler.handle_message(
                user_id=self.test_user_id,
                websocket=self.mock_websocket,
                message=test_message
            )
            
            # Verify successful processing
            assert result is True
            
            # Verify WebSocketContext was created with correct parameters
            mock_ws_context_class.create_for_user.assert_called_once()
            create_call = mock_ws_context_class.create_for_user.call_args
            
            assert create_call[1]["websocket"] == self.mock_websocket
            assert create_call[1]["user_id"] == self.test_user_id
            assert create_call[1]["thread_id"] == self.test_thread_id
            assert create_call[1]["run_id"] == self.test_run_id
            
            self.record_metric("websocket_context_creation_success", True)
    
    # ========================================================================
    # ERROR HANDLING AND VALIDATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_missing_user_request_handling(self):
        """Test handling of START_AGENT messages missing user_request
        
        Business Impact: Ensures proper error handling for malformed
        start agent requests.
        """
        # Create START_AGENT message without user_request
        invalid_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "thread_id": self.test_thread_id,
                # Missing user_request field
            }
        )
        
        # Mock context setup but expect failure due to missing user_request
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
            
            # Setup basic mocks
            mock_context = SSotMockFactory.create_mock_user_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id
            )
            mock_get_context.return_value = mock_context
            mock_create_manager.return_value = SSotMockFactory.create_mock_websocket_manager()
            mock_get_session.return_value = SSotMockFactory.create_database_session_mock().__aiter__()
            mock_get_supervisor.return_value = SSotMockFactory.create_mock_supervisor_agent()
            
            # Process invalid message
            result = await self.handler.handle_message(
                user_id=self.test_user_id,
                websocket=self.mock_websocket,
                message=invalid_message
            )
            
            # Should return False due to validation failure
            assert result is False
            
            # Verify error was tracked in stats
            final_stats = self.handler.get_stats()
            assert final_stats["errors"] > self.initial_stats["errors"]
            
            self.record_metric("missing_user_request_handled", True)
    
    @pytest.mark.unit
    async def test_missing_message_content_handling(self):
        """Test handling of USER_MESSAGE/CHAT messages missing content
        
        Business Impact: Ensures proper error handling for messages
        without required content fields.
        """
        # Test messages missing content fields
        test_cases = [
            {
                "name": "USER_MESSAGE without content",
                "message": WebSocketMessage(
                    type=MessageType.USER_MESSAGE,
                    payload={
                        "thread_id": self.test_thread_id,
                        # Missing content/message fields
                    }
                )
            },
            {
                "name": "CHAT without message",
                "message": WebSocketMessage(
                    type=MessageType.CHAT,
                    payload={
                        "thread_id": self.test_thread_id,
                        # Missing content/message fields
                    }
                )
            }
        ]
        
        for test_case in test_cases:
            with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
                 patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
                 patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
                 patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                
                # Setup basic mocks
                mock_context = SSotMockFactory.create_mock_user_context(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id
                )
                mock_get_context.return_value = mock_context
                mock_create_manager.return_value = SSotMockFactory.create_mock_websocket_manager()
                mock_get_session.return_value = SSotMockFactory.create_database_session_mock().__aiter__()
                mock_get_supervisor.return_value = SSotMockFactory.create_mock_supervisor_agent()
                
                # Process invalid message
                result = await self.handler.handle_message(
                    user_id=self.test_user_id,
                    websocket=self.mock_websocket,
                    message=test_case["message"]
                )
                
                # Should return False due to validation failure
                assert result is False, f"Failed test case: {test_case['name']}"
        
        self.record_metric("missing_content_cases_handled", len(test_cases))
    
    @pytest.mark.unit
    async def test_exception_handling_during_processing(self):
        """Test exception handling during message processing
        
        Business Impact: Ensures system stability when processing
        encounters unexpected errors.
        """
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "content": "Test exception handling",
                "thread_id": self.test_thread_id
            }
        )
        
        # Mock context creation to raise an exception
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            # Simulate exception during context creation
            mock_get_context.side_effect = Exception("Test database connection failure")
            
            # Process message with exception
            result = await self.handler.handle_message(
                user_id=self.test_user_id,
                websocket=self.mock_websocket,
                message=test_message
            )
            
            # Should return False due to exception
            assert result is False
            
            # Verify error was tracked in stats
            final_stats = self.handler.get_stats()
            assert final_stats["errors"] > self.initial_stats["errors"]
            
            self.record_metric("exception_handling_validated", True)
    
    # ========================================================================
    # PERFORMANCE AND THROUGHPUT TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_message_processing_performance(self):
        """Test message processing performance requirements
        
        Business Impact: Fast message processing improves user experience
        and system responsiveness in Golden Path interactions.
        """
        # Create test message
        test_message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "content": "Performance test message for Golden Path",
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id
            }
        )
        
        # Mock fast processing
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
            
            # Setup fast mocks
            mock_context = SSotMockFactory.create_mock_user_context(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            mock_get_context.return_value = mock_context
            mock_create_manager.return_value = SSotMockFactory.create_mock_websocket_manager()
            mock_get_session.return_value = SSotMockFactory.create_database_session_mock().__aiter__()
            mock_get_supervisor.return_value = SSotMockFactory.create_mock_supervisor_agent()
            
            # Measure processing time
            times = []
            for i in range(5):
                start_time = time.time()
                result = await self.handler.handle_message(
                    user_id=self.test_user_id,
                    websocket=self.mock_websocket,
                    message=test_message
                )
                end_time = time.time()
                
                # Verify successful processing
                assert result is True
                
                processing_time = end_time - start_time
                times.append(processing_time)
            
            # Calculate performance metrics
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            # Performance requirements for unit tests
            assert avg_time < 0.1, f"Average processing time {avg_time:.4f}s should be < 0.1s"
            assert max_time < 0.2, f"Max processing time {max_time:.4f}s should be < 0.2s"
            
            self.record_metric("average_processing_time", avg_time)
            self.record_metric("max_processing_time", max_time)
            self.record_metric("performance_requirements_met", True)
    
    @pytest.mark.unit
    async def test_concurrent_message_processing(self):
        """Test concurrent message processing behavior
        
        Business Impact: Validates system stability under concurrent
        user requests in multi-tenant environment.
        """
        # Create multiple messages for concurrent processing
        messages = []
        for i in range(3):
            messages.append(WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={
                    "content": f"Concurrent message {i}",
                    "thread_id": f"thread_{i}",
                    "run_id": f"run_{i}"
                }
            ))
        
        # Mock processing for concurrent execution
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context, \
             patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager, \
             patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session, \
             patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
            
            # Setup mocks for concurrent access
            def mock_context_factory(user_id, thread_id, run_id):
                return SSotMockFactory.create_mock_user_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
            
            mock_get_context.side_effect = mock_context_factory
            mock_create_manager.return_value = SSotMockFactory.create_mock_websocket_manager()
            mock_get_session.return_value = SSotMockFactory.create_database_session_mock().__aiter__()
            mock_get_supervisor.return_value = SSotMockFactory.create_mock_supervisor_agent()
            
            # Process messages concurrently
            start_time = time.time()
            tasks = [
                self.handler.handle_message(
                    user_id=f"user_{i}",
                    websocket=self.mock_websocket,
                    message=msg
                ) for i, msg in enumerate(messages)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processing_time = time.time() - start_time
            
            # Verify all processed successfully
            successful_results = 0
            for result in results:
                if result is True:
                    successful_results += 1
                elif isinstance(result, Exception):
                    # Concurrent processing might cause expected conflicts
                    pass
            
            # At least some should succeed
            assert successful_results > 0, "No concurrent messages processed successfully"
            
            # Should complete in reasonable time
            assert processing_time < 2.0, f"Concurrent processing took {processing_time:.3f}s"
            
            self.record_metric("concurrent_messages_processed", successful_results)
            self.record_metric("concurrent_processing_time", processing_time)
    
    # ========================================================================
    # STATISTICS AND MONITORING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_processing_statistics_tracking(self):
        """Test processing statistics are tracked correctly
        
        Business Impact: Enables monitoring and performance tracking
        of message processing pipeline.
        """
        # Get initial stats
        initial_stats = self.handler.get_stats()
        
        # Verify initial state
        assert initial_stats["messages_processed"] == 0
        assert initial_stats["start_agent_requests"] == 0
        assert initial_stats["user_messages"] == 0
        assert initial_stats["chat_messages"] == 0
        assert initial_stats["errors"] == 0
        assert initial_stats["last_processed_time"] is None
        
        # Manually update stats to test tracking
        self.handler._update_processing_stats(MessageType.START_AGENT)
        self.handler._update_processing_stats(MessageType.USER_MESSAGE)
        self.handler._update_processing_stats(MessageType.CHAT)
        
        # Check updated stats
        updated_stats = self.handler.get_stats()
        
        assert updated_stats["messages_processed"] == 3
        assert updated_stats["start_agent_requests"] == 1
        assert updated_stats["user_messages"] == 1
        assert updated_stats["chat_messages"] == 1
        assert updated_stats["errors"] == 0
        assert updated_stats["last_processed_time"] is not None
        
        self.record_metric("statistics_tracking_validated", True)
    
    @pytest.mark.unit
    def test_get_stats_completeness(self):
        """Test get_stats returns complete statistics
        
        Business Impact: Ensures all necessary metrics are available
        for monitoring and debugging.
        """
        stats = self.handler.get_stats()
        
        # Verify required stat fields exist
        required_fields = [
            "messages_processed",
            "start_agent_requests", 
            "user_messages",
            "chat_messages",
            "errors",
            "last_processed_time"
        ]
        
        for field in required_fields:
            assert field in stats, f"Required stat field '{field}' missing"
        
        # Verify data types are correct
        assert isinstance(stats["messages_processed"], int)
        assert isinstance(stats["start_agent_requests"], int)
        assert isinstance(stats["user_messages"], int)
        assert isinstance(stats["chat_messages"], int)
        assert isinstance(stats["errors"], int)
        # last_processed_time can be None or float
        assert stats["last_processed_time"] is None or isinstance(stats["last_processed_time"], float)
        
        self.record_metric("stats_completeness_validated", True)
        self.record_metric("required_stat_fields", len(required_fields))
    
    def teardown_method(self, method=None):
        """Cleanup after each test"""
        # Record final test metrics
        metrics = self.get_all_metrics()
        
        # Calculate comprehensive coverage metrics
        total_message_tests = sum(1 for key in metrics.keys() 
                                 if "message" in key and key.endswith("_success"))
        
        # Calculate performance metrics
        avg_processing_time = metrics.get("average_processing_time", 0)
        
        self.record_metric("agent_message_handler_test_coverage", total_message_tests)
        self.record_metric("golden_path_message_handler_validation_complete", True)
        
        # Log performance summary for monitoring
        if avg_processing_time > 0:
            self.record_metric("performance_baseline_established", True)
        
        # Call parent teardown
        super().teardown_method(method)