"""
Message Routing Consistency Validation Test

GitHub Issue: #1056 - Message router fragmentation blocking Golden Path
Business Impact: $500K+ ARR - Users cannot receive AI responses reliably

PURPOSE: Validate routing behavior consistency across implementations
STATUS: SHOULD FAIL initially due to inconsistent routing behavior
EXPECTED: PASS after SSOT consolidation

This test sends identical messages through different MessageRouter instances
to detect routing behavior differences that could affect user experience.
"""
import asyncio
import importlib
import time
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any, Optional
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.unit
class TestMessageRoutingConsistency(SSotAsyncTestCase):
    """Test message routing consistency across MessageRouter implementations."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.import_paths = ['netra_backend.app.websocket_core.handlers', 'netra_backend.app.agents.message_router', 'netra_backend.app.core.message_router']
        self.router_instances = {}
        self.test_messages = []

    async def asyncSetUp(self):
        """Set up async test fixtures."""
        await super().asyncSetUp()
        await self._load_router_instances()
        self._prepare_test_messages()

    async def _load_router_instances(self):
        """Load MessageRouter instances from different import paths."""
        for path in self.import_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    instance = router_class()
                    self.router_instances[path] = {'class': router_class, 'instance': instance, 'loaded': True}
                    self.logger.info(f'Loaded MessageRouter from {path}')
                else:
                    self.router_instances[path] = {'loaded': False, 'error': 'MessageRouter not found'}
            except ImportError as e:
                self.router_instances[path] = {'loaded': False, 'error': str(e)}
            except Exception as e:
                self.router_instances[path] = {'loaded': False, 'error': f'Unexpected error: {e}'}

    def _prepare_test_messages(self):
        """Prepare standard test messages for consistency testing."""
        try:
            from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, create_standard_message
            self.test_messages = [create_standard_message(MessageType.USER_MESSAGE, {'content': 'Hello', 'user_id': 'test_user'}), create_standard_message(MessageType.PING, {'timestamp': time.time()}), create_standard_message(MessageType.AGENT_REQUEST, {'message': 'test request', 'user_id': 'test_user'}), create_standard_message(MessageType.HEARTBEAT, {'user_id': 'test_user'})]
            self.logger.info(f'Prepared {len(self.test_messages)} test messages')
        except ImportError as e:
            self.logger.warning(f'Could not import message types from canonical location: {e}')
            self.test_messages = [{'type': 'user_message', 'payload': {'content': 'Hello', 'user_id': 'test_user'}}, {'type': 'ping', 'payload': {'timestamp': time.time()}}, {'type': 'agent_request', 'payload': {'message': 'test request', 'user_id': 'test_user'}}, {'type': 'heartbeat', 'payload': {'user_id': 'test_user'}}]

    async def test_message_routing_behavior_consistency(self):
        """
        Test routing behavior consistency across implementations.

        CRITICAL: This test SHOULD FAIL initially with inconsistent routing.
        EXPECTED: PASS after SSOT consolidation with consistent routing.
        """
        loaded_routers = {k: v for k, v in self.router_instances.items() if v.get('loaded')}
        if len(loaded_routers) < 2:
            self.skipTest(f'Need at least 2 loaded MessageRouter implementations, got {len(loaded_routers)}')
        routing_results = {}
        for path, router_info in loaded_routers.items():
            instance = router_info['instance']
            path_results = []
            for i, message in enumerate(self.test_messages):
                result = await self._test_message_routing(instance, message, f'msg_{i}')
                path_results.append(result)
            routing_results[path] = path_results
        consistency_violations = []
        paths = list(routing_results.keys())
        if len(paths) >= 2:
            base_path = paths[0]
            base_results = routing_results[base_path]
            for compare_path in paths[1:]:
                compare_results = routing_results[compare_path]
                for i, (base_result, compare_result) in enumerate(zip(base_results, compare_results)):
                    violations = self._compare_routing_results(base_path, base_result, compare_path, compare_result, f'message_{i}')
                    consistency_violations.extend(violations)
        self.logger.info(f'Routing consistency analysis: {len(loaded_routers)} implementations')
        for path, results in routing_results.items():
            successful = sum((1 for r in results if r.get('success', False)))
            self.logger.info(f'  {path}: {successful}/{len(results)} successful routings')
        if consistency_violations:
            for violation in consistency_violations:
                self.logger.error(f'  Routing consistency violation: {violation}')
        if len(consistency_violations) == 0:
            self.logger.info('✅ SSOT COMPLIANCE: All MessageRouter implementations exhibit consistent routing behavior')
        else:
            violation_msg = f'SSOT VIOLATION: {len(consistency_violations)} routing consistency violations detected'
            self.logger.error(f'❌ {violation_msg}')
            self.fail(f'SSOT VIOLATION: MessageRouter implementations must have consistent routing behavior. Found {len(consistency_violations)} violations proving fragmented routing logic.')

    async def _test_message_routing(self, router_instance: Any, message: Any, message_id: str) -> Dict[str, Any]:
        """Test routing a single message through a router instance."""
        result = {'message_id': message_id, 'success': False, 'error': None, 'response': None, 'execution_time': None}
        try:
            start_time = time.time()
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.state = Mock()
            mock_websocket.state.value = 1
            if hasattr(router_instance, 'route_message'):
                response = await router_instance.route_message(message)
                result['response'] = response
                result['success'] = True
            elif hasattr(router_instance, 'handle_message'):
                user_id = 'test_user'
                response = await router_instance.handle_message(user_id, mock_websocket, message)
                result['response'] = response
                result['success'] = True
            elif hasattr(router_instance, 'handlers'):
                handlers = getattr(router_instance, 'handlers')
                result['response'] = f"handlers_count: {(len(handlers) if hasattr(handlers, '__len__') else 'unknown')}"
                result['success'] = True
            else:
                result['error'] = 'No recognized routing method found'
            result['execution_time'] = time.time() - start_time
        except Exception as e:
            result['error'] = str(e)
            result['execution_time'] = time.time() - start_time
        return result

    def _compare_routing_results(self, base_path: str, base_result: Dict, compare_path: str, compare_result: Dict, message_id: str) -> List[Dict]:
        """Compare routing results between two implementations."""
        violations = []
        if base_result['success'] != compare_result['success']:
            violations.append({'type': 'success_status_mismatch', 'message_id': message_id, 'base_path': base_path, 'base_success': base_result['success'], 'compare_path': compare_path, 'compare_success': compare_result['success']})
        base_has_error = base_result['error'] is not None
        compare_has_error = compare_result['error'] is not None
        if base_has_error != compare_has_error:
            violations.append({'type': 'error_presence_mismatch', 'message_id': message_id, 'base_path': base_path, 'base_error': base_result['error'], 'compare_path': compare_path, 'compare_error': compare_result['error']})
        if base_result['execution_time'] is not None and compare_result['execution_time'] is not None:
            time_diff = abs(base_result['execution_time'] - compare_result['execution_time'])
            if time_diff > 0.1:
                violations.append({'type': 'execution_time_significant_difference', 'message_id': message_id, 'base_path': base_path, 'base_time': base_result['execution_time'], 'compare_path': compare_path, 'compare_time': compare_result['execution_time'], 'time_difference': time_diff})
        return violations

    async def test_handler_availability_consistency(self):
        """
        Test that handler availability is consistent across implementations.

        CRITICAL: This test SHOULD FAIL initially with different handler sets.
        EXPECTED: PASS after SSOT consolidation with consistent handlers.
        """
        loaded_routers = {k: v for k, v in self.router_instances.items() if v.get('loaded')}
        if len(loaded_routers) < 2:
            self.skipTest(f'Need at least 2 loaded MessageRouter implementations')
        handler_analysis = {}
        for path, router_info in loaded_routers.items():
            instance = router_info['instance']
            analysis = {'has_handlers_attr': hasattr(instance, 'handlers'), 'has_add_handler': hasattr(instance, 'add_handler'), 'has_route_message': hasattr(instance, 'route_message'), 'handler_count': None, 'handler_types': []}
            if hasattr(instance, 'handlers'):
                handlers = getattr(instance, 'handlers')
                if hasattr(handlers, '__len__'):
                    analysis['handler_count'] = len(handlers)
                    try:
                        analysis['handler_types'] = [type(h).__name__ for h in handlers]
                    except:
                        analysis['handler_types'] = ['extraction_failed']
            handler_analysis[path] = analysis
        handler_inconsistencies = []
        paths = list(handler_analysis.keys())
        if len(paths) >= 2:
            base_path = paths[0]
            base_analysis = handler_analysis[base_path]
            for compare_path in paths[1:]:
                compare_analysis = handler_analysis[compare_path]
                for key in ['has_handlers_attr', 'has_add_handler', 'has_route_message']:
                    if base_analysis[key] != compare_analysis[key]:
                        handler_inconsistencies.append({'attribute': key, 'base_path': base_path, 'base_value': base_analysis[key], 'compare_path': compare_path, 'compare_value': compare_analysis[key]})
                if base_analysis['handler_count'] is not None and compare_analysis['handler_count'] is not None:
                    if base_analysis['handler_count'] != compare_analysis['handler_count']:
                        handler_inconsistencies.append({'attribute': 'handler_count', 'base_path': base_path, 'base_value': base_analysis['handler_count'], 'compare_path': compare_path, 'compare_value': compare_analysis['handler_count']})
        self.logger.info(f'Handler availability analysis: {len(loaded_routers)} implementations')
        for path, analysis in handler_analysis.items():
            self.logger.info(f'  {path}: {analysis}')
        if handler_inconsistencies:
            for inconsistency in handler_inconsistencies:
                self.logger.error(f'  Handler inconsistency: {inconsistency}')
        if len(handler_inconsistencies) == 0:
            self.logger.info('✅ SSOT COMPLIANCE: All MessageRouter implementations have consistent handler availability')
        else:
            violation_msg = f'SSOT VIOLATION: {len(handler_inconsistencies)} handler availability inconsistencies detected'
            self.logger.error(f'❌ {violation_msg}')
            self.fail(f'SSOT VIOLATION: MessageRouter implementations must have consistent handler availability. Found {len(handler_inconsistencies)} inconsistencies proving fragmented handler management.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')