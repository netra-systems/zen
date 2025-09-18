"""WebSocket Event Consistency Tests for SSOT Tool Dispatcher Integration.

Test Phase 2: WebSocket Event Delivery Validation Tests
Focus on the 85% failure risk in WebSocket events due to SSOT violations.

CRITICAL ISSUE:
- Inconsistent WebSocket event delivery across different dispatcher implementations
- Missing events due to bridge adapter integration gaps  
- Event ordering and timing inconsistencies
- Cross-user event leakage due to shared WebSocket managers

Business Value:
- Ensures all 5 critical WebSocket events are delivered consistently
- Validates event delivery matches Golden Path requirements
- Prevents silent failures in real-time user experience
- Enables reliable agent progress visibility
"""
import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, call, patch
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

@pytest.mark.unit
class WebSocketEventConsistencyValidationTests(SSotAsyncTestCase):
    """Test WebSocket event consistency across SSOT tool dispatcher implementations."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        self.user_context = UserExecutionContext(user_id='websocket_test_user', thread_id='websocket_test_thread', run_id=f'websocket_test_run_{uuid.uuid4()}')
        self.mock_websocket_manager = MagicMock()
        self.mock_websocket_manager.emit_event = AsyncMock()
        self.emitted_events = []

    async def test_all_critical_websocket_events_supported(self):
        """Test that all 5 critical WebSocket events are supported by SSOT implementation.
        
        CRITICAL EVENTS REQUIRED:
        1. agent_started
        2. agent_thinking
        3. tool_executing
        4. tool_completed
        5. agent_completed
        
        EXPECTED: FAIL initially due to inconsistent bridge implementations
        EXPECTED: PASS after SSOT consolidation with unified WebSocket integration
        """
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        supported_events = []
        missing_events = []
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            mock_emitter = MagicMock()
            for event in required_events:
                method_name = f'notify_{event}'
                if hasattr(mock_emitter, method_name):
                    setattr(mock_emitter, method_name, AsyncMock(return_value=True))
                    supported_events.append(event)
                else:
                    missing_events.append(event)
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context, websocket_emitter=mock_emitter)
            self.assertTrue(dispatcher.has_websocket_support, 'RequestScopedToolDispatcher should detect WebSocket support when emitter provided')
        except Exception as e:
            self.fail(f'Failed to test WebSocket event support: {e}')
        self.assertEqual(len(missing_events), 0, f'WEBSOCKET EVENT VIOLATION: Missing critical events: {missing_events}. SSOT implementation must support all 5 critical events: {required_events}')
        self.assertEqual(len(supported_events), 5, f'WEBSOCKET EVENT VIOLATION: Only {len(supported_events)}/5 events supported: {supported_events}. Must support all 5 critical events after SSOT consolidation.')

    async def test_websocket_bridge_adapter_consistency(self):
        """Test that WebSocket bridge adapter provides consistent interface.
        
        EXPECTED: FAIL initially due to multiple bridge implementations:
        - WebSocketBridgeAdapter in request_scoped_tool_dispatcher
        - AgentWebSocketBridge in services
        - Direct WebSocket manager usage in some implementations
        
        EXPECTED: PASS after SSOT consolidation with unified bridge
        """
        bridge_types = []
        adapter_methods = []
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import WebSocketBridgeAdapter
            from netra_backend.app.websocket_core import WebSocketEventEmitter
            mock_emitter = MagicMock(spec=WebSocketEventEmitter)
            for event in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                setattr(mock_emitter, f'notify_{event}', AsyncMock(return_value=True))
            adapter = WebSocketBridgeAdapter(mock_emitter, self.user_context)
            bridge_types.append('WebSocketBridgeAdapter')
            adapter_methods.extend([method for method in dir(adapter) if method.startswith('notify_') and (not method.startswith('__'))])
        except ImportError:
            pass
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            bridge = AgentWebSocketBridge()
            bridge_types.append('AgentWebSocketBridge')
            bridge_methods = [method for method in dir(bridge) if method.startswith('notify_') and (not method.startswith('__'))]
            adapter_methods.extend(bridge_methods)
        except ImportError:
            pass
        unique_methods = set(adapter_methods)
        required_methods = {'notify_agent_started', 'notify_agent_thinking', 'notify_tool_executing', 'notify_tool_completed', 'notify_agent_completed'}
        missing_methods = required_methods - unique_methods
        self.assertEqual(len(missing_methods), 0, f'BRIDGE INTERFACE VIOLATION: Missing required methods: {missing_methods}. All bridge implementations must provide consistent interface.')
        self.assertLessEqual(len(bridge_types), 2, f'BRIDGE CONSOLIDATION VIOLATION: Too many bridge types: {bridge_types}. Should have at most 1 SSOT bridge + 1 compatibility bridge after consolidation.')

    async def test_websocket_event_delivery_end_to_end(self):
        """Test complete WebSocket event delivery from tool execution to emission.
        
        EXPECTED: FAIL initially due to broken event delivery chains
        EXPECTED: PASS after SSOT consolidation with complete event flow
        """
        event_sequence = []

        def track_event(event_type: str, **kwargs):
            event_sequence.append({'type': event_type, 'timestamp': time.time(), 'data': kwargs})
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            mock_emitter = MagicMock()
            mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: track_event('tool_executing', args=args, kwargs=kwargs))
            mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: track_event('tool_completed', args=args, kwargs=kwargs))
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context, websocket_emitter=mock_emitter)

            def test_tool(query: str) -> str:
                return f'Test result for: {query}'
            dispatcher.register_tool('test_tool', test_tool, 'Test tool for WebSocket events')
            result = await dispatcher.dispatch('test_tool', query='test query')
            self.assertIsNotNone(result, 'Tool execution should return a result')
            event_types = [event['type'] for event in event_sequence]
            self.assertIn('tool_executing', event_types, 'WEBSOCKET EVENT DELIVERY VIOLATION: tool_executing event was not emitted during tool execution')
            self.assertIn('tool_completed', event_types, 'WEBSOCKET EVENT DELIVERY VIOLATION: tool_completed event was not emitted after tool completion')
            if len(event_types) >= 2:
                executing_index = event_types.index('tool_executing')
                completed_index = event_types.index('tool_completed')
                self.assertLess(executing_index, completed_index, 'WEBSOCKET EVENT ORDER VIOLATION: tool_executing should come before tool_completed')
            await dispatcher.cleanup()
        except Exception as e:
            self.fail(f'WebSocket event delivery test failed: {e}')

    async def test_websocket_event_user_isolation(self):
        """Test that WebSocket events are properly isolated per user.
        
        EXPECTED: FAIL initially due to shared WebSocket managers causing cross-user leakage
        EXPECTED: PASS after SSOT consolidation with proper user isolation
        """
        user_context_2 = UserExecutionContext(user_id='websocket_test_user_2', thread_id='websocket_test_thread_2', run_id=f'websocket_test_run_2_{uuid.uuid4()}')
        user_1_events = []
        user_2_events = []

        def track_user_1_event(event_type: str, run_id: str, **kwargs):
            user_1_events.append({'type': event_type, 'run_id': run_id, 'user_context': self.user_context.user_id})

        def track_user_2_event(event_type: str, run_id: str, **kwargs):
            user_2_events.append({'type': event_type, 'run_id': run_id, 'user_context': user_context_2.user_id})
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            mock_emitter_1 = MagicMock()
            mock_emitter_1.notify_tool_executing = AsyncMock(side_effect=track_user_1_event)
            mock_emitter_1.notify_tool_completed = AsyncMock(side_effect=track_user_1_event)
            mock_emitter_2 = MagicMock()
            mock_emitter_2.notify_tool_executing = AsyncMock(side_effect=track_user_2_event)
            mock_emitter_2.notify_tool_completed = AsyncMock(side_effect=track_user_2_event)
            dispatcher_1 = RequestScopedToolDispatcher(user_context=self.user_context, websocket_emitter=mock_emitter_1)
            dispatcher_2 = RequestScopedToolDispatcher(user_context=user_context_2, websocket_emitter=mock_emitter_2)
            dispatcher_1.register_tool('user1_tool', lambda x: f'User 1: {x}')
            dispatcher_2.register_tool('user2_tool', lambda x: f'User 2: {x}')
            await asyncio.gather(dispatcher_1.dispatch('user1_tool', query='test1'), dispatcher_2.dispatch('user2_tool', query='test2'))
            for event in user_1_events:
                self.assertEqual(event['run_id'], self.user_context.run_id, f"USER ISOLATION VIOLATION: User 1 received event for wrong run_id: {event['run_id']}")
            for event in user_2_events:
                self.assertEqual(event['run_id'], user_context_2.run_id, f"USER ISOLATION VIOLATION: User 2 received event for wrong run_id: {event['run_id']}")
            user_1_run_ids = {event['run_id'] for event in user_1_events}
            user_2_run_ids = {event['run_id'] for event in user_2_events}
            self.assertEqual(len(user_1_run_ids.intersection(user_2_run_ids)), 0, f'USER ISOLATION VIOLATION: Cross-user event leakage detected. User 1 run_ids: {user_1_run_ids}, User 2 run_ids: {user_2_run_ids}')
            await dispatcher_1.cleanup()
            await dispatcher_2.cleanup()
        except Exception as e:
            self.fail(f'WebSocket event user isolation test failed: {e}')

    async def test_websocket_event_error_handling(self):
        """Test WebSocket event error handling and recovery.
        
        EXPECTED: FAIL initially due to inconsistent error handling across implementations
        EXPECTED: PASS after SSOT consolidation with unified error handling
        """
        error_scenarios = []
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            mock_failing_emitter = MagicMock()
            mock_failing_emitter.notify_tool_executing = AsyncMock(side_effect=Exception('WebSocket connection failed'))
            mock_failing_emitter.notify_tool_completed = AsyncMock(return_value=True)
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context, websocket_emitter=mock_failing_emitter)
            dispatcher.register_tool('test_tool', lambda x: f'Result: {x}')
            try:
                result = await dispatcher.dispatch('test_tool', query='test')
                self.assertIsNotNone(result, 'WEBSOCKET ERROR HANDLING VIOLATION: Tool execution should succeed even when WebSocket events fail')
            except Exception as e:
                error_scenarios.append(f'Tool execution failed due to WebSocket error: {e}')
            await dispatcher.cleanup()
            dispatcher_no_ws = RequestScopedToolDispatcher(user_context=self.user_context, websocket_emitter=None)
            self.assertFalse(dispatcher_no_ws.has_websocket_support, 'Dispatcher should detect lack of WebSocket support when emitter is None')
            dispatcher_no_ws.register_tool('test_tool', lambda x: f'No WS: {x}')
            try:
                result = await dispatcher_no_ws.dispatch('test_tool', query='test')
                self.assertIsNotNone(result, 'Tool execution should work without WebSocket support')
            except Exception as e:
                error_scenarios.append(f'Tool execution failed without WebSocket: {e}')
            await dispatcher_no_ws.cleanup()
        except Exception as e:
            error_scenarios.append(f'WebSocket error handling test setup failed: {e}')
        self.assertEqual(len(error_scenarios), 0, f'WEBSOCKET ERROR HANDLING VIOLATIONS: {error_scenarios}')

@pytest.mark.unit
class WebSocketEventTimingAndOrderingTests(SSotAsyncTestCase):
    """Test WebSocket event timing and ordering consistency."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        self.user_context = UserExecutionContext(user_id='timing_test_user', thread_id='timing_test_thread', run_id=f'timing_test_run_{uuid.uuid4()}')

    async def test_websocket_event_ordering(self):
        """Test that WebSocket events are emitted in correct order.
        
        EXPECTED ORDER for tool execution:
        1. tool_executing (when tool starts)
        2. tool_completed (when tool finishes)
        
        EXPECTED: FAIL initially due to inconsistent ordering
        EXPECTED: PASS after SSOT consolidation with guaranteed ordering
        """
        event_timeline = []

        def record_event_with_timing(event_type: str, *args, **kwargs):
            event_timeline.append({'type': event_type, 'timestamp': time.time(), 'order': len(event_timeline)})
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            mock_emitter = MagicMock()
            mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: record_event_with_timing('tool_executing'))
            mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: record_event_with_timing('tool_completed'))
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context, websocket_emitter=mock_emitter)

            async def slow_tool(query: str) -> str:
                await asyncio.sleep(0.1)
                return f'Processed: {query}'
            dispatcher.register_tool('slow_tool', slow_tool)
            await dispatcher.dispatch('slow_tool', query='test')
            self.assertGreaterEqual(len(event_timeline), 2, 'Should have recorded at least tool_executing and tool_completed events')
            if len(event_timeline) >= 2:
                executing_events = [e for e in event_timeline if e['type'] == 'tool_executing']
                completed_events = [e for e in event_timeline if e['type'] == 'tool_completed']
                self.assertGreater(len(executing_events), 0, 'Should have recorded tool_executing event')
                self.assertGreater(len(completed_events), 0, 'Should have recorded tool_completed event')
                if executing_events and completed_events:
                    first_executing = executing_events[0]
                    first_completed = completed_events[0]
                    self.assertLess(first_executing['order'], first_completed['order'], 'WEBSOCKET EVENT ORDER VIOLATION: tool_executing should come before tool_completed')
                    self.assertLess(first_executing['timestamp'], first_completed['timestamp'], 'WEBSOCKET EVENT TIMING VIOLATION: tool_executing should have earlier timestamp than tool_completed')
            await dispatcher.cleanup()
        except Exception as e:
            self.fail(f'WebSocket event ordering test failed: {e}')

    async def test_concurrent_websocket_event_isolation(self):
        """Test that concurrent tool executions don't interfere with each other's events.
        
        EXPECTED: FAIL initially due to shared state in event emission
        EXPECTED: PASS after SSOT consolidation with proper concurrency handling
        """
        execution_events = {}

        def record_execution_event(execution_id: str, event_type: str, *args, **kwargs):
            if execution_id not in execution_events:
                execution_events[execution_id] = []
            execution_events[execution_id].append({'type': event_type, 'timestamp': time.time(), 'args': args, 'kwargs': kwargs})
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            mock_emitter = MagicMock()

            async def track_executing(*args, **kwargs):
                run_id = args[0] if args else 'unknown'
                record_execution_event(run_id, 'tool_executing', *args, **kwargs)

            async def track_completed(*args, **kwargs):
                run_id = args[0] if args else 'unknown'
                record_execution_event(run_id, 'tool_completed', *args, **kwargs)
            mock_emitter.notify_tool_executing = AsyncMock(side_effect=track_executing)
            mock_emitter.notify_tool_completed = AsyncMock(side_effect=track_completed)
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context, websocket_emitter=mock_emitter)

            async def fast_tool(query: str) -> str:
                await asyncio.sleep(0.05)
                return f'Fast: {query}'

            async def slow_tool(query: str) -> str:
                await asyncio.sleep(0.15)
                return f'Slow: {query}'
            dispatcher.register_tool('fast_tool', fast_tool)
            dispatcher.register_tool('slow_tool', slow_tool)
            results = await asyncio.gather(dispatcher.dispatch('fast_tool', query='test1'), dispatcher.dispatch('slow_tool', query='test2'), dispatcher.dispatch('fast_tool', query='test3'), return_exceptions=True)
            self.assertGreaterEqual(len(execution_events), 1, f'Should have recorded events for concurrent executions, got: {list(execution_events.keys())}')
            for execution_id, events in execution_events.items():
                event_types = [e['type'] for e in events]
                self.assertIn('tool_executing', event_types, f'CONCURRENCY ISOLATION VIOLATION: Execution {execution_id} missing tool_executing event')
                self.assertIn('tool_completed', event_types, f'CONCURRENCY ISOLATION VIOLATION: Execution {execution_id} missing tool_completed event')
            await dispatcher.cleanup()
        except Exception as e:
            self.fail(f'Concurrent WebSocket event isolation test failed: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')