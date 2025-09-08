"""Integration Tests: Agent Failure Recovery and Compensation Patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure system resilience and graceful degradation under failure conditions
- Value Impact: Prevents complete workflow failures from blocking user value delivery
- Strategic Impact: Critical for enterprise-grade reliability and user trust

This test suite validates:
1. Agent failure detection and recovery mechanisms
2. Compensation patterns when agents fail
3. Timeout handling and resource cleanup
4. Retry logic and backoff strategies
5. WebSocket error event emission
6. Workflow continuation after partial failures
7. Dead agent detection and cleanup

CRITICAL: Tests realistic failure scenarios without compromising system stability.
Validates that failures don't cascade or cause resource leaks.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.agent_execution_tracker import ExecutionState
from netra_backend.app.logging_config import central_logger

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

logger = central_logger.get_logger(__name__)


class FailureModeAgent(BaseAgent):
    """Agent that can simulate various failure modes for testing."""
    
    def __init__(self, name: str, llm_manager: LLMManager, failure_mode: str = None):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Failure mode {name} agent")
        self.failure_mode = failure_mode
        self.execution_count = 0
        self.websocket_bridge = None
        self._run_id = None
        self.failure_delay = 0.1  # Delay before failure
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute with configurable failure modes."""
        self.execution_count += 1
        
        # Send started event if WebSocket available
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, f"Starting {self.name} with failure mode: {self.failure_mode or 'none'}"
            )
            
        # Introduce delay before potential failure
        await asyncio.sleep(self.failure_delay)
        
        # Simulate various failure modes
        if self.failure_mode == "immediate_exception":
            raise RuntimeError(f"Immediate failure in {self.name}")
            
        elif self.failure_mode == "timeout":
            # Simulate long-running operation that would timeout
            await asyncio.sleep(10.0)  # Longer than typical timeout
            
        elif self.failure_mode == "silent_failure":
            # Return None (simulates dead agent)
            return None
            
        elif self.failure_mode == "invalid_response":
            # Return invalid response format
            return "invalid_response_string"
            
        elif self.failure_mode == "partial_failure":
            # Execute partially then fail
            await asyncio.sleep(0.05)
            if stream_updates and self.websocket_bridge:
                await self.websocket_bridge.notify_agent_thinking(
                    run_id, self.name, "Partial execution before failure..."
                )
            raise RuntimeError(f"Partial failure in {self.name}")
            
        elif self.failure_mode == "memory_error":
            # Simulate out of memory
            raise MemoryError(f"Simulated memory error in {self.name}")
            
        elif self.failure_mode == "network_error":
            # Simulate network connectivity issue
            raise ConnectionError(f"Simulated network error in {self.name}")
            
        elif self.failure_mode == "intermittent_success":
            # Fail on first attempt, succeed on retry
            if self.execution_count == 1:
                raise RuntimeError(f"First attempt failure in {self.name}")
            
        # Success case
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, f"Completed {self.name} successfully"
            )
            
        return {
            "success": True,
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "failure_mode": self.failure_mode,
            "recovered": self.execution_count > 1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class RecoveryWebSocketManager:
    """WebSocket manager with recovery tracking."""
    
    def __init__(self):
        self.emitted_events = []
        self.error_events = []
        self.recovery_events = []
        
    async def create_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge with recovery tracking."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.emitted_events = []
        
        async def track_emit(event_type, data, **kwargs):
            event = {
                "event_type": event_type,
                "data": data,
                "user_id": user_context.user_id,
                "run_id": user_context.run_id,
                "timestamp": datetime.now(timezone.utc),
                "kwargs": kwargs
            }
            bridge.emitted_events.append(event)
            self.emitted_events.append(event)
            
            # Track specific event types
            if event_type == "agent_error":
                self.error_events.append(event)
            elif event_type == "agent_death":
                self.error_events.append(event)
            elif "recovery" in str(data).lower():
                self.recovery_events.append(event)
                
            return True
        
        # Mock all notification methods with tracking
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            track_emit("agent_started", {"agent_name": agent_name, "context": context or {}}))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, reasoning, step_number=None, progress_percentage=None:
            track_emit("agent_thinking", {"agent_name": agent_name, "reasoning": reasoning, "step_number": step_number}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, execution_time_ms:
            track_emit("agent_completed", {"agent_name": agent_name, "result": result, "execution_time_ms": execution_time_ms}))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda run_id, agent_name, error, error_context=None:
            track_emit("agent_error", {"agent_name": agent_name, "error": str(error), "error_context": error_context}))
        bridge.notify_agent_death = AsyncMock(side_effect=lambda run_id, agent_name, death_type, death_context:
            track_emit("agent_death", {"agent_name": agent_name, "death_type": death_type, "death_context": death_context}))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, parameters:
            track_emit("tool_executing", {"agent_name": agent_name, "tool_name": tool_name, "parameters": parameters}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            track_emit("tool_completed", {"agent_name": agent_name, "tool_name": tool_name, "result": result}))
        
        return bridge


