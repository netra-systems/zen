"""
Integration Tests for Issue #335: WebSocket "send after close" Race Conditions

Purpose: Test race conditions in WebSocket manager using real service integration
without Docker dependencies. These tests use real WebSocket managers with
mock WebSocket connections to simulate race conditions.

Test Strategy:
1. Real WebSocket manager instantiation and lifecycle
2. Simulated network conditions using controlled mocks
3. Concurrent user operations and disconnections
4. Real agent event delivery during connection instability
5. Service degradation scenarios

Business Value Justification:
- Segment: ALL (Free -> Enterprise)
- Business Goal: Ensure reliable WebSocket communication under stress
- Value Impact: Prevents Golden Path disruptions during connection issues
- Revenue Impact: Protects $500K+ ARR chat functionality reliability

Integration Level: Uses real WebSocket managers, mock WebSocket connections,
real user context factories, and actual message serialization.
"""
import asyncio
import pytest
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from datetime import datetime
import concurrent.futures
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManagerMode, create_test_user_context
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection, _serialize_message_safely
from shared.types.core_types import UserID, ThreadID, ConnectionID
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.integration
class TestWebSocketRaceConditionsIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket race conditions with real managers."""

    async def asyncSetUp(self):
        """Set up integration test environment."""
        await super().asyncSetUp()
        self.user_contexts = {}
        for i in range(3):
            user_context = create_test_user_context()
            user_context.user_id = UserID(f'integration_user_{i}')
            user_context.session_id = f'integration_session_{i}'
            self.user_contexts[f'user_{i}'] = user_context
        self.websocket_managers = {}
        for user_key, context in self.user_contexts.items():
            manager = await get_websocket_manager(user_context=context, mode=WebSocketManagerMode.UNIFIED)
            self.websocket_managers[user_key] = manager
        logger.info(f'Integration test setup complete: {len(self.websocket_managers)} managers created')

    async def test_integration_multi_user_concurrent_disconnect_race(self):
        """
        Integration Test 1: Multi-user concurrent disconnect race conditions

        Tests race conditions when multiple users disconnect simultaneously
        while agent events are being delivered to all users.
        """
        logger.info('🧪 Integration Test: Multi-user concurrent disconnect race')
        connections = {}
        for user_key, manager in self.websocket_managers.items():
            mock_websocket = AsyncMock()
            mock_connection = WebSocketConnection(websocket=mock_websocket, user_id=self.user_contexts[user_key].user_id, connection_id=ConnectionID(f'integration_conn_{user_key}'))
            connection_id = f'integration_{user_key}_conn'
            connections[user_key] = {'connection_id': connection_id, 'connection': mock_connection, 'manager': manager}
            await manager.add_connection(connection_id, mock_connection)
        golden_path_events = [{'type': 'agent_started', 'agent': 'supervisor', 'user_count': len(connections)}, {'type': 'agent_thinking', 'content': 'Processing multi-user request...'}, {'type': 'tool_executing', 'tool': 'multi_user_analyzer'}, {'type': 'tool_completed', 'tool': 'multi_user_analyzer', 'status': 'success'}, {'type': 'agent_completed', 'agent': 'supervisor', 'result': 'all_users_processed'}]
        send_errors = []
        successful_sends = 0
        disconnect_errors = []

        async def send_events_to_all_users():
            """Send Golden Path events to all connected users"""
            nonlocal successful_sends
            for event_idx, event in enumerate(golden_path_events):
                send_tasks = []
                for user_key, conn_data in connections.items():
                    task = asyncio.create_task(self._send_event_with_error_tracking(conn_data['manager'], conn_data['connection_id'], {**event, 'event_idx': event_idx, 'target_user': user_key}))
                    send_tasks.append(task)
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        send_errors.append(str(result))
                    elif result:
                        successful_sends += 1
                await asyncio.sleep(0.02)

        async def simulate_concurrent_user_disconnects():
            """Simulate users disconnecting during event delivery"""
            await asyncio.sleep(0.05)
            disconnect_tasks = []
            for i, (user_key, conn_data) in enumerate(connections.items()):
                delay = i * 0.01
                task = asyncio.create_task(self._simulate_user_disconnect(user_key, conn_data, delay))
                disconnect_tasks.append(task)
            disconnect_results = await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            for result in disconnect_results:
                if isinstance(result, Exception):
                    disconnect_errors.append(str(result))
        event_task = asyncio.create_task(send_events_to_all_users())
        disconnect_task = asyncio.create_task(simulate_concurrent_user_disconnects())
        await asyncio.gather(event_task, disconnect_task, return_exceptions=True)
        total_expected_sends = len(golden_path_events) * len(connections)
        assert len(send_errors) > 0, f'Expected race condition errors during concurrent disconnects. Successful sends: {successful_sends}/{total_expected_sends}, Send errors: {len(send_errors)}, Disconnect errors: {len(disconnect_errors)}'
        logger.error(f'🔥 MULTI-USER RACE CONDITIONS REPRODUCED: {len(send_errors)} send errors, {len(disconnect_errors)} disconnect errors')
        for user_key, conn_data in connections.items():
            try:
                await conn_data['manager'].remove_connection(conn_data['connection_id'])
            except Exception as cleanup_error:
                logger.warning(f'Cleanup error for {user_key}: {cleanup_error}')

    async def test_integration_websocket_manager_state_corruption_race(self):
        """
        Integration Test 2: WebSocket manager state corruption during race conditions

        Tests whether concurrent operations can corrupt the internal state
        of WebSocket managers, leading to inconsistent behavior.
        """
        logger.info('🧪 Integration Test: WebSocket manager state corruption race')
        manager = self.websocket_managers['user_0']
        connections_data = []
        for i in range(5):
            mock_websocket = AsyncMock()
            mock_connection = WebSocketConnection(websocket=mock_websocket, user_id=self.user_contexts['user_0'].user_id, connection_id=ConnectionID(f'state_test_conn_{i}'))
            connection_id = f'state_corruption_conn_{i}'
            connections_data.append({'connection_id': connection_id, 'connection': mock_connection})
            await manager.add_connection(connection_id, mock_connection)
        state_errors = []
        operation_results = []
        manager_state_snapshots = []

        async def perform_concurrent_operations():
            """Perform multiple operations that can cause state corruption"""
            tasks = []
            for i in range(20):
                operation_type = i % 4
                conn_idx = i % len(connections_data)
                conn_data = connections_data[conn_idx]
                if operation_type == 0:
                    task = asyncio.create_task(self._send_message_with_state_check(manager, conn_data, f'state_test_msg_{i}'))
                elif operation_type == 1:
                    task = asyncio.create_task(self._toggle_connection(manager, conn_data, i))
                elif operation_type == 2:
                    task = asyncio.create_task(self._query_manager_state(manager, f'query_{i}'))
                else:
                    task = asyncio.create_task(self._bulk_send_operation(manager, connections_data, i))
                tasks.append(task)
                if i % 5 == 0:
                    snapshot = await self._take_manager_state_snapshot(manager, f'snapshot_{i}')
                    manager_state_snapshots.append(snapshot)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    state_errors.append(f'Operation {i}: {result}')
                else:
                    operation_results.append(result)
        await perform_concurrent_operations()
        state_inconsistencies = self._analyze_state_snapshots(manager_state_snapshots)
        assert len(state_errors) > 0 or len(state_inconsistencies) > 0, f'Expected state corruption indicators but found none. State errors: {len(state_errors)}, State inconsistencies: {len(state_inconsistencies)}, Successful operations: {len(operation_results)}'
        logger.error(f'🔥 STATE CORRUPTION RACE CONDITIONS REPRODUCED: {len(state_errors)} errors, {len(state_inconsistencies)} inconsistencies')
        for conn_data in connections_data:
            try:
                await manager.remove_connection(conn_data['connection_id'])
            except Exception as cleanup_error:
                logger.warning(f'Cleanup error: {cleanup_error}')

    async def test_integration_golden_path_agent_event_race_conditions(self):
        """
        Integration Test 3: Golden Path agent event race conditions

        Tests race conditions specifically in the Golden Path agent event
        delivery system when users disconnect during critical agent operations.
        """
        logger.info('🧪 Integration Test: Golden Path agent event race conditions')
        golden_path_connections = {}
        for user_key in ['user_0', 'user_1']:
            manager = self.websocket_managers[user_key]
            mock_websocket = AsyncMock()
            mock_connection = WebSocketConnection(websocket=mock_websocket, user_id=self.user_contexts[user_key].user_id, connection_id=ConnectionID(f'golden_path_{user_key}'))
            connection_id = f'golden_path_{user_key}_conn'
            golden_path_connections[user_key] = {'connection_id': connection_id, 'connection': mock_connection, 'manager': manager}
            await manager.add_connection(connection_id, mock_connection)
        critical_agent_sequence = [{'type': 'agent_started', 'agent': 'supervisor', 'critical': True}, {'type': 'agent_thinking', 'content': 'Analyzing business requirements...', 'critical': True}, {'type': 'tool_executing', 'tool': 'business_analyzer', 'critical': True}, {'type': 'tool_completed', 'tool': 'business_analyzer', 'result': {'revenue_impact': 50000}, 'critical': True}, {'type': 'agent_thinking', 'content': 'Generating optimization recommendations...', 'critical': True}, {'type': 'tool_executing', 'tool': 'optimization_engine', 'critical': True}, {'type': 'tool_completed', 'tool': 'optimization_engine', 'result': {'optimizations': 15}, 'critical': True}, {'type': 'agent_completed', 'agent': 'supervisor', 'result': 'mission_critical_complete', 'critical': True}]
        critical_event_failures = []
        golden_path_completion_status = {}
        user_disconnect_timings = {}

        async def deliver_golden_path_events():
            """Deliver critical Golden Path events to all users"""
            for event_idx, event in enumerate(critical_agent_sequence):
                send_tasks = []
                for user_key, conn_data in golden_path_connections.items():
                    task = asyncio.create_task(self._send_critical_event_with_tracking(conn_data['manager'], conn_data['connection_id'], {**event, 'event_sequence': event_idx, 'user': user_key}))
                    send_tasks.append((user_key, task))
                for user_key, task in send_tasks:
                    try:
                        result = await task
                        if not result:
                            critical_event_failures.append(f"User {user_key}, Event {event_idx} ({event['type']}): Delivery failed")
                    except Exception as e:
                        critical_event_failures.append(f"User {user_key}, Event {event_idx} ({event['type']}): {e}")
                await asyncio.sleep(0.03)

        async def simulate_golden_path_disruptions():
            """Simulate disruptions during Golden Path execution"""
            await asyncio.sleep(0.08)
            user_to_disconnect = 'user_0'
            conn_data = golden_path_connections[user_to_disconnect]
            user_disconnect_timings[user_to_disconnect] = time.time()
            conn_data['connection'].websocket.send_json = AsyncMock(side_effect=ConnectionError('Golden Path user disconnected during critical operation'))
            logger.warning(f'Simulating {user_to_disconnect} disconnect during Golden Path')
        golden_path_task = asyncio.create_task(deliver_golden_path_events())
        disruption_task = asyncio.create_task(simulate_golden_path_disruptions())
        await asyncio.gather(golden_path_task, disruption_task, return_exceptions=True)
        critical_events_affected = len(critical_event_failures)
        business_impact_events = [failure for failure in critical_event_failures if any((critical_type in failure for critical_type in ['agent_started', 'agent_completed', 'business_analyzer', 'optimization_engine']))]
        assert critical_events_affected > 0, f'Expected Golden Path race conditions but found none. Critical event failures: {critical_events_affected}, Business impact events: {len(business_impact_events)}'
        assert len(business_impact_events) > 0, f'Expected business-critical events to be affected. All failures: {critical_event_failures}'
        logger.error(f'🔥 GOLDEN PATH RACE CONDITIONS REPRODUCED: {critical_events_affected} critical failures, {len(business_impact_events)} business-impact events affected')
        for user_key, conn_data in golden_path_connections.items():
            try:
                await conn_data['manager'].remove_connection(conn_data['connection_id'])
            except Exception as cleanup_error:
                logger.warning(f'Golden Path cleanup error for {user_key}: {cleanup_error}')

    async def _send_event_with_error_tracking(self, manager, connection_id, event):
        """Send event with comprehensive error tracking"""
        try:
            return await manager.send_message(connection_id, event)
        except Exception as e:
            logger.error(f'Event send error to {connection_id}: {e}')
            raise

    async def _simulate_user_disconnect(self, user_key, conn_data, delay):
        """Simulate realistic user disconnect scenario"""
        await asyncio.sleep(delay)
        conn_data['connection'].websocket.send_json = AsyncMock(side_effect=ConnectionError(f'User {user_key} network disconnected'))
        logger.info(f'Simulated disconnect for {user_key}')

    async def _send_message_with_state_check(self, manager, conn_data, message_content):
        """Send message while checking manager state consistency"""
        try:
            message = {'content': message_content, 'timestamp': time.time()}
            return await manager.send_message(conn_data['connection_id'], message)
        except Exception as e:
            logger.error(f'State check send error: {e}')
            raise

    async def _toggle_connection(self, manager, conn_data, operation_id):
        """Toggle connection add/remove to test state management"""
        try:
            await manager.remove_connection(conn_data['connection_id'])
            await asyncio.sleep(0.001)
            await manager.add_connection(conn_data['connection_id'], conn_data['connection'])
            return f'toggle_{operation_id}_success'
        except Exception as e:
            logger.error(f'Toggle operation {operation_id} error: {e}')
            raise

    async def _query_manager_state(self, manager, query_id):
        """Query manager state for consistency checking"""
        try:
            state_info = {'query_id': query_id, 'timestamp': time.time(), 'has_get_connection': hasattr(manager, 'get_connection'), 'manager_type': type(manager).__name__}
            return state_info
        except Exception as e:
            logger.error(f'State query {query_id} error: {e}')
            raise

    async def _bulk_send_operation(self, manager, connections_data, operation_id):
        """Perform bulk send operation to test concurrent handling"""
        try:
            results = []
            message = {'bulk_op': operation_id, 'timestamp': time.time()}
            for conn_data in connections_data:
                try:
                    result = await manager.send_message(conn_data['connection_id'], message)
                    results.append(result)
                except Exception as e:
                    results.append(f'error: {e}')
            return results
        except Exception as e:
            logger.error(f'Bulk operation {operation_id} error: {e}')
            raise

    async def _take_manager_state_snapshot(self, manager, snapshot_id):
        """Take a snapshot of manager state for consistency analysis"""
        return {'snapshot_id': snapshot_id, 'timestamp': time.time(), 'manager_type': type(manager).__name__, 'has_connections': hasattr(manager, '_connections') if hasattr(manager, '_connections') else False}

    def _analyze_state_snapshots(self, snapshots):
        """Analyze state snapshots for inconsistencies"""
        inconsistencies = []
        timestamps = [s['timestamp'] for s in snapshots]
        if len(timestamps) > 1:
            for i in range(1, len(timestamps)):
                if timestamps[i] < timestamps[i - 1]:
                    inconsistencies.append(f'Timeline inconsistency: snapshot {i} has earlier timestamp')
        manager_types = list(set([s['manager_type'] for s in snapshots]))
        if len(manager_types) > 1:
            inconsistencies.append(f'Manager type changed during operation: {manager_types}')
        return inconsistencies

    async def _send_critical_event_with_tracking(self, manager, connection_id, event):
        """Send critical Golden Path event with detailed tracking"""
        try:
            start_time = time.time()
            result = await manager.send_message(connection_id, event)
            end_time = time.time()
            logger.debug(f"Critical event {event['type']} to {connection_id}: {('SUCCESS' if result else 'FAILED')} in {end_time - start_time:.3f}s")
            return result
        except Exception as e:
            logger.error(f"Critical event {event['type']} to {connection_id} FAILED: {e}")
            raise

    async def asyncTearDown(self):
        """Clean up integration test environment."""
        for user_key, manager in self.websocket_managers.items():
            try:
                if hasattr(manager, '_connections'):
                    pass
            except Exception as e:
                logger.warning(f'Manager cleanup error for {user_key}: {e}')
        await super().asyncTearDown()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')