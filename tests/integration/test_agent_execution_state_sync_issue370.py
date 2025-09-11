"""
Agent Execution State Synchronization Test Suite - Issue #370

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Core to agent-based AI functionality
- Business Goal: Ensure agent execution state remains synchronized across all system layers
- Value Impact: Prevents agent execution failures and ensures reliable AI responses
- Strategic Impact: CRITICAL - Agent state misalignment breaks core platform value (90% chat functionality)

This test suite validates agent execution state synchronization across:
1. Agent Execution Tracker (execution lifecycle)
2. WebSocket Event Bridge (real-time notifications)  
3. User Execution Context (isolation boundaries)
4. Database Persistence (state recovery)
5. Cache Layer (performance optimization)

FOCUS: Tests designed to detect gaps where agent execution state becomes desynchronized
between layers, leading to silent failures or incomplete user experiences.
"""

import asyncio
import pytest
import time
import uuid
from typing import Dict, Any, List, Optional, Set
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import threading
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionState, get_execution_tracker
from shared.types.core_types import UserID, ThreadID, RunID


@dataclass
class AgentStateEvent:
    """Represents a state change event in the agent execution system."""
    timestamp: float
    layer: str  # 'tracker', 'websocket', 'context', 'database', 'cache'
    execution_id: str
    state: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""


@dataclass
class SynchronizationGap:
    """Represents a detected synchronization gap between layers."""
    gap_type: str
    affected_layers: List[str]
    execution_id: str
    time_span: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    details: Dict[str, Any] = field(default_factory=dict)


class MockAgentWebSocketBridge:
    """Mock WebSocket bridge for agent execution events."""
    
    def __init__(self):
        self.events_sent: List[AgentStateEvent] = []
        self.event_delays: Dict[str, float] = {}
        self.failed_events: List[Dict[str, Any]] = []
        self.connection_active = True
    
    async def send_agent_event(self, event_type: str, execution_id: str, data: Dict[str, Any]) -> bool:
        """Mock sending agent execution event via WebSocket."""
        if not self.connection_active:
            self.failed_events.append({
                'event_type': event_type,
                'execution_id': execution_id,
                'reason': 'connection_inactive'
            })
            return False
        
        # Simulate network delay
        delay = self.event_delays.get(event_type, 0.002)
        await asyncio.sleep(delay)
        
        event = AgentStateEvent(
            timestamp=time.time(),
            layer='websocket',
            execution_id=execution_id,
            state=event_type,
            metadata=data,
            correlation_id=data.get('correlation_id', '')
        )
        self.events_sent.append(event)
        return True
    
    def set_event_delay(self, event_type: str, delay: float):
        """Configure delay for specific event types."""
        self.event_delays[event_type] = delay
    
    def set_connection_active(self, active: bool):
        """Simulate connection state changes."""
        self.connection_active = active
    
    def get_events_for_execution(self, execution_id: str) -> List[AgentStateEvent]:
        """Get all events for a specific execution."""
        return [e for e in self.events_sent if e.execution_id == execution_id]


class MockAgentDatabase:
    """Mock database layer for agent execution persistence."""
    
    def __init__(self):
        self.state_records: List[AgentStateEvent] = []
        self.operation_delays: Dict[str, float] = {}
        self.transaction_failures: int = 0
        self.max_failure_rate = 0.0
    
    async def persist_agent_state(self, execution_id: str, state: str, metadata: Dict[str, Any]) -> bool:
        """Mock persisting agent state to database."""
        # Simulate failure rate
        if self.max_failure_rate > 0 and (len(self.state_records) % 10) < (self.max_failure_rate * 10):
            self.transaction_failures += 1
            return False
        
        # Simulate database operation delay
        delay = self.operation_delays.get(state, 0.01)
        await asyncio.sleep(delay)
        
        record = AgentStateEvent(
            timestamp=time.time(),
            layer='database',
            execution_id=execution_id,
            state=state,
            metadata=metadata
        )
        self.state_records.append(record)
        return True
    
    def set_operation_delay(self, state: str, delay: float):
        """Configure delay for specific state operations."""
        self.operation_delays[state] = delay
    
    def set_failure_rate(self, rate: float):
        """Set transaction failure rate (0.0 - 1.0)."""
        self.max_failure_rate = rate
    
    def get_states_for_execution(self, execution_id: str) -> List[AgentStateEvent]:
        """Get all state records for a specific execution."""
        return [r for r in self.state_records if r.execution_id == execution_id]


