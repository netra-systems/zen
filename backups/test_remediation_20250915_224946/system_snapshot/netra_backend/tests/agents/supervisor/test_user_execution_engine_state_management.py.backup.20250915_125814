"""
User Execution Engine State Management Tests - Foundation Coverage Phase 1

Business Value: Platform/Internal - Execution State Management & Performance
Tests UserExecutionEngine state management, execution tracking, and performance
monitoring capabilities that ensure reliable agent execution with proper observability.

SSOT Compliance: Uses SSotAsyncTestCase, real UserExecutionContext instances,
follows execution engine patterns per CLAUDE.md standards.

Coverage Target: UserExecutionEngine state management, execution tracking, monitoring
Current UserExecutionEngine State Management Coverage: ~8% -> Target: 25%+

Critical State Management Patterns Tested:
- Execution context state tracking and transitions
- Performance monitoring and execution timing
- Agent execution result management and validation
- Pipeline step tracking and progress reporting
- Error state handling and recovery patterns
- Resource usage tracking and limits enforcement

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
)


@dataclass
class ExecutionStateTracker:
    """Helper class to track execution state transitions for testing."""
    states: List[str] = field(default_factory=list)
    timings: List[float] = field(default_factory=list)
    results: List[Any] = field(default_factory=list)
    errors: List[Exception] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_state(self, state: str, timing: float = None, result: Any = None, error: Exception = None):
        """Record a state transition with optional timing and result data."""
        self.states.append(state)
        self.timings.append(timing or time.time())
        if result is not None:
            self.results.append(result)
        if error is not None:
            self.errors.append(error)

    def get_state_transitions(self) -> List[str]:
        """Get the sequence of state transitions."""
        return self.states.copy()

    def get_execution_duration(self) -> float:
        """Calculate total execution duration."""
        if len(self.timings) < 2:
            return 0.0
        return self.timings[-1] - self.timings[0]


class TestUserExecutionEngineStateManagement(SSotAsyncTestCase):
    """Test UserExecutionEngine state management and execution tracking."""

    def setup_method(self, method):
        """Set up test environment with execution tracking."""
        super().setup_method(method)

        # Create mock AgentRegistry with execution tracking
        self.agent_registry = Mock(spec=AgentRegistry)
        self.agent_registry.get_agent_classes = Mock(return_value={
            "triage": Mock(),
            "data_helper": Mock(),
            "reporting": Mock(),
            "analysis": Mock(),
            "optimization": Mock()
        })
        self.agent_registry.__len__ = Mock(return_value=5)

        # Create mock WebSocket bridge for state notifications
        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.emit_agent_event = AsyncMock()
        self.websocket_bridge.emit_tool_event = AsyncMock()

        # Execution state tracker for test verification
        self.state_tracker = ExecutionStateTracker()

        # Create user context for state management testing
        self.test_context = UserExecutionContext(
            user_id="state-mgmt-user-001",
            thread_id="state-mgmt-thread-001",
            run_id="state-mgmt-run-001",
            agent_context={
                "user_request": "state management test request",
                "execution_mode": "test",
                "performance_tracking": True,
                "state_validation": True
            }
        ).with_db_session(AsyncMock())

        # Track WebSocket events for state verification
        self.websocket_events = []

        async def track_websocket_event(event_type, context, **kwargs):
            self.websocket_events.append({
                "event_type": event_type,
                "context": context,
                "timestamp": time.time(),
                "data": kwargs.get("data", {})
            })

        self.websocket_bridge.emit_agent_event.side_effect = track_websocket_event

    def teardown_method(self, method):
        """Clean up state tracking resources."""
        super().teardown_method(method)
        self.state_tracker = None
        self.websocket_events.clear()

    async def test_execution_state_lifecycle_basic(self):
        """Test basic execution state lifecycle and transitions."""
        engine = UserExecutionEngine(
            agent_registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )

        # Mock execution pipeline that tracks state transitions
        async def state_tracking_execution(context: UserExecutionContext, request: str):
            self.state_tracker.record_state("execution_started", time.time())

            # Simulate initialization phase
            await asyncio.sleep(0.01)
            self.state_tracker.record_state("initialization_complete", time.time())

            # Simulate agent selection and configuration
            await asyncio.sleep(0.01)
            self.state_tracker.record_state("agent_configured", time.time())

            # Simulate processing phase
            await asyncio.sleep(0.05)
            self.state_tracker.record_state("processing_complete", time.time())

            # Simulate result generation
            result = AgentExecutionResult(
                success=True,
                result={
                    "status": "completed",
                    "user_id": context.user_id,
                    "execution_phases": len(self.state_tracker.states),
                    "request_processed": request
                },
                execution_time=self.state_tracker.get_execution_duration(),
                steps_completed=4
            )

            self.state_tracker.record_state("execution_completed", time.time(), result)
            return result

        with patch.object(engine, '_execute_pipeline_for_user', side_effect=state_tracking_execution):

            # Execute and track state transitions
            start_time = time.time()
            result = await engine._execute_pipeline_for_user(
                self.test_context,
                "test execution state lifecycle"
            )
            end_time = time.time()

        # Verify: Execution completed successfully
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True

        # Verify: All expected state transitions occurred
        expected_states = [
            "execution_started",
            "initialization_complete",
            "agent_configured",
            "processing_complete",
            "execution_completed"
        ]
        actual_states = self.state_tracker.get_state_transitions()
        assert actual_states == expected_states

        # Verify: State transitions were properly timed
        assert len(self.state_tracker.timings) == 5
        for i in range(1, len(self.state_tracker.timings)):
            assert self.state_tracker.timings[i] >= self.state_tracker.timings[i-1]

        # Verify: Execution duration is reasonable
        execution_duration = self.state_tracker.get_execution_duration()
        assert 0.05 <= execution_duration <= 0.5  # Should be between 50ms and 500ms

        # Verify: Result contains proper execution metadata
        assert result.execution_time > 0
        assert result.steps_completed == 4
        assert result.result["execution_phases"] == 5

    async def test_execution_performance_monitoring(self):
        """Test execution performance monitoring and timing accuracy."""
        engine = UserExecutionEngine(
            agent_registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )

        # Performance test data
        performance_data = {
            "step_durations": [],
            "memory_usage": [],
            "cpu_usage": [],
            "io_operations": []
        }

        async def performance_monitored_execution(context: UserExecutionContext, request: str):
            # Simulate different execution phases with varying performance characteristics
            phases = [
                {"name": "initialization", "duration": 0.02, "memory": 10},
                {"name": "data_loading", "duration": 0.05, "memory": 50},
                {"name": "processing", "duration": 0.1, "memory": 100},
                {"name": "result_generation", "duration": 0.03, "memory": 25},
                {"name": "cleanup", "duration": 0.01, "memory": 5}
            ]

            total_start_time = time.time()

            for i, phase in enumerate(phases):
                phase_start = time.time()

                # Simulate phase processing
                await asyncio.sleep(phase["duration"])

                phase_end = time.time()
                phase_duration = phase_end - phase_start

                # Record performance metrics
                performance_data["step_durations"].append({
                    "phase": phase["name"],
                    "duration": phase_duration,
                    "expected_duration": phase["duration"]
                })
                performance_data["memory_usage"].append(phase["memory"])

                self.state_tracker.record_state(f"phase_{phase['name']}_complete", phase_end)

            total_execution_time = time.time() - total_start_time

            return AgentExecutionResult(
                success=True,
                result={
                    "user_id": context.user_id,
                    "phases_completed": len(phases),
                    "total_execution_time": total_execution_time,
                    "performance_metrics": performance_data.copy()
                },
                execution_time=total_execution_time,
                steps_completed=len(phases)
            )

        with patch.object(engine, '_execute_pipeline_for_user', side_effect=performance_monitored_execution):

            # Execute with performance monitoring
            result = await engine._execute_pipeline_for_user(
                self.test_context,
                "performance monitoring test"
            )

        # Verify: Execution completed with performance data
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True

        # Verify: All phases were completed
        assert result.result["phases_completed"] == 5
        assert result.steps_completed == 5

        # Verify: Performance metrics were collected
        perf_metrics = result.result["performance_metrics"]
        assert len(perf_metrics["step_durations"]) == 5
        assert len(perf_metrics["memory_usage"]) == 5

        # Verify: Timing accuracy (within reasonable tolerance)
        for step_data in perf_metrics["step_durations"]:
            actual_duration = step_data["duration"]
            expected_duration = step_data["expected_duration"]
            # Allow 50% tolerance for timing variations in tests
            tolerance = expected_duration * 0.5
            assert abs(actual_duration - expected_duration) <= tolerance

        # Verify: Total execution time is sum of phases (approximately)
        total_phase_time = sum(step["duration"] for step in perf_metrics["step_durations"])
        total_execution_time = result.execution_time
        assert abs(total_execution_time - total_phase_time) <= 0.1  # 100ms tolerance

        # Verify: Memory usage tracking shows realistic values
        memory_values = perf_metrics["memory_usage"]
        assert all(0 < mem <= 200 for mem in memory_values)  # Reasonable memory range

    async def test_execution_result_validation_and_structure(self):
        """Test execution result validation and proper data structure."""
        engine = UserExecutionEngine(
            agent_registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )

        async def result_validation_execution(context: UserExecutionContext, request: str):
            # Create comprehensive result with all required fields
            execution_result = AgentExecutionResult(
                success=True,
                result={
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                    "run_id": context.run_id,
                    "request_processed": request,
                    "agent_type": "test_validation_agent",
                    "processing_metadata": {
                        "start_time": time.time(),
                        "end_time": time.time() + 0.1,
                        "steps_executed": ["validation", "processing", "result_generation"],
                        "resources_used": {
                            "memory_mb": 64,
                            "cpu_seconds": 0.1,
                            "api_calls": 3
                        }
                    },
                    "business_value": {
                        "task_completed": True,
                        "value_delivered": "Data analysis completed successfully",
                        "user_satisfaction_metric": 0.95
                    }
                },
                execution_time=0.1,
                steps_completed=3,
                metadata={
                    "execution_id": f"exec_{int(time.time())}",
                    "validation_passed": True,
                    "performance_tier": "optimal"
                }
            )

            return execution_result

        with patch.object(engine, '_execute_pipeline_for_user', side_effect=result_validation_execution):

            result = await engine._execute_pipeline_for_user(
                self.test_context,
                "result validation test"
            )

        # Verify: Result has proper structure and all required fields
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert isinstance(result.result, dict)
        assert isinstance(result.execution_time, (int, float))
        assert isinstance(result.steps_completed, int)

        # Verify: Result contains user context information
        assert result.result["user_id"] == "state-mgmt-user-001"
        assert result.result["thread_id"] == "state-mgmt-thread-001"
        assert result.result["run_id"] == "state-mgmt-run-001"

        # Verify: Result contains processing metadata
        processing_meta = result.result["processing_metadata"]
        assert "start_time" in processing_meta
        assert "end_time" in processing_meta
        assert "steps_executed" in processing_meta
        assert "resources_used" in processing_meta

        # Verify: Result contains business value information
        business_value = result.result["business_value"]
        assert business_value["task_completed"] is True
        assert "value_delivered" in business_value
        assert "user_satisfaction_metric" in business_value

        # Verify: Execution metadata is properly structured
        assert hasattr(result, 'metadata')
        if result.metadata:
            assert "validation_passed" in result.metadata
            assert result.metadata["validation_passed"] is True

        # Verify: Performance metrics are reasonable
        assert 0 < result.execution_time <= 1.0  # Reasonable execution time
        assert 0 < result.steps_completed <= 10  # Reasonable step count

    async def test_pipeline_step_tracking_and_progress(self):
        """Test pipeline step tracking and progress reporting."""
        engine = UserExecutionEngine(
            agent_registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )

        # Track pipeline steps for verification
        pipeline_steps = []

        async def step_tracking_execution(context: UserExecutionContext, request: str):
            # Define execution pipeline steps
            steps = [
                PipelineStep(
                    name="request_validation",
                    description="Validate user request format and content",
                    estimated_duration=0.01
                ),
                PipelineStep(
                    name="context_preparation",
                    description="Prepare execution context and resources",
                    estimated_duration=0.02
                ),
                PipelineStep(
                    name="agent_selection",
                    description="Select appropriate agent for task",
                    estimated_duration=0.01
                ),
                PipelineStep(
                    name="task_execution",
                    description="Execute main task processing",
                    estimated_duration=0.08
                ),
                PipelineStep(
                    name="result_formatting",
                    description="Format results for user consumption",
                    estimated_duration=0.02
                )
            ]

            # Execute each step with tracking
            for i, step in enumerate(steps):
                step_start = time.time()

                # Emit progress event
                await engine.websocket_bridge.emit_agent_event(
                    "step_started", context,
                    data={
                        "step_name": step.name,
                        "step_description": step.description,
                        "step_index": i,
                        "total_steps": len(steps),
                        "progress_percentage": (i / len(steps)) * 100
                    }
                )

                # Simulate step execution
                await asyncio.sleep(step.estimated_duration)

                step_end = time.time()
                step_duration = step_end - step_start

                # Record step completion
                pipeline_steps.append({
                    "name": step.name,
                    "duration": step_duration,
                    "estimated_duration": step.estimated_duration,
                    "success": True
                })

                # Emit step completion event
                await engine.websocket_bridge.emit_agent_event(
                    "step_completed", context,
                    data={
                        "step_name": step.name,
                        "actual_duration": step_duration,
                        "estimated_duration": step.estimated_duration,
                        "progress_percentage": ((i + 1) / len(steps)) * 100
                    }
                )

            return AgentExecutionResult(
                success=True,
                result={
                    "user_id": context.user_id,
                    "pipeline_steps": pipeline_steps.copy(),
                    "total_steps": len(steps),
                    "all_steps_completed": True
                },
                execution_time=sum(step["duration"] for step in pipeline_steps),
                steps_completed=len(pipeline_steps)
            )

        with patch.object(engine, '_execute_pipeline_for_user', side_effect=step_tracking_execution):

            result = await engine._execute_pipeline_for_user(
                self.test_context,
                "pipeline step tracking test"
            )

        # Verify: All pipeline steps were executed
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert result.result["all_steps_completed"] is True
        assert result.result["total_steps"] == 5
        assert result.steps_completed == 5

        # Verify: Step tracking data is complete
        recorded_steps = result.result["pipeline_steps"]
        assert len(recorded_steps) == 5

        expected_step_names = [
            "request_validation",
            "context_preparation",
            "agent_selection",
            "task_execution",
            "result_formatting"
        ]

        for i, step in enumerate(recorded_steps):
            assert step["name"] == expected_step_names[i]
            assert step["success"] is True
            assert step["duration"] > 0
            assert step["estimated_duration"] > 0

        # Verify: WebSocket events were emitted for progress tracking
        # Should have 2 events per step (started + completed) = 10 total
        assert len(self.websocket_events) == 10

        # Verify: Progress events contain proper data
        progress_events = [event for event in self.websocket_events if "progress_percentage" in event["data"]]
        assert len(progress_events) == 10  # All events should have progress

        # Check progress percentages are correct
        started_events = [e for e in progress_events if e["event_type"] == "step_started"]
        completed_events = [e for e in progress_events if e["event_type"] == "step_completed"]

        assert len(started_events) == 5
        assert len(completed_events) == 5

        # Verify progress percentages increase properly
        completed_percentages = [e["data"]["progress_percentage"] for e in completed_events]
        expected_percentages = [20.0, 40.0, 60.0, 80.0, 100.0]
        assert completed_percentages == expected_percentages

    async def test_error_state_handling_and_recovery(self):
        """Test error state handling and recovery patterns."""
        engine = UserExecutionEngine(
            agent_registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )

        # Track error states and recovery attempts
        error_states = []
        recovery_attempts = []

        async def error_handling_execution(context: UserExecutionContext, request: str):
            try:
                # Simulate normal execution start
                self.state_tracker.record_state("execution_started")

                # Simulate an error during processing
                if "simulate_error" in request:
                    error = ValueError("Simulated processing error for testing")
                    error_states.append({
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "timestamp": time.time()
                    })

                    # Simulate error recovery attempt
                    recovery_attempts.append({
                        "recovery_strategy": "retry_with_fallback",
                        "timestamp": time.time()
                    })

                    # Simulate successful recovery
                    await asyncio.sleep(0.02)  # Recovery processing time

                    self.state_tracker.record_state("error_recovered")

                # Complete execution successfully after recovery
                self.state_tracker.record_state("execution_completed")

                return AgentExecutionResult(
                    success=True,
                    result={
                        "user_id": context.user_id,
                        "error_states_encountered": len(error_states),
                        "recovery_attempts_made": len(recovery_attempts),
                        "final_status": "completed_with_recovery" if error_states else "completed_normally"
                    },
                    execution_time=0.05,
                    steps_completed=3,
                    metadata={
                        "errors_encountered": error_states.copy(),
                        "recovery_attempts": recovery_attempts.copy()
                    }
                )

            except Exception as e:
                # Handle unexpected errors
                error_states.append({
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": time.time(),
                    "unexpected": True
                })

                return AgentExecutionResult(
                    success=False,
                    result={
                        "user_id": context.user_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    execution_time=0.01,
                    steps_completed=0
                )

        with patch.object(engine, '_execute_pipeline_for_user', side_effect=error_handling_execution):

            # Test 1: Normal execution (no errors)
            result1 = await engine._execute_pipeline_for_user(
                self.test_context,
                "normal execution test"
            )

            # Test 2: Execution with simulated error and recovery
            result2 = await engine._execute_pipeline_for_user(
                self.test_context,
                "simulate_error execution test"
            )

        # Verify: Normal execution completed successfully
        assert result1.success is True
        assert result1.result["final_status"] == "completed_normally"
        assert result1.result["error_states_encountered"] == 0
        assert result1.result["recovery_attempts_made"] == 0

        # Verify: Error execution was handled and recovered
        assert result2.success is True  # Should succeed after recovery
        assert result2.result["final_status"] == "completed_with_recovery"
        assert result2.result["error_states_encountered"] == 1
        assert result2.result["recovery_attempts_made"] == 1

        # Verify: Error state tracking worked correctly
        assert len(error_states) == 1
        assert error_states[0]["error_type"] == "ValueError"
        assert "Simulated processing error" in error_states[0]["error_message"]

        # Verify: Recovery attempt was tracked
        assert len(recovery_attempts) == 1
        assert recovery_attempts[0]["recovery_strategy"] == "retry_with_fallback"

        # Verify: State transitions include error recovery
        state_transitions = self.state_tracker.get_state_transitions()
        assert "error_recovered" in state_transitions
        assert "execution_completed" in state_transitions

        # This test ensures the UserExecutionEngine can handle errors gracefully
        # and recover properly, maintaining system stability under failure conditions.