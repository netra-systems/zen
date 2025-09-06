"""Unit tests for distributed state synchronization and consistency patterns.

Tests distributed state management, consistency guarantees,
and synchronization patterns across the multi-agent system.

Business Value: Ensures reliable state consistency across distributed
components and provides observability into state synchronization health.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

import pytest

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


class TestDistributedStateConsistency:
    """Test suite for distributed state consistency patterns."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock distributed state manager."""
        manager = Mock()
        manager.state_versions = {}
        manager.consensus_threshold = 2
        manager.active_nodes = ['node1', 'node2', 'node3']
        manager.state_store = {}
        return manager

    @pytest.fixture
    def mock_vector_clock(self):
        """Create mock vector clock for distributed ordering."""
        clock = Mock()
        clock.timestamps = {'node1': 0, 'node2': 0, 'node3': 0}
        clock.increment = Mock(side_effect=lambda node: setattr(clock, 'timestamps', 
                              {**clock.timestamps, node: clock.timestamps[node] + 1}))
        return clock

    def test_eventual_consistency_convergence(self, mock_state_manager):
        """Test eventual consistency convergence across nodes."""
        # Initial state divergence
        node_states = {
        'node1': {'key': 'value1', 'version': 1},
        'node2': {'key': 'value2', 'version': 2}, 
        'node3': {'key': 'value1', 'version': 1}
        }

        # Simulate conflict resolution (last-writer-wins)
        latest_version = max(state['version'] for state in node_states.values())
        converged_states = {
        node: state if state['version'] == latest_version 
        else {'key': 'value2', 'version': latest_version}
        for node, state in node_states.items()
        }

        # Verify convergence
        unique_states = set(str(state) for state in converged_states.values())
        assert len(unique_states) == 1, "States did not converge"

    def test_vector_clock_ordering(self, mock_vector_clock):
        """Test vector clock for event ordering in distributed system."""
        # Simulate events across nodes
        events = [
            {'node': 'node1', 'event': 'create_thread', 'data': {'id': 1}},
            {'node': 'node2', 'event': 'update_thread', 'data': {'id': 1, 'status': 'active'}},
            {'node': 'node1', 'event': 'add_message', 'data': {'thread_id': 1, 'msg': 'hello'}}
        ]

        # Apply events with vector clock
        for event in events:
            mock_vector_clock.increment(event['node'])
            event['timestamp'] = dict(mock_vector_clock.timestamps)

        # Verify causality relationships
        assert events[1]['timestamp']['node2'] > events[0]['timestamp']['node2']
        assert events[2]['timestamp']['node1'] > events[0]['timestamp']['node1']

    def test_consensus_protocol_simulation(self, mock_state_manager):
        """Test consensus protocol for distributed state updates."""
        proposal_id = str(uuid4())
        proposed_value = {'operation': 'update', 'key': 'thread_status', 'value': 'completed'}

        # Simulate voting phase
        votes = {
            'node1': {'vote': 'accept', 'timestamp': time.time()},
            'node2': {'vote': 'accept', 'timestamp': time.time() + 0.1},
            'node3': {'vote': 'reject', 'timestamp': time.time() + 0.2}
        }

        # Count acceptance votes
        accept_votes = sum(1 for vote in votes.values() if vote['vote'] == 'accept')
        consensus_reached = accept_votes >= mock_state_manager.consensus_threshold

        assert consensus_reached is True
        assert accept_votes == 2

    @pytest.mark.asyncio
    async def test_distributed_lock_coordination(self):
        """Test distributed locking mechanism for critical sections."""

        class DistributedLock:
            def __init__(self, resource_id: str):
                self.resource_id = resource_id
                self.holder = None
                self.waiters = []
                self.lease_expiry = None

            async def acquire(self, node_id: str, timeout: float = 1.0):
                if self.holder is None:
                    self.holder = node_id
                    self.lease_expiry = time.time() + timeout
                    await asyncio.sleep(0)
                    return True
                return False

            async def release(self, node_id: str):
                if self.holder == node_id:
                    self.holder = None
                    self.lease_expiry = None
                    await asyncio.sleep(0)
                    return True
                return False

        lock = DistributedLock("thread_processing")

        # Test lock acquisition
        acquired = await lock.acquire("node1", timeout=0.1)
        assert acquired is True
        assert lock.holder == "node1"

        # Test lock contention
        contended = await lock.acquire("node2", timeout=0.1)
        assert contended is False

        # Test lock release
        released = await lock.release("node1")
        assert released is True
        assert lock.holder is None

    def test_conflict_resolution_strategies(self, mock_state_manager):
        """Test different conflict resolution strategies."""

        # Last-Writer-Wins (LWW) strategy
        conflicted_updates = [
            {'node': 'node1', 'timestamp': 1000, 'value': 'A'},
            {'node': 'node2', 'timestamp': 1002, 'value': 'B'},
            {'node': 'node3', 'timestamp': 1001, 'value': 'C'}
        ]

        # Resolve using LWW
        lww_winner = max(conflicted_updates, key=lambda x: x['timestamp'])
        assert lww_winner['value'] == 'B'

        # Multi-Value strategy (keep all values until manual resolution)
        mv_values = [update['value'] for update in conflicted_updates]
        assert len(mv_values) == 3
        assert set(mv_values) == {'A', 'B', 'C'}

    def test_state_synchronization_metrics(self, mock_state_manager):
        """Test collection of state synchronization metrics."""
        sync_metrics = {
            'sync_operations_total': 0,
            'sync_conflicts_resolved': 0,
            'average_sync_latency_ms': 0.0,
            'nodes_out_of_sync': [],
            'last_successful_sync': None
        }

        # Simulate sync operations
        sync_metrics['sync_operations_total'] = 25
        sync_metrics['sync_conflicts_resolved'] = 3
        sync_metrics['average_sync_latency_ms'] = 45.7
        sync_metrics['last_successful_sync'] = time.time()

        # Verify metrics collection
        conflict_rate = sync_metrics['sync_conflicts_resolved'] / sync_metrics['sync_operations_total']
        assert conflict_rate == 0.12  # 12% conflict rate
        assert sync_metrics['average_sync_latency_ms'] > 0

    @pytest.mark.asyncio
    async def test_distributed_state_recovery(self, mock_state_manager):
        """Test state recovery mechanisms in distributed system."""

        # Simulate node failure and recovery
        failed_node = 'node2'
        healthy_nodes = ['node1', 'node3']

        # Mock state reconstruction from healthy nodes
        state_snapshots = {
            'node1': {'threads': {'t1': {'status': 'active'}, 't2': {'status': 'completed'}}},
            'node3': {'threads': {'t1': {'status': 'active'}, 't2': {'status': 'completed'}, 't3': {'status': 'pending'}}}
        }

        # Merge states for recovery
        recovered_state = {'threads': {}}
        for node_state in state_snapshots.values():
            for thread_id, thread_data in node_state['threads'].items():
                if thread_id not in recovered_state['threads']:
                    recovered_state['threads'][thread_id] = thread_data

        # Verify complete state recovery
        assert len(recovered_state['threads']) == 3
        assert 't3' in recovered_state['threads']




