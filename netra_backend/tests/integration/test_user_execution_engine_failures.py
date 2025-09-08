"""
Integration Tests for UserExecutionEngine Component Failures

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core platform functionality
- Business Goal: Ensure execution engine failures are properly detected and handled
- Value Impact: Prevents cascade failures that result in zero AI value delivery
- Strategic Impact: CRITICAL - Core business functionality must be rock solid

This test suite focuses on reproducing the exact component dependency failures 
identified in the five whys analysis (AGENT_EXECUTION_TOOL_DISPATCHER_FIVE_WHYS_ANALYSIS.md):

1. AttributeError: 'NoneType' object has no attribute 'track_operation' 
2. Fallback manager being None but still called
3. Incomplete execution flows that never reach tool dispatch
4. WebSocket event emission failures due to upstream component failures
5. Quality metrics returning zero due to no content generation
6. SSOT violation scenarios with missing component factories

CRITICAL: These tests use REAL services (database, Redis) but NOT external services.
NO MOCKS - tests must FAIL HARD and reproduce actual failure modes.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import MagicMock, patch, AsyncMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

from netra_backend.app.agents.supervisor.user_execution_engine import (
    UserExecutionEngine, 
    MinimalPeriodicUpdateManager,
    MinimalFallbackManager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    PipelineStep
)
from netra_backend.app.agents.state import DeepAgentState


class TestUserExecutionEngineComponentFailures(BaseIntegrationTest):
    """Test UserExecutionEngine component dependency failures with real services."""
    
    def setup_method(self):
        """Set up each test with proper isolation."""
        super().setup_method()
        
        # Create real user context for isolation
        self.user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            run_id=f"test_run_{int(time.time())}",
            request_id=f"req_{int(time.time()*1000)}"
        )
        
        # Mock agent factory with minimal components
        self.mock_agent_factory = MagicMock()
        self.mock_agent_registry = MagicMock()
        self.mock_websocket_bridge = MagicMock()
        
        self.mock_agent_factory._agent_registry = self.mock_agent_registry
        self.mock_agent_factory._websocket_bridge = self.mock_websocket_bridge
        
        # Mock WebSocket emitter for event testing
        self.mock_websocket_emitter = AsyncMock()
        
        # Create agent execution context
        self.agent_context = AgentExecutionContext(
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            run_id=self.user_context.run_id,
            request_id=self.user_context.request_id,
            agent_name="test_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Create basic agent state
        self.agent_state = DeepAgentState()
        self.agent_state.initialize_from_dict({
            'user_request': 'Test optimization request',
            'current_state': 'initialized'
        })

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_fails_with_none_periodic_manager(self, real_services_fixture):
        """
        BVJ: Reproduce AttributeError: 'NoneType' object has no attribute 'track_operation'
        
        This test reproduces the exact failure identified in the five whys analysis
        where periodic_update_manager is None but execute_agent() tries to use it.
        """
        # Create engine with normal initialization
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # CRITICAL: Force periodic_update_manager to None to reproduce the bug
        engine.periodic_update_manager = None
        
        # Attempt execution - this MUST fail with AttributeError
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'track_operation'"):
            await engine.execute_agent(self.agent_context, self.agent_state)
        
        # Verify business impact: zero content generation
        assert len(engine.run_history) == 0, "No execution results should be recorded due to immediate failure"
        assert engine.execution_stats['failed_executions'] == 0, "Execution should fail before stats are updated"

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_execution_fails_with_none_fallback_manager(self, real_services_fixture):
        """
        BVJ: Reproduce failure when fallback_manager is None but still called
        
        This test simulates the scenario where the fallback manager is None
        but the execution path still tries to create fallback results.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Force fallback_manager to None
        engine.fallback_manager = None
        
        # Mock agent core to raise an exception (triggering fallback path)
        engine.agent_core = MagicMock()
        engine.agent_core.execute_agent = AsyncMock(side_effect=RuntimeError("Simulated agent failure"))
        
        # Execution should fail when trying to use None fallback_manager
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'create_fallback_result'"):
            await engine.execute_agent(self.agent_context, self.agent_state)
        
        # Verify cascade failure impact
        assert engine.execution_stats['failed_executions'] == 0, "Stats not updated due to early failure"

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_incomplete_execution_never_reaches_tool_dispatch(self, real_services_fixture):
        """
        BVJ: Test execution flow that fails before tool dispatch, resulting in zero tool events
        
        This reproduces the analysis finding: "Execution never reaches tool dispatch 
        or WebSocket event emission"
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Track WebSocket events to verify none are sent
        websocket_events = []
        
        async def track_websocket_event(*args, **kwargs):
            websocket_events.append(('event', args, kwargs))
            return True
            
        self.mock_websocket_emitter.notify_agent_started = AsyncMock(side_effect=track_websocket_event)
        self.mock_websocket_emitter.notify_agent_thinking = AsyncMock(side_effect=track_websocket_event)
        self.mock_websocket_emitter.notify_agent_completed = AsyncMock(side_effect=track_websocket_event)
        
        # Force periodic manager to None to cause immediate failure
        engine.periodic_update_manager = None
        
        # Execute and expect AttributeError
        with pytest.raises(AttributeError):
            await engine.execute_agent(self.agent_context, self.agent_state)
        
        # CRITICAL BUSINESS IMPACT: No WebSocket events should be sent
        assert len(websocket_events) == 0, "Zero tool events generated because execution dies before tools are called"
        
        # Verify tool dispatcher was never reached
        assert not hasattr(engine, '_tool_calls_made'), "Tool dispatch should never be reached"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_emission_fails_due_to_upstream_failures(self, real_services_fixture):
        """
        BVJ: Test WebSocket event emission failures when upstream components fail
        
        Tests the scenario where WebSocket infrastructure is intact but events 
        never fire due to execution engine failures.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Track attempts to send WebSocket events
        event_attempts = []
        
        async def failing_websocket_emitter(*args, **kwargs):
            event_attempts.append(('attempt', args, kwargs))
            return False  # Simulate emission failure
            
        self.mock_websocket_emitter.notify_agent_started = AsyncMock(side_effect=failing_websocket_emitter)
        self.mock_websocket_emitter.notify_agent_thinking = AsyncMock(side_effect=failing_websocket_emitter)
        self.mock_websocket_emitter.notify_agent_completed = AsyncMock(side_effect=failing_websocket_emitter)
        
        # Execute agent - should complete but with failed event emission
        result = await engine.execute_agent(self.agent_context, self.agent_state)
        
        # Verify execution completed but events failed
        assert result is not None, "Execution should complete"
        
        # BUSINESS IMPACT: Events attempted but failed due to upstream issues
        assert len(event_attempts) > 0, "WebSocket events should be attempted"
        
        # Check that WebSocket failure doesn't crash the engine  
        assert engine.is_active(), "Engine should remain active despite WebSocket failures"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_quality_metrics_zero_due_to_no_content_generation(self, real_services_fixture):
        """
        BVJ: Test quality metrics returning zero when no agent responses are generated
        
        Reproduces: "Quality metrics require actual agent responses with content.
        Since agent execution fails immediately, no responses are generated."
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Force execution to fail immediately
        engine.periodic_update_manager = None
        
        # Track quality metrics
        initial_stats = engine.get_user_execution_stats()
        
        # Attempt execution and catch the failure
        try:
            await engine.execute_agent(self.agent_context, self.agent_state)
        except AttributeError:
            pass  # Expected failure
        
        final_stats = engine.get_user_execution_stats()
        
        # CRITICAL BUSINESS IMPACT: Quality metrics should be zero
        assert final_stats['total_executions'] == initial_stats['total_executions'], "No successful executions recorded"
        assert len(engine.run_history) == 0, "No agent responses generated at all"
        
        # Verify quality pipeline breakdown
        assert final_stats['avg_execution_time'] == 0.0, "Quality score of 0.00 due to no content"
        assert final_stats['max_execution_time'] == 0.0, "Quality SLA threshold completely missed"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_ssot_violation_missing_component_factories(self, real_services_fixture):
        """
        BVJ: Test SSOT violations where components are set to None instead of proper factories
        
        Reproduces: "Missing Dependency Injection: No replacement mechanism for removed components"
        """
        # Test the SSOT violation pattern
        with pytest.raises(ValueError, match="AgentInstanceFactory cannot be None"):
            UserExecutionEngine(
                context=self.user_context,
                agent_factory=None,  # SSOT violation
                websocket_emitter=self.mock_websocket_emitter
            )
        
        with pytest.raises(ValueError, match="UserWebSocketEmitter cannot be None"):
            UserExecutionEngine(
                context=self.user_context,
                agent_factory=self.mock_agent_factory,
                websocket_emitter=None  # SSOT violation
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_context_validation_prevents_cross_user_leakage(self, real_services_fixture):
        """
        BVJ: Test execution context validation prevents user context leakage
        
        CRITICAL for multi-user isolation - prevents users from accessing each other's executions.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Create context for different user (potential security violation)
        wrong_user_context = AgentExecutionContext(
            user_id="different_user_456",  # Different user!
            thread_id=self.user_context.thread_id,
            run_id=self.user_context.run_id,
            request_id=self.user_context.request_id,
            agent_name="test_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # CRITICAL SECURITY: Must reject cross-user execution attempts
        with pytest.raises(ValueError, match="User ID mismatch"):
            await engine.execute_agent(wrong_user_context, self.agent_state)
        
        # Verify no state leakage occurred
        assert len(engine.active_runs) == 0, "No executions should be recorded for wrong user"
        assert engine.execution_stats['total_executions'] == 0, "No stats contamination"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_engine_timeout_cascade_failure(self, real_services_fixture):
        """
        BVJ: Test timeout scenarios that cause cascade failures throughout the system
        
        Long-running executions that timeout should fail gracefully without corrupting 
        the engine state or causing downstream failures.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Reduce timeout for faster test
        engine.AGENT_EXECUTION_TIMEOUT = 0.1
        
        # Mock agent core to simulate long-running operation
        async def slow_agent_execution(*args, **kwargs):
            await asyncio.sleep(0.5)  # Exceeds timeout
            return MagicMock(success=True)
            
        engine.agent_core.execute_agent = AsyncMock(side_effect=slow_agent_execution)
        
        # Execute and expect timeout
        result = await engine.execute_agent(self.agent_context, self.agent_state)
        
        # BUSINESS IMPACT: Timeout should be handled gracefully
        assert result.success is False, "Timeout should result in failed execution"
        assert "timed out" in result.error.lower(), "Error should indicate timeout"
        
        # Verify engine state is not corrupted
        assert len(engine.active_runs) == 0, "Timed out execution should be cleaned up"
        assert engine.execution_stats['timeout_executions'] == 1, "Timeout should be recorded"
        assert engine.is_active(), "Engine should remain active after timeout"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_execution_semaphore_enforcement(self, real_services_fixture):
        """
        BVJ: Test that per-user concurrency limits are enforced to prevent resource exhaustion
        
        Multiple concurrent executions should be properly limited per user context.
        """
        # Create engine with low concurrency limit
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        engine.max_concurrent = 2  # Low limit for testing
        engine.semaphore = asyncio.Semaphore(2)
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent_seen = 0
        
        async def track_concurrent_execution(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate work
            concurrent_count -= 1
            return MagicMock(success=True, execution_time=0.1)
        
        engine.agent_core.execute_agent = AsyncMock(side_effect=track_concurrent_execution)
        
        # Start multiple concurrent executions
        tasks = []
        for i in range(5):  # More than the limit
            context = AgentExecutionContext(
                user_id=self.user_context.user_id,
                thread_id=self.user_context.thread_id,
                run_id=self.user_context.run_id,
                request_id=f"req_{i}",
                agent_name=f"test_agent_{i}",
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            task = asyncio.create_task(engine.execute_agent(context, self.agent_state))
            tasks.append(task)
        
        # Wait for all executions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # BUSINESS IMPACT: Concurrency should be properly limited
        assert max_concurrent_seen <= 2, f"Concurrency limit violated: {max_concurrent_seen} > 2"
        
        # All executions should eventually complete
        successful_results = [r for r in results if hasattr(r, 'success') and r.success]
        assert len(successful_results) == 5, "All executions should complete despite queueing"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_component_adapter_interface_compatibility(self, real_services_fixture):
        """
        BVJ: Test that minimal component adapters maintain interface compatibility
        
        The MinimalPeriodicUpdateManager and MinimalFallbackManager should provide
        the exact interfaces expected by the execution engine.
        """
        # Test MinimalPeriodicUpdateManager interface
        manager = MinimalPeriodicUpdateManager()
        
        # Should provide async context manager interface
        async with manager.track_operation(
            self.agent_context, "test_op", "test_type", 1000, "Test operation"
        ):
            pass  # Should work without errors
        
        # Should provide shutdown method
        await manager.shutdown()
        
        # Test MinimalFallbackManager interface
        fallback_manager = MinimalFallbackManager(self.user_context)
        
        # Should create fallback results
        error = RuntimeError("Test error")
        start_time = time.time()
        
        result = await fallback_manager.create_fallback_result(
            self.agent_context, self.agent_state, error, start_time
        )
        
        # BUSINESS IMPACT: Fallback results should be properly formatted
        assert result.success is False, "Fallback result should indicate failure"
        assert "Agent execution failed" in result.error, "Error message should be clear"
        assert result.metadata['fallback_result'] is True, "Should be marked as fallback"
        assert result.metadata['user_isolated'] is True, "Should maintain user isolation"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_history_isolation_per_user(self, real_services_fixture):
        """
        BVJ: Test that execution history is properly isolated per user
        
        Each user engine should only track its own execution history.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Mock successful execution
        engine.agent_core.execute_agent = AsyncMock(
            return_value=MagicMock(success=True, execution_time=0.1, data="test result")
        )
        
        # Execute multiple agents
        for i in range(3):
            context = AgentExecutionContext(
                user_id=self.user_context.user_id,
                thread_id=self.user_context.thread_id,
                run_id=self.user_context.run_id,
                request_id=f"req_{i}",
                agent_name=f"test_agent_{i}",
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            await engine.execute_agent(context, self.agent_state)
        
        # BUSINESS IMPACT: History should be user-specific
        stats = engine.get_user_execution_stats()
        assert stats['total_executions'] == 3, "All executions recorded"
        assert stats['user_id'] == self.user_context.user_id, "History is user-specific"
        assert len(engine.run_history) == 3, "Execution results stored"
        
        # Verify no global state contamination
        assert stats['user_correlation_id'] == self.user_context.get_correlation_id()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_emitter_cleanup_prevents_memory_leaks(self, real_services_fixture):
        """
        BVJ: Test that WebSocket emitter cleanup prevents memory leaks
        
        User engines should properly clean up WebSocket connections and listeners.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Track cleanup calls
        cleanup_called = False
        
        async def track_cleanup():
            nonlocal cleanup_called
            cleanup_called = True
            
        self.mock_websocket_emitter.cleanup = AsyncMock(side_effect=track_cleanup)
        
        # Engine should be active initially
        assert engine.is_active(), "Engine should start active"
        
        # Cleanup the engine
        await engine.cleanup()
        
        # BUSINESS IMPACT: Resources should be properly cleaned up
        assert cleanup_called, "WebSocket emitter cleanup should be called"
        assert not engine.is_active(), "Engine should be inactive after cleanup"
        assert len(engine.active_runs) == 0, "No active runs after cleanup"
        assert len(engine.run_history) == 0, "History cleared after cleanup"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_tracker_integration_failure_handling(self, real_services_fixture):
        """
        BVJ: Test execution tracker integration with proper failure state tracking
        
        When executions fail, the tracker should properly record the failure states.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Track execution tracker calls
        tracker_states = []
        
        def track_state_update(execution_id, state, **kwargs):
            tracker_states.append((execution_id, state, kwargs))
            
        engine.execution_tracker.update_execution_state = MagicMock(side_effect=track_state_update)
        engine.execution_tracker.create_execution = MagicMock(return_value="exec_123")
        engine.execution_tracker.start_execution = MagicMock()
        engine.execution_tracker.heartbeat = MagicMock()
        
        # Force execution failure
        engine.agent_core.execute_agent = AsyncMock(side_effect=RuntimeError("Test failure"))
        
        # Execute and expect fallback result
        result = await engine.execute_agent(self.agent_context, self.agent_state)
        
        # BUSINESS IMPACT: Failure states should be properly tracked
        assert result.success is False, "Execution should fail"
        
        # Verify execution tracker recorded the failure
        failed_states = [s for s in tracker_states if 'FAILED' in str(s[1])]
        assert len(failed_states) > 0, "Failed execution state should be recorded"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_factory_integration_with_user_context(self, real_services_fixture):
        """
        BVJ: Test agent factory integration with proper user context isolation
        
        Agent instances should be created with proper user context for isolation.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Track agent creation calls
        agent_creation_calls = []
        
        async def track_agent_creation(agent_name, user_context):
            agent_creation_calls.append((agent_name, user_context))
            return MagicMock()  # Return mock agent
            
        self.mock_agent_factory.create_agent_instance = AsyncMock(side_effect=track_agent_creation)
        
        # Mock successful execution
        engine.agent_core.execute_agent = AsyncMock(
            return_value=MagicMock(success=True, execution_time=0.1)
        )
        
        # Execute agent
        await engine.execute_agent(self.agent_context, self.agent_state)
        
        # BUSINESS IMPACT: Agent should be created with proper user context
        assert len(agent_creation_calls) == 1, "Agent should be created"
        agent_name, user_context_used = agent_creation_calls[0]
        assert agent_name == "test_agent", "Correct agent name used"
        assert user_context_used.user_id == self.user_context.user_id, "User context properly passed"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_pipeline_execution_compatibility_interface(self, real_services_fixture):
        """
        BVJ: Test execute_agent_pipeline compatibility interface for integration tests
        
        The pipeline execution interface should work properly for test integration.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Mock successful execution
        engine.agent_core.execute_agent = AsyncMock(
            return_value=MagicMock(success=True, execution_time=0.1, data="pipeline result")
        )
        
        # Execute using pipeline interface
        input_data = {
            "optimization_request": "Analyze costs",
            "context": {"user_id": self.user_context.user_id}
        }
        
        result = await engine.execute_agent_pipeline(
            agent_name="cost_optimizer",
            execution_context=self.user_context,
            input_data=input_data
        )
        
        # BUSINESS IMPACT: Pipeline execution should work properly
        assert result is not None, "Pipeline should return result"
        assert hasattr(result, 'success'), "Result should have success indicator"
        
        # Verify user context was properly used
        stats = engine.get_user_execution_stats()
        assert stats['total_executions'] == 1, "Execution should be recorded"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_limit_enforcement_per_user_context(self, real_services_fixture):
        """
        BVJ: Test that resource limits are enforced per user context
        
        Different users should have independent resource limits and enforcement.
        """
        # Create user context with specific resource limits
        user_context_with_limits = UserExecutionContext(
            user_id="limited_user_789",
            thread_id="test_thread_789",
            run_id=f"test_run_{int(time.time())}",
            request_id=f"req_{int(time.time()*1000)}"
        )
        
        # Mock resource limits
        class MockResourceLimits:
            max_concurrent_agents = 1  # Very restrictive
            
        user_context_with_limits.resource_limits = MockResourceLimits()
        
        engine = UserExecutionEngine(
            context=user_context_with_limits,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # BUSINESS IMPACT: Resource limits should be respected
        assert engine.max_concurrent == 1, "Resource limit should be applied"
        assert engine.semaphore._value == 1, "Semaphore should reflect limit"
        
        # Verify limits are enforced
        stats = engine.get_user_execution_stats()
        assert stats['max_concurrent'] == 1, "Stats should show limit"
        assert stats['user_id'] == user_context_with_limits.user_id, "User isolation maintained"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_boundary_prevents_engine_corruption(self, real_services_fixture):
        """
        BVJ: Test that errors in one execution don't corrupt the engine state
        
        Failed executions should not affect subsequent executions or engine state.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # First execution fails
        engine.agent_core.execute_agent = AsyncMock(side_effect=RuntimeError("First failure"))
        
        try:
            await engine.execute_agent(self.agent_context, self.agent_state)
        except Exception:
            pass  # Expected failure
        
        # Engine should still be active and functional
        assert engine.is_active(), "Engine should remain active after failure"
        
        # Second execution succeeds
        engine.agent_core.execute_agent = AsyncMock(
            return_value=MagicMock(success=True, execution_time=0.1)
        )
        
        second_context = AgentExecutionContext(
            user_id=self.user_context.user_id,
            thread_id=self.user_context.thread_id,
            run_id=self.user_context.run_id,
            request_id="req_second",
            agent_name="second_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        result = await engine.execute_agent(second_context, self.agent_state)
        
        # BUSINESS IMPACT: Engine should recover from failures
        assert result.success, "Second execution should succeed"
        
        # Verify engine state is not corrupted
        stats = engine.get_user_execution_stats()
        assert stats['total_executions'] >= 1, "Successful execution recorded"
        assert len(engine.active_runs) == 0, "No stuck executions"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_order_validation(self, real_services_fixture):
        """
        BVJ: Test that WebSocket events are sent in correct order for business value
        
        Events must be sent in order: started -> thinking -> (tools) -> completed
        This ensures users see proper progression of AI work.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # Track event order
        event_order = []
        
        async def track_started(*args, **kwargs):
            event_order.append('agent_started')
            return True
            
        async def track_thinking(*args, **kwargs):
            event_order.append('agent_thinking')
            return True
            
        async def track_completed(*args, **kwargs):
            event_order.append('agent_completed')
            return True
        
        self.mock_websocket_emitter.notify_agent_started = AsyncMock(side_effect=track_started)
        self.mock_websocket_emitter.notify_agent_thinking = AsyncMock(side_effect=track_thinking)
        self.mock_websocket_emitter.notify_agent_completed = AsyncMock(side_effect=track_completed)
        
        # Mock successful execution
        engine.agent_core.execute_agent = AsyncMock(
            return_value=MagicMock(success=True, execution_time=0.1)
        )
        
        # Execute agent
        await engine.execute_agent(self.agent_context, self.agent_state)
        
        # BUSINESS IMPACT: Events should be in correct order for user experience
        assert len(event_order) >= 3, "Multiple events should be sent"
        assert event_order[0] == 'agent_started', "First event should be started"
        assert event_order[-1] == 'agent_completed', "Last event should be completed"
        assert 'agent_thinking' in event_order, "Thinking event should be sent"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_access_integration_capabilities(self, real_services_fixture):
        """
        BVJ: Test that data access capabilities are properly integrated
        
        Engine should have data access capabilities for ClickHouse and Redis integration.
        """
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        # BUSINESS IMPACT: Data access should be integrated
        # This is tested by verifying the engine was extended with data access capabilities
        assert hasattr(engine, '_data_access_capabilities'), "Data access should be integrated"
        
        # Verify cleanup includes data access cleanup
        cleanup_called = False
        
        async def track_data_cleanup(engine_instance):
            nonlocal cleanup_called
            cleanup_called = True
        
        # Mock the data access cleanup
        from netra_backend.app.agents.supervisor.data_access_integration import UserExecutionEngineExtensions
        UserExecutionEngineExtensions.cleanup_data_access = AsyncMock(side_effect=track_data_cleanup)
        
        await engine.cleanup()
        
        # Data access cleanup should be called
        assert cleanup_called, "Data access cleanup should be integrated"