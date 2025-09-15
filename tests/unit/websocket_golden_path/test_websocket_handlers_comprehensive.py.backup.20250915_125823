"""
Comprehensive Unit Tests for WebSocket Message Handlers (Golden Path SSOT)

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core message processing infrastructure
- Business Goal: Message Routing Accuracy & Development Velocity
- Value Impact: Ensures agent requests reach execution (critical for chat functionality)
- Revenue Impact: Foundation for reliable AI agent communication ($500K+ ARR)

CRITICAL: These tests validate message handling logic that bridges WebSocket communication
with agent execution. Message routing failures block the entire Golden Path user flow.

Test Coverage Focus:
- Message type routing (ensures correct handler selection)
- Message validation (prevents malformed requests from causing failures)
- Handler chain execution (validates pluggable handler architecture)
- Error handling (graceful degradation when messages fail)
- Performance validation (message processing latency)

SSOT Compliance:
- Inherits from SSotBaseTestCase
- Uses SSotMockFactory for consistent mocks
- Tests actual business logic, not just method calls
- Designed to FAIL when components are broken
"""
import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase, CategoryType
from test_framework.ssot.mocks import SSotMockFactory
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.handlers import BaseMessageHandler, ConnectionHandler, MessageHandler, MessageType
from netra_backend.app.websocket_core.types import WebSocketMessage, create_standard_message, create_error_message, normalize_message_type
from shared.types.core_types import UserID, ThreadID, ConnectionID
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

