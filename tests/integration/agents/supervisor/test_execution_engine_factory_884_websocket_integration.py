"""Phase 1 Integration Tests: Execution Engine Factory WebSocket Integration (Issue #884)

CRITICAL BUSINESS VALUE: These tests reproduce WebSocket coordination failures in
execution engine factory patterns that cause 1011 errors and Golden Path failures,
protecting 500K+ ARR functionality.

EXPECTED BEHAVIOR: All tests in this file should INITIALLY FAIL to demonstrate
WebSocket integration issues. They will pass after SSOT consolidation.

Business Value Justification (BVJ):
- Segment: All Segments (Chat functionality is 90% of platform value)
- Business Goal: Ensure reliable WebSocket events for chat functionality
- Value Impact: Prevents WebSocket 1011 errors, chat flow interruptions
- Strategic Impact: Foundation for 500K+ ARR real-time user interactions

Test Philosophy:
- FAILING TESTS FIRST: These tests reproduce real WebSocket coordination issues
- REAL SERVICES: Tests use real WebSocket infrastructure (NON-DOCKER)
- INTEGRATION FOCUS: Tests validate factory-WebSocket coordination patterns
- GOLDEN PATH PROTECTION: Tests protect end-to-end chat functionality
- REAL-TIME VALIDATION: Tests ensure WebSocket events work reliably
"""
import pytest
import asyncio
import gc
import inspect
import json
import time
import uuid
import unittest
import websockets
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.integration
class ExecutionEngineFactoryWebSocketIntegration884Tests(SSotAsyncTestCase):
    """Phase 1 Integration Tests: Execution Engine Factory WebSocket Integration

    These tests are designed to FAIL initially to demonstrate WebSocket coordination
    issues in factory patterns. They will pass after SSOT consolidation.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_users = []
        self.factory_instances = []
        self.created_contexts = []
        self.created_engines = []
        self.websocket_connections = []
        self.websocket_coordination_failures = []
        self.event_delivery_failures = []
        self.factory_websocket_mismatches = []
        self.websocket_test_timeout = 10.0
        self.expected_websocket_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

    async def asyncTearDown(self):
        """Clean up test resources."""
        for ws in self.websocket_connections:
            try:
                if not ws.closed:
                    await ws.close()
            except Exception:
                pass
        for engine in self.created_engines:
            try:
                if hasattr(engine, 'cleanup'):
                    await engine.cleanup()
            except Exception:
                pass
        for context in self.created_contexts:
            try:
                if hasattr(context, 'cleanup'):
                    await context.cleanup()
            except Exception:
                pass
        for factory in self.factory_instances:
            try:
                if hasattr(factory, 'shutdown'):
                    await factory.shutdown()
            except Exception:
                pass
        gc.collect()
        await super().asyncTearDown()

    async def test_execution_engine_factory_websocket_bridge_coordination_failures(self):
        """FAILING TEST: Reproduce WebSocket bridge coordination failures with factory

        BVJ: All Segments - Ensures WebSocket events work for chat functionality
        EXPECTED: FAIL - Factory/WebSocket coordination should fail
        ISSUE: Factory and WebSocket bridge initialization timing conflicts
        """
        websocket_coordination_failures = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        except ImportError as e:
            self.fail(f'Cannot import required classes - SSOT consolidation incomplete: {e}')
        try:
            factory_no_ws = ExecutionEngineFactory(websocket_bridge=None)
            self.factory_instances.append(factory_no_ws)
        except Exception as e:
            websocket_coordination_failures.append({'test': 'factory_without_websocket', 'failure_type': 'factory_creation_failure', 'error': str(e), 'description': 'Factory cannot be created without WebSocket bridge'})
        try:
            mock_bridge = MagicMock(spec=AgentWebSocketBridge)
            mock_bridge.send_event = AsyncMock()
            mock_bridge.initialized = True
            factory_with_ws = ExecutionEngineFactory(websocket_bridge=mock_bridge)
            self.factory_instances.append(factory_with_ws)
            test_context = UserExecutionContext(user_id='websocket_test_user', run_id=f'websocket_test_run_{int(time.time() * 1000)}', session_id='websocket_test_session', request_id='websocket_test_request')
            self.created_contexts.append(test_context)
            engine = await factory_with_ws.create_for_user(test_context)
            self.created_engines.append(engine)
            if not hasattr(engine, 'websocket_emitter'):
                websocket_coordination_failures.append({'test': 'engine_websocket_emitter', 'failure_type': 'missing_websocket_emitter', 'description': 'Engine created without WebSocket emitter'})
            elif engine.websocket_emitter is None:
                websocket_coordination_failures.append({'test': 'engine_websocket_emitter', 'failure_type': 'null_websocket_emitter', 'description': 'Engine WebSocket emitter is None'})
            try:
                if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                    await engine.websocket_emitter.emit_event(event_type='test_event', data={'test': 'factory_websocket_coordination'})
            except Exception as e:
                websocket_coordination_failures.append({'test': 'websocket_event_sending', 'failure_type': 'event_sending_failure', 'error': str(e), 'description': 'WebSocket event sending failed'})
            await factory_with_ws.cleanup_engine(engine)
        except Exception as e:
            websocket_coordination_failures.append({'test': 'factory_with_websocket', 'failure_type': 'factory_websocket_integration_failure', 'error': str(e), 'description': 'Factory with WebSocket bridge integration failed'})
        self.websocket_coordination_failures = websocket_coordination_failures
        self.assertEqual(len(websocket_coordination_failures), 0, f'WEBSOCKET COORDINATION FAILURES: Found {len(websocket_coordination_failures)} WebSocket coordination failures between factory and WebSocket bridge. Failures: {websocket_coordination_failures}. WebSocket coordination issues cause 1011 errors and Golden Path failures.')

    async def test_concurrent_factory_websocket_event_delivery_race_conditions(self):
        """FAILING TEST: Reproduce race conditions in concurrent WebSocket event delivery

        BVJ: All Segments - Ensures reliable WebSocket events under concurrent load
        EXPECTED: FAIL - Concurrent event delivery should cause race conditions
        ISSUE: Factory WebSocket coordination fails under concurrent user load
        """
        event_delivery_failures = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError as e:
            self.fail(f'Cannot import ExecutionEngineFactory - SSOT consolidation incomplete: {e}')
        mock_bridge = MagicMock()
        mock_bridge.send_event = AsyncMock()
        mock_bridge.initialized = True
        event_call_counts = {}
        event_timing_issues = []

        async def mock_send_event(*args, **kwargs):
            """Mock send_event that tracks calls and timing."""
            call_time = time.time()
            event_type = kwargs.get('event_type', args[0] if args else 'unknown')
            if event_type not in event_call_counts:
                event_call_counts[event_type] = []
            event_call_counts[event_type].append(call_time)
            await asyncio.sleep(0.01)
        mock_bridge.send_event = mock_send_event
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        self.factory_instances.append(factory)
        num_concurrent_users = 5
        concurrent_event_results = []

        async def simulate_user_websocket_events(user_index: int):
            """Simulate WebSocket events for a user."""
            try:
                context = UserExecutionContext(user_id=f'concurrent_ws_user_{user_index}', run_id=f'concurrent_ws_run_{user_index}_{int(time.time() * 1000)}', session_id=f'concurrent_ws_session_{user_index}', request_id=f'concurrent_ws_request_{user_index}')
                self.created_contexts.append(context)
                engine = await factory.create_for_user(context)
                self.created_engines.append(engine)
                events_sent = []
                for event_type in self.expected_websocket_events:
                    try:
                        if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                            start_time = time.time()
                            await engine.websocket_emitter.emit_event(event_type=event_type, data={'user_id': context.user_id, 'user_index': user_index, 'timestamp': start_time})
                            event_time = (time.time() - start_time) * 1000
                            events_sent.append({'event_type': event_type, 'success': True, 'event_time': event_time})
                        else:
                            events_sent.append({'event_type': event_type, 'success': False, 'error': 'No WebSocket emitter available'})
                    except Exception as e:
                        events_sent.append({'event_type': event_type, 'success': False, 'error': str(e)})
                await factory.cleanup_engine(engine)
                return {'user_index': user_index, 'success': True, 'events_sent': events_sent}
            except Exception as e:
                return {'user_index': user_index, 'success': False, 'error': str(e)}
        tasks = [simulate_user_websocket_events(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_users = []
        failed_users = []
        for result in results:
            if isinstance(result, dict):
                concurrent_event_results.append(result)
                if result['success']:
                    successful_users.append(result)
                else:
                    failed_users.append(result)
            else:
                failed_users.append({'user_index': 'unknown', 'success': False, 'error': str(result)})
        total_events_expected = num_concurrent_users * len(self.expected_websocket_events)
        total_events_delivered = sum((len(calls) for calls in event_call_counts.values()))
        if total_events_delivered != total_events_expected:
            event_delivery_failures.append({'failure_type': 'event_count_mismatch', 'expected_events': total_events_expected, 'delivered_events': total_events_delivered, 'missing_events': total_events_expected - total_events_delivered, 'description': 'Not all events were delivered - possible race condition'})
        for event_type, call_times in event_call_counts.items():
            if len(call_times) > 1:
                time_diffs = [call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)]
                max_diff = max(time_diffs) if time_diffs else 0
                min_diff = min(time_diffs) if time_diffs else 0
                if max_diff > min_diff * 10:
                    event_delivery_failures.append({'failure_type': 'event_timing_inconsistency', 'event_type': event_type, 'max_diff': max_diff, 'min_diff': min_diff, 'call_count': len(call_times), 'description': 'Event delivery timing inconsistent - possible race condition'})
        self.event_delivery_failures = event_delivery_failures
        self.assertEqual(len(event_delivery_failures), 0, f'EVENT DELIVERY FAILURES: Found {len(event_delivery_failures)} WebSocket event delivery failures during concurrent operations. Failures: {event_delivery_failures}. Event delivery race conditions cause WebSocket 1011 errors.')
        failure_rate = len(failed_users) / len(results) if results else 0
        max_acceptable_failure_rate = 0.1
        self.assertLess(failure_rate, max_acceptable_failure_rate, f'HIGH EVENT DELIVERY FAILURE RATE: {failure_rate:.1%} of concurrent users failed to send WebSocket events (threshold: {max_acceptable_failure_rate:.1%}). Failed users: {len(failed_users)}, Total: {len(results)}. WebSocket integration reliability issues detected.')

    async def test_factory_websocket_state_consistency_violations(self):
        """FAILING TEST: Reproduce WebSocket state consistency violations across factories

        BVJ: Platform - Ensures consistent WebSocket state management
        EXPECTED: FAIL - WebSocket state should be inconsistent across factory instances
        ISSUE: Factory instances have inconsistent WebSocket state management
        """
        websocket_state_violations = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError as e:
            self.fail(f'Cannot import ExecutionEngineFactory - SSOT consolidation incomplete: {e}')
        factory_configurations = [{'name': 'factory_no_ws', 'websocket_bridge': None}, {'name': 'factory_mock_ws1', 'websocket_bridge': MagicMock()}, {'name': 'factory_mock_ws2', 'websocket_bridge': MagicMock()}]
        factory_instances = []
        websocket_state_comparisons = []
        for config in factory_configurations:
            try:
                factory = ExecutionEngineFactory(websocket_bridge=config['websocket_bridge'])
                factory_instances.append({'name': config['name'], 'factory': factory, 'websocket_bridge': config['websocket_bridge']})
                self.factory_instances.append(factory)
            except Exception as e:
                websocket_state_violations.append({'factory_name': config['name'], 'failure_type': 'factory_creation_failure', 'error': str(e), 'description': 'Could not create factory with WebSocket configuration'})
        for i, factory1 in enumerate(factory_instances):
            for j, factory2 in enumerate(factory_instances):
                if i != j:
                    bridge1 = factory1['websocket_bridge']
                    bridge2 = factory2['websocket_bridge']
                    if bridge1 is not None and bridge2 is not None and (bridge1 is bridge2):
                        websocket_state_violations.append({'factory1': factory1['name'], 'factory2': factory2['name'], 'violation_type': 'shared_websocket_bridge', 'description': 'Factories share the same WebSocket bridge instance'})
                    try:
                        context1 = UserExecutionContext(user_id=f'state_test_user_{i}', run_id=f'state_test_run_{i}_{int(time.time() * 1000)}', session_id=f'state_test_session_{i}', request_id=f'state_test_request_{i}')
                        context2 = UserExecutionContext(user_id=f'state_test_user_{j}', run_id=f'state_test_run_{j}_{int(time.time() * 1000)}', session_id=f'state_test_session_{j}', request_id=f'state_test_request_{j}')
                        self.created_contexts.extend([context1, context2])
                        engine1 = await factory1['factory'].create_for_user(context1)
                        engine2 = await factory2['factory'].create_for_user(context2)
                        self.created_engines.extend([engine1, engine2])
                        emitter1 = getattr(engine1, 'websocket_emitter', None)
                        emitter2 = getattr(engine2, 'websocket_emitter', None)
                        if emitter1 is not None and emitter2 is not None and (emitter1 is emitter2):
                            websocket_state_violations.append({'factory1': factory1['name'], 'factory2': factory2['name'], 'violation_type': 'shared_websocket_emitter', 'description': 'Engines from different factories share WebSocket emitter'})
                        if bridge1 is None and emitter1 is not None or (bridge1 is not None and emitter1 is None):
                            websocket_state_violations.append({'factory': factory1['name'], 'violation_type': 'websocket_configuration_inconsistency', 'bridge_present': bridge1 is not None, 'emitter_present': emitter1 is not None, 'description': 'WebSocket bridge and emitter configuration mismatch'})
                        await factory1['factory'].cleanup_engine(engine1)
                        await factory2['factory'].cleanup_engine(engine2)
                    except Exception as e:
                        websocket_state_violations.append({'factory1': factory1['name'], 'factory2': factory2['name'], 'violation_type': 'state_consistency_test_failure', 'error': str(e), 'description': 'Could not test WebSocket state consistency'})
        self.factory_websocket_mismatches = websocket_state_violations
        self.assertEqual(len(websocket_state_violations), 0, f'WEBSOCKET STATE VIOLATIONS: Found {len(websocket_state_violations)} WebSocket state consistency violations across factory instances. Violations: {websocket_state_violations}. WebSocket state inconsistencies cause coordination failures.')

    async def test_factory_websocket_lifecycle_coordination_failures(self):
        """FAILING TEST: Reproduce WebSocket lifecycle coordination failures with factory

        BVJ: Platform - Ensures proper WebSocket lifecycle management
        EXPECTED: FAIL - WebSocket lifecycle should not coordinate properly with factory
        ISSUE: Factory and WebSocket lifecycle management is not synchronized
        """
        lifecycle_coordination_failures = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError as e:
            self.fail(f'Cannot import ExecutionEngineFactory - SSOT consolidation incomplete: {e}')
        mock_bridge = MagicMock()
        mock_bridge.send_event = AsyncMock()
        mock_bridge.initialized = True
        mock_bridge.shutdown = AsyncMock()
        try:
            factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
            self.factory_instances.append(factory)
            context = UserExecutionContext(user_id='lifecycle_test_user', run_id=f'lifecycle_test_run_{int(time.time() * 1000)}', session_id='lifecycle_test_session', request_id='lifecycle_test_request')
            self.created_contexts.append(context)
            engine = await factory.create_for_user(context)
            self.created_engines.append(engine)
            lifecycle_events = [('engine_created', {'engine_id': getattr(engine, 'engine_id', None)}), ('engine_active', {'status': 'active'}), ('engine_processing', {'task': 'test_task'}), ('engine_cleanup', {'status': 'cleaning_up'})]
            for event_type, event_data in lifecycle_events:
                try:
                    if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                        await engine.websocket_emitter.emit_event(event_type=event_type, data=event_data)
                    else:
                        lifecycle_coordination_failures.append({'lifecycle_stage': event_type, 'failure_type': 'missing_websocket_emitter', 'description': 'WebSocket emitter not available during lifecycle stage'})
                except Exception as e:
                    lifecycle_coordination_failures.append({'lifecycle_stage': event_type, 'failure_type': 'websocket_event_failure', 'error': str(e), 'description': 'WebSocket event failed during lifecycle stage'})
            try:
                await factory.cleanup_engine(engine)
                if not mock_bridge.send_event.called:
                    lifecycle_coordination_failures.append({'lifecycle_stage': 'engine_cleanup', 'failure_type': 'websocket_bridge_not_notified', 'description': 'WebSocket bridge not notified during engine cleanup'})
            except Exception as e:
                lifecycle_coordination_failures.append({'lifecycle_stage': 'engine_cleanup', 'failure_type': 'cleanup_coordination_failure', 'error': str(e), 'description': 'Factory cleanup failed to coordinate with WebSocket bridge'})
            try:
                await factory.shutdown()
            except Exception as e:
                lifecycle_coordination_failures.append({'lifecycle_stage': 'factory_shutdown', 'failure_type': 'shutdown_coordination_failure', 'error': str(e), 'description': 'Factory shutdown failed to coordinate with WebSocket bridge'})
        except Exception as e:
            lifecycle_coordination_failures.append({'lifecycle_stage': 'factory_creation', 'failure_type': 'factory_websocket_initialization_failure', 'error': str(e), 'description': 'Factory creation with WebSocket bridge failed'})
        self.assertEqual(len(lifecycle_coordination_failures), 0, f'WEBSOCKET LIFECYCLE COORDINATION FAILURES: Found {len(lifecycle_coordination_failures)} WebSocket lifecycle coordination failures with factory. Failures: {lifecycle_coordination_failures}. Lifecycle coordination issues cause WebSocket connection instability.')

    def _log_test_failure_details(self, test_name: str, failure_details: Dict[str, Any]):
        """Log detailed test failure information for analysis."""
        print(f'\n=== EXECUTION ENGINE FACTORY WEBSOCKET INTEGRATION FAILURE: {test_name} ===')
        print(f'Timestamp: {datetime.now().isoformat()}')
        print(f'Business Impact: WebSocket 1011 errors, Chat interruptions - 500K+ ARR at risk')
        print(f'Issue: #884 Execution Engine Factory WebSocket Integration Failures')
        print('\nFailure Details:')
        for key, value in failure_details.items():
            print(f'  {key}: {value}')
        print('\nWebSocket Impact:')
        print('- 1011 Errors: WebSocket connections close unexpectedly')
        print('- Chat Interruptions: Real-time chat functionality fails')
        print('- Event Delivery: WebSocket events not delivered reliably')
        print('- Golden Path: End-to-end user flow interrupted')
        print('\nNext Steps:')
        print('1. Fix factory/WebSocket bridge coordination')
        print('2. Ensure proper WebSocket lifecycle management')
        print('3. Resolve WebSocket event delivery race conditions')
        print('4. Test WebSocket integration under concurrent load')
        print('5. Re-run tests to validate WebSocket coordination fixes')
        print('=' * 60)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')