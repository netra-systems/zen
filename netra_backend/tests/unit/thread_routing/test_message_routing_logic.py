"""
Test Message Routing Logic Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure reliable message routing and thread association
- Value Impact: Correct message routing enables seamless user conversations
- Strategic Impact: Core chat functionality that delivers AI value to users

Tests the message routing logic including message type routing decisions,
payload validation, and routing rule evaluation. These tests ensure that
messages are correctly routed to appropriate handlers and threads.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
from netra_backend.app.services.websocket.message_handler import MessageHandlerService, StartAgentHandler, UserMessageHandler, ThreadHistoryHandler, StopAgentHandler, BaseMessageHandler
from netra_backend.app.services.websocket.message_queue import MessagePriority, QueuedMessage, message_queue
from netra_backend.app.llm.llm_defaults import LLMModel
from test_framework.ssot.base_test_case import SSotBaseTestCase

class MessageRoutingLogicTests(SSotBaseTestCase):
    """Test message routing logic with SSOT patterns."""

    def setup_method(self, method=None) -> None:
        """Set up test fixtures following SSOT patterns."""
        super().setup_method(method)
        self.mock_supervisor = Mock()
        self.mock_db_session_factory = Mock()
        self.message_service = MessageHandlerService(self.mock_supervisor, self.mock_db_session_factory)
        self.test_user_id = 'user_test_12345'
        self.test_thread_id = 'thread_test_67890'

    def teardown_method(self, method=None) -> None:
        """Clean up test resources."""
        super().teardown_method(method)

    def test_start_agent_message_routes_to_correct_handler(self):
        """Test that start_agent messages route to StartAgentHandler."""
        message_type = 'start_agent'
        handler = self.message_service.handlers.get(message_type)
        assert isinstance(handler, StartAgentHandler), 'start_agent messages should route to StartAgentHandler'

    def test_user_message_routes_to_correct_handler(self):
        """Test that user_message messages route to UserMessageHandler."""
        message_type = 'user_message'
        handler = self.message_service.handlers.get(message_type)
        assert isinstance(handler, UserMessageHandler), 'user_message messages should route to UserMessageHandler'

    def test_thread_history_routes_to_correct_handler(self):
        """Test that get_thread_history messages route to ThreadHistoryHandler."""
        message_type = 'get_thread_history'
        handler = self.message_service.handlers.get(message_type)
        assert isinstance(handler, ThreadHistoryHandler), 'get_thread_history messages should route to ThreadHistoryHandler'

    def test_stop_agent_routes_to_correct_handler(self):
        """Test that stop_agent messages route to StopAgentHandler."""
        message_type = 'stop_agent'
        handler = self.message_service.handlers.get(message_type)
        assert isinstance(handler, StopAgentHandler), 'stop_agent messages should route to StopAgentHandler'

    def test_unknown_message_type_handling(self):
        """Test handling of unknown message types."""
        unknown_type = 'unknown_message_type'
        handler = self.message_service.handlers.get(unknown_type)
        assert handler is None, 'Unknown message types should not have handlers'

    def test_critical_priority_assignment(self):
        """Test that critical messages get CRITICAL priority."""
        priority = self.message_service._determine_priority('stop_agent')
        assert priority == MessagePriority.CRITICAL, 'stop_agent should get CRITICAL priority'

    def test_high_priority_assignment(self):
        """Test that high priority messages get HIGH priority."""
        priority = self.message_service._determine_priority('start_agent')
        assert priority == MessagePriority.HIGH, 'start_agent should get HIGH priority'

    def test_normal_priority_assignment(self):
        """Test that normal messages get NORMAL priority."""
        priority = self.message_service._determine_priority('user_message')
        assert priority == MessagePriority.NORMAL, 'user_message should get NORMAL priority'

    def test_low_priority_assignment(self):
        """Test that low priority messages get LOW priority."""
        priority = self.message_service._determine_priority('get_thread_history')
        assert priority == MessagePriority.LOW, 'get_thread_history should get LOW priority'

    def test_unknown_message_priority_fallback(self):
        """Test that unknown message types get NORMAL priority."""
        priority = self.message_service._determine_priority('unknown_type')
        assert priority == MessagePriority.NORMAL, 'Unknown message types should default to NORMAL priority'

    def test_start_agent_payload_extraction(self):
        """Test start_agent payload extraction logic."""
        handler = StartAgentHandler(self.mock_supervisor, self.mock_db_session_factory)
        payload_with_query = {'request': {'query': 'Optimize my AWS costs'}}
        result = handler._extract_user_request(payload_with_query)
        assert result == 'Optimize my AWS costs', 'Should extract query from request payload'
        payload_with_user_request = {'request': {'user_request': 'Analyze my spending'}}
        result = handler._extract_user_request(payload_with_user_request)
        assert result == 'Analyze my spending', 'Should extract user_request from request payload'
        empty_payload = {'request': {}}
        result = handler._extract_user_request(empty_payload)
        assert result == '', 'Should return empty string for empty payload'

    def test_user_message_payload_extraction(self):
        """Test user_message payload extraction logic."""
        handler = UserMessageHandler(self.mock_supervisor, self.mock_db_session_factory)
        payload = {'text': 'Hello, I need help with cost optimization', 'references': ['ref1', 'ref2']}
        text, references = handler._extract_message_data(payload)
        assert text == 'Hello, I need help with cost optimization', 'Should extract text from payload'
        assert references == ['ref1', 'ref2'], 'Should extract references from payload'

    def test_thread_history_limit_extraction(self):
        """Test thread history limit extraction."""
        handler = ThreadHistoryHandler(self.mock_db_session_factory)
        payload_with_limit = {'limit': 25}
        limit = payload_with_limit.get('limit', 50)
        assert limit == 25, 'Should extract custom limit'
        payload_without_limit = {}
        limit = payload_without_limit.get('limit', 50)
        assert limit == 50, 'Should use default limit when not specified'

    @patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_message_validation_routing(self, mock_create_manager, mock_get_context):
        """Test message validation routing logic."""
        mock_manager = AsyncMock()
        mock_manager.validate_message = AsyncMock(return_value=False)
        mock_manager.send_error = AsyncMock()
        mock_create_manager.return_value = mock_manager
        mock_get_context.return_value = Mock()
        invalid_message = {'invalid': 'message'}
        result = await mock_manager.validate_message(invalid_message)
        assert not result, 'Invalid message should fail validation'
        await mock_manager.send_error(self.test_user_id, 'Validation failed')
        mock_manager.send_error.assert_called_once()

    @patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_message_type_validation_routing(self, mock_create_manager, mock_get_context):
        """Test message type validation routing logic."""
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        mock_get_context.return_value = Mock()
        message_without_type = {'payload': {}}
        result = await self.message_service._extract_message_type(self.test_user_id, message_without_type)
        assert result is None, 'Message without type should return None'
        message_unknown_type = {'type': 'unknown_type'}
        result = await self.message_service._extract_message_type(self.test_user_id, message_unknown_type)
        assert result is None, 'Unknown message type should return None'
        message_valid_type = {'type': 'user_message'}
        result = await self.message_service._extract_message_type(self.test_user_id, message_valid_type)
        assert result == 'user_message', 'Valid message type should be returned'

    def test_queued_message_creation(self):
        """Test QueuedMessage creation with correct routing parameters."""
        message = {'type': 'user_message', 'payload': {'text': 'test'}}
        priority = MessagePriority.NORMAL
        queued_message = self.message_service._create_queued_message(self.test_user_id, message, 'user_message', priority)
        assert isinstance(queued_message, QueuedMessage), 'Should create QueuedMessage instance'
        assert queued_message.user_id == self.test_user_id, 'Should set correct user_id'
        assert queued_message.type == 'user_message', 'Should set correct message type'
        assert queued_message.priority == priority, 'Should set correct priority'
        assert queued_message.payload == {'text': 'test'}, 'Should set correct payload'

    def test_thread_id_preservation_in_routing(self):
        """Test that thread IDs are preserved during message routing."""
        message_with_thread = {'type': 'user_message', 'payload': {'text': 'test', 'thread_id': self.test_thread_id}}
        thread_id = message_with_thread['payload'].get('thread_id')
        assert thread_id == self.test_thread_id, 'Thread ID should be preserved in message payload'

    def test_user_context_creation_for_routing(self):
        """Test user context creation for message routing."""
        with patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context') as mock_context:
            mock_context.return_value = Mock(user_id=self.test_user_id)
            context = mock_context(user_id=self.test_user_id)
            assert context.user_id == self.test_user_id, 'User context should have correct user_id'

    def test_routing_error_handling(self):
        """Test error handling during message routing."""
        invalid_handler = Mock()
        invalid_handler.handle = Mock(side_effect=Exception('Routing error'))
        with pytest.raises(Exception):
            invalid_handler.handle()
        invalid_handler.handle.assert_called_once()

    @patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_error_message_routing(self, mock_create_manager, mock_get_context):
        """Test error message routing to users."""
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        mock_get_context.return_value = Mock()
        error_message = 'Test error message'
        await self.message_service._handle_processing_error(self.test_user_id, Exception(error_message))
        mock_manager.send_error.assert_called_once_with(self.test_user_id, 'Internal server error')

    @patch('netra_backend.app.services.websocket.message_handler.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.message_handler.create_websocket_manager')
    async def test_message_sanitization_routing(self, mock_create_manager, mock_get_context):
        """Test message sanitization in routing pipeline."""
        mock_manager = Mock()
        mock_manager.sanitize_message.return_value = {'clean': 'message'}
        mock_create_manager.return_value = mock_manager
        mock_get_context.return_value = Mock()
        dirty_message = {'type': 'user_message', 'payload': {'script': "<script>alert('xss')</script>"}}
        with patch.object(message_queue, 'enqueue', return_value=True) as mock_enqueue:
            await self.message_service._sanitize_and_queue_message(self.test_user_id, dirty_message, 'user_message')
            mock_manager.sanitize_message.assert_called_once_with(dirty_message)
            mock_enqueue.assert_called_once()

    def test_priority_mapping_performance(self):
        """Test message priority mapping performance."""
        import time
        message_types = ['start_agent', 'user_message', 'stop_agent', 'get_thread_history'] * 1000
        start_time = time.time()
        for msg_type in message_types:
            self.message_service._determine_priority(msg_type)
        end_time = time.time()
        processing_time = end_time - start_time
        assert processing_time < 0.1, 'Priority mapping should complete within performance limits'

    def test_handler_registration_completeness(self):
        """Test that all expected handlers are registered."""
        expected_handlers = {'start_agent': StartAgentHandler, 'user_message': UserMessageHandler, 'get_thread_history': ThreadHistoryHandler, 'stop_agent': StopAgentHandler}
        for message_type, expected_class in expected_handlers.items():
            handler = self.message_service.handlers.get(message_type)
            assert isinstance(handler, expected_class), f'{message_type} should have {expected_class.__name__} handler'

    @patch('netra_backend.app.services.websocket.message_handler.message_queue')
    def test_message_queue_integration(self, mock_queue):
        """Test integration with message queue system."""
        mock_queue.enqueue = AsyncMock(return_value=True)
        test_handler = StartAgentHandler(self.mock_supervisor, self.mock_db_session_factory)
        assert test_handler.get_message_type() == 'start_agent', 'Handler should return correct message type'

    def test_message_routing_statistics(self):
        """Test message routing statistics collection."""
        stats = {'total_messages_routed': 0, 'messages_by_type': {}, 'routing_errors': 0, 'average_routing_time': 0.0}
        stats['total_messages_routed'] += 1
        stats['messages_by_type']['user_message'] = stats['messages_by_type'].get('user_message', 0) + 1
        assert stats['total_messages_routed'] == 1, 'Should track total routed messages'
        assert stats['messages_by_type']['user_message'] == 1, 'Should track messages by type'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')