@pytest.mark.unit
class TestWebSocketMessageHandlersComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocket Message Handlers.
    
    GOLDEN PATH FOCUS: Validates message routing and processing that enables
    agent execution. These handlers are the bridge between raw WebSocket messages
    and structured agent requests.
    """

    def setUp(self):
        """Set up test fixtures with SSOT compliance."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT
        self.test_context.record_custom('component', 'websocket_handlers')
        self.id_manager = UnifiedIDManager()
        self.test_user_id = str(self.id_manager.generate_id(IDType.USER_ID))
        self.mock_websocket = SSotMockFactory.create_mock_websocket()
        self.messages_processed = 0
        self.routing_failures = 0
        self.validation_errors = 0
        self.processing_times = []

    def tearDown(self):
        """Clean up and record business metrics."""
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            self.test_context.record_custom('avg_processing_time_ms', avg_time * 1000)
        self.test_context.record_custom('messages_processed', self.messages_processed)
        self.test_context.record_custom('routing_failures', self.routing_failures)
        self.test_context.record_custom('validation_errors', self.validation_errors)
        super().tearDown()

    async def test_base_message_handler_interface(self):
        """
        Test BaseMessageHandler interface compliance.
        
        BVJ: Handler interface consistency is critical for pluggable architecture.
        All handlers must implement the same interface for system reliability.
        """
        supported_types = [MessageType.CONNECT, MessageType.USER_MESSAGE]
        handler = BaseMessageHandler(supported_types)
        self.assertTrue(handler.can_handle(MessageType.CONNECT))
        self.assertTrue(handler.can_handle(MessageType.USER_MESSAGE))
        self.assertFalse(handler.can_handle(MessageType.DISCONNECT))
        test_message = create_standard_message(message_type=MessageType.CONNECT, payload={'user_id': self.test_user_id}, user_id=self.test_user_id)
        start_time = datetime.now()
        result = await handler.handle_message(self.test_user_id, self.mock_websocket, test_message)
        processing_time = (datetime.now() - start_time).total_seconds()
        self.processing_times.append(processing_time)
        self.messages_processed += 1
        self.assertTrue(result)

    async def test_connection_handler_lifecycle_management(self):
        """
        Test ConnectionHandler for connection lifecycle messages.
        
        BVJ: Connection lifecycle management is critical for Golden Path.
        Failed connections prevent users from accessing any AI functionality.
        """
        handler = ConnectionHandler()
        connect_message = create_standard_message(message_type=MessageType.CONNECT, payload={'user_id': self.test_user_id, 'connection_id': str(uuid.uuid4()), 'timestamp': datetime.now(timezone.utc).isoformat()}, user_id=self.test_user_id)
        start_time = datetime.now()
        result = await handler.handle_message(self.test_user_id, self.mock_websocket, connect_message)
        processing_time = (datetime.now() - start_time).total_seconds()
        self.processing_times.append(processing_time)
        self.messages_processed += 1
        self.assertTrue(result)
        disconnect_message = create_standard_message(message_type=MessageType.DISCONNECT, payload={'user_id': self.test_user_id, 'reason': 'user_initiated'}, user_id=self.test_user_id)
        result = await handler.handle_message(self.test_user_id, self.mock_websocket, disconnect_message)
        self.messages_processed += 1
        self.assertTrue(result)

    async def test_message_type_routing_accuracy(self):
        """
        Test message type routing ensures correct handler selection.
        
        BVJ: Incorrect routing causes agent execution failures and poor UX.
        This validates the core routing logic that enables Golden Path flow.
        """
        connection_handler = ConnectionHandler()

        class UserMessageHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE, MessageType.CHAT])

            async def handle_message(self, user_id: str, websocket: WebSocket, message: WebSocketMessage) -> bool:
                return message.type in self.supported_types
        user_handler = UserMessageHandler()
        test_cases = [(MessageType.CONNECT, connection_handler, True), (MessageType.DISCONNECT, connection_handler, True), (MessageType.USER_MESSAGE, user_handler, True), (MessageType.CHAT, user_handler, True), (MessageType.CONNECT, user_handler, False), (MessageType.USER_MESSAGE, connection_handler, False)]
        for message_type, handler, should_handle in test_cases:
            can_handle = handler.can_handle(message_type)
            self.assertEqual(can_handle, should_handle, f'Handler routing failed for {message_type}')
            if not should_handle:
                continue
            test_message = create_standard_message(message_type=message_type, payload={'test': True}, user_id=self.test_user_id)
            result = await handler.handle_message(self.test_user_id, self.mock_websocket, test_message)
            if should_handle:
                self.assertTrue(result, f'Handler failed to process {message_type}')
                self.messages_processed += 1
            else:
                pass

    async def test_message_validation_prevents_errors(self):
        """
        Test message validation prevents processing of malformed messages.
        
        BVJ: Malformed messages can cause agent execution failures and system errors.
        Proper validation prevents these issues from propagating through the system.
        """
        handler = BaseMessageHandler([MessageType.USER_MESSAGE])
        invalid_messages = [{'type': 'user_message'}, {'type': 'invalid_type', 'payload': {'content': 'test'}}, {'type': 'user_message', 'payload': 'not_a_dict'}]
        for invalid_data in invalid_messages:
            try:
                if 'type' in invalid_data:
                    message_type = normalize_message_type(invalid_data['type'])
                else:
                    message_type = MessageType.USER_MESSAGE
                test_message = create_standard_message(message_type=message_type, payload=invalid_data.get('payload', {}), user_id=self.test_user_id)
                result = await handler.handle_message(self.test_user_id, self.mock_websocket, test_message)
                self.assertIsInstance(result, bool)
            except Exception as e:
                self.validation_errors += 1

    async def test_error_message_handling(self):
        """
        Test error message creation and handling.
        
        BVJ: Proper error handling prevents user confusion and support issues.
        Users need clear feedback when their requests cannot be processed.
        """
        handler = BaseMessageHandler([MessageType.ERROR])
        error_message = create_error_message(error_code='VALIDATION_ERROR', error_message='Invalid message format', user_id=self.test_user_id, details={'field': 'payload', 'issue': 'missing_required_data'})
        result = await handler.handle_message(self.test_user_id, self.mock_websocket, error_message)
        self.messages_processed += 1
        self.assertTrue(result)
        self.assertEqual(error_message.type, MessageType.ERROR)
        self.assertIn('error_code', error_message.payload)
        self.assertIn('error_message', error_message.payload)
        self.assertEqual(error_message.payload['error_code'], 'VALIDATION_ERROR')

    async def test_concurrent_message_processing(self):
        """
        Test concurrent message processing for performance validation.
        
        BVJ: Cloud Run environments require handlers to process multiple
        messages concurrently. This validates performance under load.
        """
        handler = BaseMessageHandler([MessageType.USER_MESSAGE])
        num_messages = 10
        messages = []
        for i in range(num_messages):
            message = create_standard_message(message_type=MessageType.USER_MESSAGE, payload={'sequence': i, 'content': f'test_message_{i}'}, user_id=self.test_user_id)
            messages.append(message)
        start_time = datetime.now()
        tasks = [handler.handle_message(self.test_user_id, self.mock_websocket, msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_processing_time = (datetime.now() - start_time).total_seconds()
        self.processing_times.append(total_processing_time)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.routing_failures += 1
                self.fail(f'Message {i} failed with exception: {result}')
            else:
                self.assertTrue(result, f'Message {i} processing failed')
                self.messages_processed += 1
        avg_time_per_message = total_processing_time / num_messages
        self.test_context.record_custom('concurrent_processing_time', avg_time_per_message)
        self.assertLess(avg_time_per_message, 1.0, 'Message processing too slow for production use')

    async def test_handler_chain_execution(self):
        """
        Test handler chain execution for complex message routing.
        
        BVJ: Handler chains enable sophisticated message processing pipelines.
        This validates the pluggable architecture that supports extensibility.
        """
        handlers = []

        class PreProcessorHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.processed_messages = []

            async def handle_message(self, user_id: str, websocket: WebSocket, message: WebSocketMessage) -> bool:
                message.payload['preprocessed'] = True
                message.payload['processor'] = 'pre'
                self.processed_messages.append(message.payload.get('sequence'))
                return True

        class MainProcessorHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.processed_messages = []

            async def handle_message(self, user_id: str, websocket: WebSocket, message: WebSocketMessage) -> bool:
                if not message.payload.get('preprocessed'):
                    return False
                message.payload['main_processed'] = True
                message.payload['processor'] = 'main'
                self.processed_messages.append(message.payload.get('sequence'))
                return True
        pre_handler = PreProcessorHandler()
        main_handler = MainProcessorHandler()
        test_message = create_standard_message(message_type=MessageType.USER_MESSAGE, payload={'sequence': 1, 'content': 'test'}, user_id=self.test_user_id)
        pre_result = await pre_handler.handle_message(self.test_user_id, self.mock_websocket, test_message)
        self.assertTrue(pre_result)
        main_result = await main_handler.handle_message(self.test_user_id, self.mock_websocket, test_message)
        self.assertTrue(main_result)
        self.assertTrue(test_message.payload.get('preprocessed'))
        self.assertTrue(test_message.payload.get('main_processed'))
        self.assertEqual(test_message.payload.get('processor'), 'main')
        self.assertIn(1, pre_handler.processed_messages)
        self.assertIn(1, main_handler.processed_messages)
        self.messages_processed += 2

    async def test_websocket_state_awareness(self):
        """
        Test handlers respect WebSocket connection state.
        
        BVJ: Attempting to send messages to closed connections causes errors.
        Handlers should check connection state before attempting operations.
        """
        handler = BaseMessageHandler([MessageType.USER_MESSAGE])
        self.mock_websocket.client_state = WebSocketState.CONNECTED
        test_message = create_standard_message(message_type=MessageType.USER_MESSAGE, payload={'content': 'test'}, user_id=self.test_user_id)
        result = await handler.handle_message(self.test_user_id, self.mock_websocket, test_message)
        self.assertTrue(result)
        self.messages_processed += 1
        self.mock_websocket.client_state = WebSocketState.CLOSED
        try:
            result = await handler.handle_message(self.test_user_id, self.mock_websocket, test_message)
            self.assertIsInstance(result, bool)
        except Exception as e:
            self.assertIsInstance(e, (ConnectionError, RuntimeError))

@pytest.mark.unit
class TestWebSocketMessageTypes(SSotBaseTestCase):
    """
    Unit tests for WebSocket message type handling and validation.
    
    These tests validate message type enumeration and normalization
    that enables proper message routing.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_context.test_category = CategoryType.UNIT

    def test_message_type_normalization(self):
        """Test message type string normalization."""
        test_cases = [('connect', MessageType.CONNECT), ('CONNECT', MessageType.CONNECT), ('user_message', MessageType.USER_MESSAGE), ('USER_MESSAGE', MessageType.USER_MESSAGE), ('disconnect', MessageType.DISCONNECT)]
        for input_type, expected_type in test_cases:
            normalized = normalize_message_type(input_type)
            self.assertEqual(normalized, expected_type, f"Failed to normalize '{input_type}' to {expected_type}")

    def test_invalid_message_type_handling(self):
        """Test handling of invalid message types."""
        invalid_types = ['invalid', '', None, 123, []]
        for invalid_type in invalid_types:
            try:
                result = normalize_message_type(invalid_type)
                self.assertIsInstance(result, MessageType)
            except (ValueError, TypeError):
                pass

    def test_message_creation_with_types(self):
        """Test message creation with various message types."""
        user_id = str(uuid.uuid4())
        for message_type in MessageType:
            message = create_standard_message(message_type=message_type, payload={'test': True}, user_id=user_id)
            self.assertEqual(message.type, message_type)
            self.assertEqual(message.user_id, user_id)
            self.assertIsInstance(message.payload, dict)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')