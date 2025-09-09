"""
Unit Tests for WebSocket Message Handler Service Business Logic

Business Value Justification (BVJ):
- Segment: Free/Early/Mid/Enterprise (Multi-Segment Critical Infrastructure)
- Business Goal: User Experience & AI Value Delivery Excellence  
- Value Impact: Validates message processing workflows that enable $X million in AI optimization value,
  ensures proper agent event routing that powers substantive chat interactions
- Strategic Impact: Tests service layer that coordinates all 5 critical WebSocket events enabling 
  users to receive valuable AI-powered optimization recommendations in real-time

CRITICAL: These unit tests validate the BUSINESS LOGIC of the service layer message handlers,
focusing on the workflows that process agent messages and deliver value to users:

KEY BUSINESS WORKFLOWS TESTED:
1. StartAgentHandler - Initiates AI optimization workflows that deliver business value
2. UserMessageHandler - Processes ongoing user conversations with AI agents
3. ThreadHistoryHandler - Enables conversation continuity essential for complex optimizations
4. StopAgentHandler - Provides user control over AI processing
5. MessageHandlerService - Orchestrates message routing for seamless user experience

TEST STRATEGY: Pure business logic validation of service workflows.
Tests agent workflow execution, database operations, and WebSocket event generation.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, Any

# SSOT imports using absolute paths
from netra_backend.app.services.websocket.message_handler import (
    BaseMessageHandler,
    StartAgentHandler,
    UserMessageHandler,
    ThreadHistoryHandler,
    StopAgentHandler,
    MessageHandlerService
)
from netra_backend.app.llm.llm_defaults import LLMModel
from netra_backend.app.dependencies import get_user_execution_context
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.database.unit_of_work import get_unit_of_work
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestBaseMessageHandler(SSotBaseTestCase):
    """Test BaseMessageHandler abstract business logic."""
    
    def test_base_handler_is_abstract(self):
        """Test BaseMessageHandler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseMessageHandler()
            
    def test_abstract_methods_defined(self):
        """Test abstract methods are properly defined."""
        # Create concrete implementation
        class ConcreteHandler(BaseMessageHandler):
            async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
                pass
                
            def get_message_type(self) -> str:
                return "test_message"
                
        handler = ConcreteHandler()
        assert handler.get_message_type() == "test_message"
        assert callable(handler.handle)


