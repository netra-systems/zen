"""
Unit Tests for WebSocket Service Message Handler Business Logic

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Message handlers serve all user tiers for AI chat
- Business Goal: Reliable WebSocket message processing for agent execution and user communication  
- Value Impact: Handles critical user->agent message flow, enabling $120K+ MRR AI optimization services
- Strategic Impact: Core message processing pipeline for Golden Path user flow completion

This test suite validates the critical WebSocket service message handler business logic:
1. StartAgentHandler - Agent execution requests with WebSocket bridge integration
2. UserMessageHandler - User message processing with agent workflow execution
3. ThreadHistoryHandler - Conversation history retrieval for context continuity  
4. StopAgentHandler - Agent termination and cleanup
5. MessageHandlerService - Handler registration, validation, and queue management
6. BaseMessageHandler - Abstract handler interface and common functionality

CRITICAL: These handlers enable the Golden Path by processing:
- User messages -> Agent execution -> WebSocket events -> Chat responses
- Agent workflow orchestration with WebSocket bridge for real-time updates
- Thread history for conversation context and continuity
- Message validation, sanitization, and queue management

Following TEST_CREATION_GUIDE.md:
- Real message processing logic (not infrastructure mocks)
- SSOT patterns using existing services (UnitOfWork, UserExecutionContext)
- Proper test categorization (@pytest.mark.unit)
- Tests that FAIL HARD when message processing fails
- Focus on message handling business value
"""

import asyncio
import json
import pytest  
import uuid
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
from typing import Dict, Any, List, Optional