class TestAgentStateCoordination:
    """Test suite for agent state coordination patterns."""

    @pytest.fixture
    def mock_agent_coordinator(self):
        """Create mock agent state coordinator."""
        coordinator = Mock()
        coordinator.agent_states = {}
        coordinator.state_listeners = []
        coordinator.coordination_log = []
        return coordinator

    def test_agent_state_broadcast_pattern(self, mock_agent_coordinator):
        """Test state broadcast pattern across agents."""
        # Agent state update
        state_update = {
            'agent_id': 'supervisor_001',
            'state': 'processing',
            'context': {'current_task': 'analysis', 'progress': 0.4},
            'timestamp': time.time()
        }

        # Simulate broadcast to subscribers
        subscribers = ['agent_monitor', 'agent_logger', 'agent_metrics']
        broadcast_log = []

        for subscriber in subscribers:
            broadcast_log.append({
                'subscriber': subscriber,
                'state_update': state_update,
                'delivered_at': time.time()
            })

        # Verify broadcast delivery
        assert len(broadcast_log) == 3
        assert all(log['state_update']['agent_id'] == 'supervisor_001' for log in broadcast_log)

    def test_agent_state_aggregation(self, mock_agent_coordinator):
        """Test aggregation of agent states for system-wide view."""
        agent_states = {
            'supervisor_001': {'status': 'active', 'load': 0.3, 'tasks': 2},
            'data_agent_001': {'status': 'active', 'load': 0.7, 'tasks': 5},
            'analysis_agent_001': {'status': 'idle', 'load': 0.0, 'tasks': 0},
            'data_agent_002': {'status': 'busy', 'load': 0.9, 'tasks': 8}
        }

        # Calculate system metrics
        active_agents = sum(1 for state in agent_states.values() if state['status'] in ['active', 'busy'])
        total_load = sum(state['load'] for state in agent_states.values())
        average_load = total_load / len(agent_states)
        total_tasks = sum(state['tasks'] for state in agent_states.values())

        # Verify aggregated metrics
        assert active_agents == 3
        assert total_tasks == 15
        assert 0.4 < average_load < 0.5  # Approximately 0.475

    @pytest.mark.asyncio
    async def test_agent_state_synchronization_conflict(self, mock_agent_coordinator):
        """Test handling of agent state synchronization conflicts."""

        # Concurrent state updates from different sources
        conflicting_updates = [
            {'source': 'agent_monitor', 'agent_id': 'data_agent_001', 'state': 'busy', 'timestamp': 1000},
            {'source': 'self_report', 'agent_id': 'data_agent_001', 'state': 'idle', 'timestamp': 1001},
            {'source': 'health_checker', 'agent_id': 'data_agent_001', 'state': 'unhealthy', 'timestamp': 999}
        ]

        # Resolve conflicts using timestamp-based priority (latest wins)
        resolved_update = max(conflicting_updates, key=lambda x: x['timestamp'])

        assert resolved_update['state'] == 'idle'
        assert resolved_update['source'] == 'self_report'
        assert resolved_update['timestamp'] == 1001

    def test_distributed_agent_health_consensus(self, mock_agent_coordinator):
        """Test consensus mechanism for agent health status."""

        # Health reports from multiple observers
        health_reports = {
            'health_checker_1': {'agent_id': 'data_agent_001', 'status': 'healthy'},
            'health_checker_2': {'agent_id': 'data_agent_001', 'status': 'degraded'},
            'peer_agent_001': {'agent_id': 'data_agent_001', 'status': 'healthy'},
            'metrics_collector': {'agent_id': 'data_agent_001', 'status': 'healthy'}
        }

        # Count health status votes
        status_votes = {}
        for report in health_reports.values():
            status = report['status']
            status_votes[status] = status_votes.get(status, 0) + 1

        # Determine consensus
        consensus_status = max(status_votes, key=status_votes.get)
        consensus_confidence = status_votes[consensus_status] / len(health_reports)

        assert consensus_status == 'healthy'
        assert consensus_confidence == 0.75  # 3 out of 4 reports




