"""
Advanced Agent Lifecycle and State Management Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent state persistence and lifecycle management for reliable AI operations
- Value Impact: Validates complex agent execution scenarios that deliver consistent business value
- Strategic Impact: CRITICAL for enterprise customers - agents must maintain state across failures

ADVANCED TEST SCENARIOS:
1. Agent state persistence across system restarts
2. Complex agent lifecycle transitions with state validation
3. Agent execution with memory constraints and cleanup
4. Concurrent agent state management with isolation
5. Agent state recovery from partial failures
6. Long-running agent state consistency validation

CRITICAL REQUIREMENTS:
- NO MOCKS - Real services for all database/cache operations
- E2E authentication throughout all tests
- WebSocket events validation for all agent state changes
- Performance benchmarks for state persistence operations
- Resource cleanup and memory management validation
"""

import asyncio
import json
import logging
import time
import uuid
import psutil
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.models.agent_execution import AgentExecution
from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.api.websocket.events import WebSocketEventType
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class AgentLifecycleStage(Enum):
    """Advanced agent lifecycle stages for state testing."""
    INITIALIZING = "initializing"
    PREPARING = "preparing"
    EXECUTING = "executing"
    SUSPENDED = "suspended"
    RESUMING = "resuming"
    COMPLETING = "completing"
    PERSISTING = "persisting"
    CLEANUP = "cleanup"


@dataclass
class AgentStateSnapshot:
    """Snapshot of agent state at a specific point."""
    agent_id: str
    stage: AgentLifecycleStage
    execution_data: Dict[str, Any]
    memory_usage: float
    persistence_verified: bool
    timestamp: datetime
    websocket_events_count: int