from netra_backend.app.services.websocket.message_handler import (
    # Base handler interface
    BaseMessageHandler,
    # Concrete message handlers
    StartAgentHandler,
    UserMessageHandler,
    ThreadHistoryHandler,
    StopAgentHandler,
    # Service management
    MessageHandlerService
)
from netra_backend.app.services.websocket.message_queue import (
    MessagePriority,
    QueuedMessage
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.base import BaseUnitTest


class TestBaseMessageHandlerInterface(BaseUnitTest):
    """Test BaseMessageHandler abstract interface for consistent handler implementation."""
    
    @pytest.mark.unit
    def test_base_message_handler_defines_required_interface(self):
        """Test BaseMessageHandler defines required interface methods."""
        # Business value: Consistent handler interface ensures reliable message processing
        
        # Create concrete implementation for testing
        class TestHandler(BaseMessageHandler):
            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                pass
                
            def get_message_type(self) -> str:
                return "test_message"
        
        handler = TestHandler()
        
        # Validate interface methods exist
        assert hasattr(handler, 'handle'), "Must define handle method"
        assert hasattr(handler, 'get_message_type'), "Must define get_message_type method"
        
        # Validate method signatures
        assert callable(handler.handle), "Handle method must be callable"
        assert callable(handler.get_message_type), "get_message_type method must be callable"
        
        # Validate return types
        message_type = handler.get_message_type()
        assert isinstance(message_type, str), "get_message_type must return string"
        assert message_type == "test_message", "Must return correct message type"

    @pytest.mark.unit
    async def test_base_message_handler_handle_method_signature(self):
        """Test BaseMessageHandler handle method has correct signature."""
        # Business value: Consistent handle signature enables handler interchangeability
        
        class TestHandler(BaseMessageHandler):
            def __init__(self):
                self.handled_calls = []
                
            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                self.handled_calls.append((user_id, payload))
                
            def get_message_type(self) -> str:
                return "signature_test"
        
        handler = TestHandler()
        
        # Test handle method with expected parameters
        test_user_id = "test-user-123"
        test_payload = {"message": "test data", "priority": 1}
        
        await handler.handle(test_user_id, test_payload)
        
        # Validate method was called with correct parameters
        assert len(handler.handled_calls) == 1, "Handle method must be called"
        called_user_id, called_payload = handler.handled_calls[0]
        assert called_user_id == test_user_id, "Must receive user_id parameter"
        assert called_payload == test_payload, "Must receive payload parameter"


class TestStartAgentHandlerBusinessLogic(BaseUnitTest):
    """Test StartAgentHandler business logic for agent execution requests."""
    
    def setUp(self):
        """Set up StartAgentHandler for testing."""
        # Create mock supervisor and database session factory
        self.mock_supervisor = Mock()
        self.mock_supervisor.run = AsyncMock(return_value="Agent execution completed successfully")
        self.mock_supervisor.websocket_bridge = None  # Initially no bridge
        
        self.mock_db_session_factory = Mock()
        
        # Create handler
        self.handler = StartAgentHandler(self.mock_supervisor, self.mock_db_session_factory)
        
        # Mock UnitOfWork and related database operations
        self.mock_uow = Mock()
        self.mock_uow.session = Mock()
        self.mock_uow.threads = Mock()
        self.mock_uow.messages = Mock()
        self.mock_uow.runs = Mock()
        
        self.mock_thread = Mock()
        self.mock_thread.id = "thread-123"
        self.mock_run = Mock()
        self.mock_run.id = "run-456"
        
        self.uow_patcher = patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
        self.mock_get_uow = self.uow_patcher.start()
        self.mock_get_uow.return_value.__aenter__ = AsyncMock(return_value=self.mock_uow)
        self.mock_get_uow.return_value.__aexit__ = AsyncMock(return_value=None)

    def tearDown(self):
        """Clean up patches."""
        self.uow_patcher.stop()

    @pytest.mark.unit
    def test_start_agent_handler_message_type_identification(self):
        """Test StartAgentHandler correctly identifies its message type."""
        # Business value: Proper message type identification enables correct routing
        
        message_type = self.handler.get_message_type()
        assert message_type == "start_agent", "Must handle start_agent message type"

    @pytest.mark.unit
    async def test_start_agent_handler_processes_agent_request_successfully(self):
        """Test StartAgentHandler processes agent execution request with full workflow."""
        # Business value: Successful agent request processing enables AI optimization services
        
        user_id = "business-user-123"
        payload = {
            "request": {
                "query": "Optimize my AWS infrastructure costs",
                "user_request": "Help me reduce my cloud spending by 30%"
            }
        }
        
        # Configure database mocks for successful workflow
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.messages.create_message.return_value = None
        self.mock_uow.runs.create_run.return_value = self.mock_run
        self.mock_uow.runs.update_status.return_value = None
        
        # Mock WebSocket manager creation
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            # Mock WebSocket bridge creation  
            with patch('netra_backend.app.services.websocket.message_handler.create_agent_websocket_bridge') as mock_create_bridge:
                mock_websocket_bridge = Mock()
                mock_create_bridge.return_value = mock_websocket_bridge
                
                # Execute agent start request
                await self.handler.handle(user_id, payload)
        
        # Validate business workflow execution
        self.mock_uow.threads.get_or_create_for_user.assert_called_once_with(self.mock_uow.session, user_id)
        
        # Validate user message was created
        self.mock_uow.messages.create_message.assert_called()
        message_call_args = self.mock_uow.messages.create_message.call_args
        assert "Optimize my AWS infrastructure costs" in str(message_call_args), "Must create message with user query"
        
        # Validate agent run was created
        self.mock_uow.runs.create_run.assert_called_once_with(
            self.mock_uow.session,
            thread_id=self.mock_thread.id,
            assistant_id="netra-assistant",
            model="gemini-2.5-flash",
            instructions="You are Netra AI Workload Optimization Assistant"
        )
        
        # Validate supervisor was configured and executed
        assert self.mock_supervisor.thread_id == self.mock_thread.id, "Must configure thread ID"
        assert self.mock_supervisor.user_id == user_id, "Must configure user ID"
        self.mock_supervisor.run.assert_called_once_with(
            "Optimize my AWS infrastructure costs",
            self.mock_thread.id,
            user_id,
            self.mock_run.id
        )
        
        # Validate WebSocket bridge was added to supervisor
        assert self.mock_supervisor.websocket_bridge is not None, "Must add WebSocket bridge for events"

    @pytest.mark.unit
    async def test_start_agent_handler_creates_websocket_bridge_when_missing(self):
        """Test StartAgentHandler creates WebSocket bridge when supervisor lacks one."""
        # Business value: WebSocket bridge ensures agent events are sent for real-time chat updates
        
        user_id = "bridge-test-user"
        payload = {"request": {"query": "Test agent bridge creation"}}
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.runs.create_run.return_value = self.mock_run
        
        # Ensure supervisor initially has no bridge
        assert self.mock_supervisor.websocket_bridge is None, "Supervisor should start without bridge"
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager'), \
             patch('netra_backend.app.services.websocket.message_handler.create_agent_websocket_bridge') as mock_create_bridge, \
             patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context') as mock_get_context:
            
            mock_context = Mock()
            mock_get_context.return_value = mock_context
            mock_websocket_bridge = Mock()
            mock_create_bridge.return_value = mock_websocket_bridge
            
            # Execute handler
            await self.handler.handle(user_id, payload)
            
            # Validate WebSocket bridge creation
            mock_create_bridge.assert_called_once_with(mock_context)
            assert self.mock_supervisor.websocket_bridge == mock_websocket_bridge, "Must assign bridge to supervisor"

    @pytest.mark.unit
    async def test_start_agent_handler_handles_thread_creation_failure(self):
        """Test StartAgentHandler handles thread creation failure gracefully."""
        # Business value: Graceful failure handling prevents agent request crashes
        
        user_id = "thread-fail-user"
        payload = {"request": {"query": "Test thread failure handling"}}
        
        # Configure thread creation to fail
        self.mock_uow.threads.get_or_create_for_user.return_value = None
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.send_error = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            with patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context'):
                # Execute handler with thread failure
                await self.handler.handle(user_id, payload)
            
            # Validate error handling
            mock_websocket_manager.send_error.assert_called_once_with(
                user_id, "Failed to create or retrieve thread"
            )
            
            # Validate supervisor was not executed
            self.mock_supervisor.run.assert_not_called()

    @pytest.mark.unit
    async def test_start_agent_handler_saves_assistant_response_properly(self):
        """Test StartAgentHandler saves assistant response with proper formatting."""
        # Business value: Proper response saving enables conversation history and context
        
        user_id = "response-save-user"
        payload = {"request": {"query": "Test response saving"}}
        
        # Configure successful execution with response
        agent_response = {
            "analysis": "Your AWS costs can be optimized by 25%",
            "recommendations": ["Resize EC2 instances", "Use Reserved Instances"],
            "potential_savings": "$2,500/month"
        }
        self.mock_supervisor.run.return_value = agent_response
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.runs.create_run.return_value = self.mock_run
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager'):
            with patch('netra_backend.app.services.websocket.message_handler.create_agent_websocket_bridge'):
                # Execute handler
                await self.handler.handle(user_id, payload)
        
        # Validate assistant response was saved
        assistant_message_calls = [call for call in self.mock_uow.messages.create_message.call_args_list 
                                 if len(call.kwargs) > 0 and call.kwargs.get('role') == 'assistant']
        
        assert len(assistant_message_calls) >= 1, "Must save assistant response message"
        
        # Validate run status was updated to completed
        self.mock_uow.runs.update_status.assert_called_with(
            self.mock_uow.session, self.mock_run.id, "completed"
        )

    @pytest.mark.unit 
    async def test_start_agent_handler_sends_completion_message_to_user(self):
        """Test StartAgentHandler sends agent completion message to user."""
        # Business value: Completion messages inform users that agent processing is done
        
        user_id = "completion-test-user"
        payload = {"request": {"query": "Test completion message"}}
        
        agent_response = "Agent analysis complete with optimization recommendations"
        self.mock_supervisor.run.return_value = agent_response
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.runs.create_run.return_value = self.mock_run
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            with patch('netra_backend.app.services.websocket.message_handler.create_agent_websocket_bridge'):
                # Execute handler
                await self.handler.handle(user_id, payload)
            
            # Validate completion message was sent
            mock_websocket_manager.send_to_user.assert_called_with(
                user_id,
                {
                    "type": "agent_completed",
                    "payload": agent_response
                }
            )


