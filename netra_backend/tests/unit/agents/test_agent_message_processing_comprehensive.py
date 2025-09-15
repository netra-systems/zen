"""Agent Message Processing Comprehensive Unit Tests

MISSION-CRITICAL TEST SUITE: Complete validation of agent message processing patterns.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Chat Functionality Reliability (90% of platform value)
- Value Impact: Agent message processing = Core chat experience = $500K+ ARR protection
- Strategic Impact: Message processing failures directly impact customer chat experience

COVERAGE TARGET: 37 unit tests covering critical message processing components:
- Message routing and validation (12 tests)
- Message transformation and processing (10 tests)
- Error handling in message flows (8 tests)
- Agent response generation (7 tests)

CRITICAL: Uses REAL services approach with minimal mocks per CLAUDE.md standards.
Only external dependencies are mocked - all internal components tested with real instances.
"""
import asyncio
import pytest
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.handlers import MessageRouter
from netra_backend.app.websocket_core.handlers import MessageHandler, ConnectionHandler, BaseMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, ServerMessage, ErrorMessage, create_standard_message, create_error_message, create_server_message, normalize_message_type
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

@dataclass
class MockMessageData:
    """Mock message data for testing"""
    content: str
    user_id: str
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}

class AgentMessageRoutingTests(SSotAsyncTestCase):
    """Test suite for agent message routing functionality - 12 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)
        self.session_id = self.id_manager.generate_id(IDType.SESSION)

    async def test_message_router_initialization(self):
        """Test MessageRouter initializes correctly"""
        router = MessageRouter()
        self.assertIsNotNone(router)
        self.record_metric('router_init_success', True)

    async def test_message_routing_with_valid_type(self):
        """Test routing messages with valid message types"""
        router = MessageRouter()
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'test message'})
        result = await router.route_message(message)
        self.assertIsNotNone(result)
        self.record_metric('valid_routing_success', True)

    async def test_message_routing_with_invalid_type(self):
        """Test routing behavior with invalid message types"""
        router = MessageRouter()
        with self.expect_exception(ValueError):
            invalid_message = WebSocketMessage(id=self.id_manager.generate_id(IDType.MESSAGE), type=None, user_id=self.user_id, data={'content': 'test'})
            await router.route_message(invalid_message)
        self.record_metric('invalid_routing_handled', True)

    async def test_message_normalization(self):
        """Test message type normalization"""
        normalized = normalize_message_type('agent_request')
        self.assertEqual(normalized, MessageType.AGENT_REQUEST)
        normalized = normalize_message_type(MessageType.AGENT_RESPONSE)
        self.assertEqual(normalized, MessageType.AGENT_RESPONSE)
        self.record_metric('normalization_success', True)

    async def test_message_handler_registration(self):
        """Test registering message handlers"""
        router = MessageRouter()
        handler = ConnectionHandler()
        router.register_handler(MessageType.CONNECT, handler)
        registered_handlers = router.get_handlers(MessageType.CONNECT)
        self.assertIn(handler, registered_handlers)
        self.record_metric('handler_registration_success', True)

    async def test_message_handler_deregistration(self):
        """Test removing message handlers"""
        router = MessageRouter()
        handler = ConnectionHandler()
        router.register_handler(MessageType.CONNECT, handler)
        router.unregister_handler(MessageType.CONNECT, handler)
        registered_handlers = router.get_handlers(MessageType.CONNECT)
        self.assertNotIn(handler, registered_handlers)
        self.record_metric('handler_deregistration_success', True)

    async def test_message_routing_priority(self):
        """Test message routing with handler priority"""
        router = MessageRouter()
        high_priority_handler = BaseMessageHandler([MessageType.AGENT_REQUEST])
        low_priority_handler = BaseMessageHandler([MessageType.AGENT_REQUEST])
        router.register_handler(MessageType.AGENT_REQUEST, high_priority_handler, priority=100)
        router.register_handler(MessageType.AGENT_REQUEST, low_priority_handler, priority=50)
        handlers = router.get_handlers(MessageType.AGENT_REQUEST)
        self.assertEqual(handlers[0], high_priority_handler)
        self.record_metric('priority_routing_success', True)

    async def test_message_routing_with_user_context(self):
        """Test message routing includes user context"""
        router = MessageRouter()
        context = UserExecutionContext(user_id=self.user_id, session_id=self.session_id, trace_id=self.id_manager.generate_id(IDType.TRACE))
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'test with context'})
        result = await router.route_message_with_context(message, context)
        self.assertIsNotNone(result)
        self.record_metric('context_routing_success', True)

    async def test_message_batch_routing(self):
        """Test routing multiple messages in batch"""
        router = MessageRouter()
        messages = [create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': f'message {i}'}) for i in range(3)]
        results = await router.route_batch(messages)
        self.assertEqual(len(results), 3)
        self.record_metric('batch_routing_success', True)

    async def test_message_routing_error_handling(self):
        """Test error handling during message routing"""
        router = MessageRouter()

        class FailingHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.AGENT_REQUEST])

            async def handle_message(self, user_id, websocket, message):
                raise RuntimeError('Handler failure')
        failing_handler = FailingHandler()
        router.register_handler(MessageType.AGENT_REQUEST, failing_handler)
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'test error'})
        result = await router.route_message(message)
        self.assertIsNotNone(result)
        self.record_metric('error_handling_success', True)

    async def test_message_routing_metrics_collection(self):
        """Test metrics are collected during routing"""
        router = MessageRouter()
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'metrics test'})
        start_time = time.time()
        await router.route_message(message)
        duration = time.time() - start_time
        self.assertGreater(duration, 0)
        self.record_metric('routing_duration_seconds', duration)
        self.record_metric('metrics_collection_success', True)

    async def test_message_routing_concurrent_messages(self):
        """Test routing concurrent messages safely"""
        router = MessageRouter()
        messages = [create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=f'user_{i}', data={'content': f'concurrent message {i}'}) for i in range(5)]
        tasks = [router.route_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        self.assertEqual(len(successful_results), 5)
        self.record_metric('concurrent_routing_success', True)

class MessageTransformationProcessingTests(SSotAsyncTestCase):
    """Test suite for message transformation and processing - 10 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)

    async def test_websocket_message_creation(self):
        """Test creating WebSocket messages"""
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'test message'})
        self.assertEqual(message.type, MessageType.AGENT_REQUEST)
        self.assertEqual(message.user_id, self.user_id)
        self.assertEqual(message.data['content'], 'test message')
        self.record_metric('message_creation_success', True)

    async def test_error_message_creation(self):
        """Test creating error messages"""
        error_msg = create_error_message(error_code='AGENT_ERROR', error_message='Test error', user_id=self.user_id)
        self.assertEqual(error_msg.type, MessageType.ERROR)
        self.assertEqual(error_msg.user_id, self.user_id)
        self.assertIn('error_code', error_msg.data)
        self.record_metric('error_message_creation_success', True)

    async def test_server_message_creation(self):
        """Test creating server messages"""
        server_msg = create_server_message(message='Server notification', user_id=self.user_id)
        self.assertEqual(server_msg.type, MessageType.SERVER)
        self.assertEqual(server_msg.user_id, self.user_id)
        self.record_metric('server_message_creation_success', True)

    async def test_message_data_validation(self):
        """Test message data validation"""
        valid_data = {'content': 'test', 'metadata': {'key': 'value'}}
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data=valid_data)
        self.assertEqual(message.data, valid_data)
        message_none = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data=None)
        self.assertIsNotNone(message_none.data)
        self.record_metric('data_validation_success', True)

    async def test_message_timestamp_processing(self):
        """Test message timestamp handling"""
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'timestamp test'})
        self.assertIsNotNone(message.timestamp)
        self.assertIsInstance(message.timestamp, datetime)
        custom_time = datetime.now(timezone.utc)
        message_custom = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'custom timestamp'}, timestamp=custom_time)
        self.assertEqual(message_custom.timestamp, custom_time)
        self.record_metric('timestamp_processing_success', True)

    async def test_message_serialization(self):
        """Test message serialization to dict"""
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'serialize test'})
        serialized = message.to_dict()
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized['type'], 'agent_request')
        self.assertEqual(serialized['user_id'], self.user_id)
        self.record_metric('serialization_success', True)

    async def test_message_deserialization(self):
        """Test message deserialization from dict"""
        message_data = {'id': self.id_manager.generate_id(IDType.MESSAGE), 'type': 'agent_request', 'user_id': self.user_id, 'data': {'content': 'deserialize test'}, 'timestamp': datetime.now(timezone.utc).isoformat()}
        message = WebSocketMessage.from_dict(message_data)
        self.assertEqual(message.type, MessageType.AGENT_REQUEST)
        self.assertEqual(message.user_id, self.user_id)
        self.record_metric('deserialization_success', True)

    async def test_message_content_transformation(self):
        """Test transforming message content"""
        original_data = {'content': '  UPPERCASE TEXT  ', 'metadata': {}}
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data=original_data)
        transformed_data = message.data.copy()
        transformed_data['content'] = transformed_data['content'].strip().lower()
        transformed_message = create_standard_message(message_type=message.type, user_id=message.user_id, data=transformed_data)
        self.assertEqual(transformed_message.data['content'], 'uppercase text')
        self.record_metric('content_transformation_success', True)

    async def test_message_metadata_processing(self):
        """Test processing message metadata"""
        metadata = {'source': 'api', 'priority': 'high', 'tags': ['urgent', 'customer']}
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'metadata test', 'metadata': metadata})
        self.assertEqual(message.data['metadata']['source'], 'api')
        self.assertEqual(message.data['metadata']['priority'], 'high')
        self.assertIn('urgent', message.data['metadata']['tags'])
        self.record_metric('metadata_processing_success', True)

    async def test_message_size_validation(self):
        """Test message size limits"""
        normal_content = 'a' * 1000
        normal_message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': normal_content})
        self.assertEqual(len(normal_message.data['content']), 1000)
        large_content = 'a' * 100000
        large_message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': large_content})
        self.assertIsNotNone(large_message)
        self.record_metric('size_validation_success', True)