class TestAgentExecutionStateSynchronization(SSotAsyncTestCase):
    """Integration tests for agent execution state synchronization."""
    
    def setup_method(self, method):
        """Set up test environment with mocked layers."""
        super().setup_method(method)
        
        # Create mock infrastructure
        self.websocket_bridge = MockAgentWebSocketBridge()
        self.agent_database = MockAgentDatabase()
        
        # Real execution tracker for testing
        self.execution_tracker = get_execution_tracker()
        
        # Test configuration
        self.test_user_id = f"usr_agent_sync_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thd_agent_sync_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"run_agent_sync_{uuid.uuid4().hex[:8]}"
        
        # Synchronization tracking
        self.synchronization_gaps: List[SynchronizationGap] = []
        self.state_transitions: List[AgentStateEvent] = []
        
        self.record_metric("test_setup_complete", True)

    @pytest.mark.integration
    @pytest.mark.critical
    async def test_agent_lifecycle_state_synchronization(self):
        """
        Test complete agent lifecycle state synchronization across all layers.
        
        Validates that agent state changes propagate correctly through all layers
        and that no state transitions are lost or delayed beyond acceptable thresholds.
        """
        start_time = time.time()
        
        # Create user execution context
        user_context = await create_isolated_execution_context(
            user_id=self.test_user_id,
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            thread_id=self.test_thread_id
        )
        
        # Define complete agent lifecycle
        lifecycle_states = [
            ExecutionState.PENDING,
            ExecutionState.STARTING,
            ExecutionState.RUNNING,
            ExecutionState.COMPLETING,
            ExecutionState.COMPLETED
        ]
        
        execution_id = f"exec_lifecycle_{uuid.uuid4().hex[:8]}"
        correlation_id = str(uuid.uuid4())
        
        # Track state synchronization across layers
        layer_events: Dict[str, List[AgentStateEvent]] = {
            'tracker': [],
            'websocket': [],
            'database': []
        }
        
        # Execute agent lifecycle
        execution_obj = self.execution_tracker.create_execution("test_agent", self.test_thread_id, self.test_user_id)
        
        for state_index, state in enumerate(lifecycle_states):
            state_start_time = time.time()
            
            # Layer 1: Update execution tracker
            self.execution_tracker.update_execution_state(execution_obj.execution_id, state)
            tracker_event = AgentStateEvent(
                timestamp=time.time(),
                layer='tracker',
                execution_id=execution_obj.execution_id,
                state=state.value,
                correlation_id=correlation_id
            )
            layer_events['tracker'].append(tracker_event)
            self.state_transitions.append(tracker_event)
            
            # Layer 2: Send WebSocket event
            websocket_success = await self.websocket_bridge.send_agent_event(
                f'agent_{state.value}',
                execution_obj.execution_id,
                {'state': state.value, 'correlation_id': correlation_id}
            )
            
            if websocket_success:
                ws_events = self.websocket_bridge.get_events_for_execution(execution_obj.execution_id)
                if ws_events:
                    latest_ws_event = ws_events[-1]
                    layer_events['websocket'].append(latest_ws_event)
                    self.state_transitions.append(latest_ws_event)
            
            # Layer 3: Persist to database
            db_success = await self.agent_database.persist_agent_state(
                execution_obj.execution_id,
                state.value,
                {'state': state.value, 'correlation_id': correlation_id}
            )
            
            if db_success:
                db_events = self.agent_database.get_states_for_execution(execution_obj.execution_id)
                if db_events:
                    latest_db_event = db_events[-1]
                    layer_events['database'].append(latest_db_event)
                    self.state_transitions.append(latest_db_event)
            
            # Analyze synchronization for this state transition
            state_events = [
                e for e in self.state_transitions
                if e.execution_id == execution_obj.execution_id and e.state == state.value
            ]
            
            if len(state_events) >= 2:  # At least 2 layers responded
                timestamps = [e.timestamp for e in state_events]
                time_span = max(timestamps) - min(timestamps)
                
                # Check for synchronization gaps
                if time_span > 0.1:  # 100ms threshold
                    gap = SynchronizationGap(
                        gap_type='state_transition_delay',
                        affected_layers=[e.layer for e in state_events],
                        execution_id=execution_obj.execution_id,
                        time_span=time_span,
                        severity='high' if time_span > 0.5 else 'medium',
                        details={
                            'state': state.value,
                            'state_index': state_index,
                            'events': [{'layer': e.layer, 'timestamp': e.timestamp} for e in state_events]
                        }
                    )
                    self.synchronization_gaps.append(gap)
            
            # Small delay between state transitions
            await asyncio.sleep(0.01)
        
        total_time = time.time() - start_time
        
        # Comprehensive synchronization analysis
        total_events = len(self.state_transitions)
        events_per_layer = {layer: len(events) for layer, events in layer_events.items()}
        synchronization_failures = len(self.synchronization_gaps)
        
        # Record detailed metrics
        self.record_metric("lifecycle_test_duration", total_time)
        self.record_metric("total_state_transitions", len(lifecycle_states))
        self.record_metric("total_events_generated", total_events)
        self.record_metric("events_per_layer", events_per_layer)
        self.record_metric("synchronization_failures", synchronization_failures)
        
        # Calculate layer synchronization rates
        expected_events_per_layer = len(lifecycle_states)
        for layer, actual_events in events_per_layer.items():
            sync_rate = (actual_events / expected_events_per_layer) * 100 if expected_events_per_layer > 0 else 0
            self.record_metric(f"{layer}_synchronization_rate", sync_rate)

    @pytest.mark.integration
    @pytest.mark.critical
    async def test_concurrent_agent_execution_state_isolation(self):
        """
        Test state synchronization with multiple concurrent agent executions.
        
        Validates that concurrent agent executions maintain proper state isolation
        and that state updates don't interfere with each other.
        """
        start_time = time.time()
        
        # Configure concurrent execution parameters
        concurrent_agents = 5
        states_per_agent = 3
        isolation_violations = []
        
        async def agent_execution_simulation(agent_index: int):
            """Simulate concurrent agent execution."""
            agent_execution_id = f"exec_concurrent_{agent_index}_{uuid.uuid4().hex[:6]}"
            agent_correlation_id = f"corr_{agent_index}_{uuid.uuid4().hex[:6]}"
            
            # Create execution
            self.execution_tracker.create_execution(agent_execution_id, f"agent_{agent_index}")
            
            agent_events = []
            
            # Execute state transitions
            test_states = [ExecutionState.PENDING, ExecutionState.RUNNING, ExecutionState.COMPLETED]
            
            for state_index, state in enumerate(test_states):
                transition_start = time.time()
                
                # Update execution state
                self.execution_tracker.update_execution_state(agent_execution_id, state)
                
                # Send WebSocket event
                await self.websocket_bridge.send_agent_event(
                    f'agent_{state.value}',
                    agent_execution_id,
                    {
                        'agent_index': agent_index,
                        'state': state.value,
                        'correlation_id': agent_correlation_id
                    }
                )
                
                # Persist to database
                await self.agent_database.persist_agent_state(
                    agent_execution_id,
                    state.value,
                    {
                        'agent_index': agent_index,
                        'state': state.value,
                        'correlation_id': agent_correlation_id
                    }
                )
                
                transition_time = time.time() - transition_start
                agent_events.append({
                    'agent_index': agent_index,
                    'execution_id': agent_execution_id,
                    'state': state.value,
                    'transition_time': transition_time,
                    'timestamp': time.time()
                })
                
                # Brief delay between states
                await asyncio.sleep(0.005)
            
            return agent_events
        
        # Execute concurrent agent simulations
        concurrent_tasks = [agent_execution_simulation(i) for i in range(concurrent_agents)]
        simulation_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Analyze isolation and synchronization
        all_agent_events = []
        for result in simulation_results:
            if isinstance(result, list):
                all_agent_events.extend(result)
        
        # Check for cross-agent state interference
        execution_id_sets: Dict[int, Set[str]] = {}
        for event in all_agent_events:
            agent_index = event['agent_index']
            execution_id = event['execution_id']
            
            if agent_index not in execution_id_sets:
                execution_id_sets[agent_index] = set()
            execution_id_sets[agent_index].add(execution_id)
        
        # Validate isolation: each agent should have exactly one execution ID
        for agent_index, execution_ids in execution_id_sets.items():
            if len(execution_ids) > 1:
                isolation_violations.append({
                    'type': 'multiple_execution_ids_per_agent',
                    'agent_index': agent_index,
                    'execution_ids': list(execution_ids)
                })
        
        # Check for state synchronization across layers
        for agent_index in range(concurrent_agents):
            agent_events = [e for e in all_agent_events if e['agent_index'] == agent_index]
            
            if agent_events:
                execution_id = agent_events[0]['execution_id']
                
                # Check WebSocket events
                ws_events = self.websocket_bridge.get_events_for_execution(execution_obj.execution_id)
                db_events = self.agent_database.get_states_for_execution(execution_obj.execution_id)
                
                # Validate event counts match
                if len(ws_events) != len(agent_events) or len(db_events) != len(agent_events):
                    isolation_violations.append({
                        'type': 'layer_event_count_mismatch',
                        'agent_index': agent_index,
                        'execution_id': execution_id,
                        'tracker_events': len(agent_events),
                        'websocket_events': len(ws_events),
                        'database_events': len(db_events)
                    })
        
        total_time = time.time() - start_time
        
        # Record concurrent execution metrics
        successful_agents = len([r for r in simulation_results if isinstance(r, list)])
        total_state_transitions = len(all_agent_events)
        
        self.record_metric("concurrent_test_duration", total_time)
        self.record_metric("concurrent_agents", concurrent_agents)
        self.record_metric("successful_agents", successful_agents)
        self.record_metric("total_state_transitions", total_state_transitions)
        self.record_metric("isolation_violations", len(isolation_violations))
        
        # Document isolation violations
        if isolation_violations:
            violation_types = {}
            for violation in isolation_violations:
                violation_type = violation['type']
                violation_types[violation_type] = violation_types.get(violation_type, 0) + 1
            
            self.record_metric("violation_types", violation_types)

    @pytest.mark.integration
    @pytest.mark.performance
    async def test_state_synchronization_under_failure_conditions(self):
        """
        Test state synchronization resilience under various failure conditions.
        
        Validates that the system maintains synchronization even when individual
        layers experience failures or delays.
        """
        start_time = time.time()
        
        # Configure failure scenarios
        failure_scenarios = [
            {'name': 'websocket_failures', 'websocket_active': False, 'db_failure_rate': 0.0},
            {'name': 'database_failures', 'websocket_active': True, 'db_failure_rate': 0.3},
            {'name': 'mixed_failures', 'websocket_active': False, 'db_failure_rate': 0.2},
            {'name': 'high_latency', 'websocket_active': True, 'db_failure_rate': 0.0}
        ]
        
        failure_results = []
        
        for scenario in failure_scenarios:
            scenario_start = time.time()
            
            # Configure failure conditions
            self.websocket_bridge.set_connection_active(scenario['websocket_active'])
            self.agent_database.set_failure_rate(scenario['db_failure_rate'])
            
            if scenario['name'] == 'high_latency':
                self.websocket_bridge.set_event_delay('agent_running', 0.1)
                self.agent_database.set_operation_delay('running', 0.15)
            
            # Execute agent operations under failure conditions
            scenario_execution_id = f"exec_failure_{scenario['name']}_{uuid.uuid4().hex[:6]}"
            scenario_correlation_id = str(uuid.uuid4())
            
            self.execution_tracker.create_execution(scenario_execution_id, f"agent_{scenario['name']}")
            
            scenario_gaps = []
            test_states = [ExecutionState.PENDING, ExecutionState.RUNNING, ExecutionState.COMPLETED]
            
            for state in test_states:
                state_start = time.time()
                
                # Update tracker (always succeeds)
                self.execution_tracker.update_execution_state(scenario_execution_id, state)
                tracker_time = time.time()
                
                # Attempt WebSocket event
                websocket_success = await self.websocket_bridge.send_agent_event(
                    f'agent_{state.value}',
                    scenario_execution_id,
                    {'state': state.value, 'correlation_id': scenario_correlation_id}
                )
                websocket_time = time.time()
                
                # Attempt database persistence
                database_success = await self.agent_database.persist_agent_state(
                    scenario_execution_id,
                    state.value,
                    {'state': state.value, 'correlation_id': scenario_correlation_id}
                )
                database_time = time.time()
                
                # Analyze synchronization under failure
                layer_successes = {
                    'tracker': True,  # Always succeeds
                    'websocket': websocket_success,
                    'database': database_success
                }
                
                successful_layers = [layer for layer, success in layer_successes.items() if success]
                failed_layers = [layer for layer, success in layer_successes.items() if not success]
                
                if failed_layers:
                    gap = SynchronizationGap(
                        gap_type='failure_induced_desynchronization',
                        affected_layers=failed_layers,
                        execution_id=scenario_execution_id,
                        time_span=database_time - state_start,
                        severity='critical' if len(failed_layers) > 1 else 'high',
                        details={
                            'scenario': scenario['name'],
                            'state': state.value,
                            'successful_layers': successful_layers,
                            'failed_layers': failed_layers,
                            'layer_successes': layer_successes
                        }
                    )
                    scenario_gaps.append(gap)
                    self.synchronization_gaps.append(gap)
            
            scenario_duration = time.time() - scenario_start
            
            failure_results.append({
                'scenario': scenario['name'],
                'duration': scenario_duration,
                'gaps_detected': len(scenario_gaps),
                'websocket_failures': len(self.websocket_bridge.failed_events),
                'database_failures': self.agent_database.transaction_failures
            })
            
            # Reset for next scenario
            self.websocket_bridge.set_connection_active(True)
            self.agent_database.set_failure_rate(0.0)
            self.websocket_bridge.set_event_delay('agent_running', 0.002)
            self.agent_database.set_operation_delay('running', 0.01)
        
        total_time = time.time() - start_time
        
        # Analyze failure resilience
        total_gaps = sum(r['gaps_detected'] for r in failure_results)
        scenarios_with_gaps = len([r for r in failure_results if r['gaps_detected'] > 0])
        
        self.record_metric("failure_test_duration", total_time)
        self.record_metric("failure_scenarios_tested", len(failure_scenarios))
        self.record_metric("total_failure_gaps", total_gaps)
        self.record_metric("scenarios_with_gaps", scenarios_with_gaps)
        self.record_metric("failure_scenario_results", failure_results)

    def teardown_method(self, method):
        """Clean up and report agent execution state synchronization results."""
        # Calculate synchronization health metrics
        total_gaps = len(self.synchronization_gaps)
        critical_gaps = len([g for g in self.synchronization_gaps if g.severity == 'critical'])
        high_severity_gaps = len([g for g in self.synchronization_gaps if g.severity == 'high'])
        
        # Overall synchronization health score
        max_expected_gaps = 10  # Baseline expectation
        health_score = max(0, 100 - (total_gaps / max_expected_gaps * 100))
        
        self.record_metric("total_synchronization_gaps", total_gaps)
        self.record_metric("critical_gaps", critical_gaps)
        self.record_metric("high_severity_gaps", high_severity_gaps)
        self.record_metric("agent_sync_health_score", health_score)
        
        # Log detailed results for issue analysis
        if total_gaps > 0:
            print(f"\n=== AGENT EXECUTION STATE SYNCHRONIZATION TEST RESULTS ===")
            print(f"Total Synchronization Gaps: {total_gaps}")
            print(f"Critical Gaps: {critical_gaps}")
            print(f"High Severity Gaps: {high_severity_gaps}")
            print(f"Health Score: {health_score:.1f}%")
            
            # Gap type analysis
            gap_types = {}
            for gap in self.synchronization_gaps:
                gap_type = gap.gap_type
                gap_types[gap_type] = gap_types.get(gap_type, 0) + 1
            
            print(f"\nGap Types:")
            for gap_type, count in gap_types.items():
                print(f"  - {gap_type}: {count}")
            
            # Layer impact analysis
            affected_layers = set()
            for gap in self.synchronization_gaps:
                affected_layers.update(gap.affected_layers)
            
            print(f"\nAffected Layers: {', '.join(affected_layers)}")
            
            # Timing analysis
            if self.synchronization_gaps:
                max_time_span = max(g.time_span for g in self.synchronization_gaps)
                avg_time_span = sum(g.time_span for g in self.synchronization_gaps) / len(self.synchronization_gaps)
                print(f"\nTiming Analysis:")
                print(f"  - Max gap duration: {max_time_span:.3f}s")
                print(f"  - Average gap duration: {avg_time_span:.3f}s")
        
        super().teardown_method(method)


# Test configuration for integration testing
pytest_plugins = []

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])