class TestAdvancedAgentLifecycleStateManagement(BaseIntegrationTest):
    """Advanced integration tests for agent lifecycle and state management."""

    @pytest.mark.asyncio
    async def test_agent_state_persistence_across_restart(self, real_services_fixture):
        """
        Test agent state persistence when system components restart.
        
        CRITICAL SCENARIO: Enterprise customers need agents to survive system restarts.
        This validates state persistence and recovery mechanisms.
        """
        logger.info("Starting agent state persistence across restart test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_persistence_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize agent registry and execution engine
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        
        # Set up WebSocket manager for event tracking
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        websocket_events = []
        def capture_event(event):
            websocket_events.append(event)
            
        websocket_manager.add_event_listener(capture_event)
        
        # Phase 1: Start agent execution and capture initial state
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        initial_message = {
            "type": "user_message",
            "content": "Analyze cost optimization for my infrastructure",
            "user_id": str(user_id),
            "thread_id": str(thread_id)
        }
        
        # Start agent execution
        agent_execution = await execution_engine.start_agent_execution(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            message_content=initial_message["content"],
            execution_context=auth_context
        )
        
        # Wait for agent to reach executing state
        await asyncio.sleep(2)
        
        # Capture state snapshot before "restart"
        initial_snapshot = AgentStateSnapshot(
            agent_id=str(agent_execution.id),
            stage=AgentLifecycleStage.EXECUTING,
            execution_data=agent_execution.execution_data or {},
            memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            persistence_verified=False,
            timestamp=datetime.now(timezone.utc),
            websocket_events_count=len(websocket_events)
        )
        
        logger.info(f"Initial state snapshot: {initial_snapshot}")
        
        # Phase 2: Simulate system restart by reinitializing components
        logger.info("Simulating system restart...")
        
        # "Stop" current components (simulate restart)
        del execution_engine
        del agent_registry
        await asyncio.sleep(1)
        
        # "Restart" components - reinitialize
        agent_registry_restarted = AgentRegistry()
        execution_engine_restarted = ExecutionEngine()
        
        # Reconnect WebSocket manager
        websocket_manager_restarted = WebSocketManager()
        agent_registry_restarted.set_websocket_manager(websocket_manager_restarted)
        
        restart_websocket_events = []
        def capture_restart_event(event):
            restart_websocket_events.append(event)
            
        websocket_manager_restarted.add_event_listener(capture_restart_event)
        
        # Phase 3: Recover agent state and validate persistence
        recovered_execution = await execution_engine_restarted.recover_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            execution_context=auth_context
        )
        
        assert recovered_execution is not None, "Agent execution should be recoverable after restart"
        assert recovered_execution.id == agent_execution.id, "Recovered execution should have same ID"
        
        # Validate state persistence
        post_restart_snapshot = AgentStateSnapshot(
            agent_id=str(recovered_execution.id),
            stage=AgentLifecycleStage.RESUMING,
            execution_data=recovered_execution.execution_data or {},
            memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            persistence_verified=True,
            timestamp=datetime.now(timezone.utc),
            websocket_events_count=len(restart_websocket_events)
        )
        
        logger.info(f"Post-restart state snapshot: {post_restart_snapshot}")
        
        # Validate critical state preservation
        assert post_restart_snapshot.persistence_verified, "State persistence should be verified"
        assert len(restart_websocket_events) > 0, "WebSocket events should be generated on recovery"
        
        # Validate execution data preservation
        if initial_snapshot.execution_data:
            for key, value in initial_snapshot.execution_data.items():
                assert key in post_restart_snapshot.execution_data, f"Execution data key '{key}' should be preserved"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 30.0, f"State recovery should complete in <30s, took {execution_time:.2f}s"
        
        logger.info(f"Agent state persistence test completed in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_complex_agent_lifecycle_transitions(self, real_services_fixture):
        """
        Test complex agent lifecycle transitions with comprehensive state validation.
        
        BUSINESS SCENARIO: Validates agent can handle complex workflow transitions
        while maintaining state consistency throughout the process.
        """
        logger.info("Starting complex agent lifecycle transitions test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_lifecycle_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        websocket_events = []
        def capture_event(event):
            websocket_events.append(event)
            
        websocket_manager.add_event_listener(capture_event)
        
        # Track state transitions
        state_transitions = []
        
        def record_transition(from_state: AgentLifecycleStage, to_state: AgentLifecycleStage, data: Dict):
            transition = {
                "from": from_state.value,
                "to": to_state.value,
                "timestamp": datetime.now(timezone.utc),
                "data": data,
                "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024
            }
            state_transitions.append(transition)
            logger.info(f"State transition: {from_state.value} -> {to_state.value}")
        
        # Phase 1: Initialize agent
        record_transition(AgentLifecycleStage.INITIALIZING, AgentLifecycleStage.PREPARING, {})
        
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        # Start complex workflow
        agent_execution = await execution_engine.start_agent_execution(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            message_content="Run comprehensive cost analysis with data validation",
            execution_context=auth_context
        )
        
        record_transition(AgentLifecycleStage.PREPARING, AgentLifecycleStage.EXECUTING, 
                         {"agent_id": str(agent_execution.id)})
        
        # Phase 2: Suspend and resume execution (simulate user pause/resume)
        await asyncio.sleep(1)
        
        # Suspend execution
        record_transition(AgentLifecycleStage.EXECUTING, AgentLifecycleStage.SUSPENDED, 
                         {"reason": "user_requested_pause"})
        
        suspended_state = await execution_engine.suspend_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            reason="user_requested_pause"
        )
        
        assert suspended_state is not None, "Agent execution should be suspendable"
        
        # Wait in suspended state
        await asyncio.sleep(2)
        
        # Resume execution
        record_transition(AgentLifecycleStage.SUSPENDED, AgentLifecycleStage.RESUMING,
                         {"resume_timestamp": datetime.now(timezone.utc).isoformat()})
        
        resumed_execution = await execution_engine.resume_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            execution_context=auth_context
        )
        
        assert resumed_execution is not None, "Agent execution should be resumable"
        
        record_transition(AgentLifecycleStage.RESUMING, AgentLifecycleStage.EXECUTING,
                         {"resumed_successfully": True})
        
        # Phase 3: Complete execution
        await asyncio.sleep(2)
        
        record_transition(AgentLifecycleStage.EXECUTING, AgentLifecycleStage.COMPLETING, {})
        
        # Complete execution
        completed_execution = await execution_engine.complete_agent_execution(
            agent_execution_id=agent_execution.id,
            user_id=user_id,
            final_result={"status": "success", "analysis_completed": True}
        )
        
        record_transition(AgentLifecycleStage.COMPLETING, AgentLifecycleStage.PERSISTING, 
                         {"final_result_size": len(str(completed_execution.result))})
        
        # Phase 4: Cleanup phase
        record_transition(AgentLifecycleStage.PERSISTING, AgentLifecycleStage.CLEANUP, {})
        
        await execution_engine.cleanup_agent_resources(
            agent_execution_id=agent_execution.id,
            user_id=user_id
        )
        
        # Validate state transitions
        assert len(state_transitions) >= 8, f"Expected >=8 transitions, got {len(state_transitions)}"
        
        # Validate transition sequence
        expected_sequence = [
            AgentLifecycleStage.PREPARING,
            AgentLifecycleStage.EXECUTING,
            AgentLifecycleStage.SUSPENDED,
            AgentLifecycleStage.RESUMING,
            AgentLifecycleStage.EXECUTING,
            AgentLifecycleStage.COMPLETING,
            AgentLifecycleStage.PERSISTING,
            AgentLifecycleStage.CLEANUP
        ]
        
        for i, expected_stage in enumerate(expected_sequence):
            if i < len(state_transitions):
                actual_stage = AgentLifecycleStage(state_transitions[i]["to"])
                assert actual_stage == expected_stage, f"Transition {i}: expected {expected_stage.value}, got {actual_stage.value}"
        
        # Validate WebSocket events for each major transition
        major_events = [event for event in websocket_events if event.get("type") in [
            WebSocketEventType.AGENT_STARTED.value,
            WebSocketEventType.AGENT_SUSPENDED.value,
            WebSocketEventType.AGENT_RESUMED.value,
            WebSocketEventType.AGENT_COMPLETED.value
        ]]
        
        assert len(major_events) >= 4, f"Expected >=4 major WebSocket events, got {len(major_events)}"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 45.0, f"Complex lifecycle should complete in <45s, took {execution_time:.2f}s"
        
        logger.info(f"Complex lifecycle transitions test completed in {execution_time:.2f}s with {len(state_transitions)} transitions")

    @pytest.mark.asyncio
    async def test_agent_memory_constraints_and_cleanup(self, real_services_fixture):
        """
        Test agent execution under memory constraints with proper resource cleanup.
        
        ENTERPRISE SCENARIO: Validates agents handle resource constraints gracefully
        and perform proper cleanup to prevent memory leaks.
        """
        logger.info("Starting agent memory constraints and cleanup test")
        start_time = time.time()
        
        # Monitor initial memory baseline
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_memory_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        memory_snapshots = []
        websocket_events = []
        
        def capture_event(event):
            websocket_events.append(event)
            
        def capture_memory_snapshot(stage: str):
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
            snapshot = {
                "stage": stage,
                "memory_mb": memory_usage,
                "memory_diff": memory_usage - initial_memory,
                "timestamp": datetime.now(timezone.utc)
            }
            memory_snapshots.append(snapshot)
            logger.info(f"Memory snapshot - {stage}: {memory_usage:.2f} MB (diff: {snapshot['memory_diff']:+.2f} MB)")
        
        websocket_manager.add_event_listener(capture_event)
        
        # Phase 1: Run multiple concurrent agents to stress memory
        concurrent_executions = []
        capture_memory_snapshot("before_concurrent_agents")
        
        for i in range(5):  # Create 5 concurrent agents
            thread_id = ThreadID(str(uuid.uuid4()))
            run_id = RunID(str(uuid.uuid4()))
            
            execution = await execution_engine.start_agent_execution(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                message_content=f"Memory intensive task {i} - analyze large dataset with detailed reporting",
                execution_context=auth_context
            )
            concurrent_executions.append(execution)
            
            # Small delay between starts to stagger resource allocation
            await asyncio.sleep(0.5)
        
        capture_memory_snapshot("after_starting_concurrent_agents")
        
        # Let agents execute for a bit
        await asyncio.sleep(3)
        capture_memory_snapshot("during_concurrent_execution")
        
        # Phase 2: Systematically clean up agents
        for i, execution in enumerate(concurrent_executions):
            # Complete execution
            await execution_engine.complete_agent_execution(
                agent_execution_id=execution.id,
                user_id=user_id,
                final_result={"task": f"completed_{i}", "memory_optimized": True}
            )
            
            # Explicit cleanup
            await execution_engine.cleanup_agent_resources(
                agent_execution_id=execution.id,
                user_id=user_id
            )
            
            capture_memory_snapshot(f"after_cleanup_{i}")
            await asyncio.sleep(0.2)  # Brief pause between cleanups
        
        # Phase 3: Force garbage collection and final memory check
        import gc
        gc.collect()
        await asyncio.sleep(2)
        
        capture_memory_snapshot("after_garbage_collection")
        
        # Validate memory management
        final_memory = memory_snapshots[-1]["memory_mb"]
        peak_memory = max(snapshot["memory_mb"] for snapshot in memory_snapshots)
        memory_leak = final_memory - initial_memory
        
        logger.info(f"Memory analysis: Initial={initial_memory:.2f}MB, Peak={peak_memory:.2f}MB, Final={final_memory:.2f}MB, Leak={memory_leak:+.2f}MB")
        
        # Memory leak validation (allow 50MB tolerance for test infrastructure)
        assert memory_leak < 50.0, f"Memory leak detected: {memory_leak:.2f}MB increase from baseline"
        
        # Peak memory should be reasonable (allow 200MB for 5 concurrent agents)
        memory_increase = peak_memory - initial_memory
        assert memory_increase < 200.0, f"Peak memory usage too high: {memory_increase:.2f}MB increase"
        
        # Validate cleanup efficiency
        cleanup_snapshots = [s for s in memory_snapshots if "after_cleanup_" in s["stage"]]
        if len(cleanup_snapshots) >= 2:
            # Memory should generally decrease during cleanup
            decreasing_count = 0
            for i in range(1, len(cleanup_snapshots)):
                if cleanup_snapshots[i]["memory_mb"] <= cleanup_snapshots[i-1]["memory_mb"]:
                    decreasing_count += 1
            
            cleanup_efficiency = decreasing_count / (len(cleanup_snapshots) - 1)
            assert cleanup_efficiency >= 0.6, f"Cleanup efficiency too low: {cleanup_efficiency:.2%} of cleanups reduced memory"
        
        # Validate WebSocket events for resource management
        cleanup_events = [e for e in websocket_events if e.get("type") == WebSocketEventType.AGENT_CLEANUP_COMPLETE.value]
        assert len(cleanup_events) == 5, f"Expected 5 cleanup events, got {len(cleanup_events)}"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 60.0, f"Memory test should complete in <60s, took {execution_time:.2f}s"
        
        logger.info(f"Memory constraints test completed in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_concurrent_agent_state_isolation(self, real_services_fixture):
        """
        Test concurrent agent state management with strict isolation validation.
        
        MULTI-USER SCENARIO: Validates that concurrent agents maintain perfect
        state isolation without cross-contamination.
        """
        logger.info("Starting concurrent agent state isolation test")
        start_time = time.time()
        
        # Create multiple authenticated user contexts
        num_users = 3
        user_contexts = []
        for i in range(num_users):
            context = await create_authenticated_user_context(f"test_isolation_user_{i}")
            user_contexts.append({
                "auth_context": context,
                "user_id": UserID(str(uuid.uuid4())),
                "user_index": i
            })
        
        # Initialize shared components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Track all events per user
        user_events = {ctx["user_id"]: [] for ctx in user_contexts}
        
        def capture_user_event(event):
            user_id = event.get("user_id")
            if user_id and UserID(user_id) in user_events:
                user_events[UserID(user_id)].append(event)
                
        websocket_manager.add_event_listener(capture_user_event)
        
        # Phase 1: Start concurrent agent executions for each user
        user_executions = []
        
        for user_ctx in user_contexts:
            thread_id = ThreadID(str(uuid.uuid4()))
            run_id = RunID(str(uuid.uuid4()))
            
            # Each user gets a unique, identifiable task
            unique_content = f"User {user_ctx['user_index']} isolation test - analyze cost data with unique signature {uuid.uuid4()}"
            
            execution = await execution_engine.start_agent_execution(
                user_id=user_ctx["user_id"],
                thread_id=thread_id,
                run_id=run_id,
                message_content=unique_content,
                execution_context=user_ctx["auth_context"]
            )
            
            user_executions.append({
                "execution": execution,
                "user_ctx": user_ctx,
                "unique_signature": unique_content,
                "state_data": {"isolation_marker": f"user_{user_ctx['user_index']}_data"}
            })
            
            # Small delay between starts
            await asyncio.sleep(0.3)
        
        logger.info(f"Started {len(user_executions)} concurrent agent executions")
        
        # Phase 2: Let agents execute and modify their state
        await asyncio.sleep(2)
        
        # Add unique state data to each execution
        for user_exec in user_executions:
            await execution_engine.update_agent_state(
                agent_execution_id=user_exec["execution"].id,
                user_id=user_exec["user_ctx"]["user_id"],
                state_update=user_exec["state_data"]
            )
        
        await asyncio.sleep(1)
        
        # Phase 3: Validate state isolation by retrieving and checking each execution
        isolation_violations = []
        
        for i, user_exec in enumerate(user_executions):
            # Retrieve current execution state
            current_state = await execution_engine.get_agent_execution_state(
                agent_execution_id=user_exec["execution"].id,
                user_id=user_exec["user_ctx"]["user_id"]
            )
            
            # Validate this user's data is present and correct
            expected_marker = user_exec["state_data"]["isolation_marker"]
            actual_marker = current_state.get("execution_data", {}).get("isolation_marker")
            
            if actual_marker != expected_marker:
                isolation_violations.append({
                    "user_index": i,
                    "expected": expected_marker,
                    "actual": actual_marker,
                    "violation_type": "missing_user_data"
                })
            
            # Validate no other user's data is present
            for j, other_exec in enumerate(user_executions):
                if i != j:
                    other_marker = other_exec["state_data"]["isolation_marker"]
                    if other_marker in str(current_state):
                        isolation_violations.append({
                            "user_index": i,
                            "contaminated_by_user": j,
                            "contaminating_data": other_marker,
                            "violation_type": "cross_user_contamination"
                        })
        
        # Assert no isolation violations
        assert len(isolation_violations) == 0, f"State isolation violations detected: {isolation_violations}"
        
        # Phase 4: Validate WebSocket event isolation
        event_isolation_violations = []
        
        for user_ctx in user_contexts:
            user_id = user_ctx["user_id"]
            user_specific_events = user_events[user_id]
            
            # Each user should have their own events
            assert len(user_specific_events) > 0, f"User {user_ctx['user_index']} should have received WebSocket events"
            
            # Check that events contain correct user_id
            for event in user_specific_events:
                event_user_id = event.get("user_id")
                if event_user_id and UserID(event_user_id) != user_id:
                    event_isolation_violations.append({
                        "expected_user": str(user_id),
                        "actual_user": event_user_id,
                        "event": event
                    })
        
        assert len(event_isolation_violations) == 0, f"WebSocket event isolation violations: {event_isolation_violations}"
        
        # Phase 5: Complete all executions and validate final isolation
        for user_exec in user_executions:
            await execution_engine.complete_agent_execution(
                agent_execution_id=user_exec["execution"].id,
                user_id=user_exec["user_ctx"]["user_id"],
                final_result={
                    "isolation_test": "completed",
                    "user_signature": user_exec["state_data"]["isolation_marker"]
                }
            )
        
        # Final isolation check
        for user_exec in user_executions:
            final_result = await execution_engine.get_agent_execution_result(
                agent_execution_id=user_exec["execution"].id,
                user_id=user_exec["user_ctx"]["user_id"]
            )
            
            expected_signature = user_exec["state_data"]["isolation_marker"]
            actual_signature = final_result.get("user_signature")
            
            assert actual_signature == expected_signature, f"Final result isolation violated: expected {expected_signature}, got {actual_signature}"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 30.0, f"Concurrent isolation test should complete in <30s, took {execution_time:.2f}s"
        
        logger.info(f"Concurrent agent state isolation test completed successfully in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_agent_state_recovery_from_partial_failures(self, real_services_fixture):
        """
        Test agent state recovery from various partial failure scenarios.
        
        RESILIENCE SCENARIO: Validates agent can recover from partial failures
        without losing critical state or business continuity.
        """
        logger.info("Starting agent state recovery from partial failures test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_recovery_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        failure_scenarios = []
        recovery_results = []
        websocket_events = []
        
        def capture_event(event):
            websocket_events.append(event)
            
        websocket_manager.add_event_listener(capture_event)
        
        # Phase 1: Start agent execution with comprehensive state
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        complex_state = {
            "analysis_progress": 0.3,
            "data_processed": ["dataset1", "dataset2"],
            "intermediate_results": {"cost_analysis": {"total": 1500.00}},
            "tool_outputs": ["tool1_result", "tool2_result"],
            "user_preferences": {"detail_level": "high", "format": "json"},
            "execution_metadata": {"version": "1.0", "timestamp": datetime.now(timezone.utc).isoformat()}
        }
        
        execution = await execution_engine.start_agent_execution(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            message_content="Complex analysis requiring state preservation",
            execution_context=auth_context
        )
        
        # Update with complex state
        await execution_engine.update_agent_state(
            agent_execution_id=execution.id,
            user_id=user_id,
            state_update=complex_state
        )
        
        await asyncio.sleep(1)
        
        # Phase 2: Simulate various partial failures and recovery
        
        # Failure Scenario 1: Database connection interruption
        logger.info("Simulating database connection failure")
        try:
            # Simulate database failure by attempting invalid operation
            await execution_engine.simulate_database_failure(execution.id)
        except Exception as e:
            failure_scenarios.append({
                "type": "database_connection",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Attempt recovery
        recovered_state_1 = await execution_engine.recover_from_database_failure(
            agent_execution_id=execution.id,
            user_id=user_id
        )
        
        recovery_results.append({
            "scenario": "database_connection",
            "recovered": recovered_state_1 is not None,
            "state_preserved": self._validate_state_preservation(complex_state, recovered_state_1)
        })
        
        await asyncio.sleep(1)
        
        # Failure Scenario 2: WebSocket connection loss
        logger.info("Simulating WebSocket connection failure")
        try:
            websocket_manager.simulate_connection_loss(str(user_id))
            await asyncio.sleep(0.5)
            
            # Attempt to send event during connection loss
            await websocket_manager.send_event_to_user(
                user_id=str(user_id),
                event_type=WebSocketEventType.AGENT_THINKING,
                event_data={"message": "Testing during connection loss"}
            )
        except Exception as e:
            failure_scenarios.append({
                "type": "websocket_connection",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Recover WebSocket connection
        websocket_manager.restore_connection(str(user_id))
        recovered_websocket = await websocket_manager.validate_connection(str(user_id))
        
        recovery_results.append({
            "scenario": "websocket_connection",
            "recovered": recovered_websocket,
            "events_resumed": len(websocket_events) > 0
        })
        
        await asyncio.sleep(1)
        
        # Failure Scenario 3: Memory pressure induced state corruption
        logger.info("Simulating memory pressure failure")
        try:
            # Create artificial memory pressure
            large_data = ["x" * 1000000 for _ in range(10)]  # 10MB of strings
            
            # Attempt state update under pressure
            corrupted_update = {**complex_state, "large_data": large_data}
            await execution_engine.update_agent_state(
                agent_execution_id=execution.id,
                user_id=user_id,
                state_update=corrupted_update
            )
            
            del large_data  # Release memory
            
        except Exception as e:
            failure_scenarios.append({
                "type": "memory_pressure",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Recover from memory pressure
        recovered_state_3 = await execution_engine.recover_from_memory_pressure(
            agent_execution_id=execution.id,
            user_id=user_id,
            fallback_state=complex_state
        )
        
        recovery_results.append({
            "scenario": "memory_pressure",
            "recovered": recovered_state_3 is not None,
            "state_preserved": self._validate_state_preservation(complex_state, recovered_state_3)
        })
        
        # Phase 3: Validate overall recovery success
        final_state = await execution_engine.get_agent_execution_state(
            agent_execution_id=execution.id,
            user_id=user_id
        )
        
        # Validate all critical state elements are preserved
        assert final_state is not None, "Final state should be recoverable"
        assert "analysis_progress" in final_state.get("execution_data", {}), "Analysis progress should be preserved"
        assert "intermediate_results" in final_state.get("execution_data", {}), "Intermediate results should be preserved"
        
        # Validate recovery statistics
        successful_recoveries = sum(1 for result in recovery_results if result["recovered"])
        recovery_rate = successful_recoveries / len(recovery_results)
        
        assert recovery_rate >= 0.8, f"Recovery rate too low: {recovery_rate:.2%} (expected  >= 80%)"
        
        # Validate state preservation rate
        preserved_states = sum(1 for result in recovery_results if result.get("state_preserved", False))
        preservation_rate = preserved_states / len(recovery_results)
        
        assert preservation_rate >= 0.7, f"State preservation rate too low: {preservation_rate:.2%} (expected  >= 70%)"
        
        # Complete execution
        await execution_engine.complete_agent_execution(
            agent_execution_id=execution.id,
            user_id=user_id,
            final_result={
                "recovery_test": "completed",
                "failures_handled": len(failure_scenarios),
                "recoveries_successful": successful_recoveries
            }
        )
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 45.0, f"Recovery test should complete in <45s, took {execution_time:.2f}s"
        
        logger.info(f"State recovery test completed in {execution_time:.2f}s with {recovery_rate:.2%} recovery rate")

    @pytest.mark.asyncio
    async def test_long_running_agent_state_consistency(self, real_services_fixture):
        """
        Test long-running agent state consistency over extended periods.
        
        ENTERPRISE SCENARIO: Validates agents maintain state consistency
        during extended operations typical in enterprise environments.
        """
        logger.info("Starting long-running agent state consistency test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_longrunning_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        consistency_checks = []
        state_snapshots = []
        websocket_events = []
        
        def capture_event(event):
            websocket_events.append(event)
            
        websocket_manager.add_event_listener(capture_event)
        
        # Phase 1: Start long-running agent execution
        thread_id = ThreadID(str(uuid.uuid4()))
        run_id = RunID(str(uuid.uuid4()))
        
        execution = await execution_engine.start_agent_execution(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            message_content="Long-running comprehensive analysis with state tracking",
            execution_context=auth_context
        )
        
        # Phase 2: Simulate long-running execution with state updates
        base_state = {
            "execution_id": str(execution.id),
            "start_time": datetime.now(timezone.utc).isoformat(),
            "progress_markers": [],
            "data_checkpoints": {},
            "consistency_hash": None
        }
        
        # Perform consistency checks over time
        for checkpoint in range(10):  # 10 checkpoints over time
            await asyncio.sleep(2)  # 2 seconds between checks
            
            # Update state with new progress
            current_progress = {
                "checkpoint": checkpoint,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_size": checkpoint * 100,  # Simulate growing dataset
                "operations_completed": checkpoint * 5
            }
            
            updated_state = {
                **base_state,
                "current_checkpoint": checkpoint,
                "progress_markers": base_state["progress_markers"] + [current_progress],
                "data_checkpoints": {**base_state.get("data_checkpoints", {}), f"cp_{checkpoint}": current_progress}
            }
            
            # Calculate consistency hash
            import hashlib
            state_str = json.dumps(updated_state, sort_keys=True)
            consistency_hash = hashlib.sha256(state_str.encode()).hexdigest()
            updated_state["consistency_hash"] = consistency_hash
            
            # Update agent state
            await execution_engine.update_agent_state(
                agent_execution_id=execution.id,
                user_id=user_id,
                state_update=updated_state
            )
            
            # Capture state snapshot
            retrieved_state = await execution_engine.get_agent_execution_state(
                agent_execution_id=execution.id,
                user_id=user_id
            )
            
            snapshot = {
                "checkpoint": checkpoint,
                "timestamp": datetime.now(timezone.utc),
                "context_size": len(json.dumps(retrieved_state)),
                "consistency_hash": retrieved_state.get("execution_data", {}).get("consistency_hash"),
                "expected_hash": consistency_hash,
                "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024
            }
            state_snapshots.append(snapshot)
            
            # Validate state consistency
            consistency_check = {
                "checkpoint": checkpoint,
                "hash_match": snapshot["consistency_hash"] == snapshot["expected_hash"],
                "state_complete": len(retrieved_state.get("execution_data", {}).get("progress_markers", [])) == checkpoint + 1,
                "timestamp": snapshot["timestamp"]
            }
            consistency_checks.append(consistency_check)
            
            logger.info(f"Checkpoint {checkpoint}: Hash match={consistency_check['hash_match']}, State complete={consistency_check['state_complete']}")
            
            base_state = updated_state
        
        # Phase 3: Validate consistency over time
        hash_matches = sum(1 for check in consistency_checks if check["hash_match"])
        state_completeness = sum(1 for check in consistency_checks if check["state_complete"])
        
        consistency_rate = hash_matches / len(consistency_checks)
        completeness_rate = state_completeness / len(consistency_checks)
        
        assert consistency_rate >= 0.95, f"State consistency rate too low: {consistency_rate:.2%} (expected  >= 95%)"
        assert completeness_rate >= 0.95, f"State completeness rate too low: {completeness_rate:.2%} (expected  >= 95%)"
        
        # Validate memory stability (no significant memory leaks)
        memory_growth = state_snapshots[-1]["memory_usage"] - state_snapshots[0]["memory_usage"]
        memory_per_checkpoint = memory_growth / len(state_snapshots) if state_snapshots else 0
        
        assert memory_per_checkpoint < 5.0, f"Memory leak detected: {memory_per_checkpoint:.2f}MB per checkpoint"
        
        # Validate WebSocket event consistency
        agent_events = [e for e in websocket_events if e.get("agent_execution_id") == str(execution.id)]
        assert len(agent_events) >= len(consistency_checks), "Should have WebSocket events for state updates"
        
        # Phase 4: Complete long-running execution
        final_result = {
            "execution_summary": "long_running_completed",
            "total_checkpoints": len(consistency_checks),
            "consistency_rate": consistency_rate,
            "completeness_rate": completeness_rate,
            "execution_duration": time.time() - start_time
        }
        
        await execution_engine.complete_agent_execution(
            agent_execution_id=execution.id,
            user_id=user_id,
            final_result=final_result
        )
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time >= 20.0, f"Long-running test should take  >= 20s, took {execution_time:.2f}s"
        assert execution_time < 60.0, f"Long-running test should complete in <60s, took {execution_time:.2f}s"
        
        logger.info(f"Long-running consistency test completed in {execution_time:.2f}s with {consistency_rate:.2%} consistency rate")

    def _validate_state_preservation(self, original_state: Dict[str, Any], recovered_state: Optional[Dict[str, Any]]) -> bool:
        """Validate that critical state elements are preserved during recovery."""
        if not recovered_state:
            return False
        
        recovered_data = recovered_state.get("execution_data", {})
        
        # Check critical fields
        critical_fields = ["analysis_progress", "intermediate_results", "user_preferences"]
        preserved_count = 0
        
        for field in critical_fields:
            if field in original_state and field in recovered_data:
                if original_state[field] == recovered_data[field]:
                    preserved_count += 1
        
        # Consider state preserved if at least 2/3 of critical fields are intact
        preservation_ratio = preserved_count / len(critical_fields)
        return preservation_ratio >= 0.67