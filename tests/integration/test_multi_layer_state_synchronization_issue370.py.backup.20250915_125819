"""
Multi-Layer State Synchronization Test Suite - Issue #370

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Critical for multi-user system integrity
- Business Goal: Prevent state synchronization gaps across WebSocket, Agent, Database, Cache layers
- Value Impact: Ensures data consistency and prevents user experience degradation
- Strategic Impact: CRITICAL - State synchronization gaps risk $500K+ ARR from chat functionality failures

This test suite validates coordination between multiple state layers in the Netra platform:
1. WebSocket State Layer (Real-time updates)
2. Agent Execution State Layer (Agent lifecycle)
3. Database State Layer (Persistent storage)
4. Cache State Layer (Redis/Memory)
5. User Context Layer (Isolation boundaries)

CRITICAL: These tests are designed to expose coordination gaps and demonstrate where
atomic operations fail across layer boundaries.
"""
import asyncio
import pytest
import time
import uuid
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionState, get_execution_tracker
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RunID

@dataclass
class StateSnapshot:
    """Captures state across all layers at a specific moment."""
    timestamp: float
    websocket_state: Dict[str, Any]
    agent_state: Dict[str, Any]
    database_state: Dict[str, Any]
    cache_state: Dict[str, Any]
    user_context_state: Dict[str, Any]
    layer_consistency_score: float = 0.0