class TestUserMessageHandlerBusinessLogic(BaseUnitTest):
    """Test UserMessageHandler business logic for user message processing."""
    
    def setUp(self):
        """Set up UserMessageHandler for testing."""
        # Create mock supervisor and database session factory
        self.mock_supervisor = Mock()
        self.mock_supervisor.run = AsyncMock(return_value="User message processed successfully")
        
        self.mock_db_session_factory = Mock()
        
        # Create handler
        self.handler = UserMessageHandler(self.mock_supervisor, self.mock_db_session_factory)
        
        # Mock UnitOfWork and related database operations
        self.mock_uow = Mock()
        self.mock_uow.session = Mock()
        self.mock_uow.threads = Mock()
        self.mock_uow.messages = Mock()
        self.mock_uow.runs = Mock()
        
        self.mock_thread = Mock()
        self.mock_thread.id = "thread-789"
        self.mock_run = Mock()
        self.mock_run.id = "run-101"
        
        self.uow_patcher = patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
        self.mock_get_uow = self.uow_patcher.start()
        self.mock_get_uow.return_value.__aenter__ = AsyncMock(return_value=self.mock_uow)
        self.mock_get_uow.return_value.__aexit__ = AsyncMock(return_value=None)

    def tearDown(self):
        """Clean up patches."""
        self.uow_patcher.stop()

    @pytest.mark.unit
    def test_user_message_handler_message_type_identification(self):
        """Test UserMessageHandler correctly identifies its message type."""
        # Business value: Proper message type identification enables user message routing
        
        message_type = self.handler.get_message_type()
        assert message_type == "user_message", "Must handle user_message type"

    @pytest.mark.unit
    async def test_user_message_handler_processes_user_message_with_context(self):
        """Test UserMessageHandler processes user messages with proper thread context."""
        # Business value: User message processing enables ongoing AI chat conversations
        
        user_id = "chat-user-456"
        payload = {
            "text": "Can you help me analyze my current cloud spending patterns?",
            "references": [{"type": "file", "name": "aws-bill.pdf"}]
        }
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.messages.create_message.return_value = None
        self.mock_uow.runs.create_run.return_value = self.mock_run
        self.mock_uow.runs.update_status.return_value = None
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            # Execute user message handling
            await self.handler.handle(user_id, payload)
        
        # Validate user message was processed
        self.mock_uow.threads.get_or_create_for_user.assert_called_once_with(self.mock_uow.session, user_id)
        
        # Validate message was created with references
        self.mock_uow.messages.create_message.assert_called()
        message_calls = self.mock_uow.messages.create_message.call_args_list
        
        # Find the user message creation call
        user_message_call = next(
            call for call in message_calls 
            if call.kwargs.get('role') == 'user'
        )
        assert "Can you help me analyze" in user_message_call.kwargs['content'], "Must preserve user message text"
        assert user_message_call.kwargs.get('metadata'), "Must include references metadata"
        
        # Validate supervisor was executed with correct parameters
        self.mock_supervisor.run.assert_called_once_with(
            "Can you help me analyze my current cloud spending patterns?",
            self.mock_thread.id,
            user_id,
            self.mock_run.id
        )

    @pytest.mark.unit
    async def test_user_message_handler_handles_messages_without_references(self):
        """Test UserMessageHandler handles user messages without references properly."""
        # Business value: Support for simple text messages without file attachments
        
        user_id = "simple-user-789"
        payload = {
            "text": "What are the top 3 ways to reduce AWS costs?",
            "references": []  # Empty references
        }
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.runs.create_run.return_value = self.mock_run
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager'):
            # Execute user message handling
            await self.handler.handle(user_id, payload)
        
        # Validate message was created without references metadata
        message_calls = self.mock_uow.messages.create_message.call_args_list
        user_message_call = next(
            call for call in message_calls 
            if call.kwargs.get('role') == 'user'
        )
        
        # Metadata should be None when no references
        assert user_message_call.kwargs.get('metadata') is None, "Must not include empty references metadata"

    @pytest.mark.unit
    async def test_user_message_handler_saves_assistant_response_with_metadata(self):
        """Test UserMessageHandler saves assistant response with proper metadata."""
        # Business value: Proper response metadata enables response categorization
        
        user_id = "metadata-user-101"
        payload = {"text": "Test message metadata handling"}
        
        assistant_response = "Based on your request, here are my recommendations..."
        self.mock_supervisor.run.return_value = assistant_response
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.runs.create_run.return_value = self.mock_run
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager'):
            # Execute handler
            await self.handler.handle(user_id, payload)
        
        # Validate assistant response was saved with metadata
        message_calls = self.mock_uow.messages.create_message.call_args_list
        assistant_message_calls = [
            call for call in message_calls 
            if call.kwargs.get('role') == 'assistant'
        ]
        
        assert len(assistant_message_calls) >= 1, "Must save assistant response"
        
        assistant_call = assistant_message_calls[0]
        assert assistant_call.kwargs.get('metadata', {}).get('type') == 'agent_response', "Must tag as agent response"
        assert assistant_call.kwargs.get('assistant_id') == 'netra-assistant', "Must identify assistant"


