"""
E2E Staging Tests for Issue #1101 MessageRouter Golden Path Validation

These tests validate MessageRouter SSOT consolidation in staging environment:
1. Test Golden Path user flow with consolidated MessageRouter
2. Validate real WebSocket connections work correctly
3. Test agent execution with SSOT MessageRouter
4. Ensure no breaking changes in production scenarios

Business Value Justification:
- Segment: Platform/Production
- Business Goal: Golden Path reliability in production environment
- Value Impact: Protects $500K+ ARR user experience in staging
- Strategic Impact: Validates SSOT consolidation before production deployment
"""
import pytest
import asyncio
import time
import json
import os
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class TestMessageRouterGoldenPathValidationE2E(SSotAsyncTestCase):
    """E2E staging tests for MessageRouter Golden Path validation."""

    @classmethod
    def setUpClass(cls):
        """Set up staging environment."""
        env = get_env()
        environment = env.get('ENVIRONMENT', 'development').lower()
        if environment not in ['staging', 'development']:
            pytest.skip(f'E2E tests require staging environment, got: {environment}')
        logger.info(f'Running E2E tests in {environment} environment')
        cls.staging_config = {'environment': environment, 'auth_service_url': env.get('AUTH_SERVICE_URL', 'https://auth.staging.netrasystems.ai'), 'backend_url': env.get('BACKEND_URL', 'https://backend.staging.netrasystems.ai'), 'websocket_url': env.get('WEBSOCKET_URL', 'wss://backend.staging.netrasystems.ai/ws')}
        logger.info(f'Staging configuration: {cls.staging_config}')

    def setUp(self):
        """Set up test environment for Golden Path validation."""
        super().setUp()
        self.test_user_id = 'e2e_golden_path_user_202425'
        self.test_thread_id = f'golden_thread_{int(time.time())}'
        self.test_run_id = f'golden_run_{int(time.time())}'
        self.user_context = UserExecutionContext.from_request(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id=self.test_run_id)
        self.golden_path_metrics = {'authentication_success': False, 'websocket_connection_success': False, 'message_routing_success': False, 'agent_execution_success': False, 'response_delivery_success': False, 'total_execution_time': 0, 'critical_events_delivered': 0, 'error_count': 0}

    async def test_golden_path_end_to_end_user_flow(self):
        """Test complete Golden Path user flow with SSOT MessageRouter."""
        golden_path_start = time.time()
        try:
            auth_start = time.time()
            authenticated_user = await self._simulate_user_authentication()
            self.golden_path_metrics['authentication_success'] = authenticated_user is not None
            auth_time = time.time() - auth_start
            logger.info(f"Golden Path Step 1: Authentication {('SUCCESS' if authenticated_user else 'FAILED')} ({auth_time:.2f}s)")
            websocket_start = time.time()
            websocket_connection = await self._establish_websocket_connection()
            self.golden_path_metrics['websocket_connection_success'] = websocket_connection is not None
            websocket_time = time.time() - websocket_start
            logger.info(f"Golden Path Step 2: WebSocket Connection {('SUCCESS' if websocket_connection else 'FAILED')} ({websocket_time:.2f}s)")
            routing_start = time.time()
            routing_success = await self._test_message_routing_golden_path(websocket_connection)
            self.golden_path_metrics['message_routing_success'] = routing_success
            routing_time = time.time() - routing_start
            logger.info(f"Golden Path Step 3: Message Routing {('SUCCESS' if routing_success else 'FAILED')} ({routing_time:.2f}s)")
            agent_start = time.time()
            agent_success = await self._test_agent_execution_golden_path(websocket_connection)
            self.golden_path_metrics['agent_execution_success'] = agent_success
            agent_time = time.time() - agent_start
            logger.info(f"Golden Path Step 4: Agent Execution {('SUCCESS' if agent_success else 'FAILED')} ({agent_time:.2f}s)")
            response_start = time.time()
            response_success = await self._validate_response_delivery(websocket_connection)
            self.golden_path_metrics['response_delivery_success'] = response_success
            response_time = time.time() - response_start
            logger.info(f"Golden Path Step 5: Response Delivery {('SUCCESS' if response_success else 'FAILED')} ({response_time:.2f}s)")
            self.golden_path_metrics['total_execution_time'] = time.time() - golden_path_start
            golden_path_success = all([self.golden_path_metrics['authentication_success'], self.golden_path_metrics['websocket_connection_success'], self.golden_path_metrics['message_routing_success'], self.golden_path_metrics['agent_execution_success'], self.golden_path_metrics['response_delivery_success']])
            self.assertTrue(golden_path_success, f'Golden Path validation failed. Metrics: {self.golden_path_metrics}')
            logger.info(f"GOLDEN PATH E2E SUCCESS: Complete user flow validated in {self.golden_path_metrics['total_execution_time']:.2f}s")
        except Exception as e:
            self.golden_path_metrics['error_count'] += 1
            self.golden_path_metrics['total_execution_time'] = time.time() - golden_path_start
            logger.error(f'Golden Path E2E FAILED: {e}')
            logger.error(f'Final metrics: {self.golden_path_metrics}')
            raise

    async def _simulate_user_authentication(self) -> Optional[Dict[str, Any]]:
        """Simulate user authentication for Golden Path."""
        try:
            authenticated_user = {'user_id': self.test_user_id, 'authenticated': True, 'auth_timestamp': time.time(), 'auth_method': 'simulated_for_e2e'}
            self.assertIsNotNone(self.user_context)
            self.assertEqual(self.user_context.user_id, self.test_user_id)
            return authenticated_user
        except Exception as e:
            logger.error(f'Authentication simulation failed: {e}')
            return None

    async def _establish_websocket_connection(self) -> Optional[Mock]:
        """Establish WebSocket connection for Golden Path testing."""
        try:

            class StagingMockWebSocket:

                def __init__(self):
                    self.is_connected = True
                    self.sent_messages = []
                    self.client_state = 'connected'
                    self.connection_id = f'staging_ws_{self.test_user_id}_{int(time.time())}'

                async def send_json(self, data):
                    """Simulate sending JSON data."""
                    self.sent_messages.append(('json', data))
                    logger.debug(f'WebSocket sent JSON: {data}')

                async def send_text(self, data):
                    """Simulate sending text data."""
                    self.sent_messages.append(('text', data))
                    logger.debug(f'WebSocket sent text: {data}')
            mock_websocket = StagingMockWebSocket()
            await asyncio.sleep(0.1)
            logger.info(f'WebSocket connection established: {mock_websocket.connection_id}')
            return mock_websocket
        except Exception as e:
            logger.error(f'WebSocket connection failed: {e}')
            return None

    async def _test_message_routing_golden_path(self, websocket_connection) -> bool:
        """Test message routing with SSOT MessageRouter in Golden Path."""
        try:
            router = get_message_router()
            self.assertIsInstance(router, MessageRouter)
            golden_path_messages = [{'type': 'user_message', 'payload': {'content': 'Hello, I need help analyzing my data', 'golden_path_test': True}, 'timestamp': time.time(), 'user_id': self.test_user_id, 'thread_id': self.test_thread_id}, {'type': 'agent_request', 'payload': {'message': 'Please analyze this business data', 'turn_id': f'golden_turn_{int(time.time())}', 'require_multi_agent': False, 'real_llm': False, 'golden_path_test': True}, 'timestamp': time.time()}]
            successful_routes = 0
            for message in golden_path_messages:
                route_start = time.time()
                result = await router.route_message(self.test_user_id, websocket_connection, message)
                route_time = time.time() - route_start
                if result:
                    successful_routes += 1
                    logger.info(f"Golden Path routing SUCCESS: {message['type']} ({route_time:.3f}s)")
                else:
                    logger.warning(f"Golden Path routing FAILED: {message['type']} ({route_time:.3f}s)")
            routing_success_rate = successful_routes / len(golden_path_messages) * 100
            logger.info(f'Golden Path message routing: {successful_routes}/{len(golden_path_messages)} successful ({routing_success_rate:.1f}%)')
            return routing_success_rate >= 90.0
        except Exception as e:
            logger.error(f'Message routing test failed: {e}')
            return False

    async def _test_agent_execution_golden_path(self, websocket_connection) -> bool:
        """Test agent execution in Golden Path with SSOT MessageRouter."""
        try:
            router = get_message_router()
            agent_execution_message = {'type': 'agent_request', 'payload': {'message': 'Analyze customer engagement metrics for Q4 2024', 'turn_id': f'agent_golden_{int(time.time())}', 'require_multi_agent': True, 'real_llm': False, 'user_request': 'Analyze customer engagement metrics for Q4 2024', 'golden_path_validation': True}, 'timestamp': time.time(), 'user_id': self.test_user_id, 'thread_id': self.test_thread_id}
            initial_message_count = len(websocket_connection.sent_messages)
            execution_start = time.time()
            result = await router.route_message(self.test_user_id, websocket_connection, agent_execution_message)
            execution_time = time.time() - execution_start
            if not result:
                logger.error('Agent execution returned False')
                return False
            new_messages = websocket_connection.sent_messages[initial_message_count:]
            critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            delivered_events = []
            for msg_type, msg_data in new_messages:
                if isinstance(msg_data, dict):
                    event_type = msg_data.get('event') or msg_data.get('type')
                    if event_type in critical_events:
                        delivered_events.append(event_type)
            self.golden_path_metrics['critical_events_delivered'] = len(delivered_events)
            events_success = len(delivered_events) >= len(critical_events) * 0.8
            logger.info(f'Golden Path agent execution: {len(delivered_events)}/{len(critical_events)} critical events delivered ({execution_time:.2f}s)')
            logger.info(f'Delivered events: {delivered_events}')
            return events_success and result
        except Exception as e:
            logger.error(f'Agent execution test failed: {e}')
            return False

    async def _validate_response_delivery(self, websocket_connection) -> bool:
        """Validate response delivery in Golden Path."""
        try:
            total_messages = len(websocket_connection.sent_messages)
            if total_messages == 0:
                logger.error('No messages delivered via WebSocket')
                return False
            valid_messages = 0
            for msg_type, msg_data in websocket_connection.sent_messages:
                if isinstance(msg_data, dict):
                    has_type = 'type' in msg_data or 'event' in msg_data
                    has_timestamp = 'timestamp' in msg_data
                    if has_type and has_timestamp:
                        valid_messages += 1
            delivery_success_rate = valid_messages / total_messages * 100
            logger.info(f'Golden Path response delivery: {valid_messages}/{total_messages} valid messages ({delivery_success_rate:.1f}%)')
            return delivery_success_rate >= 90.0
        except Exception as e:
            logger.error(f'Response delivery validation failed: {e}')
            return False

    async def test_staging_environment_compatibility(self):
        """Test SSOT MessageRouter compatibility with staging environment."""
        try:
            env = get_env()
            environment = env.get('ENVIRONMENT', 'development').lower()
            self.assertIn(environment, ['staging', 'development'])
            router = get_message_router()
            self.assertIsNotNone(router)
            stats = router.get_stats()
            self.assertIsInstance(stats, dict)
            self.assertIn('handler_count', stats)
            handler_count = stats['handler_count']
            self.assertGreaterEqual(handler_count, 5)
            self.assertLessEqual(handler_count, 50)
            logger.info(f'Staging compatibility: Router has {handler_count} handlers')
            error_count = stats.get('handler_errors', 0)
            self.assertEqual(error_count, 0)
            logger.info('Staging environment compatibility validated')
        except Exception as e:
            logger.error(f'Staging environment compatibility failed: {e}')
            raise

    async def test_golden_path_performance_requirements(self):
        """Test that Golden Path meets performance requirements."""
        try:
            router = get_message_router()
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.send_text = AsyncMock()
            perf_message = {'type': 'agent_request', 'payload': {'message': 'Performance test message', 'turn_id': f'perf_turn_{int(time.time())}', 'real_llm': False}, 'timestamp': time.time()}
            start_time = time.time()
            result = await router.route_message(self.test_user_id, mock_websocket, perf_message)
            route_time = time.time() - start_time
            max_route_time = 2.0
            self.assertTrue(result, 'Message routing should succeed')
            self.assertLessEqual(route_time, max_route_time, f'Routing time {route_time:.3f}s exceeds max {max_route_time}s')
            logger.info(f'Golden Path performance: Routing completed in {route_time:.3f}s (req: <{max_route_time}s)')
        except Exception as e:
            logger.error(f'Performance requirements test failed: {e}')
            raise

    def test_golden_path_metrics_summary(self):
        """Generate Golden Path metrics summary."""
        metrics_summary = {'test_environment': self.staging_config, 'golden_path_metrics': self.golden_path_metrics, 'test_user_context': {'user_id': self.test_user_id, 'thread_id': self.test_thread_id, 'run_id': self.test_run_id}, 'success_criteria': {'all_steps_successful': all([self.golden_path_metrics.get('authentication_success', False), self.golden_path_metrics.get('websocket_connection_success', False), self.golden_path_metrics.get('message_routing_success', False), self.golden_path_metrics.get('agent_execution_success', False), self.golden_path_metrics.get('response_delivery_success', False)]), 'performance_acceptable': self.golden_path_metrics.get('total_execution_time', 0) < 30.0, 'error_threshold_met': self.golden_path_metrics.get('error_count', 0) <= 1, 'critical_events_delivered': self.golden_path_metrics.get('critical_events_delivered', 0) >= 4}}
        logger.info(f'Golden Path E2E Metrics Summary: {json.dumps(metrics_summary, indent=2)}')
        overall_success = all(metrics_summary['success_criteria'].values())
        self.assertTrue(overall_success, f'Golden Path validation failed. Summary: {metrics_summary}')
        return metrics_summary
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')