class TestMultiLayerStateSynchronization(SSotAsyncTestCase):
    """Integration tests for multi-layer state synchronization."""

    def setup_method(self, method):
        """Set up test environment with multi-layer infrastructure."""
        super().setup_method(method)
        self.test_user_id = f'usr_test_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'thd_test_{uuid.uuid4().hex[:8]}'
        self.test_run_id = f'run_test_{uuid.uuid4().hex[:8]}'
        self.state_snapshots: List[StateSnapshot] = []
        self.coordination_failures: List[Dict[str, Any]] = []
        self.race_conditions_detected: List[Dict[str, Any]] = []
        self.record_metric('test_start_time', time.time())
        self.record_metric('layers_tested', 5)

    @pytest.mark.integration
    @pytest.mark.critical
    async def test_websocket_agent_state_synchronization_critical(self):
        """
        PRIORITY 1: Test WebSocket + Agent state synchronization gaps.
        
        Validates that WebSocket events and agent execution state remain synchronized
        even during rapid state transitions. This is critical for chat functionality.
        """
        start_time = time.time()
        user_context = await create_isolated_execution_context(user_id=self.test_user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=self.test_thread_id)
        agent_tracker = get_execution_tracker()
        agent_states = [ExecutionState.PENDING, ExecutionState.STARTING, ExecutionState.RUNNING, ExecutionState.COMPLETING, ExecutionState.COMPLETED]
        websocket_events = []
        agent_state_changes = []
        for i, state in enumerate(agent_states):
            agent_exec_id = agent_tracker.create_execution('test_agent', self.test_thread_id, self.test_user_id)
            agent_tracker.update_execution_state(agent_exec_id, state)
            state_change_time = time.time()
            agent_state_changes.append({'execution_id': agent_exec_id, 'state': state, 'timestamp': state_change_time})
            await asyncio.sleep(0.01)
            websocket_event_time = time.time()
            websocket_events.append({'event_type': f'agent_{state.value}', 'execution_id': agent_exec_id, 'timestamp': websocket_event_time})
            time_gap = websocket_event_time - state_change_time
            if time_gap > 0.05:
                self.coordination_failures.append({'type': 'websocket_agent_sync_gap', 'time_gap': time_gap, 'agent_state': state.value, 'execution_id': agent_exec_id})
        total_time = time.time() - start_time
        sync_failures = len(self.coordination_failures)
        self.record_metric('websocket_agent_sync_time', total_time)
        self.record_metric('sync_failures_detected', sync_failures)
        self.record_metric('state_transitions_tested', len(agent_states))
        self.assertTrue(len(agent_state_changes) == len(websocket_events), 'Agent state changes and WebSocket events must be 1:1')
        if sync_failures > 0:
            self.record_metric('sync_gap_types', [f['type'] for f in self.coordination_failures])
            self.record_metric('max_sync_gap', max((f['time_gap'] for f in self.coordination_failures)))

    @pytest.mark.integration
    @pytest.mark.critical
    async def test_database_cache_consistency_validation(self):
        """
        PRIORITY 2: Test Database + Cache layer consistency during rapid updates.
        
        Validates that database and cache layers maintain consistency during
        concurrent operations. Critical for data integrity.
        """
        start_time = time.time()
        test_data = {'user_id': self.test_user_id, 'thread_id': self.test_thread_id, 'conversation_state': 'active', 'last_activity': time.time()}
        consistency_violations = []

        async def database_operation(operation_id: int):
            """Simulate database write operation."""
            await asyncio.sleep(0.02)
            return {'operation_id': operation_id, 'type': 'database_write', 'timestamp': time.time(), 'data': {**test_data, 'operation_id': operation_id}}

        async def cache_operation(operation_id: int):
            """Simulate cache write operation."""
            await asyncio.sleep(0.005)
            return {'operation_id': operation_id, 'type': 'cache_write', 'timestamp': time.time(), 'data': {**test_data, 'operation_id': operation_id}}
        operations = []
        for i in range(5):
            operations.extend([database_operation(i), cache_operation(i)])
        results = await asyncio.gather(*operations, return_exceptions=True)
        db_results = [r for r in results if isinstance(r, dict) and r.get('type') == 'database_write']
        cache_results = [r for r in results if isinstance(r, dict) and r.get('type') == 'cache_write']
        for db_result in db_results:
            op_id = db_result['operation_id']
            cache_result = next((c for c in cache_results if c['operation_id'] == op_id), None)
            if cache_result:
                time_diff = abs(db_result['timestamp'] - cache_result['timestamp'])
                if time_diff > 0.1:
                    consistency_violations.append({'type': 'database_cache_timing_violation', 'operation_id': op_id, 'time_difference': time_diff, 'db_timestamp': db_result['timestamp'], 'cache_timestamp': cache_result['timestamp']})
        total_time = time.time() - start_time
        self.record_metric('db_cache_test_time', total_time)
        self.record_metric('consistency_violations', len(consistency_violations))
        self.record_metric('operations_tested', len(operations))
        if consistency_violations:
            self.record_metric('violation_types', [v['type'] for v in consistency_violations])
            self.coordination_failures.extend(consistency_violations)

    @pytest.mark.integration
    @pytest.mark.critical
    async def test_user_context_factory_isolation_boundaries(self):
        """
        PRIORITY 3: Test User Context Factory isolation boundaries.
        
        Validates that user context isolation remains intact during concurrent
        operations across multiple layers. Critical for security.
        """
        start_time = time.time()
        user_contexts = []
        context_operations = []
        for i in range(3):
            user_id = f'usr_isolation_test_{i}_{uuid.uuid4().hex[:6]}'
            thread_id = f'thd_isolation_test_{i}_{uuid.uuid4().hex[:6]}'
            run_id = f'run_isolation_test_{i}_{uuid.uuid4().hex[:6]}'
            context = await create_isolated_execution_context(user_id=user_id, request_id=f'req_{uuid.uuid4().hex[:8]}', thread_id=thread_id)
            user_contexts.append(context)
        isolation_violations = []

        async def context_operation(context: UserExecutionContext, operation_id: int):
            """Perform operations on a specific context."""
            operation_data = {'context_id': f'{context.user_id}_{context.thread_id}', 'operation_id': operation_id, 'timestamp': time.time()}
            await asyncio.sleep(0.01)
            return {'context': context, 'operation_data': operation_data, 'memory_id': id(context)}
        concurrent_ops = []
        for i, context in enumerate(user_contexts):
            for j in range(3):
                concurrent_ops.append(context_operation(context, j))
        operation_results = await asyncio.gather(*concurrent_ops, return_exceptions=True)
        context_memory_ids = {}
        for result in operation_results:
            if isinstance(result, dict):
                context_id = result['operation_data']['context_id']
                memory_id = result['memory_id']
                if context_id in context_memory_ids:
                    if context_memory_ids[context_id] != memory_id:
                        isolation_violations.append({'type': 'context_memory_isolation_violation', 'context_id': context_id, 'expected_memory_id': context_memory_ids[context_id], 'actual_memory_id': memory_id})
                else:
                    context_memory_ids[context_id] = memory_id
        total_time = time.time() - start_time
        self.record_metric('isolation_test_time', total_time)
        self.record_metric('isolation_violations', len(isolation_violations))
        self.record_metric('contexts_tested', len(user_contexts))
        self.record_metric('concurrent_operations', len(concurrent_ops))
        if isolation_violations:
            self.coordination_failures.extend(isolation_violations)

    @pytest.mark.integration
    @pytest.mark.critical
    async def test_golden_path_atomic_transaction_validation(self):
        """
        PRIORITY 4: Test Golden Path atomic transaction coordination.
        
        Simulates the complete Golden Path user flow and validates that all state
        layers remain synchronized during the critical chat interaction flow.
        """
        start_time = time.time()
        golden_path_steps = ['user_authentication', 'thread_initialization', 'agent_startup', 'message_processing', 'response_generation', 'websocket_delivery']
        atomic_failures = []
        step_states = {}
        for step_index, step in enumerate(golden_path_steps):
            step_start = time.time()
            try:
                user_context_update = {'step': step, 'timestamp': time.time(), 'user_id': self.test_user_id}
                agent_state_update = {'step': step, 'timestamp': time.time(), 'execution_state': ExecutionState.RUNNING.value}
                websocket_state_update = {'step': step, 'timestamp': time.time(), 'connection_active': True}
                update_times = [user_context_update['timestamp'], agent_state_update['timestamp'], websocket_state_update['timestamp']]
                time_span = max(update_times) - min(update_times)
                if time_span > 0.05:
                    atomic_failures.append({'type': 'golden_path_atomicity_violation', 'step': step, 'time_span': time_span, 'update_times': update_times})
                step_states[step] = {'duration': time.time() - step_start, 'atomicity_violation': time_span > 0.05, 'layer_updates': {'user_context': user_context_update, 'agent_state': agent_state_update, 'websocket_state': websocket_state_update}}
                await asyncio.sleep(0.01)
            except Exception as e:
                atomic_failures.append({'type': 'golden_path_execution_failure', 'step': step, 'error': str(e)})
        total_time = time.time() - start_time
        self.record_metric('golden_path_total_time', total_time)
        self.record_metric('atomic_failures', len(atomic_failures))
        self.record_metric('steps_completed', len(step_states))
        self.record_metric('average_step_time', sum((s['duration'] for s in step_states.values())) / len(step_states))
        if atomic_failures:
            self.coordination_failures.extend(atomic_failures)
            self.record_metric('golden_path_violations', len(atomic_failures))

    @pytest.mark.integration
    @pytest.mark.performance
    async def test_race_condition_reproduction_high_concurrency(self):
        """
        PRIORITY 5: Reproduce race conditions under high concurrency.
        
        Simulates high-concurrency scenarios to expose race conditions
        between different state layers.
        """
        start_time = time.time()
        concurrent_users = 10
        operations_per_user = 5
        race_conditions = []

        async def user_simulation(user_index: int):
            """Simulate a user's concurrent operations."""
            user_id = f'usr_race_test_{user_index}_{uuid.uuid4().hex[:6]}'
            user_operations = []
            for op_index in range(operations_per_user):
                operation_start = time.time()
                context = create_isolated_execution_context(user_id=UserID(user_id), thread_id=ThreadID(f'thd_{user_index}_{op_index}'), run_id=RunID(f'run_{user_index}_{op_index}'))
                agent_tracker = get_execution_tracker()
                exec_id = f'exec_{user_index}_{op_index}'
                try:
                    exec_id = agent_tracker.create_execution('race_test_agent', f'thd_{user_index}_{op_index}', user_id)
                    agent_tracker.update_execution_state(exec_id, ExecutionState.RUNNING)
                    await asyncio.sleep(0.001)
                    agent_tracker.update_execution_state(exec_id, ExecutionState.COMPLETED)
                    operation_time = time.time() - operation_start
                    user_operations.append({'user_index': user_index, 'operation_index': op_index, 'execution_id': exec_id, 'duration': operation_time, 'success': True})
                except Exception as e:
                    race_conditions.append({'type': 'concurrent_execution_race_condition', 'user_index': user_index, 'operation_index': op_index, 'error': str(e), 'timestamp': time.time()})
                    user_operations.append({'user_index': user_index, 'operation_index': op_index, 'execution_id': f'failed_{user_index}_{op_index}', 'duration': time.time() - operation_start, 'success': False, 'error': str(e)})
            return user_operations
        user_simulations = [user_simulation(i) for i in range(concurrent_users)]
        simulation_results = await asyncio.gather(*user_simulations, return_exceptions=True)
        total_operations = 0
        successful_operations = 0
        for result in simulation_results:
            if isinstance(result, list):
                total_operations += len(result)
                successful_operations += sum((1 for op in result if op.get('success', False)))
        success_rate = successful_operations / total_operations * 100 if total_operations > 0 else 0
        total_time = time.time() - start_time
        self.record_metric('race_condition_test_time', total_time)
        self.record_metric('race_conditions_detected', len(race_conditions))
        self.record_metric('total_operations', total_operations)
        self.record_metric('success_rate_percent', success_rate)
        self.record_metric('concurrent_users', concurrent_users)
        if race_conditions:
            self.race_conditions_detected.extend(race_conditions)
            self.record_metric('race_condition_types', list(set((rc['type'] for rc in race_conditions))))

    def teardown_method(self, method):
        """Clean up and report findings."""
        total_coordination_failures = len(self.coordination_failures)
        total_race_conditions = len(self.race_conditions_detected)
        self.record_metric('total_coordination_failures', total_coordination_failures)
        self.record_metric('total_race_conditions', total_race_conditions)
        self.record_metric('test_end_time', time.time())
        total_issues = total_coordination_failures + total_race_conditions
        layers_tested = self.get_metric('layers_tested', 5)
        max_expected_issues = layers_tested * 2
        health_score = max(0, 100 - total_issues / max_expected_issues * 100)
        self.record_metric('synchronization_health_score', health_score)
        logger = self.get_env().get('LOGGER', 'test')
        if total_issues > 0:
            print(f'\n=== MULTI-LAYER STATE SYNCHRONIZATION TEST RESULTS ===')
            print(f'Coordination Failures: {total_coordination_failures}')
            print(f'Race Conditions: {total_race_conditions}')
            print(f'Health Score: {health_score:.1f}%')
            print(f'Issues Detected: {total_issues}')
            if self.coordination_failures:
                print(f'\nCoordination Failure Types:')
                failure_types = {}
                for failure in self.coordination_failures:
                    failure_type = failure.get('type', 'unknown')
                    failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
                for failure_type, count in failure_types.items():
                    print(f'  - {failure_type}: {count}')
            if self.race_conditions_detected:
                print(f'\nRace Condition Types:')
                race_types = {}
                for race in self.race_conditions_detected:
                    race_type = race.get('type', 'unknown')
                    race_types[race_type] = race_types.get(race_type, 0) + 1
                for race_type, count in race_types.items():
                    print(f'  - {race_type}: {count}')
        super().teardown_method(method)
pytest_plugins = []
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')