class TestThreadHistoryHandlerBusinessLogic(BaseUnitTest):
    """Test ThreadHistoryHandler business logic for conversation history retrieval."""
    
    def setUp(self):
        """Set up ThreadHistoryHandler for testing."""
        self.mock_db_session_factory = Mock()
        self.handler = ThreadHistoryHandler(self.mock_db_session_factory)
        
        # Mock UnitOfWork
        self.mock_uow = Mock()
        self.mock_uow.session = Mock()
        self.mock_uow.threads = Mock()
        self.mock_uow.messages = Mock()
        
        self.mock_thread = Mock()
        self.mock_thread.id = "history-thread-123"
        
        self.uow_patcher = patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
        self.mock_get_uow = self.uow_patcher.start()
        self.mock_get_uow.return_value.__aenter__ = AsyncMock(return_value=self.mock_uow)
        self.mock_get_uow.return_value.__aexit__ = AsyncMock(return_value=None)

    def tearDown(self):
        """Clean up patches."""
        self.uow_patcher.stop()

    @pytest.mark.unit
    def test_thread_history_handler_message_type_identification(self):
        """Test ThreadHistoryHandler correctly identifies its message type."""
        # Business value: Proper message type identification enables history request routing
        
        message_type = self.handler.get_message_type()
        assert message_type == "get_thread_history", "Must handle get_thread_history type"

    @pytest.mark.unit
    async def test_thread_history_handler_retrieves_conversation_history(self):
        """Test ThreadHistoryHandler retrieves and formats conversation history."""
        # Business value: History retrieval enables conversation context and continuity
        
        user_id = "history-user-456"
        payload = {"limit": 25}
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        
        # Create mock messages
        mock_messages = [
            Mock(
                id="msg-1",
                role="user",
                content=[{"text": {"value": "How can I optimize my costs?"}}],
                created_at="2024-01-15T10:30:00Z"
            ),
            Mock(
                id="msg-2", 
                role="assistant",
                content=[{"text": {"value": "I recommend analyzing your EC2 usage patterns..."}}],
                created_at="2024-01-15T10:31:30Z"
            ),
            Mock(
                id="msg-3",
                role="user", 
                content=[{"text": {"value": "Can you be more specific about EC2 optimization?"}}],
                created_at="2024-01-15T10:32:15Z"
            )
        ]
        self.mock_uow.messages.get_thread_messages.return_value = mock_messages
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            # Execute history retrieval
            await self.handler.handle(user_id, payload)
        
        # Validate thread history was retrieved
        self.mock_uow.messages.get_thread_messages.assert_called_once_with(
            self.mock_uow.session, self.mock_thread.id, limit=25
        )
        
        # Validate history response was sent
        mock_websocket_manager.send_to_user.assert_called_once()
        
        call_args = mock_websocket_manager.send_to_user.call_args
        assert call_args[0][0] == user_id, "Must send to correct user"
        
        response_data = call_args[0][1]
        assert response_data["type"] == "thread_history", "Must use thread_history type"
        assert response_data["payload"]["thread_id"] == self.mock_thread.id, "Must include thread ID"
        
        history_messages = response_data["payload"]["messages"]
        assert len(history_messages) == 3, "Must include all messages"
        
        # Validate message formatting
        assert history_messages[0]["role"] == "user", "Must preserve message roles"
        assert "How can I optimize" in history_messages[0]["content"], "Must preserve message content"
        assert history_messages[1]["role"] == "assistant", "Must include assistant responses"

    @pytest.mark.unit
    async def test_thread_history_handler_uses_default_limit_when_not_specified(self):
        """Test ThreadHistoryHandler uses default limit when not specified in payload."""
        # Business value: Default limits prevent excessive data transfer for history requests
        
        user_id = "limit-test-user"
        payload = {}  # No limit specified
        
        # Configure database mocks
        self.mock_uow.threads.get_or_create_for_user.return_value = self.mock_thread
        self.mock_uow.messages.get_thread_messages.return_value = []
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager'):
            # Execute history retrieval without limit
            await self.handler.handle(user_id, payload)
        
        # Validate default limit was used
        self.mock_uow.messages.get_thread_messages.assert_called_once_with(
            self.mock_uow.session, self.mock_thread.id, limit=50  # Default limit
        )

    @pytest.mark.unit
    async def test_thread_history_handler_handles_thread_retrieval_failure(self):
        """Test ThreadHistoryHandler handles thread retrieval failure gracefully."""
        # Business value: Graceful failure handling prevents history request crashes
        
        user_id = "fail-history-user"
        payload = {"limit": 10}
        
        # Configure thread retrieval to fail
        self.mock_uow.threads.get_or_create_for_user.return_value = None
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.send_error = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            # Execute history retrieval with thread failure
            await self.handler.handle(user_id, payload)
            
            # Validate error handling
            mock_websocket_manager.send_error.assert_called_once_with(
                user_id, "Failed to retrieve thread"
            )
            
            # Validate messages were not queried
            self.mock_uow.messages.get_thread_messages.assert_not_called()