@pytest.mark.unit
class TestStartAgentHandler(SSotBaseTestCase):
    """Test StartAgentHandler business logic - CRITICAL for agent workflow execution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supervisor = Mock()
        self.mock_supervisor.run = AsyncMock(return_value="Agent execution completed")
        self.mock_db_session_factory = Mock()
        
        self.handler = StartAgentHandler(self.mock_supervisor, self.mock_db_session_factory)
        
    def test_handler_initialization(self):
        """Test StartAgentHandler initializes with required dependencies."""
        assert self.handler.supervisor == self.mock_supervisor
        assert self.handler.db_session_factory == self.mock_db_session_factory
        assert self.handler.get_message_type() == "start_agent"
        
    def test_extract_user_request_from_payload(self):
        """Test _extract_user_request extracts request from different payload formats."""
        # Test with 'query' key
        payload1 = {"request": {"query": "Optimize my infrastructure"}}
        result1 = self.handler._extract_user_request(payload1)
        assert result1 == "Optimize my infrastructure"
        
        # Test with 'user_request' key
        payload2 = {"request": {"user_request": "Reduce cloud costs"}}
        result2 = self.handler._extract_user_request(payload2)
        assert result2 == "Reduce cloud costs"
        
        # Test with empty payload
        payload3 = {}
        result3 = self.handler._extract_user_request(payload3)
        assert result3 == ""
        
    @patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
    async def test_setup_thread_and_run_creates_thread_and_run(self, mock_uow):
        """Test _setup_thread_and_run creates database entries for agent execution."""
        # Setup mocks
        mock_uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=mock_uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock thread creation
        mock_thread = Mock()
        mock_thread.id = "thread-123"
        mock_uow_instance.threads.get_or_create_for_user = AsyncMock(return_value=mock_thread)
        
        # Mock message creation
        mock_uow_instance.messages.create_message = AsyncMock()
        
        # Mock run creation
        mock_run = Mock()
        mock_run.id = "run-456"
        mock_uow_instance.runs.create_run = AsyncMock(return_value=mock_run)
        
        user_id = "test-user-123"
        user_request = "Optimize my cluster"
        
        # Execute business logic
        thread_id, run_id = await self.handler._setup_thread_and_run(user_id, user_request)
        
        # Verify business outcomes
        assert thread_id == "thread-123"
        assert run_id == "run-456"
        
        # Verify database operations
        mock_uow_instance.threads.get_or_create_for_user.assert_called_once()
        mock_uow_instance.messages.create_message.assert_called_once()
        mock_uow_instance.runs.create_run.assert_called_once()
        
    @patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_setup_thread_and_run_handles_thread_creation_failure(self, mock_create_manager, mock_uow):
        """Test _setup_thread_and_run handles thread creation failures gracefully."""
        # Setup mocks
        mock_uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=mock_uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock thread creation failure
        mock_uow_instance.threads.get_or_create_for_user = AsyncMock(return_value=None)
        
        # Mock WebSocket manager for error sending
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        user_id = "test-user-456"
        user_request = "Test request"
        
        # Execute business logic
        thread_id, run_id = await self.handler._setup_thread_and_run(user_id, user_request)
        
        # Verify business outcomes
        assert thread_id is None
        assert run_id is None
        
        # Verify error sent to user
        mock_manager.send_error.assert_called_once_with(
            user_id, "Failed to create or retrieve thread"
        )
        
    def test_configure_supervisor_sets_required_properties(self):
        """Test _configure_supervisor sets required supervisor properties."""
        thread_id = "config-thread-123"
        user_id = "config-user-456"
        
        # Execute business logic
        self.handler._configure_supervisor(thread_id, user_id)
        
        # Verify business outcomes
        assert self.handler.supervisor.thread_id == thread_id
        assert self.handler.supervisor.user_id == user_id
        assert self.handler.supervisor.db_session is None
        
    async def test_execute_agent_workflow_creates_websocket_bridge(self):
        """Test _execute_agent_workflow creates WebSocket bridge for event emission."""
        # Setup supervisor without WebSocket bridge
        self.handler.supervisor.websocket_bridge = None
        
        user_request = "Test optimization"
        thread_id = "ws-bridge-thread-123"
        user_id = "ws-bridge-user-456"
        run_id = "ws-bridge-run-789"
        
        with patch('netra_backend.app.services.websocket.message_handler.create_agent_websocket_bridge') as mock_create_bridge:
            with patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context') as mock_get_context:
                mock_context = Mock()
                mock_get_context.return_value = mock_context
                
                mock_bridge = Mock()
                mock_create_bridge.return_value = mock_bridge
                
                # Execute business logic
                result = await self.handler._execute_agent_workflow(
                    user_request, thread_id, user_id, run_id
                )
                
                # Verify business outcomes
                assert self.handler.supervisor.websocket_bridge == mock_bridge
                mock_get_context.assert_called_once_with(
                    user_id=user_id,
                    thread_id=thread_id, 
                    run_id=run_id
                )
                mock_create_bridge.assert_called_once_with(mock_context)
                self.handler.supervisor.run.assert_called_once_with(
                    user_request, thread_id, user_id, run_id
                )
                
    @patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
    async def test_save_assistant_response_stores_agent_output(self, mock_uow):
        """Test _save_assistant_response stores agent response in database."""
        # Setup mocks
        mock_uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=mock_uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_uow_instance.messages.create_message = AsyncMock()
        mock_uow_instance.runs.update_status = AsyncMock()
        
        thread_id = "response-thread-123"
        run_id = "response-run-456"
        response = {"optimization_results": "Cost reduced by 20%"}
        
        # Execute business logic
        await self.handler._save_assistant_response(thread_id, run_id, response)
        
        # Verify business outcomes
        mock_uow_instance.messages.create_message.assert_called_once()
        call_args = mock_uow_instance.messages.create_message.call_args
        
        assert call_args[1]["thread_id"] == thread_id
        assert call_args[1]["run_id"] == run_id
        assert call_args[1]["role"] == "assistant"
        assert call_args[1]["assistant_id"] == "netra-assistant"
        
        # Response should be JSON serialized
        content = call_args[1]["content"]
        assert isinstance(content, str)
        assert "optimization_results" in content
        
        # Run status should be updated
        mock_uow_instance.runs.update_status.assert_called_once_with(
            mock_uow_instance.session, run_id, "completed"
        )
        
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_send_agent_completion_notifies_user(self, mock_create_manager):
        """Test _send_agent_completion sends completion event to user."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        user_id = "completion-user-123"
        response = "Optimization completed successfully"
        
        # Execute business logic
        await self.handler._send_agent_completion(user_id, response)
        
        # Verify business outcomes
        mock_manager.send_to_user.assert_called_once()
        call_args = mock_manager.send_to_user.call_args[0]
        
        assert call_args[0] == user_id
        message = call_args[1]
        assert message["type"] == "agent_completed"
        assert message["payload"] == response
        
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_handle_agent_error_sends_error_to_user(self, mock_create_manager):
        """Test _handle_agent_error sends error notification to user."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        user_id = "error-user-123"
        error = Exception("Agent execution failed")
        
        # Execute business logic
        await self.handler._handle_agent_error(user_id, error)
        
        # Verify business outcomes
        mock_manager.send_error.assert_called_once_with(
            user_id, "Failed to start agent: Agent execution failed"
        )
        
    @patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
    async def test_handle_processes_complete_workflow(self, mock_uow):
        """Test handle processes complete start_agent workflow end-to-end."""
        # Setup extensive mocking for full workflow
        mock_uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=mock_uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock thread and run creation
        mock_thread = Mock()
        mock_thread.id = "workflow-thread-123"
        mock_uow_instance.threads.get_or_create_for_user = AsyncMock(return_value=mock_thread)
        mock_uow_instance.messages.create_message = AsyncMock()
        
        mock_run = Mock()
        mock_run.id = "workflow-run-456"
        mock_uow_instance.runs.create_run = AsyncMock(return_value=mock_run)
        mock_uow_instance.runs.update_status = AsyncMock()
        
        # Mock supervisor execution
        self.handler.supervisor.run = AsyncMock(return_value="Workflow completed")
        
        user_id = "workflow-user-123"
        payload = {
            "request": {
                "query": "Optimize my Kubernetes deployment"
            }
        }
        
        with patch.object(self.handler, '_send_agent_completion') as mock_send_completion:
            # Execute business logic
            await self.handler.handle(user_id, payload)
            
            # Verify complete workflow execution
            mock_uow_instance.threads.get_or_create_for_user.assert_called()
            self.handler.supervisor.run.assert_called_once()
            mock_send_completion.assert_called_once_with(user_id, "Workflow completed")


@pytest.mark.unit
class TestUserMessageHandler(SSotBaseTestCase):
    """Test UserMessageHandler business logic - processes ongoing user conversations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supervisor = Mock()
        self.mock_supervisor.run = AsyncMock(return_value="User message processed")
        self.mock_db_session_factory = Mock()
        
        self.handler = UserMessageHandler(self.mock_supervisor, self.mock_db_session_factory)
        
    def test_handler_initialization(self):
        """Test UserMessageHandler initializes correctly."""
        assert self.handler.supervisor == self.mock_supervisor
        assert self.handler.db_session_factory == self.mock_db_session_factory
        assert self.handler.get_message_type() == "user_message"
        
    def test_extract_message_data_from_payload(self):
        """Test _extract_message_data extracts text and references."""
        payload = {
            "text": "What are the optimization results?",
            "references": [
                {"type": "document", "id": "doc-123"},
                {"type": "previous_chat", "id": "chat-456"}
            ]
        }
        
        text, references = self.handler._extract_message_data(payload)
        
        assert text == "What are the optimization results?"
        assert len(references) == 2
        assert references[0]["type"] == "document"
        assert references[1]["id"] == "chat-456"
        
    @patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
    async def test_create_user_message_and_run_with_references(self, mock_uow):
        """Test _create_user_message_and_run stores message with references."""
        # Setup mocks
        mock_uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=mock_uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_thread = Mock()
        mock_thread.id = "message-thread-123"
        
        mock_run = Mock()
        mock_run.id = "message-run-456" 
        mock_uow_instance.runs.create_run = AsyncMock(return_value=mock_run)
        mock_uow_instance.messages.create_message = AsyncMock()
        
        text = "Follow up question"
        references = [{"type": "chat", "id": "previous-123"}]
        
        # Execute business logic
        thread_id, run_id = await self.handler._create_user_message_and_run(
            mock_uow_instance, mock_thread, text, references
        )
        
        # Verify business outcomes
        assert thread_id == "message-thread-123"
        assert run_id == "message-run-456"
        
        # Verify message created with metadata
        mock_uow_instance.messages.create_message.assert_called_once()
        call_args = mock_uow_instance.messages.create_message.call_args
        
        assert call_args[1]["content"] == text
        assert call_args[1]["role"] == "user"
        assert call_args[1]["metadata"]["references"] == references
        
    def test_configure_message_supervisor_sets_properties(self):
        """Test _configure_message_supervisor configures supervisor for message processing."""
        thread_id = "msg-config-thread-123"
        user_id = "msg-config-user-456"
        
        # Execute business logic
        self.handler._configure_message_supervisor(thread_id, user_id)
        
        # Verify business outcomes
        assert self.handler.supervisor.thread_id == thread_id
        assert self.handler.supervisor.user_id == user_id
        assert self.handler.supervisor.db_session is None
        
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_send_user_message_completion_sends_agent_response(self, mock_create_manager):
        """Test _send_user_message_completion sends agent response to user."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        user_id = "msg-completion-user-123"
        response = "Your optimization analysis is ready"
        
        # Execute business logic
        await self.handler._send_user_message_completion(user_id, response)
        
        # Verify business outcomes
        mock_manager.send_to_user.assert_called_once()
        call_args = mock_manager.send_to_user.call_args[0]
        
        assert call_args[0] == user_id
        message = call_args[1]
        assert message["type"] == "agent_completed"
        assert message["payload"] == response


@pytest.mark.unit
class TestThreadHistoryHandler(SSotBaseTestCase):
    """Test ThreadHistoryHandler business logic - enables conversation continuity."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_session_factory = Mock()
        self.handler = ThreadHistoryHandler(self.mock_db_session_factory)
        
    def test_handler_initialization(self):
        """Test ThreadHistoryHandler initializes correctly."""
        assert self.handler.db_session_factory == self.mock_db_session_factory
        assert self.handler.get_message_type() == "get_thread_history"
        
    @patch('netra_backend.app.services.websocket.message_handler.get_unit_of_work')
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_process_thread_history_request_retrieves_messages(self, mock_create_manager, mock_uow):
        """Test _process_thread_history_request retrieves and formats thread messages."""
        # Setup mocks
        mock_uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=mock_uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock thread retrieval
        mock_thread = Mock()
        mock_thread.id = "history-thread-123"
        mock_uow_instance.threads.get_or_create_for_user = AsyncMock(return_value=mock_thread)
        
        # Mock message retrieval
        mock_message = Mock()
        mock_message.id = "msg-123"
        mock_message.role = "user"
        mock_message.content = [{"text": {"value": "Original question"}}]
        mock_message.created_at = datetime.now(timezone.utc)
        
        mock_uow_instance.messages.get_thread_messages = AsyncMock(return_value=[mock_message])
        
        # Mock WebSocket manager
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        user_id = "history-user-123"
        payload = {"limit": 10}
        
        # Execute business logic
        await self.handler._process_thread_history_request(mock_uow_instance, user_id, payload)
        
        # Verify business outcomes
        mock_uow_instance.messages.get_thread_messages.assert_called_once_with(
            mock_uow_instance.session, "history-thread-123", limit=10
        )
        
        # Verify response sent to user
        mock_manager.send_to_user.assert_called_once()
        call_args = mock_manager.send_to_user.call_args[0]
        
        assert call_args[0] == user_id
        response = call_args[1]
        assert response["type"] == "thread_history"
        assert response["payload"]["thread_id"] == "history-thread-123"
        assert len(response["payload"]["messages"]) == 1
        
    def test_format_message_entry_structures_message_data(self):
        """Test _format_message_entry formats message for client consumption."""
        mock_message = Mock()
        mock_message.id = "format-msg-123"
        mock_message.role = "assistant"
        mock_message.created_at = datetime.now(timezone.utc)
        
        content = "Here are your optimization recommendations"
        
        # Execute business logic
        formatted = self.handler._format_message_entry(mock_message, content)
        
        # Verify business outcomes
        assert formatted["role"] == "assistant"
        assert formatted["content"] == content
        assert formatted["id"] == "format-msg-123"
        assert formatted["created_at"] == mock_message.created_at


