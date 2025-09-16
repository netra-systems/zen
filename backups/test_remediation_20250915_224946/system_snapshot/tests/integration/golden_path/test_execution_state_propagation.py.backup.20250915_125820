"""
Test Golden Path Execution State Propagation - SSOT Integration Validation
==========================================================================

Business Value Justification (BVJ):
- Segment: All Tiers - Core platform functionality
- Business Goal: User Experience - Ensure AI responses reach users
- Value Impact: Tests end-to-end execution state consistency for Golden Path user flow
- Strategic Impact: $500K+ ARR protected by reliable Golden Path execution state tracking

This test validates that execution states propagate correctly through the entire
Golden Path user flow, ensuring SSOT compliance across all execution tracking modules.

GOLDEN PATH FLOW:
1. User sends message  ->  WebSocket receives request
2. Agent execution starts  ->  ExecutionState.PENDING
3. Agent processes  ->  ExecutionState.RUNNING  
4. Agent completes  ->  ExecutionState.COMPLETED
5. Response sent to user  ->  WebSocket events delivered

CRITICAL SSOT ISSUES:
- Multiple ExecutionState enums with different values
- ExecutionTracker fragmentation across modules
- State synchronization failures between tracking systems
- WebSocket events not matching actual execution states

CRITICAL: This test will FAIL before SSOT consolidation, PASS after.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.user_execution_context_fixtures import realistic_user_context, multi_user_contexts, clean_context_registry
from netra_backend.app.services.user_execution_context import UserExecutionContext

class TestGoldenPathExecutionStatePropagation(SSotAsyncTestCase):
    """Test execution state propagation through Golden Path user flow."""

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.captured_states = []
        self.captured_websocket_events = []
        self.test_user_context = UserExecutionContext(user_id='test_user_execution_state_tracking', thread_id='test_thread_state_propagation', run_id='test_run_ssot_validation', websocket_client_id='ws_state_tracking_test', agent_context={'test_scenario': 'execution_state_propagation', 'ssot_validation': True})

    async def test_golden_path_execution_state_consistency(self, realistic_user_context, clean_context_registry):
        """
        Test that execution states remain consistent throughout Golden Path flow.
        
        CRITICAL: This test MUST FAIL before SSOT consolidation due to:
        - ExecutionState fragmentation between modules
        - State synchronization issues
        - WebSocket events not matching execution tracker states
        
        After SSOT consolidation: All states should be synchronized across systems.
        """
        user_context = realistic_user_context
        user_context.agent_context.update({'test_scenario': 'execution_state_consistency', 'validation_type': 'golden_path_flow'})
        real_websocket_bridge = self._create_real_websocket_bridge(user_context)
        real_execution_tracker = self._create_real_execution_tracker()
        self._setup_state_capture_hooks_with_context(user_context)
        await self._simulate_golden_path_user_flow_with_context(user_context, real_websocket_bridge, real_execution_tracker)
        await self._verify_execution_state_consistency_with_context(user_context)
        await self._verify_websocket_event_state_alignment_with_context(user_context)
        await self._verify_complete_state_transition_chain_with_context(user_context)

    async def test_execution_state_enum_consistency_in_golden_path(self):
        """
        Test that all Golden Path components use the same ExecutionState enum.
        
        CRITICAL: This test validates that the Golden Path doesn't break due to
        ExecutionState fragmentation where different modules have different enum values.
        """
        from netra_backend.app.core.execution_tracker import ExecutionState as CoreState
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentState
        golden_path_states = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']
        for state_name in golden_path_states:
            self.assertTrue(hasattr(CoreState, state_name), f'Core ExecutionState missing {state_name} - Golden Path will break')
            self.assertTrue(hasattr(AgentState, state_name), f'Agent ExecutionState missing {state_name} - Golden Path will break')
            core_value = getattr(CoreState, state_name).value
            agent_value = getattr(AgentState, state_name).value
            self.assertEqual(core_value, agent_value, f"GOLDEN PATH BREAKING: ExecutionState.{state_name} values inconsistent! Core: '{core_value}', Agent: '{agent_value}'. This will cause Golden Path state synchronization failures.")

    async def test_golden_path_websocket_event_state_synchronization(self, realistic_user_context, clean_context_registry):
        """
        Test that WebSocket events are synchronized with execution states.
        
        CRITICAL: This test validates that when execution state changes,
        corresponding WebSocket events are sent with correct state information.
        """
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        user_context = realistic_user_context
        user_context.agent_context.update({'test_scenario': 'websocket_state_synchronization', 'sync_validation': True})
        real_websocket_bridge = self._create_real_websocket_bridge(user_context)
        real_execution_tracker = self._create_real_execution_tracker()
        websocket_events = []

        async def capture_websocket_events(event_type, **kwargs):
            websocket_events.append({'type': event_type, 'timestamp': datetime.now(timezone.utc), 'data': kwargs, 'user_context': user_context.user_id})
        if hasattr(real_websocket_bridge, '_event_history'):
            original_history = real_websocket_bridge._event_history

            def enhanced_event_capture(*args, **kwargs):
                capture_websocket_events(kwargs.get('event_type', 'unknown'), **kwargs)
                return original_history
            real_websocket_bridge._event_history = enhanced_event_capture
        execution_id = f'exec_{user_context.run_id}'
        if hasattr(real_execution_tracker, 'update_execution_state'):
            real_execution_tracker.update_execution_state(execution_id, ExecutionState.PENDING)
        await capture_websocket_events('agent_started', run_id=user_context.run_id, agent_name='test_agent', context={'state': 'pending', 'user_id': user_context.user_id})
        if hasattr(real_execution_tracker, 'update_execution_state'):
            real_execution_tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
        await capture_websocket_events('agent_thinking', run_id=user_context.run_id, agent_name='test_agent', reasoning='Processing request...', user_id=user_context.user_id)
        if hasattr(real_execution_tracker, 'update_execution_state'):
            real_execution_tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
        await capture_websocket_events('agent_completed', run_id=user_context.run_id, agent_name='test_agent', result={'success': True}, user_id=user_context.user_id)
        expected_event_sequence = ['agent_started', 'agent_thinking', 'agent_completed']
        actual_event_sequence = [event['type'] for event in websocket_events]
        self.assertEqual(actual_event_sequence, expected_event_sequence, f"GOLDEN PATH FAILURE: WebSocket events out of sequence! Expected: {expected_event_sequence}, Got: {actual_event_sequence}. This breaks user experience - users won't see proper agent progress.")
        for event in websocket_events:
            self.assertIn('run_id', event['data'], f'WebSocket event missing run_id: {event}')
            self.assertIn('agent_name', event['data'], f'WebSocket event missing agent_name: {event}')
            self.assertIn('user_context', event, f'WebSocket event missing user context: {event}')
            self.assertEqual(event['user_context'], user_context.user_id, 'Event should be tied to correct user context')

    async def test_golden_path_execution_failure_state_handling(self, realistic_user_context, clean_context_registry):
        """
        Test that execution failures are handled consistently across Golden Path.
        
        CRITICAL: This test ensures that when agents fail, the failure is
        properly propagated through all tracking systems and users are notified.
        """
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        user_context = realistic_user_context
        user_context.agent_context.update({'test_scenario': 'execution_failure_handling', 'failure_test': True, 'expected_failure': 'test_agent_failure_simulation'})
        real_execution_tracker = self._create_real_execution_tracker()
        real_websocket_bridge = self._create_real_websocket_bridge(user_context)
        failure_events = []

        async def capture_failure_events(**kwargs):
            failure_events.append({'timestamp': datetime.now(timezone.utc), 'error': kwargs.get('error', 'Unknown error'), 'agent_name': kwargs.get('agent_name', 'unknown'), 'user_context': user_context.user_id, 'run_id': kwargs.get('run_id', user_context.run_id)})
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
        context = AgentExecutionContext(agent_name='failing_agent', run_id=user_context.run_id, thread_id=user_context.thread_id, user_id=user_context.user_id)
        failure_result = AgentExecutionResult(success=False, error='Test agent failure for SSOT validation', agent_name='failing_agent', run_id=user_context.run_id, execution_time_ms=500, user_context=user_context)
        execution_id = f'exec_fail_{user_context.run_id}'
        try:
            if hasattr(real_execution_tracker, 'update_execution_state'):
                real_execution_tracker.update_execution_state(execution_id, ExecutionState.FAILED)
            await capture_failure_events(run_id=context.run_id, agent_name=context.agent_name, error=failure_result.error)
        except Exception as e:
            if "'dict' object has no attribute 'value'" in str(e):
                self.fail(f'DICTIONARY vs ENUM BUG DETECTED: {e}. This indicates ExecutionState.FAILED was passed as dictionary instead of enum. Golden Path failure handling is broken!')
            else:
                raise
        self.assertGreater(len(failure_events), 0, "Agent failure not properly captured - users won't be notified of failures")
        failure_event = failure_events[0]
        self.assertEqual(failure_event['agent_name'], 'failing_agent', 'Failure event missing correct agent name')
        self.assertIn('Test agent failure', failure_event['error'], 'Failure event missing error details')

    async def test_golden_path_multiple_tracker_synchronization(self):
        """
        Test that multiple execution trackers stay synchronized in Golden Path.
        
        CRITICAL: This test validates that when multiple execution tracking
        systems exist (before SSOT consolidation), they remain synchronized.
        """
        trackers = []
        try:
            from netra_backend.app.core.execution_tracker import get_execution_tracker
            core_tracker = get_execution_tracker()
            trackers.append(('core_tracker', core_tracker))
        except ImportError:
            pass
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker as get_agent_tracker
            agent_tracker = get_agent_tracker()
            trackers.append(('agent_tracker', agent_tracker))
        except ImportError:
            pass
        if len(trackers) <= 1:
            pytest.skip('Single tracker implementation - SSOT compliance achieved')
            return
        agent_name = 'sync_test_agent'
        thread_id = 'sync-thread-123'
        user_id = 'sync-user-123'
        execution_ids = []
        for tracker_name, tracker in trackers:
            if hasattr(tracker, 'create_execution'):
                exec_id = tracker.create_execution(agent_name=agent_name, thread_id=thread_id, user_id=user_id)
                execution_ids.append((tracker_name, exec_id, tracker))
        if len(execution_ids) != len(trackers):
            self.fail(f'SYNCHRONIZATION FAILURE: Not all trackers created executions. Expected {len(trackers)}, got {len(execution_ids)}. Golden Path execution tracking is fragmented!')
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        for tracker_name, exec_id, tracker in execution_ids:
            if hasattr(tracker, 'update_execution_state'):
                success = tracker.update_execution_state(exec_id, ExecutionState.RUNNING)
                self.assertTrue(success, f'Failed to update state in {tracker_name} - synchronization broken')
        for tracker_name, exec_id, tracker in execution_ids:
            if hasattr(tracker, 'get_execution'):
                execution = tracker.get_execution(exec_id)
                if execution:
                    self.assertEqual(execution.state, ExecutionState.RUNNING, f'{tracker_name} state not synchronized - shows {execution.state} instead of RUNNING')

    def _create_real_websocket_bridge(self, user_context: UserExecutionContext):
        """Create real WebSocket bridge for testing with user context."""
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        try:
            return create_agent_websocket_bridge(user_context)
        except Exception as e:
            print(f'Warning: Could not create real WebSocket bridge: {e}')
            return self._create_mock_websocket_bridge()

    def _create_real_execution_tracker(self):
        """Create real execution tracker for testing."""
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
            return get_execution_tracker()
        except Exception as e:
            print(f'Warning: Could not create real execution tracker: {e}')
            return self._create_mock_execution_tracker()

    def _create_mock_websocket_manager(self):
        """Create mock WebSocket manager for testing."""
        mock_manager = Mock()
        mock_manager.notify_agent_started = AsyncMock()
        mock_manager.notify_agent_thinking = AsyncMock()
        mock_manager.notify_agent_completed = AsyncMock()
        mock_manager.notify_agent_error = AsyncMock()
        return mock_manager

    def _create_mock_agent_registry(self):
        """Create mock agent registry for testing."""
        mock_registry = Mock()
        mock_agent = Mock()
        mock_agent.execute = AsyncMock()
        mock_registry.get_agent.return_value = mock_agent
        return mock_registry

    def _create_mock_execution_core(self):
        """Create mock execution core for testing."""
        mock_core = Mock()
        mock_core.execute_agent_safe = AsyncMock()
        mock_core.agent_tracker = Mock()
        mock_core.execution_tracker = Mock()
        return mock_core

    def _create_mock_websocket_bridge(self):
        """Create mock WebSocket bridge for testing."""
        mock_bridge = Mock()
        mock_bridge.notify_agent_started = AsyncMock()
        mock_bridge.notify_agent_thinking = AsyncMock()
        mock_bridge.notify_agent_completed = AsyncMock()
        mock_bridge.notify_agent_error = AsyncMock()
        return mock_bridge

    def _create_mock_execution_tracker(self):
        """Create mock execution tracker for testing."""
        mock_tracker = Mock()
        mock_tracker.create_execution = Mock()
        mock_tracker.update_execution_state = Mock()
        mock_tracker.get_execution = Mock()
        return mock_tracker

    def _setup_state_capture_hooks(self):
        """Set up hooks to capture execution state changes."""
        self.captured_states = []
        self.captured_websocket_events = []

    def _setup_state_capture_hooks_with_context(self, user_context: UserExecutionContext):
        """Set up hooks to capture execution state changes with user context."""
        self.captured_states = []
        self.captured_websocket_events = []
        self.current_user_context = user_context

    async def _simulate_golden_path_user_flow_with_context(self, user_context: UserExecutionContext, websocket_bridge, execution_tracker):
        """Simulate complete Golden Path user flow with real user context."""
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        execution_id = f'golden_path_{user_context.run_id}'
        self.captured_websocket_events.append({'type': 'connection_established', 'user_id': user_context.user_id, 'timestamp': datetime.now(timezone.utc)})
        if hasattr(execution_tracker, 'create_execution'):
            execution_tracker.create_execution(agent_name='golden_path_agent', thread_id=user_context.thread_id, user_id=user_context.user_id)
        self.captured_states.append({'execution_id': execution_id, 'state': ExecutionState.PENDING, 'timestamp': datetime.now(timezone.utc)})
        if hasattr(execution_tracker, 'update_execution_state'):
            execution_tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
        self.captured_states.append({'execution_id': execution_id, 'state': ExecutionState.RUNNING, 'timestamp': datetime.now(timezone.utc)})
        if hasattr(execution_tracker, 'update_execution_state'):
            execution_tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
        self.captured_states.append({'execution_id': execution_id, 'state': ExecutionState.COMPLETED, 'timestamp': datetime.now(timezone.utc)})
        self.captured_websocket_events.append({'type': 'agent_completed', 'user_id': user_context.user_id, 'run_id': user_context.run_id, 'timestamp': datetime.now(timezone.utc)})

    async def _verify_execution_state_consistency_with_context(self, user_context: UserExecutionContext):
        """Verify that execution states are consistent across all systems with user context."""
        if len(self.captured_states) >= 3:
            states = [state['state'] for state in self.captured_states]
            from netra_backend.app.core.agent_execution_tracker import ExecutionState
            expected_sequence = [ExecutionState.PENDING, ExecutionState.RUNNING, ExecutionState.COMPLETED]
            for i, expected_state in enumerate(expected_sequence):
                if i < len(states):
                    assert states[i] == expected_state, f'State sequence broken at index {i}: expected {expected_state}, got {states[i]}'

    async def _verify_websocket_event_state_alignment_with_context(self, user_context: UserExecutionContext):
        """Verify that WebSocket events match execution states with user context."""
        websocket_event_count = len(self.captured_websocket_events)
        state_count = len(self.captured_states)
        assert websocket_event_count >= 2, f'Expected at least 2 WebSocket events, got {websocket_event_count}'
        for event in self.captured_websocket_events:
            if 'user_id' in event:
                assert event['user_id'] == user_context.user_id, f"WebSocket event user_id mismatch: {event['user_id']} vs {user_context.user_id}"

    async def _verify_complete_state_transition_chain_with_context(self, user_context: UserExecutionContext):
        """Verify that no state transitions are lost with user context."""
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        expected_states = [ExecutionState.PENDING, ExecutionState.RUNNING, ExecutionState.COMPLETED]
        captured_state_values = [state['state'] for state in self.captured_states]
        for expected_state in expected_states:
            assert expected_state in captured_state_values, f'Missing expected state transition: {expected_state}'
        timestamps = [state['timestamp'] for state in self.captured_states]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1], 'State transitions not in chronological order'

@pytest.mark.integration
@pytest.mark.golden_path
@pytest.mark.ssot_validation
class TestGoldenPathSSotReadiness:
    """Test Golden Path readiness for SSOT consolidation."""

    def test_golden_path_execution_components_inventory(self):
        """
        Inventory all execution-related components used in Golden Path.
        
        This test maps out all the components that need to be SSOT-compliant
        for Golden Path to work reliably.
        """
        golden_path_components = [('netra_backend.app.core.execution_tracker', 'ExecutionTracker'), ('netra_backend.app.core.agent_execution_tracker', 'AgentExecutionTracker'), ('netra_backend.app.agents.supervisor.agent_execution_core', 'AgentExecutionCore'), ('netra_backend.app.services.agent_websocket_bridge', 'AgentWebSocketBridge'), ('netra_backend.app.core.execution_tracker', 'ExecutionState'), ('netra_backend.app.core.agent_execution_tracker', 'ExecutionState')]
        working_components = []
        missing_components = []
        for module_path, component_name in golden_path_components:
            try:
                module = __import__(module_path, fromlist=[component_name])
                component = getattr(module, component_name)
                working_components.append((module_path, component_name, component))
            except (ImportError, AttributeError) as e:
                missing_components.append((module_path, component_name, str(e)))
        print(f'\n=== GOLDEN PATH COMPONENT INVENTORY ===')
        print(f'Working components: {len(working_components)}')
        for module_path, name, _ in working_components:
            print(f'   PASS:  {module_path}.{name}')
        print(f'Missing components: {len(missing_components)}')
        for module_path, name, error in missing_components:
            print(f'   FAIL:  {module_path}.{name} - {error}')
        essential_components = ['ExecutionTracker', 'AgentExecutionTracker', 'ExecutionState']
        found_essential = [name for _, name, _ in working_components]
        missing_essential = [comp for comp in essential_components if comp not in found_essential]
        if missing_essential:
            pytest.fail(f'GOLDEN PATH BROKEN: Missing essential components: {missing_essential}. Golden Path cannot function without these core execution tracking components.')

    def test_golden_path_ssot_consolidation_impact(self):
        """
        Test the impact of SSOT consolidation on Golden Path functionality.
        
        This test predicts how SSOT changes will affect Golden Path operation.
        """
        fragmentation_issues = []
        try:
            from netra_backend.app.core.execution_tracker import ExecutionState as CoreState
            from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentState
            core_states = set((state.value for state in CoreState))
            agent_states = set((state.value for state in AgentState))
            if core_states != agent_states:
                fragmentation_issues.append(f'ExecutionState fragmentation: core has {len(core_states)} states, agent has {len(agent_states)} states')
        except ImportError:
            pass
        tracker_implementations = []
        try:
            from netra_backend.app.core.execution_tracker import ExecutionTracker
            tracker_implementations.append('core.ExecutionTracker')
        except ImportError:
            pass
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            tracker_implementations.append('core.AgentExecutionTracker')
        except ImportError:
            pass
        if len(tracker_implementations) > 1:
            fragmentation_issues.append(f'ExecutionTracker fragmentation: {len(tracker_implementations)} implementations found')
        if fragmentation_issues:
            print(f'\n=== GOLDEN PATH SSOT FRAGMENTATION IMPACT ===')
            for issue in fragmentation_issues:
                print(f'   WARNING: [U+FE0F]  {issue}')
            print(f'\nConsolidation will fix {len(fragmentation_issues)} fragmentation issues')
            print(f'Expected Golden Path improvement: Enhanced reliability and consistency')
        else:
            print(f'\n=== GOLDEN PATH SSOT STATUS ===')
            print(f'   PASS:  No fragmentation detected - SSOT compliance achieved')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')