class TestStopAgentHandlerBusinessLogic(BaseUnitTest):
    """Test StopAgentHandler business logic for agent termination."""
    
    def setUp(self):
        """Set up StopAgentHandler for testing."""
        self.mock_supervisor = Mock()
        self.handler = StopAgentHandler(self.mock_supervisor)

    @pytest.mark.unit
    def test_stop_agent_handler_message_type_identification(self):
        """Test StopAgentHandler correctly identifies its message type."""
        # Business value: Proper message type identification enables agent stop routing
        
        message_type = self.handler.get_message_type()
        assert message_type == "stop_agent", "Must handle stop_agent type"

    @pytest.mark.unit
    async def test_stop_agent_handler_sends_agent_stopped_confirmation(self):
        """Test StopAgentHandler sends agent stopped confirmation to user."""
        # Business value: Stop confirmation informs users that agent processing has ended
        
        user_id = "stop-test-user"
        payload = {"reason": "user_requested"}
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            with patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context'):
                # Execute stop agent request
                await self.handler.handle(user_id, payload)
            
            # Validate stop confirmation was sent
            mock_websocket_manager.send_to_user.assert_called_once_with(
                user_id,
                {
                    "type": "agent_stopped",
                    "payload": {"status": "stopped"}
                }
            )


class TestMessageHandlerServiceBusinessLogic(BaseUnitTest):
    """Test MessageHandlerService business logic for handler management and message routing."""
    
    def setUp(self):
        """Set up MessageHandlerService for testing."""
        self.mock_supervisor = Mock()
        self.mock_db_session_factory = Mock()
        
        # Mock message queue
        self.mock_message_queue = Mock()
        self.mock_message_queue.register_handler = Mock()
        self.mock_message_queue.enqueue = AsyncMock(return_value=True)
        self.mock_message_queue.process_queue = AsyncMock()
        self.mock_message_queue.stop_processing = AsyncMock()
        self.mock_message_queue.get_queue_stats = AsyncMock(return_value={"processed": 10, "pending": 0})
        
        # Patch message queue
        self.queue_patcher = patch('netra_backend.app.services.websocket.message_handler.message_queue', self.mock_message_queue)
        self.queue_patcher.start()
        
        # Create service
        self.service = MessageHandlerService(self.mock_supervisor, self.mock_db_session_factory)

    def tearDown(self):
        """Clean up patches."""
        self.queue_patcher.stop()

    @pytest.mark.unit
    def test_message_handler_service_registers_all_required_handlers(self):
        """Test MessageHandlerService registers all required message handlers."""
        # Business value: Complete handler registration ensures all message types are processed
        
        # Validate handlers were registered
        expected_handlers = [
            "start_agent",
            "user_message", 
            "get_thread_history",
            "stop_agent"
        ]
        
        registered_types = list(self.service.handlers.keys())
        
        for expected_type in expected_handlers:
            assert expected_type in registered_types, f"Must register {expected_type} handler"
        
        # Validate handlers were registered with message queue
        assert self.mock_message_queue.register_handler.call_count >= len(expected_handlers), "Must register handlers with queue"

    @pytest.mark.unit
    async def test_message_handler_service_validates_message_format_before_processing(self):
        """Test MessageHandlerService validates message format before queue processing."""
        # Business value: Message validation prevents processing of malformed messages
        
        user_id = "validation-user-123"
        
        # Test with valid message
        valid_message = {
            "type": "user_message",
            "payload": {"text": "Test message"},
            "timestamp": 1640995200
        }
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.validate_message = Mock(return_value=True)
            mock_websocket_manager.sanitize_message = Mock(return_value=valid_message)
            mock_create_manager.return_value = mock_websocket_manager
            
            # Process valid message
            await self.service.handle_message(user_id, valid_message)
            
            # Validate message validation was called
            mock_websocket_manager.validate_message.assert_called_once_with(valid_message)
            
            # Validate message was queued
            self.mock_message_queue.enqueue.assert_called_once()
            
            queued_message = self.mock_message_queue.enqueue.call_args[0][0]
            assert queued_message.user_id == user_id, "Must preserve user ID in queued message"
            assert queued_message.type == "user_message", "Must preserve message type"

    @pytest.mark.unit
    async def test_message_handler_service_rejects_invalid_message_format(self):
        """Test MessageHandlerService rejects messages with invalid format."""
        # Business value: Invalid message rejection prevents processing errors
        
        user_id = "invalid-message-user"
        invalid_message = {
            "payload": {"text": "Missing type field"},
            "timestamp": 1640995200
        }
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.validate_message = Mock(return_value=False)
            mock_websocket_manager.send_error = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            # Process invalid message
            await self.service.handle_message(user_id, invalid_message)
            
            # Validate error was sent
            mock_websocket_manager.send_error.assert_called_once_with(user_id, "Invalid message format")
            
            # Validate message was not queued
            self.mock_message_queue.enqueue.assert_not_called()

    @pytest.mark.unit
    async def test_message_handler_service_handles_unknown_message_types(self):
        """Test MessageHandlerService handles unknown message types gracefully."""
        # Business value: Unknown message type handling prevents handler crashes
        
        user_id = "unknown-type-user"
        unknown_message = {
            "type": "unknown_message_type",
            "payload": {"data": "test"},
            "timestamp": 1640995200
        }
        
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            mock_websocket_manager = Mock()
            mock_websocket_manager.validate_message = Mock(return_value=True)
            mock_websocket_manager.send_error = AsyncMock()
            mock_create_manager.return_value = mock_websocket_manager
            
            # Process unknown message type
            await self.service.handle_message(user_id, unknown_message)
            
            # Validate error was sent for unknown type
            mock_websocket_manager.send_error.assert_called_once_with(
                user_id, "Unknown message type: unknown_message_type"
            )

    @pytest.mark.unit
    def test_message_handler_service_assigns_correct_message_priorities(self):
        """Test MessageHandlerService assigns correct priorities to different message types."""
        # Business value: Message prioritization ensures critical messages are processed first
        
        # Test priority mapping
        assert self.service._determine_priority("stop_agent") == MessagePriority.CRITICAL, "Stop agent must be critical priority"
        assert self.service._determine_priority("start_agent") == MessagePriority.HIGH, "Start agent must be high priority"
        assert self.service._determine_priority("user_message") == MessagePriority.NORMAL, "User message must be normal priority"
        assert self.service._determine_priority("get_thread_history") == MessagePriority.LOW, "History must be low priority"
        
        # Test unknown message type gets normal priority
        assert self.service._determine_priority("unknown_type") == MessagePriority.NORMAL, "Unknown type must default to normal"

    @pytest.mark.unit
    async def test_message_handler_service_provides_queue_statistics(self):
        """Test MessageHandlerService provides queue processing statistics."""
        # Business value: Statistics enable monitoring and performance optimization
        
        # Get queue statistics
        stats = await self.service.get_stats()
        
        # Validate statistics retrieval
        self.mock_message_queue.get_queue_stats.assert_called_once()
        assert stats == {"processed": 10, "pending": 0}, "Must return queue statistics"

    @pytest.mark.unit
    async def test_message_handler_service_starts_and_stops_queue_processing(self):
        """Test MessageHandlerService can start and stop queue processing."""
        # Business value: Queue lifecycle management enables controlled message processing
        
        # Start processing with custom worker count
        await self.service.start_processing(worker_count=5)
        
        # Validate queue processing was started
        self.mock_message_queue.process_queue.assert_called_once_with(5)
        
        # Stop processing
        await self.service.stop_processing()
        
        # Validate queue processing was stopped
        self.mock_message_queue.stop_processing.assert_called_once()


if __name__ == "__main__":
    # Run tests with proper WebSocket service message handler validation
    pytest.main([__file__, "-v", "--tb=short"])