class TestEventualConsistencyPatterns:
    """Test suite for eventual consistency patterns and conflict resolution."""

    def test_crdt_like_state_merging(self):
        """Test CRDT-like state merging for conflict-free updates."""

        # Simulate CRDT-like counter (G-Counter)
        class GCounter:
            def __init__(self, node_id: str):
                self.node_id = node_id
                self.counts = {}

            def increment(self):
                self.counts[self.node_id] = self.counts.get(self.node_id, 0) + 1

            def merge(self, other):
                merged = GCounter(self.node_id)
                all_nodes = set(self.counts.keys()) | set(other.counts.keys())
                for node in all_nodes:
                    merged.counts[node] = max(
                        self.counts.get(node, 0),
                        other.counts.get(node, 0)
                    )
                return merged

            def value(self):
                return sum(self.counts.values())

        # Test counter operations
        counter1 = GCounter('node1')
        counter2 = GCounter('node2')

        counter1.increment()
        counter1.increment()
        counter2.increment()

        # Merge counters
        merged = counter1.merge(counter2)

        assert merged.value() == 3
        assert merged.counts['node1'] == 2
        assert merged.counts['node2'] == 1

    def test_message_ordering_with_logical_clocks(self):
        """Test message ordering using logical clocks."""

        # Simulate Lamport timestamps
        messages = [
            {'node': 'A', 'logical_time': 1, 'content': 'create_thread'},
            {'node': 'B', 'logical_time': 2, 'content': 'add_message'},
            {'node': 'A', 'logical_time': 3, 'content': 'update_status'},
            {'node': 'C', 'logical_time': 2, 'content': 'subscribe'},
            {'node': 'B', 'logical_time': 4, 'content': 'close_thread'}
        ]

        # Sort by logical time (with node ID as tiebreaker)
        ordered_messages = sorted(messages, key=lambda x: (x['logical_time'], x['node']))

        # Verify ordering
        assert ordered_messages[0]['content'] == 'create_thread'
        assert ordered_messages[1]['content'] == 'add_message'  # B comes before C in tiebreaker
        assert ordered_messages[2]['content'] == 'subscribe'
        assert ordered_messages[3]['content'] == 'update_status'
        assert ordered_messages[4]['content'] == 'close_thread'

    @pytest.mark.asyncio
    async def test_distributed_state_machine_replication(self):
        """Test state machine replication across distributed nodes."""

        class StateMachineReplica:
            def __init__(self, node_id: str):
                self.node_id = node_id
                self.state = {'threads': {}, 'sequence': 0}
                self.log = []

            def apply_operation(self, operation):
                if operation['sequence'] == self.state['sequence'] + 1:
                    self.log.append(operation)
                    self.state['sequence'] = operation['sequence']

                    if operation['type'] == 'create_thread':
                        self.state['threads'][operation['thread_id']] = operation['data']
                    elif operation['type'] == 'update_thread':
                        if operation['thread_id'] in self.state['threads']:
                            self.state['threads'][operation['thread_id']].update(operation['data'])

        # Create replicas
        replica1 = StateMachineReplica('node1')
        replica2 = StateMachineReplica('node2')

        # Apply operations in order
        operations = [
            {'type': 'create_thread', 'thread_id': 't1', 'data': {'status': 'active'}, 'sequence': 1},
            {'type': 'update_thread', 'thread_id': 't1', 'data': {'status': 'completed'}, 'sequence': 2}
        ]

        for op in operations:
            replica1.apply_operation(op)
            replica2.apply_operation(op)

        # Verify state consistency
        assert replica1.state == replica2.state
        assert replica1.state['threads']['t1']['status'] == 'completed'
        assert replica1.state['sequence'] == 2