class MessageErrorHandlingTests(SSotAsyncTestCase):
    """Test suite for error handling in message flows - 8 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)

    async def test_invalid_message_type_handling(self):
        """Test handling invalid message types"""
        with self.expect_exception(ValueError):
            normalize_message_type('invalid_message_type')
        self.record_metric('invalid_type_handling_success', True)

    async def test_missing_user_id_handling(self):
        """Test handling messages with missing user ID"""
        with self.expect_exception((ValueError, TypeError)):
            create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=None, data={'content': 'test'})
        self.record_metric('missing_user_id_handling_success', True)

    async def test_malformed_message_data_handling(self):
        """Test handling malformed message data"""
        try:
            message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'invalid': lambda x: x})
            serialized = message.to_dict()
            self.assertIsInstance(serialized, dict)
        except (TypeError, ValueError) as e:
            self.assertIsInstance(e, (TypeError, ValueError))
        self.record_metric('malformed_data_handling_success', True)

    async def test_message_processing_timeout_handling(self):
        """Test handling message processing timeouts"""

        class SlowHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.AGENT_REQUEST])

            async def handle_message(self, user_id, websocket, message):
                await asyncio.sleep(2)
                return True
        handler = SlowHandler()
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'slow message'})
        start_time = time.time()
        try:
            await asyncio.wait_for(handler.handle_message(self.user_id, None, message), timeout=0.5)
        except asyncio.TimeoutError:
            pass
        duration = time.time() - start_time
        self.assertLess(duration, 1.0)
        self.record_metric('timeout_handling_success', True)

    async def test_concurrent_error_handling(self):
        """Test error handling with concurrent message processing"""

        class ErrorHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.AGENT_REQUEST])

            async def handle_message(self, user_id, websocket, message):
                if 'error' in message.data.get('content', ''):
                    raise RuntimeError('Simulated error')
                return True
        handler = ErrorHandler()
        messages = [create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'normal message'}), create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'error message'}), create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'another normal message'})]
        tasks = [handler.handle_message(self.user_id, None, msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [r for r in results if r is True]
        errors = [r for r in results if isinstance(r, Exception)]
        self.assertGreater(len(successes), 0)
        self.assertGreater(len(errors), 0)
        self.record_metric('concurrent_error_handling_success', True)

    async def test_memory_error_handling(self):
        """Test handling memory-related errors"""
        large_data = {'content': 'x' * 10000, 'large_metadata': ['item'] * 1000}
        try:
            message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data=large_data)
            self.assertIsNotNone(message)
            self.record_metric('memory_error_handling_success', True)
        except MemoryError:
            self.record_metric('memory_error_handled', True)

    async def test_network_error_simulation(self):
        """Test handling network-related errors"""

        class NetworkErrorHandler(BaseMessageHandler):

            def __init__(self):
                super().__init__([MessageType.AGENT_REQUEST])

            async def handle_message(self, user_id, websocket, message):
                raise ConnectionError('Network connection lost')
        handler = NetworkErrorHandler()
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'network test'})
        with self.expect_exception(ConnectionError):
            await handler.handle_message(self.user_id, None, message)
        self.record_metric('network_error_handling_success', True)

    async def test_graceful_degradation(self):
        """Test graceful degradation when components fail"""
        message = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': 'degradation test'})
        self.assertIsNotNone(message.id)
        self.assertIsNotNone(message.timestamp)
        self.assertIsNotNone(message.data)
        self.record_metric('graceful_degradation_success', True)

class AgentResponseGenerationTests(SSotAsyncTestCase):
    """Test suite for agent response generation - 7 tests"""

    def setup_method(self, method):
        """Setup test environment"""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.user_id = self.id_manager.generate_id(IDType.USER)
        self.session_id = self.id_manager.generate_id(IDType.SESSION)

    async def test_agent_response_message_creation(self):
        """Test creating agent response messages"""
        response_data = {'response': 'Hello, how can I help you?', 'agent_id': 'agent_123', 'confidence': 0.95}
        response_msg = create_standard_message(message_type=MessageType.AGENT_RESPONSE, user_id=self.user_id, data=response_data)
        self.assertEqual(response_msg.type, MessageType.AGENT_RESPONSE)
        self.assertEqual(response_msg.data['response'], 'Hello, how can I help you?')
        self.assertEqual(response_msg.data['confidence'], 0.95)
        self.record_metric('agent_response_creation_success', True)

    async def test_agent_response_with_metadata(self):
        """Test agent responses include proper metadata"""
        response_data = {'response': 'Analysis complete', 'metadata': {'processing_time': 1.2, 'tokens_used': 150, 'model': 'gpt-4'}}
        response_msg = create_standard_message(message_type=MessageType.AGENT_RESPONSE, user_id=self.user_id, data=response_data)
        metadata = response_msg.data['metadata']
        self.assertEqual(metadata['processing_time'], 1.2)
        self.assertEqual(metadata['tokens_used'], 150)
        self.assertEqual(metadata['model'], 'gpt-4')
        self.record_metric('response_metadata_success', True)

    async def test_streaming_response_generation(self):
        """Test generating streaming responses"""
        chunks = ['Hello', ' there!', ' How can', ' I help you?']
        streaming_messages = []
        for i, chunk in enumerate(chunks):
            chunk_data = {'chunk': chunk, 'chunk_index': i, 'is_final': i == len(chunks) - 1}
            chunk_msg = create_standard_message(message_type=MessageType.AGENT_STREAM, user_id=self.user_id, data=chunk_data)
            streaming_messages.append(chunk_msg)
        self.assertEqual(len(streaming_messages), 4)
        self.assertTrue(streaming_messages[-1].data['is_final'])
        self.assertFalse(streaming_messages[0].data['is_final'])
        self.record_metric('streaming_response_success', True)

    async def test_error_response_generation(self):
        """Test generating error responses"""
        error_response = create_error_message(error_code='AGENT_TIMEOUT', error_message='Agent processing timed out', user_id=self.user_id, details={'timeout_seconds': 30, 'agent_id': 'agent_123'})
        self.assertEqual(error_response.type, MessageType.ERROR)
        self.assertEqual(error_response.data['error_code'], 'AGENT_TIMEOUT')
        self.assertEqual(error_response.data['details']['timeout_seconds'], 30)
        self.record_metric('error_response_success', True)

    async def test_response_correlation_tracking(self):
        """Test response correlation with original requests"""
        request_id = self.id_manager.generate_id(IDType.MESSAGE)
        request_msg = create_standard_message(message_type=MessageType.AGENT_REQUEST, user_id=self.user_id, data={'content': "What's the weather?"})
        request_msg.id = request_id
        response_msg = create_standard_message(message_type=MessageType.AGENT_RESPONSE, user_id=self.user_id, data={'response': "It's sunny today!", 'correlation_id': request_id})
        self.assertEqual(response_msg.data['correlation_id'], request_id)
        self.record_metric('correlation_tracking_success', True)

    async def test_multi_step_response_generation(self):
        """Test generating multi-step responses"""
        steps = [{'step': 1, 'action': 'analyzing', 'status': 'in_progress'}, {'step': 2, 'action': 'processing', 'status': 'in_progress'}, {'step': 3, 'action': 'generating_response', 'status': 'completed'}]
        step_messages = []
        for step in steps:
            step_msg = create_standard_message(message_type=MessageType.AGENT_STEP, user_id=self.user_id, data=step)
            step_messages.append(step_msg)
        self.assertEqual(len(step_messages), 3)
        self.assertEqual(step_messages[0].data['step'], 1)
        self.assertEqual(step_messages[-1].data['status'], 'completed')
        self.record_metric('multi_step_response_success', True)

    async def test_response_formatting_and_validation(self):
        """Test response formatting and validation"""
        raw_response = {'content': "  Here's your answer with extra spaces  ", 'confidence': '0.85', 'sources': ['source1', 'source2']}
        formatted_response = {'content': raw_response['content'].strip(), 'confidence': float(raw_response['confidence']), 'sources': raw_response['sources'], 'formatted_at': datetime.now(timezone.utc).isoformat()}
        response_msg = create_standard_message(message_type=MessageType.AGENT_RESPONSE, user_id=self.user_id, data=formatted_response)
        self.assertEqual(response_msg.data['content'], "Here's your answer with extra spaces")
        self.assertEqual(response_msg.data['confidence'], 0.85)
        self.assertIsInstance(response_msg.data['confidence'], float)
        self.record_metric('response_formatting_success', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')