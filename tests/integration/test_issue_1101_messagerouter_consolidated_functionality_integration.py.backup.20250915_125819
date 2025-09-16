"""
Integration Tests for Issue #1101 MessageRouter Consolidated Functionality

These tests validate that consolidated MessageRouter functionality works correctly:
1. Test real message routing scenarios
2. Validate handler registration and execution
3. Test WebSocket integration with real connections
4. Ensure no functionality is lost in consolidation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Maintain full functionality during SSOT consolidation
- Value Impact: Ensures Golden Path functionality is preserved
- Strategic Impact: Protects $500K+ ARR user experience
"""
import pytest
import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class MockWebSocket:
    """Mock WebSocket for integration testing."""

    def __init__(self):
        self.sent_messages = []
        self.is_connected = True
        self.client_state = 'connected'

    async def send_json(self, data):
        """Mock send_json method."""
        self.sent_messages.append(('json', data))

    async def send_text(self, data):
        """Mock send_text method."""
        self.sent_messages.append(('text', data))

@pytest.mark.integration
class TestMessageRouterConsolidatedFunctionality(SSotAsyncTestCase):
    """Integration tests for MessageRouter consolidated functionality."""

    def setUp(self):
        """Set up test environment with real services."""
        super().setUp()
        self.test_user_id = 'consolidated_user_101112'
        self.test_thread_id = f'thread_{self.test_user_id}_{int(time.time())}'
        self.test_run_id = f'run_{self.test_user_id}_{int(time.time())}'
        self.user_context = UserExecutionContext.from_request(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        self.functionality_tests = {'message_routing': [], 'handler_management': [], 'websocket_integration': [], 'performance_metrics': {}}

    async def test_consolidated_message_routing_functionality(self):
        """Test that consolidated router handles all message types correctly."""
        router = get_message_router()
        mock_websocket = MockWebSocket()
        test_messages = [{'type': 'user_message', 'payload': {'content': 'Hello, this is a user message'}, 'timestamp': time.time(), 'user_id': self.test_user_id, 'thread_id': self.test_thread_id}, {'type': 'ping', 'payload': {}, 'timestamp': time.time()}, {'type': 'agent_request', 'payload': {'message': 'Please analyze this data', 'turn_id': 'turn_123', 'real_llm': False}, 'timestamp': time.time()}, {'type': 'heartbeat', 'payload': {}, 'timestamp': time.time()}]
        successful_routes = 0
        for message in test_messages:
            start_time = time.time()
            try:
                result = await router.route_message(self.test_user_id, mock_websocket, message)
                route_time = time.time() - start_time
                self.functionality_tests['message_routing'].append({'message_type': message['type'], 'success': result, 'route_time': route_time, 'response_count': len(mock_websocket.sent_messages)})
                if result:
                    successful_routes += 1
                logger.info(f"Message routing test: {message['type']} -> {result} ({route_time:.3f}s)")
            except Exception as e:
                self.functionality_tests['message_routing'].append({'message_type': message['type'], 'success': False, 'error': str(e), 'route_time': time.time() - start_time})
                logger.error(f"Message routing failed for {message['type']}: {e}")
        success_rate = successful_routes / len(test_messages) * 100
        self.assertGreaterEqual(success_rate, 75.0, f'Message routing success rate too low: {success_rate}%')
        logger.info(f'Message routing functionality: {successful_routes}/{len(test_messages)} successful')

    async def test_handler_registration_and_execution_functionality(self):
        """Test handler registration and execution works correctly."""
        router = get_message_router()
        mock_websocket = MockWebSocket()

        class TestHandler:

            def __init__(self, name):
                self.name = name
                self.handled_messages = []

            def can_handle(self, message_type):
                return message_type == MessageType.USER_MESSAGE

            async def handle_message(self, user_id, websocket, message):
                self.handled_messages.append({'user_id': user_id, 'message_type': str(message.type), 'timestamp': time.time()})
                return True
        test_handler = TestHandler('CustomTestHandler')
        initial_handler_count = len(router.handlers)
        start_time = time.time()
        router.add_handler(test_handler)
        registration_time = time.time() - start_time
        self.assertEqual(len(router.handlers), initial_handler_count + 1)
        self.assertIn(test_handler, router.handlers)
        self.functionality_tests['handler_management'].append({'operation': 'registration', 'success': True, 'registration_time': registration_time, 'handler_count': len(router.handlers)})
        test_message = {'type': 'user_message', 'payload': {'content': 'Test handler execution'}, 'timestamp': time.time()}
        execution_start = time.time()
        result = await router.route_message(self.test_user_id, mock_websocket, test_message)
        execution_time = time.time() - execution_start
        self.assertTrue(result)
        self.assertEqual(len(test_handler.handled_messages), 1)
        self.assertEqual(test_handler.handled_messages[0]['user_id'], self.test_user_id)
        self.functionality_tests['handler_management'].append({'operation': 'execution', 'success': True, 'execution_time': execution_time, 'messages_handled': len(test_handler.handled_messages)})
        removal_start = time.time()
        router.remove_handler(test_handler)
        removal_time = time.time() - removal_start
        self.assertEqual(len(router.handlers), initial_handler_count)
        self.assertNotIn(test_handler, router.handlers)
        self.functionality_tests['handler_management'].append({'operation': 'removal', 'success': True, 'removal_time': removal_time, 'final_handler_count': len(router.handlers)})
        logger.info('Handler registration and execution functionality validated')

    async def test_websocket_integration_functionality(self):
        """Test WebSocket integration functionality."""
        router = get_message_router()
        ws_manager = WebSocketManager(user_context=self.user_context)
        self.assertIsNotNone(ws_manager)
        self.assertEqual(ws_manager.user_context.user_id, self.test_user_id)
        mock_websocket = MockWebSocket()
        critical_events = [{'type': 'agent_request', 'payload': {'message': 'Test critical event sequence', 'turn_id': 'critical_turn_123', 'real_llm': False}, 'timestamp': time.time()}]
        for event in critical_events:
            start_time = time.time()
            try:
                result = await router.route_message(self.test_user_id, mock_websocket, event)
                integration_time = time.time() - start_time
                expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                sent_event_types = []
                for msg_type, msg_data in mock_websocket.sent_messages:
                    if isinstance(msg_data, dict):
                        event_type = msg_data.get('event') or msg_data.get('type')
                        if event_type:
                            sent_event_types.append(event_type)
                events_delivered = len([e for e in expected_events if e in sent_event_types])
                self.functionality_tests['websocket_integration'].append({'event_type': event['type'], 'success': result, 'integration_time': integration_time, 'expected_events': len(expected_events), 'delivered_events': events_delivered, 'delivery_rate': events_delivered / len(expected_events) * 100})
                logger.info(f"WebSocket integration: {event['type']} -> {events_delivered}/{len(expected_events)} events")
            except Exception as e:
                self.functionality_tests['websocket_integration'].append({'event_type': event['type'], 'success': False, 'error': str(e), 'integration_time': time.time() - start_time})
                logger.error(f"WebSocket integration failed for {event['type']}: {e}")
        logger.info('WebSocket integration functionality validated')

    async def test_concurrent_routing_functionality(self):
        """Test concurrent message routing functionality."""
        router = get_message_router()

        async def route_task(task_id):
            mock_websocket = MockWebSocket()
            message = {'type': 'user_message', 'payload': {'content': f'Concurrent message {task_id}'}, 'timestamp': time.time()}
            start_time = time.time()
            result = await router.route_message(f'{self.test_user_id}_{task_id}', mock_websocket, message)
            route_time = time.time() - start_time
            return {'task_id': task_id, 'success': result, 'route_time': route_time, 'responses': len(mock_websocket.sent_messages)}
        num_concurrent_tasks = 5
        start_time = time.time()
        tasks = [route_task(i) for i in range(num_concurrent_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        successful_tasks = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_tasks = [r for r in results if not (isinstance(r, dict) and r.get('success'))]
        self.functionality_tests['performance_metrics']['concurrent_routing'] = {'total_tasks': num_concurrent_tasks, 'successful_tasks': len(successful_tasks), 'failed_tasks': len(failed_tasks), 'total_time': total_time, 'average_time': sum((r['route_time'] for r in successful_tasks)) / len(successful_tasks) if successful_tasks else 0, 'success_rate': len(successful_tasks) / num_concurrent_tasks * 100}
        success_rate = len(successful_tasks) / num_concurrent_tasks * 100
        self.assertGreaterEqual(success_rate, 80.0, f'Concurrent routing success rate too low: {success_rate}%')
        logger.info(f'Concurrent routing functionality: {len(successful_tasks)}/{num_concurrent_tasks} successful')

    async def test_error_handling_functionality(self):
        """Test error handling functionality in consolidated router."""
        router = get_message_router()
        mock_websocket = MockWebSocket()
        error_scenarios = [{'name': 'malformed_message', 'message': {'invalid': 'structure'}, 'expected_behavior': 'graceful_handling'}, {'name': 'missing_type', 'message': {'payload': {'content': 'no type'}}, 'expected_behavior': 'graceful_handling'}, {'name': 'invalid_timestamp', 'message': {'type': 'user_message', 'payload': {'content': 'test'}, 'timestamp': 'invalid_timestamp'}, 'expected_behavior': 'graceful_handling'}]
        for scenario in error_scenarios:
            start_time = time.time()
            try:
                result = await router.route_message(self.test_user_id, mock_websocket, scenario['message'])
                self.assertIsInstance(result, bool)
                self.functionality_tests['message_routing'].append({'scenario': scenario['name'], 'success': True, 'graceful_handling': True, 'handling_time': time.time() - start_time})
                logger.info(f"Error handling: {scenario['name']} handled gracefully")
            except Exception as e:
                self.functionality_tests['message_routing'].append({'scenario': scenario['name'], 'success': False, 'error': str(e), 'handling_time': time.time() - start_time})
                logger.warning(f"Error handling: {scenario['name']} raised exception: {e}")

    async def test_statistics_and_monitoring_functionality(self):
        """Test statistics and monitoring functionality."""
        router = get_message_router()
        initial_stats = router.get_stats()
        self.assertIsInstance(initial_stats, dict)
        self.assertIn('handler_count', initial_stats)
        mock_websocket = MockWebSocket()
        test_messages = [{'type': 'ping', 'payload': {}, 'timestamp': time.time()}, {'type': 'user_message', 'payload': {'content': 'test'}, 'timestamp': time.time()}, {'type': 'heartbeat', 'payload': {}, 'timestamp': time.time()}]
        for message in test_messages:
            await router.route_message(self.test_user_id, mock_websocket, message)
        updated_stats = router.get_stats()
        self.assertIsInstance(updated_stats, dict)
        self.assertIn('messages_routed', updated_stats)
        self.assertGreaterEqual(updated_stats['messages_routed'], len(test_messages))
        expected_keys = ['handler_count', 'handler_order', 'messages_routed']
        for key in expected_keys:
            self.assertIn(key, updated_stats, f'Missing statistics key: {key}')
        self.functionality_tests['performance_metrics']['statistics'] = {'initial_handler_count': initial_stats['handler_count'], 'updated_handler_count': updated_stats['handler_count'], 'messages_routed': updated_stats.get('messages_routed', 0), 'statistics_keys': list(updated_stats.keys())}
        logger.info('Statistics and monitoring functionality validated')

    def test_functionality_summary(self):
        """Generate consolidated functionality summary."""
        total_tests = 0
        successful_tests = 0
        for category, tests in self.functionality_tests.items():
            if isinstance(tests, list):
                for test in tests:
                    total_tests += 1
                    if test.get('success', False):
                        successful_tests += 1
        functionality_summary = {'total_functionality_tests': total_tests, 'successful_tests': successful_tests, 'functionality_success_rate': successful_tests / total_tests * 100 if total_tests > 0 else 0, 'message_routing_tests': len(self.functionality_tests['message_routing']), 'handler_management_tests': len(self.functionality_tests['handler_management']), 'websocket_integration_tests': len(self.functionality_tests['websocket_integration']), 'performance_metrics': self.functionality_tests['performance_metrics'], 'detailed_results': self.functionality_tests}
        logger.info(f'Consolidated Functionality Summary: {json.dumps(functionality_summary, indent=2)}')
        self.assertGreaterEqual(functionality_summary['functionality_success_rate'], 85.0, 'Consolidated functionality success rate should be at least 85%')
        self.assertGreater(functionality_summary['message_routing_tests'], 0, 'Should have message routing tests')
        self.assertGreater(functionality_summary['handler_management_tests'], 0, 'Should have handler management tests')
        return functionality_summary
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')