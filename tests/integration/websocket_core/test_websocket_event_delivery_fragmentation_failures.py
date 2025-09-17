"""Integration Tests: WebSocket Event Delivery Fragmentation Failures - Issue #965

PURPOSE: Test WebSocket event delivery consistency failures caused by manager fragmentation

BUSINESS IMPACT:
- Priority: P0 CRITICAL
- Impact: $500K+ ARR Golden Path chat functionality
- Root Cause: Multiple WebSocket Manager implementations cause inconsistent event delivery
- User Experience: Chat users experience missing/delayed agent progress events

TEST OBJECTIVES:
1. Reproduce event delivery failures with fragmented WebSocket managers
2. Validate cross-manager event routing inconsistencies
3. Test user isolation failures affecting event delivery
4. Demonstrate race conditions in multi-manager event dispatch
5. Prove Golden Path chat functionality degradation

EXPECTED BEHAVIOR:
- Tests should FAIL with current fragmentation (inconsistent event delivery)
- Tests should PASS after SSOT consolidation to unified_manager.py only

This test suite requires integration-level testing (no Docker dependencies).
"""

import sys
import os
import asyncio
import json
import time
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.integration
class WebSocketEventDeliveryFragmentationTests(SSotAsyncTestCase, unittest.TestCase):
    """Test event delivery failures caused by WebSocket Manager fragmentation."""

    def setUp(self):
        """Set up test environment for event delivery fragmentation testing."""
        super().setUp()
        self.mock_websockets = []
        self.test_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

    def tearDown(self):
        """Clean up test resources."""
        super().tearDown()
        for mock_ws in self.mock_websockets:
            if hasattr(mock_ws, 'close'):
                try:
                    asyncio.run(mock_ws.close())
                except:
                    pass

    async def test_event_delivery_inconsistency_across_managers(self):
        """
        EVENT FRAGMENTATION TEST: Validate inconsistent event delivery across different manager instances.

        EXPECTED TO FAIL: Different managers deliver events inconsistently
        EXPECTED TO PASS: Single SSOT manager delivers all events consistently
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create test user contexts
        user1_context = UserExecutionContext(
            user_id='user_1_event_test',
            thread_id='thread_1',
            run_id='run_1_event',
            request_id='req_1_event'
        )
        user2_context = UserExecutionContext(
            user_id='user_2_event_test',
            thread_id='thread_2',
            run_id='run_2_event',
            request_id='req_2_event'
        )

        managers_events = {}

        try:
            # Test multiple manager implementations for event delivery
            manager_modules = [
                'netra_backend.app.websocket_core.websocket_manager',
                'netra_backend.app.websocket_core.unified_manager'
            ]

            for module_path in manager_modules:
                try:
                    # Import manager and create instance
                    import importlib
                    module = importlib.import_module(module_path)

                    if hasattr(module, 'get_websocket_manager'):
                        manager = await module.get_websocket_manager(user_context=user1_context)
                    elif hasattr(module, 'WebSocketManager'):
                        manager = module.WebSocketManager(user_context=user1_context)
                    elif hasattr(module, 'UnifiedWebSocketManager'):
                        manager = module.UnifiedWebSocketManager(user_context=user1_context)
                    else:
                        self.logger.warning(f"No WebSocket manager found in {module_path}")
                        continue

                    # Mock WebSocket connection for event capture
                    mock_websocket = AsyncMock()
                    mock_websocket.send = AsyncMock()
                    self.mock_websockets.append(mock_websocket)

                    # Override manager's WebSocket connection
                    if hasattr(manager, '_connections'):
                        manager._connections[user1_context.user_id] = mock_websocket
                    elif hasattr(manager, 'connections'):
                        manager.connections[user1_context.user_id] = mock_websocket

                    # Send test events through this manager
                    events_sent = []
                    for event_type in self.test_events:
                        try:
                            await manager.send_agent_event(
                                user_id=user1_context.user_id,
                                event_type=event_type,
                                data={'test': f'{event_type}_data', 'manager': module_path}
                            )
                            events_sent.append(event_type)
                        except Exception as e:
                            self.logger.error(f"Failed to send {event_type} via {module_path}: {e}")

                    managers_events[module_path] = {
                        'events_sent': events_sent,
                        'websocket_calls': mock_websocket.send.call_count,
                        'manager_type': type(manager).__name__
                    }

                except Exception as e:
                    self.logger.error(f"Failed to test manager from {module_path}: {e}")
                    managers_events[module_path] = {
                        'events_sent': [],
                        'websocket_calls': 0,
                        'error': str(e)
                    }

            # Analyze event delivery consistency
            self.logger.info("Event delivery analysis across managers:")
            event_counts = {}
            websocket_call_counts = {}

            for module_path, results in managers_events.items():
                events_count = len(results['events_sent'])
                call_count = results['websocket_calls']

                self.logger.info(f"  {module_path}: {events_count} events, {call_count} WebSocket calls")
                self.logger.info(f"    Manager type: {results.get('manager_type', 'N/A')}")
                self.logger.info(f"    Events: {results['events_sent']}")

                event_counts[module_path] = events_count
                websocket_call_counts[module_path] = call_count

            # Verify consistency requirement
            if len(event_counts) > 1:
                unique_event_counts = set(event_counts.values())
                unique_call_counts = set(websocket_call_counts.values())

                # All managers should deliver the same number of events
                self.assertEqual(
                    len(unique_event_counts), 1,
                    f"EVENT DELIVERY INCONSISTENCY: Different managers deliver different numbers of events. "
                    f"Counts per manager: {event_counts}. All managers must deliver all {len(self.test_events)} events consistently."
                )

                # All managers should make the same number of WebSocket calls
                self.assertEqual(
                    len(unique_call_counts), 1,
                    f"WEBSOCKET CALL INCONSISTENCY: Different managers make different numbers of WebSocket calls. "
                    f"Calls per manager: {websocket_call_counts}. This indicates fragmented event delivery mechanisms."
                )

        except Exception as e:
            self.fail(f"EVENT DELIVERY FRAGMENTATION: Cannot test event consistency due to manager fragmentation: {e}")

    async def test_cross_user_event_isolation_with_fragmented_managers(self):
        """
        USER ISOLATION TEST: Validate event isolation fails with multiple manager instances.

        EXPECTED TO FAIL: Fragmented managers cause cross-user event contamination
        EXPECTED TO PASS: Single SSOT manager maintains proper event isolation
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create distinct user contexts
        user1_context = UserExecutionContext(
            user_id='isolated_user_1',
            thread_id='thread_iso_1',
            run_id='run_iso_1',
            request_id='req_iso_1'
        )
        user2_context = UserExecutionContext(
            user_id='isolated_user_2',
            thread_id='thread_iso_2',
            run_id='run_iso_2',
            request_id='req_iso_2'
        )

        try:
            # Create managers for both users
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            manager1 = get_websocket_manager(user_context=user1_context)
            manager2 = get_websocket_manager(user_context=user2_context)

            # Mock WebSocket connections
            mock_ws1 = AsyncMock()
            mock_ws2 = AsyncMock()
            mock_ws1.send = AsyncMock()
            mock_ws2.send = AsyncMock()

            self.mock_websockets.extend([mock_ws1, mock_ws2])

            # Set up connections
            if hasattr(manager1, '_connections'):
                manager1._connections[user1_context.user_id] = mock_ws1
                manager2._connections[user2_context.user_id] = mock_ws2

            # Send events to user1 only
            user1_events = ['agent_started', 'agent_thinking', 'agent_completed']
            for event_type in user1_events:
                await manager1.send_agent_event(
                    user_id=user1_context.user_id,
                    event_type=event_type,
                    data={'user': 'user1', 'secret': 'user1_secret_data'}
                )

            # Verify user2 did not receive user1's events
            user1_calls = mock_ws1.send.call_count
            user2_calls = mock_ws2.send.call_count

            self.logger.info(f"User1 WebSocket calls: {user1_calls}")
            self.logger.info(f"User2 WebSocket calls: {user2_calls}")

            # User1 should have received events, User2 should not
            self.assertGreater(user1_calls, 0, "USER ISOLATION FAILURE: User1 should have received events")
            self.assertEqual(user2_calls, 0, "USER ISOLATION FAILURE: User2 should not have received user1's events")

            # Check if managers share state (indicating fragmentation)
            if hasattr(manager1, '_connections') and hasattr(manager2, '_connections'):
                shared_connections = (
                    id(manager1._connections) == id(manager2._connections)
                )
                self.assertFalse(
                    shared_connections,
                    "MANAGER FRAGMENTATION: Managers share connection storage, breaking user isolation"
                )

        except Exception as e:
            self.fail(f"USER ISOLATION FRAGMENTATION: Cannot test isolation due to manager fragmentation: {e}")

    async def test_race_condition_in_multi_manager_event_dispatch(self):
        """
        RACE CONDITION TEST: Validate race conditions in event dispatch with multiple managers.

        EXPECTED TO FAIL: Multiple managers create race conditions in event ordering
        EXPECTED TO PASS: Single SSOT manager eliminates race conditions
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        test_context = UserExecutionContext(
            user_id='race_test_user',
            thread_id='race_thread',
            run_id='race_run',
            request_id='race_request'
        )

        try:
            # Create multiple manager instances for same user (simulating fragmentation)
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            managers = []
            mock_websockets = []

            # Create multiple managers (simulating fragmentation scenario)
            for i in range(3):
                manager = get_websocket_manager(user_context=test_context)
                mock_ws = AsyncMock()
                mock_ws.send = AsyncMock()

                # Track send timestamps
                send_timestamps = []
                original_send = mock_ws.send

                async def timestamped_send(data):
                    send_timestamps.append(time.time())
                    return await original_send(data)

                mock_ws.send = timestamped_send
                mock_ws.timestamps = send_timestamps

                if hasattr(manager, '_connections'):
                    manager._connections[test_context.user_id] = mock_ws

                managers.append(manager)
                mock_websockets.append(mock_ws)
                self.mock_websockets.append(mock_ws)

            # Send events simultaneously from all managers (race condition test)
            tasks = []
            for i, manager in enumerate(managers):
                for j, event_type in enumerate(self.test_events):
                    task = asyncio.create_task(
                        manager.send_agent_event(
                            user_id=test_context.user_id,
                            event_type=event_type,
                            data={
                                'manager_id': i,
                                'event_sequence': j,
                                'timestamp': time.time()
                            }
                        )
                    )
                    tasks.append(task)

            # Execute all tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze race condition results
            total_events_sent = 0
            timestamp_analysis = {}

            for i, mock_ws in enumerate(mock_websockets):
                call_count = mock_ws.send.call_count
                timestamps = getattr(mock_ws, 'timestamps', [])

                total_events_sent += call_count
                timestamp_analysis[f'manager_{i}'] = {
                    'call_count': call_count,
                    'timestamps': timestamps,
                    'time_span': max(timestamps) - min(timestamps) if timestamps else 0
                }

                self.logger.info(f"Manager {i}: {call_count} events, time span: {timestamp_analysis[f'manager_{i}']['time_span']:.3f}s")

            # Race condition detection
            expected_total = len(managers) * len(self.test_events)

            if total_events_sent != expected_total:
                self.logger.error(f"RACE CONDITION DETECTED: Expected {expected_total} total events, got {total_events_sent}")

            # Check for overlapping timestamps (indicating race conditions)
            all_timestamps = []
            for analysis in timestamp_analysis.values():
                all_timestamps.extend(analysis['timestamps'])

            if len(all_timestamps) > 1:
                all_timestamps.sort()
                time_gaps = [all_timestamps[i+1] - all_timestamps[i] for i in range(len(all_timestamps)-1)]
                min_gap = min(time_gaps) if time_gaps else 1.0

                # If events are too close together, it indicates potential race conditions
                if min_gap < 0.001:  # Less than 1ms apart
                    self.logger.warning(f"POTENTIAL RACE CONDITION: Events only {min_gap*1000:.1f}ms apart")

            self.assertEqual(
                total_events_sent, expected_total,
                f"RACE CONDITION FAILURE: Multiple managers caused event delivery inconsistency. "
                f"Expected {expected_total} events, delivered {total_events_sent}. "
                f"Manager fragmentation creates race conditions in event dispatch."
            )

        except Exception as e:
            self.fail(f"RACE CONDITION FRAGMENTATION: Cannot test race conditions due to manager fragmentation: {e}")

@pytest.mark.integration
class WebSocketManagerGoldenPathFragmentationTests(SSotAsyncTestCase, unittest.TestCase):
    """Test Golden Path chat functionality degradation caused by WebSocket Manager fragmentation."""

    async def test_golden_path_chat_functionality_degradation(self):
        """
        GOLDEN PATH TEST: Validate chat functionality degradation with fragmented managers.

        EXPECTED TO FAIL: Fragmentation causes incomplete chat event sequences
        EXPECTED TO PASS: SSOT manager delivers complete Golden Path experience
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Simulate Golden Path user scenario
        golden_path_context = UserExecutionContext(
            user_id='golden_path_user',
            thread_id='golden_path_thread',
            run_id='golden_path_run',
            request_id='golden_path_request'
        )

        # Define complete Golden Path event sequence
        golden_path_events = [
            {'type': 'agent_started', 'data': {'agent': 'supervisor', 'task': 'user_optimization_request'}},
            {'type': 'agent_thinking', 'data': {'step': 'analyzing_requirements', 'progress': 25}},
            {'type': 'tool_executing', 'data': {'tool': 'data_analyzer', 'action': 'fetch_metrics'}},
            {'type': 'tool_completed', 'data': {'tool': 'data_analyzer', 'result': 'metrics_retrieved'}},
            {'type': 'agent_thinking', 'data': {'step': 'generating_optimization', 'progress': 75}},
            {'type': 'tool_executing', 'data': {'tool': 'optimizer', 'action': 'calculate_improvements'}},
            {'type': 'tool_completed', 'data': {'tool': 'optimizer', 'result': 'optimization_complete'}},
            {'type': 'agent_completed', 'data': {'result': 'optimization_delivered', 'value': '$50K_savings'}}
        ]

        try:
            # Test Golden Path with current (potentially fragmented) manager
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            manager = get_websocket_manager(user_context=golden_path_context)

            # Mock WebSocket for Golden Path event capture
            mock_websocket = AsyncMock()
            mock_websocket.send = AsyncMock()

            # Capture all events with metadata
            sent_events = []
            original_send = mock_websocket.send

            async def event_capturing_send(data):
                try:
                    if isinstance(data, str):
                        event_data = json.loads(data)
                        sent_events.append({
                            'timestamp': time.time(),
                            'data': event_data,
                            'raw': data
                        })
                except json.JSONDecodeError:
                    sent_events.append({
                        'timestamp': time.time(),
                        'data': None,
                        'raw': data
                    })
                return await original_send(data)

            mock_websocket.send = event_capturing_send

            if hasattr(manager, '_connections'):
                manager._connections[golden_path_context.user_id] = mock_websocket

            # Send complete Golden Path event sequence
            for event in golden_path_events:
                try:
                    await manager.send_agent_event(
                        user_id=golden_path_context.user_id,
                        event_type=event['type'],
                        data=event['data']
                    )
                    # Small delay to simulate real agent workflow timing
                    await asyncio.sleep(0.01)
                except Exception as e:
                    self.logger.error(f"Failed to send Golden Path event {event['type']}: {e}")

            # Analyze Golden Path event delivery completeness
            self.logger.info(f"Golden Path Analysis: {len(sent_events)} events captured")

            event_types_sent = []
            for captured in sent_events:
                if captured['data'] and isinstance(captured['data'], dict):
                    event_type = captured['data'].get('type') or captured['data'].get('event_type')
                    if event_type:
                        event_types_sent.append(event_type)

            expected_event_types = [event['type'] for event in golden_path_events]

            # Verify complete Golden Path event sequence
            self.assertEqual(
                len(event_types_sent), len(expected_event_types),
                f"GOLDEN PATH DEGRADATION: Incomplete event sequence. "
                f"Expected {len(expected_event_types)} events: {expected_event_types}, "
                f"but only {len(event_types_sent)} delivered: {event_types_sent}. "
                f"WebSocket Manager fragmentation breaks $500K+ ARR chat functionality."
            )

            # Verify event sequence order is preserved
            for i, expected_type in enumerate(expected_event_types):
                if i < len(event_types_sent):
                    self.assertEqual(
                        event_types_sent[i], expected_type,
                        f"GOLDEN PATH EVENT ORDER FAILURE: Event {i} should be '{expected_type}' "
                        f"but got '{event_types_sent[i]}'. Manager fragmentation disrupts event sequencing."
                    )

            # Verify business-critical events are present
            critical_events = ['agent_started', 'agent_completed']
            for critical_event in critical_events:
                self.assertIn(
                    critical_event, event_types_sent,
                    f"CRITICAL EVENT MISSING: Golden Path requires '{critical_event}' for user experience. "
                    f"WebSocket Manager fragmentation causes missing business-critical events."
                )

        except Exception as e:
            self.fail(f"GOLDEN PATH FRAGMENTATION: Cannot test Golden Path due to manager fragmentation: {e}")

if __name__ == '__main__':
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category integration')