class TestAgentFailureRecoveryIntegration(BaseIntegrationTest):
    """Integration tests for agent failure recovery and compensation."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        self.websocket_manager = RecoveryWebSocketManager()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_manager.initialize = AsyncMock()
        return mock_manager
        
    @pytest.fixture
    async def recovery_user_context(self):
        """Create user context for recovery testing."""
        return UserExecutionContext(
            user_id=f"recovery_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"recovery_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"recovery_run_{uuid.uuid4().hex[:8]}",
            request_id=f"recovery_req_{uuid.uuid4().hex[:8]}",
            metadata={"recovery_test": True}
        )
        
    @pytest.fixture
    async def failure_agents(self, mock_llm_manager):
        """Create agents with different failure modes."""
        return {
            "immediate_fail": FailureModeAgent("immediate_fail", mock_llm_manager, "immediate_exception"),
            "timeout_agent": FailureModeAgent("timeout_agent", mock_llm_manager, "timeout"),
            "silent_fail": FailureModeAgent("silent_fail", mock_llm_manager, "silent_failure"),
            "invalid_response": FailureModeAgent("invalid_response", mock_llm_manager, "invalid_response"),
            "partial_fail": FailureModeAgent("partial_fail", mock_llm_manager, "partial_failure"),
            "memory_fail": FailureModeAgent("memory_fail", mock_llm_manager, "memory_error"),
            "network_fail": FailureModeAgent("network_fail", mock_llm_manager, "network_error"),
            "intermittent": FailureModeAgent("intermittent", mock_llm_manager, "intermittent_success"),
            "working_agent": FailureModeAgent("working_agent", mock_llm_manager, None)  # No failure mode
        }
        
    @pytest.fixture
    async def failure_registry(self, failure_agents):
        """Create registry with failure-mode agents."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: failure_agents.get(name)
        registry.get_async = AsyncMock(side_effect=lambda name, context=None: failure_agents.get(name))
        registry.list_keys = lambda: list(failure_agents.keys())
        return registry

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_immediate_exception_recovery(
        self, recovery_user_context, failure_registry, failure_agents, mock_llm_manager
    ):
        """Test recovery from immediate agent exceptions."""
        
        # Business Value: Exception recovery prevents complete workflow failure
        
        websocket_bridge = await self.websocket_manager.create_bridge(recovery_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=failure_registry,
            websocket_bridge=websocket_bridge,
            user_context=recovery_user_context
        )
        
        # Create execution context for failing agent
        context = AgentExecutionContext(
            user_id=recovery_user_context.user_id,
            thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            request_id=recovery_user_context.request_id,
            agent_name="immediate_fail",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            max_retries=2  # Allow retries
        )
        
        state = DeepAgentState(
            user_request={"message": "Test immediate failure recovery"},
            user_id=recovery_user_context.user_id,
            chat_thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            agent_input={"test": "immediate_exception"}
        )
        
        # Execute agent (should handle failure gracefully)
        start_time = time.time()
        result = await engine.execute_agent(context, recovery_user_context)
        execution_time = time.time() - start_time
        
        # Validate failure was handled
        assert result is not None
        assert result.success is False
        assert "Immediate failure" in result.error or "immediate" in result.error.lower()
        assert execution_time < 2.0  # Should fail fast
        
        # Validate WebSocket error events were sent
        error_events = self.websocket_manager.error_events
        assert len(error_events) > 0
        
        error_event = error_events[0]
        assert error_event["data"]["agent_name"] == "immediate_fail"
        assert "failure" in error_event["data"]["error"].lower()
        
        # Validate agent execution was tracked
        failing_agent = failure_agents["immediate_fail"]
        assert failing_agent.execution_count >= 1  # Attempted at least once
        
        # Validate execution stats
        stats = await engine.get_execution_stats()
        assert stats["failed_executions"] > 0
        
        logger.info(f"✅ Immediate exception recovery test passed in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_timeout_handling(
        self, recovery_user_context, failure_registry, failure_agents, mock_llm_manager
    ):
        """Test agent timeout detection and cleanup."""
        
        # Business Value: Timeout handling prevents hung agents from blocking users
        
        websocket_bridge = await self.websocket_manager.create_bridge(recovery_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=failure_registry,
            websocket_bridge=websocket_bridge,
            user_context=recovery_user_context
        )
        
        # Set short timeout for testing
        engine.AGENT_EXECUTION_TIMEOUT = 0.5  # 500ms timeout
        
        context = AgentExecutionContext(
            user_id=recovery_user_context.user_id,
            thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            request_id=recovery_user_context.request_id,
            agent_name="timeout_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        state = DeepAgentState(
            user_request={"message": "Test timeout handling"},
            user_id=recovery_user_context.user_id,
            chat_thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            agent_input={"test": "timeout"}
        )
        
        # Execute agent (should timeout)
        start_time = time.time()
        result = await engine.execute_agent(context, recovery_user_context)
        execution_time = time.time() - start_time
        
        # Validate timeout was handled
        assert result is not None
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert execution_time < 1.0  # Should timeout quickly
        
        # Validate timeout events
        timeout_events = [e for e in self.websocket_manager.emitted_events 
                         if "timeout" in str(e.get("data", {})).lower()]
        assert len(timeout_events) > 0
        
        # Validate execution stats
        stats = await engine.get_execution_stats()
        assert stats["timeout_executions"] > 0
        
        logger.info(f"✅ Agent timeout handling test passed in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_silent_failure_detection(
        self, recovery_user_context, failure_registry, failure_agents, mock_llm_manager
    ):
        """Test detection of silent agent failures (returning None)."""
        
        # Business Value: Silent failure detection prevents hanging user sessions
        
        websocket_bridge = await self.websocket_manager.create_bridge(recovery_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=failure_registry,
            websocket_bridge=websocket_bridge,
            user_context=recovery_user_context
        )
        
        context = AgentExecutionContext(
            user_id=recovery_user_context.user_id,
            thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            request_id=recovery_user_context.request_id,
            agent_name="silent_fail",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        state = DeepAgentState(
            user_request={"message": "Test silent failure detection"},
            user_id=recovery_user_context.user_id,
            chat_thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            agent_input={"test": "silent_failure"}
        )
        
        # Execute agent (should detect silent failure)
        result = await engine.execute_agent(context, recovery_user_context)
        
        # Validate silent failure was detected
        assert result is not None
        assert result.success is False
        assert "died silently" in result.error or "None" in result.error
        
        # Validate death detection events
        death_events = [e for e in self.websocket_manager.error_events 
                       if e["event_type"] == "agent_death" or "death" in str(e)]
        
        # May not have death events for None return, but should have error events
        error_events = [e for e in self.websocket_manager.error_events 
                       if "silent" in str(e.get("data", {})).lower()]
        assert len(error_events) > 0 or len(death_events) > 0
        
        logger.info("✅ Silent failure detection test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_retry_logic_with_backoff(
        self, recovery_user_context, failure_registry, failure_agents, mock_llm_manager
    ):
        """Test agent retry logic with exponential backoff."""
        
        # Business Value: Retry logic improves success rates for transient failures
        
        websocket_bridge = await self.websocket_manager.create_bridge(recovery_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=failure_registry,
            websocket_bridge=websocket_bridge,
            user_context=recovery_user_context
        )
        
        context = AgentExecutionContext(
            user_id=recovery_user_context.user_id,
            thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            request_id=recovery_user_context.request_id,
            agent_name="intermittent",  # Fails first time, succeeds on retry
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            max_retries=3
        )
        
        state = DeepAgentState(
            user_request={"message": "Test retry logic"},
            user_id=recovery_user_context.user_id,
            chat_thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            agent_input={"test": "intermittent_success"}
        )
        
        # Execute agent (should succeed on retry)
        start_time = time.time()
        result = await engine.execute_agent(context, recovery_user_context)
        execution_time = time.time() - start_time
        
        # Validate retry succeeded
        assert result is not None
        assert result.success is True  # Should succeed after retry
        assert result.agent_name == "intermittent"
        
        # Validate agent was executed multiple times
        intermittent_agent = failure_agents["intermittent"]
        assert intermittent_agent.execution_count >= 2  # First failure + retry
        
        # Should see recovery in the result
        assert "recovered" in result.data or result.metadata.get("recovered", False)
        
        # Validate retry events in WebSocket
        retry_events = [e for e in self.websocket_manager.emitted_events 
                       if "retry" in str(e.get("data", {})).lower()]
        
        # May have retry events or success after failure
        thinking_events = [e for e in self.websocket_manager.emitted_events 
                          if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) >= 2  # Should have multiple thinking events
        
        logger.info(f"✅ Retry logic with backoff test passed in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_workflow_compensation_after_failure(
        self, recovery_user_context, failure_registry, failure_agents, mock_llm_manager
    ):
        """Test workflow continues with compensation after agent failure."""
        
        # Business Value: Compensation patterns ensure partial value delivery
        
        websocket_bridge = await self.websocket_manager.create_bridge(recovery_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=failure_registry,
            websocket_bridge=websocket_bridge,
            user_context=recovery_user_context
        )
        
        # Create pipeline with failing and compensating agents
        pipeline_steps = [
            PipelineStep(
                agent_name="working_agent",  # Should succeed
                strategy=None,
                metadata={"continue_on_error": True}
            ),
            PipelineStep(
                agent_name="immediate_fail",  # Will fail
                strategy=None,
                metadata={"continue_on_error": True}
            ),
            PipelineStep(
                agent_name="working_agent",  # Compensation - should still run
                strategy=None, 
                metadata={"continue_on_error": True, "compensation": True}
            )
        ]
        
        base_context = AgentExecutionContext(
            user_id=recovery_user_context.user_id,
            thread_id=recovery_user_context.thread_id,
            run_id=recovery_user_context.run_id,
            request_id=recovery_user_context.request_id,
            agent_name="compensation_workflow",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=0
        )
        
        # Execute pipeline with compensation
        results = await engine.execute_pipeline(
            steps=pipeline_steps,
            context=base_context,
            user_context=recovery_user_context
        )
        
        # Validate compensation workflow
        assert len(results) == 3
        
        # First agent should succeed
        assert results[0].success is True
        assert results[0].agent_name == "working_agent"
        
        # Second agent should fail
        assert results[1].success is False
        assert results[1].agent_name == "immediate_fail"
        
        # Third agent (compensation) should succeed
        assert results[2].success is True
        assert results[2].agent_name == "working_agent"
        
        # Validate working agent executed multiple times (original + compensation)
        working_agent = failure_agents["working_agent"]
        assert working_agent.execution_count >= 2
        
        # Validate compensation events
        completed_events = [e for e in self.websocket_manager.emitted_events
                           if e["event_type"] == "agent_completed"]
        assert len(completed_events) >= 2  # At least 2 completions (working agents)
        
        logger.info("✅ Workflow compensation after failure test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_cleanup_after_failures(
        self, recovery_user_context, failure_registry, failure_agents, mock_llm_manager
    ):
        """Test proper resource cleanup after various failure modes."""
        
        # Business Value: Resource cleanup prevents memory leaks in production
        
        websocket_bridge = await self.websocket_manager.create_bridge(recovery_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=failure_registry,
            websocket_bridge=websocket_bridge,
            user_context=recovery_user_context
        )
        
        # Test multiple failure modes
        failure_agents_to_test = ["immediate_fail", "partial_fail", "memory_fail", "network_fail"]
        
        initial_stats = await engine.get_execution_stats()
        initial_active_runs = len(engine.active_runs)
        
        # Execute each failing agent
        for agent_name in failure_agents_to_test:
            context = AgentExecutionContext(
                user_id=recovery_user_context.user_id,
                thread_id=recovery_user_context.thread_id,
                run_id=f"{recovery_user_context.run_id}_{agent_name}",
                request_id=f"{recovery_user_context.request_id}_{agent_name}",
                agent_name=agent_name,
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            state = DeepAgentState(
                user_request={"message": f"Test {agent_name} cleanup"},
                user_id=recovery_user_context.user_id,
                chat_thread_id=recovery_user_context.thread_id,
                run_id=context.run_id,
                agent_input={"test": agent_name}
            )
            
            # Execute failing agent
            result = await engine.execute_agent(context, recovery_user_context)
            
            # Should fail but not crash
            assert result is not None
            assert result.success is False
            
            # Check resource cleanup after each failure
            current_active_runs = len(engine.active_runs)
            assert current_active_runs == initial_active_runs  # Should be cleaned up
        
        # Final resource check
        final_stats = await engine.get_execution_stats()
        
        # Should have no active runs
        assert len(engine.active_runs) == initial_active_runs
        assert final_stats["concurrent_executions"] == 0
        
        # Should have tracked all failures
        assert final_stats["failed_executions"] > initial_stats["failed_executions"]
        assert final_stats["total_executions"] > initial_stats["total_executions"]
        
        # Test engine shutdown cleanup
        await engine.shutdown()
        assert len(engine.active_runs) == 0
        
        logger.info("✅ Resource cleanup after failures test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_failure_isolation(
        self, failure_registry, failure_agents, mock_llm_manager
    ):
        """Test that concurrent agent failures don't interfere with each other."""
        
        # Business Value: Failure isolation prevents cascade failures
        
        # Create multiple user contexts for concurrent testing
        user_contexts = []
        engines = []
        
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"concurrent_failure_user_{i}",
                thread_id=f"concurrent_failure_thread_{i}",
                run_id=f"concurrent_failure_run_{i}",
                request_id=f"concurrent_failure_req_{i}",
                metadata={"concurrent_failure_test": i}
            )
            user_contexts.append(context)
            
            websocket_bridge = await self.websocket_manager.create_bridge(context)
            engine = ExecutionEngine._init_from_factory(
                registry=failure_registry,
                websocket_bridge=websocket_bridge,
                user_context=context
            )
            engines.append(engine)
        
        # Define different failure scenarios for each user
        failure_scenarios = ["immediate_fail", "timeout_agent", "working_agent"]
        
        async def run_failure_scenario(user_index, context, engine, failure_agent):
            """Run failure scenario for specific user."""
            exec_context = AgentExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                request_id=context.request_id,
                agent_name=failure_agent,
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            # Set short timeout for timeout test
            if failure_agent == "timeout_agent":
                engine.AGENT_EXECUTION_TIMEOUT = 0.3
            
            state = DeepAgentState(
                user_request={"message": f"Concurrent failure test {user_index}"},
                user_id=context.user_id,
                chat_thread_id=context.thread_id,
                run_id=context.run_id,
                agent_input={"concurrent_test": user_index}
            )
            
            result = await engine.execute_agent(exec_context, context)
            return {"user_id": context.user_id, "result": result, "scenario": failure_agent}
        
        # Execute scenarios concurrently
        tasks = []
        for i, (context, engine) in enumerate(zip(user_contexts, engines)):
            task = run_failure_scenario(i, context, engine, failure_scenarios[i])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate concurrent failure isolation
        assert len(results) == 3
        
        # Validate results by scenario
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Scenario {i} raised exception: {result}"
            
            scenario = failure_scenarios[i]
            if scenario == "working_agent":
                assert result["result"].success is True
            else:
                assert result["result"].success is False
                
        # Validate failure isolation - each engine should have independent stats
        for i, engine in enumerate(engines):
            stats = await engine.get_execution_stats()
            
            if failure_scenarios[i] == "working_agent":
                # Working agent should have no failures
                assert stats["failed_executions"] == 0
            else:
                # Failing agents should have exactly 1 failure each
                assert stats["failed_executions"] > 0
                assert stats["total_executions"] > 0
                
        logger.info("✅ Concurrent failure isolation test passed")


if __name__ == "__main__":
    # Run specific test for development
    pytest.main([__file__, "-v", "-s"])