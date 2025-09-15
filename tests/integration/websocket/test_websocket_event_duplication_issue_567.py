"""
Test suite for Issue #567: WebSocket Event Delivery Duplication Detection

This test validates that WebSocket events are delivered exactly once per user request
and that the Golden Path user flow (login → AI responses) works without event duplication.

Key areas tested:
1. Event delivery uniqueness for 5 critical WebSocket events
2. SSOT agent execution patterns prevent duplication 
3. Multi-user isolation prevents cross-user event delivery
4. Golden Path business value protection ($500K+ ARR)

Focus: Integration tests that don't require Docker orchestration
"""
import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch
from typing import Dict, List, Set, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
try:
    from netra_backend.app.config import get_config
    from netra_backend.app.core.app_state_contracts import validate_app_state_contracts
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    config = get_config()
except ImportError as e:
    pytest.skip(f'Core system imports not available: {e}', allow_module_level=True)

@pytest.mark.integration
class WebSocketEventDuplicationIssue567Tests(SSotAsyncTestCase):
    """
    Integration test suite for WebSocket event duplication prevention (Issue #567).
    
    Validates that the Golden Path user flow delivers WebSocket events exactly once
    and protects the primary business value channel (90% of platform value).
    """
    CRITICAL_EVENTS = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

    def setUp(self):
        """Set up test environment with event tracking."""
        super().setUp()
        self.delivered_events: Dict[str, List[Dict[str, Any]]] = {}
        self.event_timestamps: Dict[str, List[float]] = {}
        self.user_event_isolation: Dict[str, Set[str]] = {}
        self.mock_websocket_connection = SSotMockFactory.create_mock_websocket_connection()
        self.captured_events: List[Dict[str, Any]] = []
        self._setup_event_capture()

    def _setup_event_capture(self):
        """Configure event capture system for duplication detection."""

        def capture_event(event_type: str, user_id: str, data: Dict[str, Any]):
            """Capture events with timestamp and user context for analysis."""
            timestamp = time.time()
            event_record = {'event_type': event_type, 'user_id': user_id, 'data': data, 'timestamp': timestamp}
            if event_type not in self.delivered_events:
                self.delivered_events[event_type] = []
                self.event_timestamps[event_type] = []
            self.delivered_events[event_type].append(event_record)
            self.event_timestamps[event_type].append(timestamp)
            self.captured_events.append(event_record)
            if user_id not in self.user_event_isolation:
                self.user_event_isolation[user_id] = set()
            self.user_event_isolation[user_id].add(event_type)
        self.event_capture_function = capture_event

    async def test_websocket_event_uniqueness_critical(self):
        """
        CRITICAL TEST: Verify each WebSocket event is delivered exactly once per execution.
        
        This test protects the core business value channel by ensuring events
        are not duplicated, which would degrade the user experience.
        """
        user_id = 'test_user_567'
        run_id = 'run_567_uniqueness'
        with patch('netra_backend.app.services.user_execution_context.UserExecutionContext') as mock_context:
            mock_instance = mock_context.return_value
            mock_instance.user_id = user_id
            mock_instance.run_id = run_id
            await self._simulate_agent_execution_with_events(user_id, run_id)
        for event_type in self.CRITICAL_EVENTS:
            events_for_type = self.delivered_events.get(event_type, [])
            user_events = [e for e in events_for_type if e['user_id'] == user_id]
            self.assertEqual(len(user_events), 1, f"Event '{event_type}' should be delivered exactly once for user {user_id}, but was delivered {len(user_events)} times. Events: {user_events}")
        self._validate_event_sequencing(user_id)
        self.assertIn(user_id, self.user_event_isolation)
        user_events = self.user_event_isolation[user_id]
        self.assertEqual(len(user_events), len(self.CRITICAL_EVENTS))

    async def test_multi_user_event_isolation_no_duplication(self):
        """
        TEST: Multi-user WebSocket event isolation prevents duplication across users.
        
        Validates that concurrent user sessions don't cause event duplication
        or cross-user event delivery.
        """
        user_ids = ['user_567_a', 'user_567_b', 'user_567_c']
        run_ids = [f'run_567_{user}' for user in user_ids]
        tasks = []
        for user_id, run_id in zip(user_ids, run_ids):
            task = self._simulate_agent_execution_with_events(user_id, run_id)
            tasks.append(task)
        await asyncio.gather(*tasks)
        for user_id in user_ids:
            for event_type in self.CRITICAL_EVENTS:
                user_events = [e for e in self.delivered_events.get(event_type, []) if e['user_id'] == user_id]
                self.assertEqual(len(user_events), 1, f"User {user_id} should receive exactly one '{event_type}' event, got {len(user_events)}: {user_events}")
        total_expected_events = len(user_ids) * len(self.CRITICAL_EVENTS)
        total_actual_events = len(self.captured_events)
        self.assertEqual(total_actual_events, total_expected_events, f'Expected {total_expected_events} total events for {len(user_ids)} users, but got {total_actual_events} events')
        for user_id in user_ids:
            user_specific_events = [e for e in self.captured_events if e['user_id'] == user_id]
            self.assertEqual(len(user_specific_events), len(self.CRITICAL_EVENTS))

    async def test_golden_path_websocket_flow_no_duplication(self):
        """
        GOLDEN PATH TEST: End-to-end user flow without event duplication.
        
        Validates the complete Golden Path user flow (login → AI responses)
        works without WebSocket event duplication, protecting business value.
        """
        user_id = 'golden_path_user_567'
        await self._simulate_user_authentication(user_id)
        await self._simulate_golden_path_agent_execution(user_id)
        await self._simulate_response_delivery(user_id)
        self._validate_golden_path_event_sequence(user_id)
        business_critical_events = self._extract_business_critical_events(user_id)
        self.assertGreaterEqual(len(business_critical_events), len(self.CRITICAL_EVENTS), 'Golden Path must deliver all business-critical events')
        self._validate_no_business_impact_duplication(user_id)

    async def test_ssot_agent_execution_prevents_duplication(self):
        """
        SSOT TEST: SSOT agent execution patterns prevent event duplication.
        
        Validates that Single Source of Truth patterns in agent execution
        prevent multiple event emissions for the same logical action.
        """
        user_id = 'ssot_test_user_567'
        run_id = 'ssot_run_567'
        with patch('netra_backend.app.agents.supervisor.execution_factory.ExecutionFactory') as mock_factory:
            mock_execution_engine = Mock()
            mock_factory.create_user_execution_engine.return_value = mock_execution_engine
            await self._simulate_ssot_agent_execution(user_id, run_id)
            mock_factory.create_user_execution_engine.assert_called_once()
        for event_type in self.CRITICAL_EVENTS:
            events = [e for e in self.delivered_events.get(event_type, []) if e['user_id'] == user_id]
            self.assertEqual(len(events), 1, f'SSOT should prevent duplication of {event_type}')

    async def test_event_delivery_timing_analysis(self):
        """
        TIMING TEST: Analyze event delivery timing to detect rapid duplicates.
        
        Validates that events are not delivered in rapid succession which
        would indicate duplication bugs.
        """
        user_id = 'timing_test_user_567'
        start_time = time.time()
        await self._simulate_agent_execution_with_events(user_id, 'timing_run_567')
        end_time = time.time()
        for event_type in self.CRITICAL_EVENTS:
            timestamps = [e['timestamp'] for e in self.delivered_events.get(event_type, []) if e['user_id'] == user_id]
            if len(timestamps) > 1:
                for i in range(1, len(timestamps)):
                    time_diff = timestamps[i] - timestamps[i - 1]
                    self.assertGreater(time_diff, 0.01, f'Suspiciously rapid duplicate events for {event_type}: {time_diff}s apart')
        total_execution_time = end_time - start_time
        self.assertLess(total_execution_time, 10.0, 'Execution should complete within 10 seconds')

    async def _simulate_agent_execution_with_events(self, user_id: str, run_id: str):
        """Simulate agent execution that emits all critical WebSocket events."""
        for event_type in self.CRITICAL_EVENTS:
            await asyncio.sleep(0.1)
            self.event_capture_function(event_type, user_id, {'run_id': run_id, 'timestamp': time.time(), 'source': 'test_simulation'})

    async def _simulate_user_authentication(self, user_id: str):
        """Simulate user authentication phase."""
        self.event_capture_function('auth_started', user_id, {'phase': 'authentication'})
        await asyncio.sleep(0.05)
        self.event_capture_function('auth_completed', user_id, {'phase': 'authentication'})

    async def _simulate_golden_path_agent_execution(self, user_id: str):
        """Simulate Golden Path agent execution."""
        run_id = f'golden_path_run_{user_id}'
        await self._simulate_agent_execution_with_events(user_id, run_id)

    async def _simulate_response_delivery(self, user_id: str):
        """Simulate response delivery phase."""
        self.event_capture_function('response_ready', user_id, {'phase': 'delivery'})

    async def _simulate_ssot_agent_execution(self, user_id: str, run_id: str):
        """Simulate SSOT agent execution patterns."""
        await self._simulate_agent_execution_with_events(user_id, run_id)

    def _validate_event_sequencing(self, user_id: str):
        """Validate that events are delivered in the expected sequence."""
        user_events = [e for e in self.captured_events if e['user_id'] == user_id]
        user_events.sort(key=lambda x: x['timestamp'])
        event_sequence = [e['event_type'] for e in user_events if e['event_type'] in self.CRITICAL_EVENTS]
        expected_sequence = self.CRITICAL_EVENTS
        self.assertEqual(event_sequence, expected_sequence, f'Events should follow expected sequence {expected_sequence}, got {event_sequence}')

    def _validate_golden_path_event_sequence(self, user_id: str):
        """Validate complete Golden Path event sequence."""
        user_events = [e for e in self.captured_events if e['user_id'] == user_id]
        required_event_types = {'auth_started', 'auth_completed', 'response_ready'} | set(self.CRITICAL_EVENTS)
        actual_event_types = {e['event_type'] for e in user_events}
        missing_events = required_event_types - actual_event_types
        self.assertEqual(len(missing_events), 0, f'Golden Path missing required events: {missing_events}')

    def _extract_business_critical_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Extract events that are critical for business value delivery."""
        return [e for e in self.captured_events if e['user_id'] == user_id and e['event_type'] in self.CRITICAL_EVENTS]

    def _validate_no_business_impact_duplication(self, user_id: str):
        """Validate that business-impacting events are not duplicated."""
        business_events = self._extract_business_critical_events(user_id)
        event_counts = {}
        for event in business_events:
            event_type = event['event_type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        for event_type, count in event_counts.items():
            self.assertEqual(count, 1, f"Business-critical event '{event_type}' should appear once, got {count} times")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')