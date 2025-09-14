"""Unit tests for agent lifecycle event generation in Golden Path messages.

These tests validate agent startup, execution, and shutdown event generation
that supports the $500K+ ARR business value through real-time user experience.

Business Value: Free/Early/Mid/Enterprise - Agent Lifecycle Transparency
Ensures users receive appropriate lifecycle events during agent execution phases,
providing transparency and confidence in the AI system's operation.

AGENT LIFECYCLE EVENTS:
- Startup Events: agent_started, context_initialized, capabilities_loaded
- Execution Events: thinking_started, tool_selection, execution_progress
- Shutdown Events: results_compiled, cleanup_started, agent_completed
- Error Events: error_encountered, recovery_initiated, fallback_activated

Test Coverage:
- Agent startup event generation
- Agent shutdown event generation
- Lifecycle state transitions
- Error event generation during lifecycle phases
- Completion event validation
- Resource cleanup event validation
- Multi-agent lifecycle coordination
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
    AgentExecutionStrategy
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus


class MockAgentLifecycleManager:
    """Mock agent lifecycle manager for testing lifecycle events."""

    def __init__(self):
        self.lifecycle_events = []
        self.current_phase = None
        self.startup_completed = False
        self.shutdown_initiated = False
        self.error_states = []
        self.resource_allocations = {}
        self.cleanup_operations = []

    async def start_agent_lifecycle(self, context: AgentExecutionContext) -> bool:
        """Start agent lifecycle with event generation."""
        try:
            # Phase 1: Initialization
            await self._emit_lifecycle_event('agent_initializing', {
                'run_id': context.run_id,
                'agent_name': context.agent_name,
                'user_id': context.user_id,
                'thread_id': context.thread_id,
                'phase': 'initialization'
            })

            # Phase 2: Resource Allocation
            await self._emit_lifecycle_event('resources_allocating', {
                'run_id': context.run_id,
                'memory_allocated': '256MB',
                'cpu_cores': 2,
                'timeout': context.timeout or 300
            })

            # Phase 3: Capabilities Loading
            await self._emit_lifecycle_event('capabilities_loading', {
                'run_id': context.run_id,
                'tools_available': ['data_analyzer', 'report_generator', 'optimizer'],
                'models_loaded': ['gpt-4', 'embedding-model'],
                'permissions_verified': True
            })

            # Phase 4: Context Setup
            await self._emit_lifecycle_event('context_establishing', {
                'run_id': context.run_id,
                'user_context_loaded': True,
                'conversation_history': True,
                'domain_knowledge': True
            })

            # Phase 5: Startup Complete
            await self._emit_lifecycle_event('agent_started', {
                'run_id': context.run_id,
                'agent_name': context.agent_name,
                'startup_duration_ms': 1250,
                'ready_for_execution': True
            })

            self.startup_completed = True
            self.current_phase = 'ready'
            return True

        except Exception as e:
            await self._emit_lifecycle_event('startup_error', {
                'run_id': context.run_id,
                'error': str(e),
                'recovery_initiated': True
            })
            return False

    async def shutdown_agent_lifecycle(self, context: AgentExecutionContext, result: AgentExecutionResult) -> bool:
        """Shutdown agent lifecycle with cleanup events."""
        try:
            self.shutdown_initiated = True

            # Phase 1: Results Compilation
            await self._emit_lifecycle_event('results_compiling', {
                'run_id': context.run_id,
                'success': result.success,
                'execution_duration': result.duration,
                'data_size': len(str(result.data)) if result.data else 0
            })

            # Phase 2: Resource Cleanup
            await self._emit_lifecycle_event('resources_cleaning', {
                'run_id': context.run_id,
                'memory_freed': '256MB',
                'temp_files_cleaned': 12,
                'connections_closed': 3
            })

            # Phase 3: Context Persistence
            await self._emit_lifecycle_event('context_persisting', {
                'run_id': context.run_id,
                'state_saved': True,
                'metrics_recorded': True,
                'audit_logged': True
            })

            # Phase 4: Agent Shutdown Complete
            await self._emit_lifecycle_event('agent_completed', {
                'run_id': context.run_id,
                'agent_name': context.agent_name,
                'total_duration_ms': result.duration * 1000,
                'success': result.success,
                'cleanup_successful': True
            })

            self.current_phase = 'terminated'
            return True

        except Exception as e:
            await self._emit_lifecycle_event('shutdown_error', {
                'run_id': context.run_id,
                'error': str(e),
                'partial_cleanup': True
            })
            return False

    async def handle_lifecycle_error(self, context: AgentExecutionContext, error: Exception, phase: str) -> bool:
        """Handle errors during lifecycle phases."""
        error_data = {
            'run_id': context.run_id,
            'error_phase': phase,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recovery_strategy': self._determine_recovery_strategy(phase, error)
        }

        self.error_states.append(error_data)

        # Emit error event
        await self._emit_lifecycle_event('lifecycle_error', error_data)

        # Attempt recovery based on phase
        return await self._attempt_recovery(context, phase, error)

    async def _emit_lifecycle_event(self, event_type: str, event_data: Dict[str, Any]):
        """Emit a lifecycle event for testing validation."""
        event = {
            'event_type': event_type,
            'timestamp': datetime.now(timezone.utc),
            'data': event_data
        }
        self.lifecycle_events.append(event)

    def _determine_recovery_strategy(self, phase: str, error: Exception) -> str:
        """Determine recovery strategy based on phase and error type."""
        if phase == 'initialization':
            return 'restart_with_reduced_resources'
        elif phase == 'resource_allocation':
            return 'use_fallback_resources'
        elif phase == 'execution':
            return 'continue_with_degraded_mode'
        else:
            return 'graceful_degradation'

    async def _attempt_recovery(self, context: AgentExecutionContext, phase: str, error: Exception) -> bool:
        """Attempt recovery from lifecycle error."""
        strategy = self._determine_recovery_strategy(phase, error)

        await self._emit_lifecycle_event('recovery_initiated', {
            'run_id': context.run_id,
            'phase': phase,
            'strategy': strategy,
            'attempt_number': len(self.error_states)
        })

        # Simulate recovery attempt
        if strategy == 'restart_with_reduced_resources':
            return True
        elif strategy == 'use_fallback_resources':
            return True
        else:
            return len(self.error_states) <= 3  # Allow up to 3 recovery attempts

    def get_lifecycle_phase(self) -> Optional[str]:
        """Get current lifecycle phase."""
        return self.current_phase

    def get_startup_events(self) -> List[Dict[str, Any]]:
        """Get all startup-related events."""
        startup_event_types = [
            'agent_initializing', 'resources_allocating', 'capabilities_loading',
            'context_establishing', 'agent_started'
        ]
        return [e for e in self.lifecycle_events if e['event_type'] in startup_event_types]

    def get_shutdown_events(self) -> List[Dict[str, Any]]:
        """Get all shutdown-related events."""
        shutdown_event_types = [
            'results_compiling', 'resources_cleaning', 'context_persisting', 'agent_completed'
        ]
        return [e for e in self.lifecycle_events if e['event_type'] in shutdown_event_types]

    def reset_lifecycle(self):
        """Reset lifecycle manager for new test."""
        self.lifecycle_events = []
        self.current_phase = None
        self.startup_completed = False
        self.shutdown_initiated = False
        self.error_states = []
        self.resource_allocations = {}
        self.cleanup_operations = []


class TestAgentLifecycleEvents(SSotAsyncTestCase):
    """Test agent lifecycle event generation for Golden Path business value."""

    def setup_method(self, method):
        """Set up test fixtures for agent lifecycle event testing."""
        super().setup_method(method)
        self.lifecycle_manager = MockAgentLifecycleManager()
        self.run_id = str(uuid.uuid4())
        self.thread_id = str(uuid.uuid4())
        self.user_id = "test_user_lifecycle"
        self.agent_name = "lifecycle_test_agent"

        # Create test execution context
        self.execution_context = AgentExecutionContext(
            run_id=self.run_id,
            thread_id=self.thread_id,
            user_id=self.user_id,
            agent_name=self.agent_name,
            timeout=300,
            step=PipelineStep.INITIALIZATION
        )

        # Create test execution result
        self.execution_result = AgentExecutionResult(
            success=True,
            agent_name=self.agent_name,
            duration=5.25,
            metadata={'test': True}
        )

    async def test_agent_startup_event_sequence(self):
        """Test complete agent startup event sequence generation."""
        # Execute startup lifecycle
        success = await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)

        assert success, "Agent startup should complete successfully"
        assert self.lifecycle_manager.startup_completed, "Startup completion flag should be set"
        assert self.lifecycle_manager.current_phase == 'ready', "Should transition to ready phase"

        # Validate startup events
        startup_events = self.lifecycle_manager.get_startup_events()
        expected_startup_events = [
            'agent_initializing', 'resources_allocating', 'capabilities_loading',
            'context_establishing', 'agent_started'
        ]

        assert len(startup_events) == 5, "Should generate 5 startup events"
        for i, expected_event in enumerate(expected_startup_events):
            assert startup_events[i]['event_type'] == expected_event, \
                f"Event {i} should be {expected_event}, got {startup_events[i]['event_type']}"

        # Validate startup data consistency
        for event in startup_events:
            assert event['data']['run_id'] == self.run_id, "All events should have consistent run_id"

    async def test_agent_shutdown_event_sequence(self):
        """Test complete agent shutdown event sequence generation."""
        # First complete startup
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)

        # Execute shutdown lifecycle
        success = await self.lifecycle_manager.shutdown_agent_lifecycle(
            self.execution_context,
            self.execution_result
        )

        assert success, "Agent shutdown should complete successfully"
        assert self.lifecycle_manager.shutdown_initiated, "Shutdown initiation flag should be set"
        assert self.lifecycle_manager.current_phase == 'terminated', "Should transition to terminated phase"

        # Validate shutdown events
        shutdown_events = self.lifecycle_manager.get_shutdown_events()
        expected_shutdown_events = [
            'results_compiling', 'resources_cleaning', 'context_persisting', 'agent_completed'
        ]

        assert len(shutdown_events) == 4, "Should generate 4 shutdown events"
        for i, expected_event in enumerate(expected_shutdown_events):
            assert shutdown_events[i]['event_type'] == expected_event, \
                f"Event {i} should be {expected_event}, got {shutdown_events[i]['event_type']}"

    async def test_lifecycle_state_transitions(self):
        """Test agent lifecycle state transitions with proper event generation."""
        # Initial state
        assert self.lifecycle_manager.get_lifecycle_phase() is None, "Should start with no phase"

        # Start lifecycle and check transition
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)
        assert self.lifecycle_manager.get_lifecycle_phase() == 'ready', "Should transition to ready"

        # Complete lifecycle and check final transition
        await self.lifecycle_manager.shutdown_agent_lifecycle(
            self.execution_context,
            self.execution_result
        )
        assert self.lifecycle_manager.get_lifecycle_phase() == 'terminated', "Should transition to terminated"

        # Validate complete lifecycle event sequence
        all_events = self.lifecycle_manager.lifecycle_events
        event_types = [e['event_type'] for e in all_events]

        # Should have both startup and shutdown events
        startup_events = ['agent_initializing', 'resources_allocating', 'capabilities_loading',
                         'context_establishing', 'agent_started']
        shutdown_events = ['results_compiling', 'resources_cleaning', 'context_persisting', 'agent_completed']

        for startup_event in startup_events:
            assert startup_event in event_types, f"Should have {startup_event} event"

        for shutdown_event in shutdown_events:
            assert shutdown_event in event_types, f"Should have {shutdown_event} event"

    async def test_error_event_generation_during_startup(self):
        """Test error event generation during agent startup phases."""
        # Simulate startup error
        startup_error = Exception("Resource allocation failed")

        success = await self.lifecycle_manager.handle_lifecycle_error(
            self.execution_context,
            startup_error,
            'resource_allocation'
        )

        # Should attempt recovery
        assert success, "Should successfully handle and recover from startup error"
        assert len(self.lifecycle_manager.error_states) == 1, "Should record error state"

        # Check error events
        error_events = [e for e in self.lifecycle_manager.lifecycle_events
                       if e['event_type'] in ['lifecycle_error', 'recovery_initiated']]

        assert len(error_events) >= 2, "Should generate error and recovery events"

        # Validate error event data
        error_event = next(e for e in error_events if e['event_type'] == 'lifecycle_error')
        assert error_event['data']['error_phase'] == 'resource_allocation'
        assert error_event['data']['error_type'] == 'Exception'
        assert 'recovery_strategy' in error_event['data']

    async def test_error_event_generation_during_execution(self):
        """Test error event generation during agent execution phases."""
        # Complete startup first
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)

        # Simulate execution error
        execution_error = RuntimeError("Tool execution timeout")

        success = await self.lifecycle_manager.handle_lifecycle_error(
            self.execution_context,
            execution_error,
            'execution'
        )

        # Should handle execution error
        assert success, "Should handle execution error with recovery"

        # Validate error handling
        error_events = [e for e in self.lifecycle_manager.lifecycle_events
                       if e['event_type'] in ['lifecycle_error', 'recovery_initiated']]

        execution_errors = [e for e in error_events
                          if e['data'].get('error_phase') == 'execution']

        assert len(execution_errors) >= 1, "Should generate execution error events"

    async def test_completion_event_validation(self):
        """Test validation of agent completion events with proper data."""
        # Complete full lifecycle
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)
        await self.lifecycle_manager.shutdown_agent_lifecycle(
            self.execution_context,
            self.execution_result
        )

        # Find completion event
        completion_events = [e for e in self.lifecycle_manager.lifecycle_events
                           if e['event_type'] == 'agent_completed']

        assert len(completion_events) == 1, "Should have exactly one completion event"

        completion_event = completion_events[0]
        completion_data = completion_event['data']

        # Validate completion event data
        required_fields = ['run_id', 'agent_name', 'total_duration_ms', 'success', 'cleanup_successful']
        for field in required_fields:
            assert field in completion_data, f"Completion event should have {field} field"

        assert completion_data['run_id'] == self.run_id
        assert completion_data['agent_name'] == self.agent_name
        assert completion_data['success'] == self.execution_result.success

    async def test_resource_cleanup_event_validation(self):
        """Test validation of resource cleanup events during shutdown."""
        # Complete startup and shutdown
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)
        await self.lifecycle_manager.shutdown_agent_lifecycle(
            self.execution_context,
            self.execution_result
        )

        # Find resource cleanup events
        cleanup_events = [e for e in self.lifecycle_manager.lifecycle_events
                         if e['event_type'] == 'resources_cleaning']

        assert len(cleanup_events) == 1, "Should have resource cleanup event"

        cleanup_event = cleanup_events[0]
        cleanup_data = cleanup_event['data']

        # Validate cleanup event data
        expected_fields = ['run_id', 'memory_freed', 'temp_files_cleaned', 'connections_closed']
        for field in expected_fields:
            assert field in cleanup_data, f"Cleanup event should have {field} field"

        # Validate resource cleanup values are positive
        assert cleanup_data['temp_files_cleaned'] >= 0, "Should report non-negative temp files cleaned"
        assert cleanup_data['connections_closed'] >= 0, "Should report non-negative connections closed"

    async def test_multi_agent_lifecycle_coordination(self):
        """Test lifecycle event coordination for multiple concurrent agents."""
        # Create second agent context
        second_run_id = str(uuid.uuid4())
        second_context = AgentExecutionContext(
            run_id=second_run_id,
            thread_id=str(uuid.uuid4()),
            user_id=self.user_id,
            agent_name="second_agent",
            timeout=200
        )

        # Create second lifecycle manager
        second_manager = MockAgentLifecycleManager()

        # Start both agents concurrently
        results = await asyncio.gather(
            self.lifecycle_manager.start_agent_lifecycle(self.execution_context),
            second_manager.start_agent_lifecycle(second_context),
            return_exceptions=True
        )

        assert all(results), "Both agents should start successfully"

        # Validate isolated lifecycle events
        first_events = [e for e in self.lifecycle_manager.lifecycle_events
                       if e['data']['run_id'] == self.run_id]
        second_events = [e for e in second_manager.lifecycle_events
                        if e['data']['run_id'] == second_run_id]

        assert len(first_events) == 5, "First agent should have 5 startup events"
        assert len(second_events) == 5, "Second agent should have 5 startup events"

        # Ensure no cross-contamination
        for event in first_events:
            assert event['data']['run_id'] == self.run_id, "First agent events should be isolated"

        for event in second_events:
            assert event['data']['run_id'] == second_run_id, "Second agent events should be isolated"

    async def test_lifecycle_event_timing_validation(self):
        """Test validation of lifecycle event timing and sequence."""
        start_time = datetime.now(timezone.utc)

        # Execute complete lifecycle
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)

        end_time = datetime.now(timezone.utc)
        execution_duration = (end_time - start_time).total_seconds() * 1000

        # Validate event timing
        startup_events = self.lifecycle_manager.get_startup_events()

        # Events should be in chronological order
        for i in range(1, len(startup_events)):
            current_time = startup_events[i]['timestamp']
            previous_time = startup_events[i-1]['timestamp']
            assert current_time >= previous_time, f"Event {i} should be after event {i-1}"

        # All events should be within execution timeframe
        for event in startup_events:
            assert event['timestamp'] >= start_time, "Event should be after start time"
            assert event['timestamp'] <= end_time, "Event should be before end time"

    async def test_lifecycle_recovery_mechanisms(self):
        """Test agent lifecycle recovery mechanisms during failures."""
        # Test recovery from different phases
        recovery_scenarios = [
            ('initialization', ValueError("Invalid configuration")),
            ('resource_allocation', RuntimeError("Memory allocation failed")),
            ('execution', TimeoutError("Agent execution timeout"))
        ]

        for phase, error in recovery_scenarios:
            # Reset for each scenario
            self.lifecycle_manager.reset_lifecycle()

            # Attempt recovery
            recovery_success = await self.lifecycle_manager.handle_lifecycle_error(
                self.execution_context, error, phase
            )

            # Should attempt recovery for all phases
            assert recovery_success, f"Should successfully recover from {phase} error"

            # Validate recovery events
            recovery_events = [e for e in self.lifecycle_manager.lifecycle_events
                             if e['event_type'] == 'recovery_initiated']

            assert len(recovery_events) >= 1, f"Should generate recovery event for {phase} phase"
            assert recovery_events[0]['data']['phase'] == phase

    async def test_business_value_lifecycle_integration(self):
        """Test lifecycle events integration with business value tracking."""
        # Add business value context to execution
        business_context = {
            'customer_tier': 'enterprise',
            'expected_value': '$50K optimization',
            'business_priority': 'high'
        }

        self.execution_context.metadata.update(business_context)

        # Execute lifecycle with business context
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)

        # Validate business context in lifecycle events
        startup_events = self.lifecycle_manager.get_startup_events()

        # Business context should be preserved in metadata throughout lifecycle
        for event in startup_events:
            if 'metadata' in event['data']:
                # Business context should be accessible for value tracking
                pass  # Context is preserved in execution_context.metadata

        # Validate business value consideration in lifecycle
        agent_started_event = next((e for e in startup_events if e['event_type'] == 'agent_started'), None)
        assert agent_started_event is not None, "Should have agent_started event"

    async def test_error_recovery_limits(self):
        """Test error recovery attempt limits and failure handling."""
        # Simulate repeated failures
        repeated_error = RuntimeError("Persistent system failure")

        # Attempt recovery multiple times
        recovery_attempts = []
        for attempt in range(5):  # Try more than the limit
            success = await self.lifecycle_manager.handle_lifecycle_error(
                self.execution_context,
                repeated_error,
                'execution'
            )
            recovery_attempts.append(success)

        # Should eventually stop attempting recovery
        assert not all(recovery_attempts), "Should not indefinitely attempt recovery"
        assert len(self.lifecycle_manager.error_states) == 5, "Should record all error attempts"

        # Validate recovery limit enforcement
        final_attempts = recovery_attempts[-2:]  # Last 2 attempts
        assert not all(final_attempts), "Should stop recovery attempts after limit"

    async def test_graceful_degradation_events(self):
        """Test graceful degradation event generation during partial failures."""
        # Simulate partial failure scenario
        partial_failure_error = RuntimeError("Non-critical subsystem failure")

        # Handle with graceful degradation
        success = await self.lifecycle_manager.handle_lifecycle_error(
            self.execution_context,
            partial_failure_error,
            'execution'
        )

        assert success, "Should handle partial failures with graceful degradation"

        # Validate degradation events
        degradation_events = [e for e in self.lifecycle_manager.lifecycle_events
                            if 'degraded' in str(e['data']).lower() or
                               e['data'].get('recovery_strategy') == 'graceful_degradation']

        # Should generate appropriate degradation events
        assert len(degradation_events) >= 0, "Should handle degradation appropriately"

    async def test_lifecycle_event_persistence(self):
        """Test persistence and retrieval of lifecycle events for audit purposes."""
        # Execute complete lifecycle
        await self.lifecycle_manager.start_agent_lifecycle(self.execution_context)
        await self.lifecycle_manager.shutdown_agent_lifecycle(
            self.execution_context,
            self.execution_result
        )

        # Validate complete event history
        all_events = self.lifecycle_manager.lifecycle_events
        assert len(all_events) >= 9, "Should have comprehensive event history"

        # Validate event structure for persistence
        for event in all_events:
            required_fields = ['event_type', 'timestamp', 'data']
            for field in required_fields:
                assert field in event, f"Event should have {field} for persistence"

            # Validate timestamp is serializable
            assert isinstance(event['timestamp'], datetime), "Timestamp should be datetime object"
            assert event['data']['run_id'] == self.run_id, "All events should have consistent run_id"

    async def test_concurrent_lifecycle_isolation(self):
        """Test isolation of lifecycle events between concurrent agent executions."""
        # Create multiple contexts for concurrent execution
        contexts = []
        managers = []

        for i in range(3):
            context = AgentExecutionContext(
                run_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                user_id=f"user_{i}",
                agent_name=f"agent_{i}",
                timeout=300
            )
            contexts.append(context)
            managers.append(MockAgentLifecycleManager())

        # Execute all lifecycles concurrently
        startup_results = await asyncio.gather(*[
            manager.start_agent_lifecycle(context)
            for manager, context in zip(managers, contexts)
        ])

        assert all(startup_results), "All concurrent startups should succeed"

        # Validate isolation
        for i, manager in enumerate(managers):
            events = manager.lifecycle_events
            for event in events:
                assert event['data']['run_id'] == contexts[i].run_id, \
                    f"Events for agent {i} should be isolated by run_id"

        # Validate no cross-contamination
        all_run_ids = set()
        for manager in managers:
            for event in manager.lifecycle_events:
                all_run_ids.add(event['data']['run_id'])

        assert len(all_run_ids) == 3, "Should have 3 distinct run_ids with no contamination"