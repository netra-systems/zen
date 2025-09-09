"""
Race Condition Tests: Agent Execution State Management

This module tests for race conditions in concurrent agent execution scenarios.
Validates that agent execution state remains consistent under high concurrent load.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure reliable agent execution under concurrent load
- Value Impact: Prevents execution failures, state corruption, and user experience degradation
- Strategic Impact: CRITICAL - Multi-user agent execution is core platform functionality

Test Coverage:
- 50 concurrent agent executions (simulates peak load)
- State isolation between concurrent executions
- Execution tracker race conditions
- Agent registry concurrent access
- WebSocket event emission under load
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState  # DEPRECATED - tests are migrating away
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = central_logger.get_logger(__name__)


class TestAgentExecutionStateRaces(SSotBaseTestCase):
    """Test race conditions in agent execution state management."""
    
    def setup_method(self):
        """Set up test environment with isolated state."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.set("TEST_MODE", "race_condition_testing", source="test")
        
        # Track test execution state
        self.execution_states: Dict[str, str] = {}
        self.state_transitions: List[Dict] = []
        self.race_condition_detections: List[Dict] = []
        
    def teardown_method(self):
        """Clean up test state."""
        self.execution_states.clear()
        self.state_transitions.clear()
        self.race_condition_detections.clear()
        super().teardown_method()
    
    def _create_mock_agent_registry(self) -> Mock:
        """Create mock agent registry for testing."""
        registry = Mock()
        
        # Create mock agent that tracks execution state
        mock_agent = AsyncMock()
        mock_agent.execute = self._create_state_tracking_execute()
        registry.get.return_value = mock_agent
        
        return registry
    
    def _create_state_tracking_execute(self):
        """Create agent execute method that tracks state changes."""
        async def execute(user_execution_context: UserExecutionContext, run_id: str, websocket_enabled: bool = True):
            execution_id = f"exec_{run_id}_{int(time.time() * 1000)}"
            
            # Record execution start
            self._record_state_transition(execution_id, "started")
            
            # Simulate work with potential race condition
            await asyncio.sleep(0.001)  # Tiny delay to create race window
            
            # Check for state corruption during execution
            if execution_id in self.execution_states:
                # Race condition detected - execution ID already exists
                self._detect_race_condition(execution_id, "duplicate_execution_id")
            
            self.execution_states[execution_id] = "executing"
            self._record_state_transition(execution_id, "executing")
            
            # More work simulation
            await asyncio.sleep(0.002)
            
            # Complete execution
            self.execution_states[execution_id] = "completed"
            self._record_state_transition(execution_id, "completed")
            
            return AgentExecutionResult(
                success=True,
                agent_name="test_agent",
                duration=0.003,
                data={"execution_id": execution_id, "result": "success"}
            )
        
        return execute
    
    def _create_mock_websocket_bridge(self) -> Mock:
        """Create mock WebSocket bridge that tracks event ordering."""
        bridge = AsyncMock()
        self.websocket_events: List[Dict] = []
        
        async def track_event(event_type: str, run_id: str, agent_name: str, **kwargs):
            event = {
                "type": event_type,
                "run_id": run_id,
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "kwargs": kwargs
            }
            self.websocket_events.append(event)
            
            # Check for event ordering race conditions
            self._check_event_ordering_races(event)
        
        bridge.notify_agent_started = lambda run_id, agent_name, **kw: track_event("started", run_id, agent_name, **kw)
        bridge.notify_agent_thinking = lambda run_id, agent_name, **kw: track_event("thinking", run_id, agent_name, **kw)
        bridge.notify_agent_completed = lambda run_id, agent_name, **kw: track_event("completed", run_id, agent_name, **kw)
        bridge.notify_agent_error = lambda run_id, agent_name, **kw: track_event("error", run_id, agent_name, **kw)
        
        return bridge
    
    def _record_state_transition(self, execution_id: str, state: str):
        """Record state transition for race condition analysis."""
        transition = {
            "execution_id": execution_id,
            "state": state,
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.state_transitions.append(transition)
    
    def _detect_race_condition(self, execution_id: str, condition_type: str):
        """Record race condition detection."""
        race_condition = {
            "execution_id": execution_id,
            "condition_type": condition_type,
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_condition_detections.append(race_condition)
        logger.warning(f"Race condition detected: {race_condition}")
    
    def _check_event_ordering_races(self, event: Dict):
        """Check for WebSocket event ordering race conditions."""
        run_id = event["run_id"]
        event_type = event["type"]
        
        # Get all events for this run_id
        run_events = [e for e in self.websocket_events if e["run_id"] == run_id]
        
        # Check for invalid event ordering
        if event_type == "completed" and len(run_events) < 2:
            # Completed event without started event - race condition
            self._detect_race_condition(run_id, "missing_started_event")
        elif event_type == "started" and len([e for e in run_events if e["type"] == "started"]) > 1:
            # Multiple started events - race condition
            self._detect_race_condition(run_id, "duplicate_started_event")
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_50_concurrent_agent_executions(self):
        """Test 50 concurrent agent executions for race conditions."""
        # Setup
        registry = self._create_mock_agent_registry()
        websocket_bridge = self._create_mock_websocket_bridge()
        execution_core = AgentExecutionCore(registry, websocket_bridge)
        
        # Create 50 concurrent execution contexts
        contexts = []
        user_execution_contexts = []
        for i in range(50):
            user_id = f"user_{i:03d}"
            run_id = f"run_{i:03d}_{uuid.uuid4().hex[:8]}"
            thread_id = f"thread_{i:03d}"
            
            context = AgentExecutionContext(
                agent_name="test_agent",
                run_id=run_id,
                user_id=user_id,
                thread_id=thread_id,
                retry_count=0,
                max_retries=2
            )
            contexts.append(context)
            
            # CRITICAL SECURITY FIX: Use UserExecutionContext for proper user isolation
            user_execution_context = UserExecutionContext.from_agent_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_context={
                    'agent_name': 'test_agent',
                    'test_scenario': 'race_condition_test',
                    'iteration': i
                },
                audit_metadata={
                    'test_name': 'test_50_concurrent_agent_executions',
                    'execution_number': i,
                    'created_for': 'race_condition_testing'
                }
            )
            user_execution_contexts.append(user_execution_context)
        
        # Execute all agents concurrently
        start_time = time.time()
        
        async def execute_agent(ctx, user_ctx):
            try:
                return await execution_core.execute_agent(ctx, user_ctx)
            except Exception as e:
                logger.error(f"Agent execution failed: {e}")
                return AgentExecutionResult(
                    success=False,
                    agent_name=ctx.agent_name,
                    error=str(e),
                    duration=0.0
                )
        
        # Use asyncio.gather to run all executions concurrently
        results = await asyncio.gather(
            *[execute_agent(ctx, user_ctx) for ctx, user_ctx in zip(contexts, user_execution_contexts)],
            return_exceptions=True
        )
        
        execution_time = time.time() - start_time
        
        # Analyze results for race conditions
        successful_executions = len([r for r in results if isinstance(r, AgentExecutionResult) and r.success])
        failed_executions = len([r for r in results if not isinstance(r, AgentExecutionResult) or not r.success])
        
        # Check for race condition indicators
        unique_execution_ids = set()
        duplicate_execution_ids = []
        
        for result in results:
            if isinstance(result, AgentExecutionResult) and result.data:
                exec_id = result.data.get("execution_id")
                if exec_id:
                    if exec_id in unique_execution_ids:
                        duplicate_execution_ids.append(exec_id)
                    else:
                        unique_execution_ids.add(exec_id)
        
        # Assertions for race condition detection
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected: {self.race_condition_detections}"
        )
        
        assert len(duplicate_execution_ids) == 0, (
            f"Duplicate execution IDs detected: {duplicate_execution_ids}"
        )
        
        # Verify all executions completed successfully
        assert successful_executions == 50, (
            f"Expected 50 successful executions, got {successful_executions}. "
            f"Failed: {failed_executions}. Race conditions may have caused failures."
        )
        
        # Verify reasonable execution time (should be concurrent, not sequential)
        assert execution_time < 5.0, (
            f"Execution took {execution_time:.2f}s, expected < 5s. "
            f"This suggests serialization instead of concurrent execution."
        )
        
        # Verify WebSocket events were sent for all executions
        assert len(self.websocket_events) >= 100, (  # At least 2 events per execution
            f"Expected at least 100 WebSocket events, got {len(self.websocket_events)}. "
            f"Some events may have been lost due to race conditions."
        )
        
        logger.info(
            f"✅ 50 concurrent agent executions completed successfully in {execution_time:.2f}s. "
            f"Success rate: {successful_executions}/50, Events: {len(self.websocket_events)}, "
            f"Race conditions: {len(self.race_condition_detections)}"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_execution_state_isolation(self):
        """Test that execution states remain isolated between concurrent operations."""
        registry = self._create_mock_agent_registry()
        websocket_bridge = self._create_mock_websocket_bridge()
        execution_core = AgentExecutionCore(registry, websocket_bridge)
        
        # Create contexts with overlapping user IDs but different run IDs
        contexts = []
        for i in range(20):
            user_id = f"user_{i % 5}"  # 5 users, 4 runs each
            run_id = f"run_{i}_{uuid.uuid4().hex[:8]}"
            
            context = AgentExecutionContext(
                agent_name="test_agent",
                run_id=run_id,
                user_id=user_id,
                thread_id=f"thread_{i}",
                retry_count=0,
                max_retries=2
            )
            contexts.append(context)
        
        # Execute concurrently with proper UserExecutionContext
        user_execution_contexts = []
        for ctx in contexts:
            user_execution_context = UserExecutionContext.from_agent_execution_context(
                user_id=ctx.user_id,
                thread_id=ctx.thread_id,
                run_id=ctx.run_id,
                agent_context={
                    'agent_name': 'test_agent',
                    'test_scenario': 'state_isolation_test'
                },
                audit_metadata={
                    'test_name': 'test_execution_state_isolation',
                    'created_for': 'race_condition_testing'
                }
            )
            user_execution_contexts.append(user_execution_context)
        
        results = await asyncio.gather(
            *[execution_core.execute_agent(ctx, user_ctx) for ctx, user_ctx in zip(contexts, user_execution_contexts)],
            return_exceptions=True
        )
        
        # Check for state isolation violations
        user_executions = {}
        for ctx, result in zip(contexts, results):
            if ctx.user_id not in user_executions:
                user_executions[ctx.user_id] = []
            user_executions[ctx.user_id].append({
                "run_id": ctx.run_id,
                "result": result,
                "success": isinstance(result, AgentExecutionResult) and result.success
            })
        
        # Verify each user had exactly 4 executions
        for user_id, executions in user_executions.items():
            assert len(executions) == 4, (
                f"User {user_id} should have 4 executions, got {len(executions)}"
            )
            
            # Verify all executions for this user succeeded
            successful = len([e for e in executions if e["success"]])
            assert successful == 4, (
                f"User {user_id} should have 4 successful executions, got {successful}. "
                f"State isolation failure may have caused execution failures."
            )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"State isolation race conditions detected: {self.race_condition_detections}"
        )
        
        logger.info(
            f"✅ Execution state isolation verified: 5 users × 4 executions each = 20 total. "
            f"All executions isolated successfully."
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_execution_tracker_concurrent_access(self):
        """Test execution tracker for race conditions under concurrent access."""
        execution_tracker = get_execution_tracker()
        
        # Create multiple concurrent executions accessing the tracker
        async def create_and_track_execution(index: int):
            try:
                exec_id = execution_tracker.create_execution(
                    agent_name=f"agent_{index}",
                    thread_id=f"thread_{index}",
                    user_id=f"user_{index % 10}",  # 10 users
                    timeout_seconds=30,
                    metadata={"test_index": index}
                )
                
                # Start execution
                execution_tracker.start_execution(exec_id)
                
                # Simulate some work
                await asyncio.sleep(0.001)
                
                # Send heartbeat
                success = execution_tracker.heartbeat(exec_id)
                assert success, f"Heartbeat failed for execution {exec_id}"
                
                # Update state
                execution_tracker.update_execution_state(
                    exec_id, ExecutionState.RUNNING, {"step": "processing"}
                )
                
                await asyncio.sleep(0.001)
                
                # Complete execution
                execution_tracker.update_execution_state(
                    exec_id, ExecutionState.COMPLETED, {"result": "success"}
                )
                
                return {"exec_id": exec_id, "success": True, "index": index}
                
            except Exception as e:
                logger.error(f"Execution tracking failed for index {index}: {e}")
                return {"exec_id": None, "success": False, "index": index, "error": str(e)}
        
        # Run 30 concurrent execution tracking operations
        results = await asyncio.gather(
            *[create_and_track_execution(i) for i in range(30)],
            return_exceptions=True
        )
        
        # Analyze results
        successful_tracks = len([r for r in results if isinstance(r, dict) and r.get("success")])
        failed_tracks = len([r for r in results if not isinstance(r, dict) or not r.get("success")])
        
        # Check for execution ID collisions (race condition indicator)
        exec_ids = [r.get("exec_id") for r in results if isinstance(r, dict) and r.get("exec_id")]
        unique_exec_ids = set(exec_ids)
        
        assert len(exec_ids) == len(unique_exec_ids), (
            f"Execution ID collisions detected: {len(exec_ids)} total IDs, "
            f"{len(unique_exec_ids)} unique IDs. This indicates a race condition in ID generation."
        )
        
        # Verify all tracking operations succeeded
        assert successful_tracks == 30, (
            f"Expected 30 successful execution tracks, got {successful_tracks}. "
            f"Failed: {failed_tracks}. Race conditions may have caused tracking failures."
        )
        
        logger.info(
            f"✅ Execution tracker concurrent access test passed: "
            f"{successful_tracks}/30 successful tracks, {len(unique_exec_ids)} unique execution IDs"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions  
    async def test_websocket_event_emission_races(self):
        """Test WebSocket event emission for race conditions under concurrent load."""
        registry = self._create_mock_agent_registry()
        websocket_bridge = self._create_mock_websocket_bridge()
        execution_core = AgentExecutionCore(registry, websocket_bridge)
        
        # Create 15 concurrent executions
        contexts = []
        states = []
        for i in range(15):
            context = AgentExecutionContext(
                agent_name="test_agent",
                run_id=f"run_{i}_{uuid.uuid4().hex[:6]}",
                user_id=f"user_{i % 5}",  # 5 users
                thread_id=f"thread_{i}",
                retry_count=0,
                max_retries=2
            )
            contexts.append(context)
            
            state = DeepAgentState()
            state.user_id = context.user_id
            state.thread_id = context.thread_id
            states.append(state)
        
        # Execute all concurrently
        await asyncio.gather(
            *[execution_core.execute_agent(ctx, st) for ctx, st in zip(contexts, states)],
            return_exceptions=True
        )
        
        # Analyze WebSocket events for race conditions
        events_by_run = {}
        for event in self.websocket_events:
            run_id = event["run_id"]
            if run_id not in events_by_run:
                events_by_run[run_id] = []
            events_by_run[run_id].append(event)
        
        # Verify each execution had proper event sequence
        for run_id, events in events_by_run.items():
            event_types = [e["type"] for e in events]
            
            # Should have at least started and completed events
            assert "started" in event_types, (
                f"Run {run_id} missing 'started' event. Race condition may have lost event."
            )
            assert "completed" in event_types, (
                f"Run {run_id} missing 'completed' event. Race condition may have lost event."
            )
            
            # Started should come before completed
            started_idx = event_types.index("started")
            completed_idx = event_types.index("completed")
            assert started_idx < completed_idx, (
                f"Run {run_id} has incorrect event order: started at {started_idx}, "
                f"completed at {completed_idx}. Race condition in event emission."
            )
        
        # Check for race condition detections
        assert len(self.race_condition_detections) == 0, (
            f"WebSocket event race conditions detected: {self.race_condition_detections}"
        )
        
        # Verify all 15 runs have events
        assert len(events_by_run) == 15, (
            f"Expected events for 15 runs, got {len(events_by_run)}. "
            f"Missing events may indicate race conditions."
        )
        
        logger.info(
            f"✅ WebSocket event emission race test passed: "
            f"{len(events_by_run)} runs with proper event sequences, "
            f"{len(self.websocket_events)} total events, "
            f"0 race conditions detected"
        )
    
    @pytest.mark.unit
    @pytest.mark.race_conditions
    async def test_timing_anomaly_detection(self):
        """Test for timing anomalies that indicate race conditions."""
        registry = self._create_mock_agent_registry()
        websocket_bridge = self._create_mock_websocket_bridge()
        execution_core = AgentExecutionCore(registry, websocket_bridge)
        
        # Track execution timing
        execution_times = []
        
        async def timed_execution(index: int):
            start_time = time.time()
            
            context = AgentExecutionContext(
                agent_name="test_agent",
                run_id=f"timed_run_{index}",
                user_id=f"user_{index % 3}",
                thread_id=f"thread_{index}",
                retry_count=0,
                max_retries=2
            )
            
            user_execution_context = UserExecutionContext.from_agent_execution_context(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                agent_context={
                    'agent_name': 'test_agent',
                    'test_scenario': 'timing_anomaly_test',
                    'execution_index': index
                },
                audit_metadata={
                    'test_name': 'test_timing_anomaly_detection',
                    'created_for': 'race_condition_testing'
                }
            )
            
            result = await execution_core.execute_agent(context, user_execution_context)
            end_time = time.time()
            
            execution_time = end_time - start_time
            execution_times.append({
                "index": index,
                "time": execution_time,
                "success": isinstance(result, AgentExecutionResult) and result.success
            })
            
            return result
        
        # Run 20 concurrent executions
        await asyncio.gather(
            *[timed_execution(i) for i in range(20)],
            return_exceptions=True
        )
        
        # Analyze timing patterns for anomalies
        times = [et["time"] for et in execution_times if et["success"]]
        
        if len(times) > 0:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            # Check for excessive variation (potential race condition indicator)
            time_variation = max_time - min_time
            assert time_variation < 1.0, (
                f"Excessive timing variation detected: {time_variation:.3f}s "
                f"(min: {min_time:.3f}s, max: {max_time:.3f}s, avg: {avg_time:.3f}s). "
                f"This may indicate resource contention or race conditions."
            )
            
            # Check for unreasonably fast executions (potential skip/corruption)
            fast_executions = [t for t in times if t < 0.001]  # < 1ms
            assert len(fast_executions) == 0, (
                f"Found {len(fast_executions)} unreasonably fast executions (< 1ms). "
                f"This may indicate race conditions causing skipped work."
            )
            
            # Check for unreasonably slow executions (potential deadlock)
            slow_executions = [t for t in times if t > 2.0]  # > 2s
            assert len(slow_executions) == 0, (
                f"Found {len(slow_executions)} unreasonably slow executions (> 2s). "
                f"This may indicate deadlocks or resource contention."
            )
            
            logger.info(
                f"✅ Timing anomaly detection passed: "
                f"{len(times)}/20 successful executions, "
                f"avg time: {avg_time:.3f}s, variation: {time_variation:.3f}s"
            )
        else:
            logger.warning("No successful executions to analyze for timing anomalies")
            assert False, "No successful executions completed - this indicates a critical race condition"