@pytest.mark.unit
class TestStopAgentHandler(SSotBaseTestCase):
    """Test StopAgentHandler business logic - provides user control over AI processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supervisor = Mock()
        self.handler = StopAgentHandler(self.mock_supervisor)
        
    def test_handler_initialization(self):
        """Test StopAgentHandler initializes correctly."""
        assert self.handler.supervisor == self.mock_supervisor
        assert self.handler.get_message_type() == "stop_agent"
        
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_handle_sends_agent_stopped_notification(self, mock_create_manager):
        """Test handle sends agent stopped notification to user."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        user_id = "stop-user-123"
        payload = {}
        
        # Execute business logic
        await self.handler.handle(user_id, payload)
        
        # Verify business outcomes
        mock_manager.send_to_user.assert_called_once()
        call_args = mock_manager.send_to_user.call_args[0]
        
        assert call_args[0] == user_id
        message = call_args[1]
        assert message["type"] == "agent_stopped"
        assert message["payload"]["status"] == "stopped"


@pytest.mark.unit
class TestMessageHandlerService(SSotBaseTestCase):
    """Test MessageHandlerService business logic - CRITICAL for message orchestration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supervisor = Mock()
        self.mock_db_session_factory = Mock()
        
        self.service = MessageHandlerService(self.mock_supervisor, self.mock_db_session_factory)
        
    def test_service_initialization_creates_all_handlers(self):
        """Test MessageHandlerService initializes with all required handlers."""
        assert isinstance(self.service.handlers, dict)
        assert "start_agent" in self.service.handlers
        assert "user_message" in self.service.handlers
        assert "get_thread_history" in self.service.handlers
        assert "stop_agent" in self.service.handlers
        
        # Verify handler types
        assert isinstance(self.service.handlers["start_agent"], StartAgentHandler)
        assert isinstance(self.service.handlers["user_message"], UserMessageHandler)
        assert isinstance(self.service.handlers["get_thread_history"], ThreadHistoryHandler)
        assert isinstance(self.service.handlers["stop_agent"], StopAgentHandler)
        
    def test_register_handler_adds_to_handlers_and_queue(self):
        """Test register_handler adds handler to both registry and message queue."""
        # Create mock handler
        mock_handler = Mock(spec=BaseMessageHandler)
        mock_handler.get_message_type.return_value = "custom_message"
        mock_handler.handle = AsyncMock()
        
        with patch('netra_backend.app.services.websocket.message_handler.message_queue') as mock_queue:
            # Execute business logic
            self.service.register_handler(mock_handler)
            
            # Verify business outcomes
            assert "custom_message" in self.service.handlers
            assert self.service.handlers["custom_message"] == mock_handler
            mock_queue.register_handler.assert_called_once_with(
                "custom_message", mock_handler.handle
            )
            
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_validate_message_format_validates_with_manager(self, mock_create_manager):
        """Test _validate_message_format uses WebSocket manager for validation."""
        # Setup mocks
        mock_manager = Mock()
        mock_manager.validate_message.return_value = True
        mock_create_manager.return_value = mock_manager
        
        user_id = "validate-user-123"
        message = {"type": "test", "payload": {"data": "test"}}
        
        # Execute business logic
        result = await self.service._validate_message_format(user_id, message)
        
        # Verify business outcomes
        assert result is True
        mock_manager.validate_message.assert_called_once_with(message)
        
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_validate_message_format_sends_error_on_invalid(self, mock_create_manager):
        """Test _validate_message_format sends error for invalid messages."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_manager.validate_message.return_value = False
        mock_create_manager.return_value = mock_manager
        
        user_id = "invalid-user-123"
        message = {"invalid": "message"}
        
        # Execute business logic
        result = await self.service._validate_message_format(user_id, message)
        
        # Verify business outcomes
        assert result is False
        mock_manager.send_error.assert_called_once_with(user_id, "Invalid message format")
        
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_extract_message_type_validates_known_types(self, mock_create_manager):
        """Test _extract_message_type validates against registered handlers."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        user_id = "type-user-123"
        
        # Test valid message type
        valid_message = {"type": "start_agent", "payload": {}}
        result = await self.service._extract_message_type(user_id, valid_message)
        assert result == "start_agent"
        
        # Test invalid message type
        invalid_message = {"type": "unknown_type", "payload": {}}
        result = await self.service._extract_message_type(user_id, invalid_message)
        assert result is None
        mock_manager.send_error.assert_called_with(
            user_id, "Unknown message type: unknown_type"
        )
        
    def test_determine_priority_maps_message_types_correctly(self):
        """Test _determine_priority assigns correct priorities to message types."""
        from netra_backend.app.services.websocket.message_queue import MessagePriority
        
        # Test critical priority
        assert self.service._determine_priority("stop_agent") == MessagePriority.CRITICAL
        
        # Test high priority
        assert self.service._determine_priority("start_agent") == MessagePriority.HIGH
        
        # Test normal priority
        assert self.service._determine_priority("user_message") == MessagePriority.NORMAL
        
        # Test low priority
        assert self.service._determine_priority("get_thread_history") == MessagePriority.LOW
        
        # Test unknown type defaults to normal
        assert self.service._determine_priority("unknown") == MessagePriority.NORMAL
        
    @patch('netra_backend.app.services.websocket.message_handler.message_queue')
    async def test_sanitize_and_queue_message_creates_queued_message(self, mock_queue):
        """Test _sanitize_and_queue_message creates properly formatted queued message."""
        with patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager') as mock_create_manager:
            # Setup mocks
            mock_manager = Mock()
            mock_manager.sanitize_message.return_value = {"sanitized": "data"}
            mock_create_manager.return_value = mock_manager
            mock_queue.enqueue = AsyncMock(return_value=True)
            
            user_id = "queue-user-123"
            message = {"type": "start_agent", "payload": {"request": {"query": "test"}}}
            message_type = "start_agent"
            
            # Execute business logic
            await self.service._sanitize_and_queue_message(user_id, message, message_type)
            
            # Verify business outcomes
            mock_manager.sanitize_message.assert_called_once_with(message)
            mock_queue.enqueue.assert_called_once()
            
            # Verify queued message structure
            call_args = mock_queue.enqueue.call_args[0][0]
            assert call_args.user_id == user_id
            assert call_args.type == message_type
            assert call_args.payload == {"sanitized": "data"}
            
    @patch('netra_backend.app.services.websocket.message_handler.message_queue')
    async def test_get_stats_returns_comprehensive_statistics(self, mock_queue):
        """Test get_stats returns comprehensive service statistics."""
        # Setup mock queue stats
        mock_queue.get_queue_stats = AsyncMock(return_value={
            "pending_messages": 5,
            "processed_messages": 100
        })
        
        # Execute business logic
        stats = await self.service.get_stats()
        
        # Verify business outcomes
        assert "pending_messages" in stats
        assert "processed_messages" in stats
        assert stats["pending_messages"] == 5
        assert stats["processed_messages"] == 100


if __name__ == "__main__":
    pytest.main([__file__])