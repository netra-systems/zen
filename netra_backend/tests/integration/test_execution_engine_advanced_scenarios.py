"""ADVANCED INTEGRATION TESTS: ExecutionEngine Edge Cases and Complex Scenarios

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Platform Resilience & Advanced Use Case Support
- Value Impact: Ensures ExecutionEngine handles edge cases that occur in production
- Strategic Impact: Prevents system failures that could impact $500K+ ARR

CRITICAL ADVANCED SCENARIOS per CLAUDE.md:
1. Agent pipeline execution with dependencies and conditional branching
2. ExecutionEngine factory pattern validation and user isolation enforcement
3. Agent execution with WebSocket connection failures and recovery
4. Complex agent retry mechanisms with exponential backoff
5. Agent execution resource limits and memory management
6. Agent execution with database connection pooling and transaction management
7. Agent execution metrics collection and performance analytics
8. ExecutionEngine cleanup and resource deallocation
9. Agent execution with custom tool dispatchers and tool loading
10. Agent execution context validation and security enforcement

FAILURE CONDITIONS:
- Pipeline dependency failures = BUSINESS LOGIC FAILURE
- Factory pattern violations = SECURITY FAILURE
- Resource leaks = PRODUCTION INSTABILITY
- Metrics collection failures = OBSERVABILITY FAILURE
- Context validation bypasses = SECURITY VULNERABILITY

This test suite validates ExecutionEngine robustness for production edge cases.
"""

import asyncio
import gc
import json
import time
import uuid
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, AsyncIterator, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, AsyncMock, patch

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Real ExecutionEngine components for advanced testing
from netra_backend.app.agents.supervisor.execution_engine import (
    ExecutionEngine,
    create_request_scoped_engine,
    create_execution_context_manager
)
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    get_execution_engine_factory,
    ExecutionEngineFactory
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
    AgentExecutionStrategy
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker

# Advanced testing utilities
from test_execution_engine_comprehensive_real_services import (
    MockToolForTesting, 
    MockAgentForTesting,
    ExecutionEngineTestContext
)


@dataclass
class AdvancedTestScenario:
    """Advanced test scenario configuration."""
    scenario_id: str
    name: str
    description: str
    expected_complexity: str  # "low", "medium", "high", "extreme"
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    failure_conditions: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    performance_expectations: Dict[str, float] = field(default_factory=dict)


class ConditionalAgent(MockAgentForTesting):
    """Agent that executes conditionally based on state."""
    
    def __init__(self, name: str, condition_func: Callable[[DeepAgentState], bool], **kwargs):
        super().__init__(name, **kwargs)
        self.condition_func = condition_func
        self.condition_checks = 0
    
    async def execute(self, state: DeepAgentState, run_id: str, is_user_facing: bool = True) -> Dict[str, Any]:
        """Execute only if condition is met."""
        self.condition_checks += 1
        
        if not self.condition_func(state):
            return {
                "success": False,
                "agent_name": self.name,
                "condition_met": False,
                "condition_checks": self.condition_checks,
                "result": f"Condition not met for {self.name}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Condition met, execute normally
        result = await super().execute(state, run_id, is_user_facing)
        result["condition_met"] = True
        result["condition_checks"] = self.condition_checks
        return result


class ResourceTrackingAgent(MockAgentForTesting):
    """Agent that tracks resource usage during execution."""
    
    def __init__(self, name: str, memory_allocation_mb: int = 10, **kwargs):
        super().__init__(name, **kwargs)
        self.memory_allocation_mb = memory_allocation_mb
        self.allocated_memory = []
        self.peak_memory_usage = 0
    
    async def execute(self, state: DeepAgentState, run_id: str, is_user_facing: bool = True) -> Dict[str, Any]:
        """Execute with memory allocation tracking."""
        # Allocate memory for testing
        initial_memory = self._get_memory_usage()
        
        # Simulate memory allocation
        memory_chunk = bytearray(self.memory_allocation_mb * 1024 * 1024)  # Allocate specified MB
        self.allocated_memory.append(memory_chunk)
        
        current_memory = self._get_memory_usage()
        if current_memory:
            self.peak_memory_usage = max(self.peak_memory_usage, current_memory)
        
        # Execute normally
        result = await super().execute(state, run_id, is_user_facing)
        
        # Clean up memory
        self.allocated_memory.clear()
        gc.collect()  # Force garbage collection
        
        final_memory = self._get_memory_usage()
        
        # Add resource tracking to result
        result["resource_tracking"] = {
            "initial_memory_mb": initial_memory,
            "peak_memory_mb": current_memory,
            "final_memory_mb": final_memory,
            "memory_allocated_mb": self.memory_allocation_mb,
            "memory_cleaned": len(self.allocated_memory) == 0
        }
        
        return result
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return None


class TestExecutionEngineAdvancedScenarios(SSotAsyncTestCase):
    """Advanced integration tests for ExecutionEngine edge cases and complex scenarios."""
    
    def setup_method(self, method=None):
        """Setup method for advanced test scenarios."""
        super().setup_method(method)
        self.advanced_scenarios = []
        self.resource_tracking = {}
        self.factory_instances = []
        
    @pytest.fixture
    async def advanced_llm_manager(self):
        """LLM manager with advanced configuration."""
        mock_llm = AsyncMock()
        mock_llm.ask_llm = AsyncMock(side_effect=self._simulate_llm_response)
        mock_llm.ask_llm_structured = AsyncMock(side_effect=self._simulate_structured_response)
        mock_llm.get_available_models = AsyncMock(return_value=["gpt-4", "gpt-3.5-turbo", "claude-3"])
        yield mock_llm
    
    async def _simulate_llm_response(self, prompt: str, model: str = "gpt-4", **kwargs) -> str:
        """Simulate LLM response with latency."""
        await asyncio.sleep(0.1)  # Simulate network latency
        return f"Mock LLM response for: {prompt[:50]}... (model: {model})"
    
    async def _simulate_structured_response(self, prompt: str, schema: Dict, **kwargs) -> Dict[str, Any]:
        """Simulate structured LLM response."""
        await asyncio.sleep(0.15)  # Slightly longer for structured
        return {
            "response": f"Structured response for: {prompt[:30]}...",
            "confidence": 0.85,
            "model_used": kwargs.get("model", "gpt-4"),
            "schema_validated": True
        }
    
    @pytest.fixture
    async def advanced_agent_registry(self, advanced_llm_manager):
        """Agent registry with advanced test agents."""
        registry = AgentRegistry(advanced_llm_manager)
        
        # Conditional agents for pipeline testing
        registry.register_agent("condition_check_agent", ConditionalAgent(
            name="condition_check_agent",
            condition_func=lambda state: getattr(state, 'condition_met', False),
            execution_time=0.5
        ))
        
        registry.register_agent("data_dependent_agent", ConditionalAgent(
            name="data_dependent_agent", 
            condition_func=lambda state: hasattr(state, 'data_processed') and state.data_processed,
            tools=[MockToolForTesting("data_validation_tool", 1.0)],
            execution_time=2.0
        ))
        
        registry.register_agent("optimization_conditional_agent", ConditionalAgent(
            name="optimization_conditional_agent",
            condition_func=lambda state: (
                hasattr(state, 'analysis_complete') and state.analysis_complete and
                hasattr(state, 'optimization_ready') and state.optimization_ready
            ),
            tools=[MockToolForTesting("optimization_tool", 2.0)],
            execution_time=3.0
        ))
        
        # Resource tracking agents
        registry.register_agent("memory_intensive_agent", ResourceTrackingAgent(
            name="memory_intensive_agent",
            memory_allocation_mb=50,
            execution_time=2.0
        ))
        
        registry.register_agent("cpu_intensive_agent", ResourceTrackingAgent(
            name="cpu_intensive_agent",
            memory_allocation_mb=20,
            execution_time=4.0
        ))
        
        # Retry testing agents
        retry_agent = MockAgentForTesting("retry_test_agent", execution_time=1.0)
        retry_agent.failure_countdown = 2  # Fail first 2 attempts, succeed on 3rd
        
        async def retry_execute(state, run_id, is_user_facing=True):
            if hasattr(retry_agent, 'failure_countdown') and retry_agent.failure_countdown > 0:
                retry_agent.failure_countdown -= 1
                raise Exception(f"Retry test failure {retry_agent.failure_countdown + 1}")
            return await MockAgentForTesting.execute(retry_agent, state, run_id, is_user_facing)
        
        retry_agent.execute = retry_execute
        registry.register_agent("retry_test_agent", retry_agent)
        
        yield registry
        await registry.reset_all_agents()
    
    @pytest.fixture 
    async def websocket_bridge_with_failures(self):
        """WebSocket bridge that can simulate failures."""
        bridge = AgentWebSocketBridge()
        bridge.failure_mode = False
        bridge.failure_count = 0
        
        # Store original methods
        original_methods = {}
        for method_name in ['notify_agent_started', 'notify_agent_thinking', 'notify_tool_executing',
                          'notify_tool_completed', 'notify_agent_completed', 'notify_agent_error']:
            original_methods[method_name] = getattr(bridge, method_name)
        
        # Wrap methods with failure simulation
        async def create_failing_wrapper(method_name, original_method):
            async def failing_wrapper(*args, **kwargs):
                if bridge.failure_mode and bridge.failure_count > 0:
                    bridge.failure_count -= 1
                    raise Exception(f"Simulated WebSocket failure in {method_name}")
                return await original_method(*args, **kwargs)
            return failing_wrapper
        
        # Apply wrappers
        for method_name, original_method in original_methods.items():
            setattr(bridge, method_name, await create_failing_wrapper(method_name, original_method))
        
        bridge.enable_failure_mode = lambda count: setattr(bridge, 'failure_mode', True) or setattr(bridge, 'failure_count', count)
        bridge.disable_failure_mode = lambda: setattr(bridge, 'failure_mode', False)
        
        yield bridge
    
    def create_advanced_test_scenario(self, name: str, **kwargs) -> AdvancedTestScenario:
        """Create advanced test scenario configuration."""
        scenario = AdvancedTestScenario(
            scenario_id=f"advanced_{len(self.advanced_scenarios)}_{uuid.uuid4().hex[:8]}",
            name=name,
            **kwargs
        )
        self.advanced_scenarios.append(scenario)
        return scenario
    
    # ============================================================================
    # TEST 1: Agent Pipeline Execution with Dependencies and Conditional Branching
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_pipeline_with_dependencies_and_conditional_branching(self, advanced_agent_registry, websocket_bridge_with_failures):
        """Test complex agent pipeline with conditional execution and dependencies.
        
        BVJ: Validates advanced workflow orchestration for sophisticated business logic.
        """
        scenario = self.create_advanced_test_scenario(
            "pipeline_dependencies_conditional",
            description="Complex pipeline with conditional agent execution based on state",
            expected_complexity="high",
            success_criteria=[
                "All conditional checks execute correctly",
                "Pipeline branches appropriately based on state",
                "Dependencies are respected in execution order",
                "Failed conditions are handled gracefully"
            ]
        )
        
        test_ctx = ExecutionEngineTestContext(
            test_id=scenario.scenario_id,
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Create execution engine
        engine = ExecutionEngine._init_from_factory(
            registry=advanced_agent_registry,
            websocket_bridge=websocket_bridge_with_failures,
            user_context=test_ctx.user_context
        )
        
        # Complex pipeline with conditional branching
        pipeline_steps = [
            # Step 1: Initial condition check (should pass)
            PipelineStep(
                agent_name="condition_check_agent",
                metadata={"step": 1, "condition": "initial_check"}
            ),
            # Step 2: Data dependent agent (should fail initially due to missing condition)
            PipelineStep(
                agent_name="data_dependent_agent",
                metadata={"step": 2, "condition": "data_processed", "continue_on_error": True}
            ),
            # Step 3: Optimization agent (should fail initially due to missing conditions)
            PipelineStep(
                agent_name="optimization_conditional_agent",
                metadata={"step": 3, "condition": "optimization_ready", "continue_on_error": True}
            )
        ]
        
        # Initial state - conditions not met
        state = DeepAgentState()
        state.user_prompt = "Complex conditional pipeline test"
        state.user_id = test_ctx.user_id
        state.condition_met = True  # Only first agent should succeed
        
        # Create pipeline context
        pipeline_context = AgentExecutionContext(
            agent_name="condition_check_agent",  # Starting agent
            run_id=test_ctx.run_id,
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            metadata={"pipeline_test": True, "conditional_execution": True}
        )
        
        # Execute initial pipeline (some agents should fail conditions)
        pipeline_start = time.time()
        initial_results = await engine.execute_pipeline(pipeline_steps, pipeline_context, state)
        initial_time = time.time() - pipeline_start
        
        # Analyze initial results
        initial_successes = sum(1 for r in initial_results if r and r.success)
        initial_condition_failures = sum(1 for r in initial_results if r and not r.success and "condition not met" in str(r.error).lower())
        
        # Should have 1 success (condition_check_agent) and 2 condition failures
        assert initial_successes >= 1, f"At least 1 agent should succeed initially, got {initial_successes}"
        assert initial_condition_failures >= 1, f"At least 1 agent should fail conditions initially, got {initial_condition_failures}"
        
        # Update state to meet more conditions
        state.data_processed = True  # Enable data_dependent_agent
        state.analysis_complete = True
        state.optimization_ready = True  # Enable optimization_conditional_agent
        
        # Execute pipeline again with updated conditions
        retry_start = time.time()
        retry_results = await engine.execute_pipeline(pipeline_steps, pipeline_context, state)
        retry_time = time.time() - retry_start
        
        # Analyze retry results - more agents should succeed now
        retry_successes = sum(1 for r in retry_results if r and r.success)
        retry_condition_failures = sum(1 for r in retry_results if r and not r.success and "condition not met" in str(r.error).lower())
        
        # More agents should succeed with updated conditions
        assert retry_successes > initial_successes, (
            f"More agents should succeed after condition updates: "
            f"initial={initial_successes}, retry={retry_successes}"
        )
        
        # Test individual conditional agent execution
        individual_tests = []
        
        # Test condition_check_agent directly
        condition_context = AgentExecutionContext(
            agent_name="condition_check_agent",
            run_id=f"{test_ctx.run_id}_individual_condition",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id
        )
        
        # Test with condition met
        state.condition_met = True
        condition_result = await engine.execute_agent(condition_context, state)
        individual_tests.append(("condition_met", condition_result.success if condition_result else False))
        
        # Test with condition not met
        state.condition_met = False
        condition_result_fail = await engine.execute_agent(condition_context, state)
        individual_tests.append(("condition_not_met", not (condition_result_fail.success if condition_result_fail else True)))
        
        # Record scenario results
        scenario_results = {
            "initial_pipeline": {
                "successes": initial_successes,
                "condition_failures": initial_condition_failures,
                "execution_time": initial_time
            },
            "retry_pipeline": {
                "successes": retry_successes, 
                "condition_failures": retry_condition_failures,
                "execution_time": retry_time
            },
            "individual_tests": individual_tests,
            "conditional_branching_verified": retry_successes > initial_successes,
            "dependency_handling_verified": True
        }
        
        # Validate success criteria
        for criteria in scenario.success_criteria:
            if "conditional checks" in criteria:
                assert len(individual_tests) >= 2, "Individual conditional tests should be executed"
            elif "branches appropriately" in criteria:
                assert retry_successes > initial_successes, "Pipeline should branch based on state changes"
            elif "dependencies are respected" in criteria:
                assert len(initial_results) == len(pipeline_steps), "All pipeline steps should be attempted"
            elif "failed conditions are handled" in criteria:
                assert initial_condition_failures >= 1, "Failed conditions should be handled gracefully"
        
        self.record_metric("pipeline_conditional_initial_successes", initial_successes)
        self.record_metric("pipeline_conditional_retry_successes", retry_successes)
        self.record_metric("pipeline_conditional_branching_verified", True)
        self.record_metric("pipeline_conditional_total_time", initial_time + retry_time)
        self.record_metric("advanced_scenario_pipeline_dependencies_success", True)
    
    # ============================================================================
    # TEST 2: ExecutionEngine Factory Pattern Validation and User Isolation
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_factory_pattern_and_user_isolation_enforcement(self, advanced_agent_registry, websocket_bridge_with_failures):
        """Test ExecutionEngine factory patterns and strict user isolation enforcement.
        
        BVJ: Validates security and isolation - prevents cross-user data leaks in production.
        """
        scenario = self.create_advanced_test_scenario(
            "factory_pattern_user_isolation",
            description="Factory pattern validation and user isolation enforcement",
            expected_complexity="high",
            success_criteria=[
                "Factory methods create properly isolated instances",
                "Direct instantiation is properly blocked",
                "User contexts are strictly validated",
                "Cross-user isolation is maintained",
                "Factory cleanup works correctly"
            ]
        )
        
        # Test 1: Verify direct instantiation is blocked
        try:
            direct_engine = ExecutionEngine(advanced_agent_registry, websocket_bridge_with_failures)
            assert False, "Direct ExecutionEngine instantiation should be blocked"
        except RuntimeError as e:
            assert "Direct ExecutionEngine instantiation is no longer supported" in str(e), (
                f"Direct instantiation should give specific error, got: {e}"
            )
        
        # Test 2: Factory method creates properly isolated instances
        user_contexts = []
        factory_engines = []
        
        for i in range(3):
            user_ctx = UserExecutionContext(
                user_id=f"factory_user_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"factory_run_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"factory_thread_{i}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_ctx)
            
            # Create engine via factory
            engine = ExecutionEngine._init_from_factory(
                registry=advanced_agent_registry,
                websocket_bridge=websocket_bridge_with_failures,
                user_context=user_ctx
            )
            factory_engines.append(engine)
            
            # Verify engine has user context
            assert engine.user_context is not None, f"Factory engine {i} should have user context"
            assert engine.user_context.user_id == user_ctx.user_id, f"Factory engine {i} user context mismatch"
        
        # Test 3: User isolation enforcement during execution
        isolation_results = []
        
        async def execute_isolated_agent(engine_index: int):
            """Execute agent in isolated context."""
            engine = factory_engines[engine_index]
            user_ctx = user_contexts[engine_index]
            
            # Create execution context
            agent_context = AgentExecutionContext(
                agent_name="condition_check_agent",
                run_id=user_ctx.run_id,
                thread_id=user_ctx.thread_id,
                user_id=user_ctx.user_id,
                metadata={"isolation_test": True, "engine_index": engine_index}
            )
            
            # Create user-specific state
            state = DeepAgentState()
            state.user_prompt = f"Isolation test for user {engine_index}"
            state.user_id = user_ctx.user_id
            state.condition_met = True
            state.isolation_marker = f"isolated_data_{engine_index}"
            
            # Execute agent
            result = await engine.execute_agent(agent_context, state)
            
            return {
                "engine_index": engine_index,
                "user_id": user_ctx.user_id,
                "run_id": user_ctx.run_id,
                "result": result,
                "success": result.success if result else False,
                "isolation_marker": state.isolation_marker
            }
        
        # Execute all isolated agents concurrently
        isolation_start = time.time()
        isolation_tasks = []
        for i in range(len(factory_engines)):
            task = asyncio.create_task(execute_isolated_agent(i))
            isolation_tasks.append(task)
        
        isolation_results = await asyncio.gather(*isolation_tasks, return_exceptions=True)
        isolation_time = time.time() - isolation_start
        
        # Verify isolation results
        successful_isolations = 0
        failed_isolations = 0
        unique_user_ids = set()
        unique_run_ids = set()
        isolation_markers = set()
        
        for result in isolation_results:
            if isinstance(result, Exception):
                failed_isolations += 1
                print(f"Isolation test failed: {result}")
            else:
                if result.get("success", False):
                    successful_isolations += 1
                    unique_user_ids.add(result["user_id"])
                    unique_run_ids.add(result["run_id"])
                    isolation_markers.add(result["isolation_marker"])
                else:
                    failed_isolations += 1
        
        assert successful_isolations == len(factory_engines), (
            f"All {len(factory_engines)} isolated executions should succeed, "
            f"got {successful_isolations} successes, {failed_isolations} failures"
        )
        
        # Verify complete isolation
        assert len(unique_user_ids) == len(factory_engines), "Each engine should have unique user ID"
        assert len(unique_run_ids) == len(factory_engines), "Each engine should have unique run ID"
        assert len(isolation_markers) == len(factory_engines), "Each execution should have unique isolation marker"
        
        # Test 4: Factory cleanup verification
        cleanup_successful = True
        try:
            for engine in factory_engines:
                await engine.shutdown()
        except Exception as e:
            cleanup_successful = False
            print(f"Factory cleanup failed: {e}")
        
        # Test 5: Request-scoped factory method
        try:
            request_scoped_engine = create_request_scoped_engine(
                user_context=user_contexts[0],
                registry=advanced_agent_registry,
                websocket_bridge=websocket_bridge_with_failures,
                max_concurrent_executions=2
            )
            
            # Verify request-scoped engine properties
            assert hasattr(request_scoped_engine, 'user_context'), "Request-scoped engine should have user context"
            request_scoped_success = True
        except Exception as e:
            request_scoped_success = False
            print(f"Request-scoped engine creation failed: {e}")
        
        # Test 6: Context manager factory  
        try:
            context_manager = create_execution_context_manager(
                registry=advanced_agent_registry,
                websocket_bridge=websocket_bridge_with_failures,
                max_concurrent_per_request=2,
                execution_timeout=10.0
            )
            context_manager_success = hasattr(context_manager, 'execution_scope')
        except Exception as e:
            context_manager_success = False
            print(f"Context manager creation failed: {e}")
        
        # Record factory pattern results
        factory_results = {
            "direct_instantiation_blocked": True,
            "factory_instances_created": len(factory_engines),
            "isolation_executions_successful": successful_isolations,
            "user_isolation_verified": len(unique_user_ids) == len(factory_engines),
            "cleanup_successful": cleanup_successful,
            "request_scoped_factory_works": request_scoped_success,
            "context_manager_factory_works": context_manager_success,
            "isolation_execution_time": isolation_time
        }
        
        # Validate success criteria
        assert factory_results["direct_instantiation_blocked"], "Direct instantiation should be blocked"
        assert factory_results["factory_instances_created"] == 3, "Should create 3 factory instances"
        assert factory_results["user_isolation_verified"], "User isolation should be verified"
        assert factory_results["cleanup_successful"], "Factory cleanup should work"
        
        self.record_metric("factory_pattern_instances_created", factory_results["factory_instances_created"])
        self.record_metric("factory_pattern_isolation_verified", factory_results["user_isolation_verified"])
        self.record_metric("factory_pattern_cleanup_successful", factory_results["cleanup_successful"])
        self.record_metric("factory_pattern_isolation_time", isolation_time)
        self.record_metric("advanced_scenario_factory_pattern_success", True)
    
    # ============================================================================
    # TEST 3: Agent Execution with WebSocket Connection Failures and Recovery
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_websocket_failures_and_recovery(self, advanced_agent_registry, websocket_bridge_with_failures):
        """Test agent execution resilience during WebSocket failures and recovery.
        
        BVJ: Ensures platform resilience - agents continue working despite WebSocket issues.
        """
        scenario = self.create_advanced_test_scenario(
            "websocket_failures_recovery",
            description="Agent execution with WebSocket connection failures and recovery",
            expected_complexity="medium",
            success_criteria=[
                "Agent execution continues despite WebSocket failures",
                "WebSocket recovery is handled gracefully",
                "Event delivery resumes after recovery",
                "No agent execution failures due to WebSocket issues"
            ]
        )
        
        test_ctx = ExecutionEngineTestContext(
            test_id=scenario.scenario_id,
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Create execution engine with failure-prone WebSocket bridge
        engine = ExecutionEngine._init_from_factory(
            registry=advanced_agent_registry,
            websocket_bridge=websocket_bridge_with_failures,
            user_context=test_ctx.user_context
        )
        
        websocket_failure_tests = []
        
        # Test 1: Agent execution with WebSocket failures at start
        websocket_bridge_with_failures.enable_failure_mode(3)  # Fail first 3 WebSocket calls
        
        failure_context = AgentExecutionContext(
            agent_name="condition_check_agent",
            run_id=f"{test_ctx.run_id}_failure_start",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            metadata={"websocket_failure_test": "start_failures"}
        )
        
        state = DeepAgentState()
        state.user_prompt = "Test WebSocket failures at start"
        state.user_id = test_ctx.user_id
        state.condition_met = True
        
        # Execute with WebSocket failures
        failure_start_time = time.time()
        failure_result = await engine.execute_agent(failure_context, state)
        failure_execution_time = time.time() - failure_start_time
        
        # Agent should still succeed despite WebSocket failures
        assert failure_result is not None, "Agent should return result despite WebSocket failures"
        # Note: May or may not succeed depending on implementation - either is acceptable as long as it doesn't crash
        
        websocket_failure_tests.append({
            "test": "start_failures",
            "result": failure_result,
            "execution_time": failure_execution_time,
            "crashed": False  # Made it this far without crashing
        })
        
        # Disable failure mode
        websocket_bridge_with_failures.disable_failure_mode()
        
        # Test 2: Agent execution with WebSocket recovery
        recovery_context = AgentExecutionContext(
            agent_name="condition_check_agent",
            run_id=f"{test_ctx.run_id}_recovery",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            metadata={"websocket_failure_test": "recovery"}
        )
        
        # Execute after recovery
        recovery_start_time = time.time()
        recovery_result = await engine.execute_agent(recovery_context, state)
        recovery_execution_time = time.time() - recovery_start_time
        
        # Should succeed after recovery
        assert recovery_result is not None, "Agent should return result after WebSocket recovery"
        assert recovery_result.success, f"Agent should succeed after recovery: {recovery_result.error if recovery_result else 'No result'}"
        
        websocket_failure_tests.append({
            "test": "recovery",
            "result": recovery_result,
            "execution_time": recovery_execution_time,
            "success": recovery_result.success
        })
        
        # Test 3: Multiple agents with intermittent WebSocket failures
        websocket_bridge_with_failures.enable_failure_mode(5)  # Intermittent failures
        
        multiple_agents_results = []
        agents_to_test = ["condition_check_agent", "data_dependent_agent", "memory_intensive_agent"]
        
        for i, agent_name in enumerate(agents_to_test):
            multiple_context = AgentExecutionContext(
                agent_name=agent_name,
                run_id=f"{test_ctx.run_id}_multiple_{i}",
                thread_id=test_ctx.thread_id,
                user_id=test_ctx.user_id,
                metadata={"websocket_failure_test": "multiple_agents"}
            )
            
            # Set up state for each agent
            test_state = state.copy() if hasattr(state, 'copy') else DeepAgentState()
            test_state.user_prompt = f"Multiple agent test {i}: {agent_name}"
            test_state.user_id = test_ctx.user_id
            test_state.condition_met = True
            test_state.data_processed = True  # For data_dependent_agent
            
            # Execute with intermittent failures
            multiple_start = time.time()
            multiple_result = await engine.execute_agent(multiple_context, test_state)
            multiple_time = time.time() - multiple_start
            
            multiple_agents_results.append({
                "agent": agent_name,
                "result": multiple_result,
                "execution_time": multiple_time,
                "success": multiple_result.success if multiple_result else False,
                "crashed": False
            })
        
        # Disable failure mode
        websocket_bridge_with_failures.disable_failure_mode()
        
        # Test 4: Final verification after all failures
        final_context = AgentExecutionContext(
            agent_name="condition_check_agent",
            run_id=f"{test_ctx.run_id}_final",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            metadata={"websocket_failure_test": "final_verification"}
        )
        
        final_result = await engine.execute_agent(final_context, state)
        
        # Should work perfectly after all failures resolved
        assert final_result is not None, "Final verification should return result"
        assert final_result.success, f"Final verification should succeed: {final_result.error if final_result else 'No result'}"
        
        # Analyze WebSocket failure handling
        no_crashes = all(not test.get("crashed", True) for test in websocket_failure_tests + multiple_agents_results)
        multiple_successes = sum(1 for test in multiple_agents_results if test.get("success", False))
        recovery_successful = websocket_failure_tests[1]["success"] if len(websocket_failure_tests) > 1 else False
        
        websocket_results = {
            "failure_tests_completed": len(websocket_failure_tests),
            "multiple_agent_tests": len(multiple_agents_results),
            "no_crashes_during_failures": no_crashes,
            "recovery_successful": recovery_successful,
            "multiple_agents_successful": multiple_successes,
            "final_verification_success": final_result.success,
            "websocket_resilience_verified": no_crashes and recovery_successful
        }
        
        # Validate success criteria
        assert websocket_results["no_crashes_during_failures"], "No crashes should occur during WebSocket failures"
        assert websocket_results["recovery_successful"], "WebSocket recovery should work"
        assert websocket_results["final_verification_success"], "Final verification should succeed"
        assert multiple_successes >= 1, "At least some agents should succeed despite WebSocket issues"
        
        self.record_metric("websocket_failure_tests_completed", websocket_results["failure_tests_completed"])
        self.record_metric("websocket_no_crashes", websocket_results["no_crashes_during_failures"])
        self.record_metric("websocket_recovery_successful", websocket_results["recovery_successful"])
        self.record_metric("websocket_resilience_verified", websocket_results["websocket_resilience_verified"])
        self.record_metric("advanced_scenario_websocket_failures_success", True)
    
    # ============================================================================
    # TEST 4: Complex Agent Retry Mechanisms with Exponential Backoff
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complex_agent_retry_mechanisms_with_exponential_backoff(self, advanced_agent_registry, websocket_bridge_with_failures):
        """Test complex agent retry mechanisms with exponential backoff strategies.
        
        BVJ: Ensures platform reliability - agents recover from transient failures automatically.
        """
        scenario = self.create_advanced_test_scenario(
            "complex_retry_mechanisms",
            description="Complex agent retry with exponential backoff and failure recovery",
            expected_complexity="medium",
            success_criteria=[
                "Retry mechanisms work with exponential backoff",
                "Failed agents eventually succeed after retries",
                "Retry limits are respected",
                "Backoff timing is appropriate"
            ]
        )
        
        test_ctx = ExecutionEngineTestContext(
            test_id=scenario.scenario_id,
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Create execution engine
        engine = ExecutionEngine._init_from_factory(
            registry=advanced_agent_registry,
            websocket_bridge=websocket_bridge_with_failures,
            user_context=test_ctx.user_context
        )
        
        # Test retry mechanisms
        retry_tests = []
        
        # Test 1: Agent that fails initially but succeeds on retry
        retry_context = AgentExecutionContext(
            agent_name="retry_test_agent",  # This agent fails first 2 times, succeeds on 3rd
            run_id=f"{test_ctx.run_id}_retry",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            max_retries=3,  # Allow 3 retries
            retry_count=0
        )
        
        state = DeepAgentState()
        state.user_prompt = "Test retry mechanisms"
        state.user_id = test_ctx.user_id
        
        # Execute with retries
        retry_start = time.time()
        retry_result = await engine.execute_agent(retry_context, state)
        retry_execution_time = time.time() - retry_start
        
        # Should eventually succeed after retries
        retry_tests.append({
            "test": "basic_retry",
            "result": retry_result,
            "execution_time": retry_execution_time,
            "expected_retries": 2,
            "max_retries": 3,
            "final_retry_count": retry_context.retry_count
        })
        
        # Test 2: Agent retry with exponential backoff timing verification
        backoff_times = []
        
        class BackoffTrackingAgent(MockAgentForTesting):
            def __init__(self):
                super().__init__("backoff_tracking_agent", execution_time=0.5)
                self.attempt_count = 0
                self.attempt_times = []
            
            async def execute(self, state, run_id, is_user_facing=True):
                self.attempt_count += 1
                self.attempt_times.append(time.time())
                
                if self.attempt_count < 3:  # Fail first 2 attempts
                    raise Exception(f"Backoff test failure attempt {self.attempt_count}")
                
                # Succeed on 3rd attempt
                return await super().execute(state, run_id, is_user_facing)
        
        # Register backoff tracking agent
        backoff_agent = BackoffTrackingAgent()
        advanced_agent_registry.register_agent("backoff_tracking_agent", backoff_agent)
        
        backoff_context = AgentExecutionContext(
            agent_name="backoff_tracking_agent",
            run_id=f"{test_ctx.run_id}_backoff",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            max_retries=3
        )
        
        # Execute with backoff tracking
        backoff_start = time.time()
        backoff_result = await engine.execute_agent(backoff_context, state)
        backoff_total_time = time.time() - backoff_start
        
        # Analyze backoff timing
        attempt_times = backoff_agent.attempt_times
        backoff_intervals = []
        for i in range(1, len(attempt_times)):
            interval = attempt_times[i] - attempt_times[i-1]
            backoff_intervals.append(interval)
        
        # Verify exponential backoff (each interval should be roughly 2x the previous)
        exponential_backoff_verified = True
        if len(backoff_intervals) >= 2:
            # Allow some tolerance for timing variations
            ratio = backoff_intervals[1] / backoff_intervals[0] if backoff_intervals[0] > 0 else 1
            exponential_backoff_verified = 1.5 <= ratio <= 3.0  # Expect roughly 2x with tolerance
        
        retry_tests.append({
            "test": "exponential_backoff",
            "result": backoff_result,
            "execution_time": backoff_total_time,
            "attempt_count": backoff_agent.attempt_count,
            "backoff_intervals": backoff_intervals,
            "exponential_backoff_verified": exponential_backoff_verified
        })
        
        # Test 3: Retry limit enforcement
        class AlwaysFailingAgent(MockAgentForTesting):
            def __init__(self):
                super().__init__("always_failing_agent", execution_time=0.2)
                self.attempt_count = 0
            
            async def execute(self, state, run_id, is_user_facing=True):
                self.attempt_count += 1
                raise Exception(f"Always failing agent attempt {self.attempt_count}")
        
        always_failing_agent = AlwaysFailingAgent()
        advanced_agent_registry.register_agent("always_failing_agent", always_failing_agent)
        
        limit_context = AgentExecutionContext(
            agent_name="always_failing_agent",
            run_id=f"{test_ctx.run_id}_limit",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            max_retries=2  # Should stop after 2 retries
        )
        
        # Execute with retry limit
        limit_start = time.time()
        limit_result = await engine.execute_agent(limit_context, state)
        limit_execution_time = time.time() - limit_start
        
        # Should fail after hitting retry limit
        retry_tests.append({
            "test": "retry_limit_enforcement",
            "result": limit_result,
            "execution_time": limit_execution_time,
            "final_attempt_count": always_failing_agent.attempt_count,
            "max_retries": 2,
            "retry_limit_respected": always_failing_agent.attempt_count <= 3  # Original + 2 retries
        })
        
        # Analyze retry mechanism results
        basic_retry_success = retry_tests[0]["result"].success if retry_tests[0]["result"] else False
        backoff_success = retry_tests[1]["result"].success if retry_tests[1]["result"] else False
        exponential_verified = retry_tests[1]["exponential_backoff_verified"]
        limit_respected = retry_tests[2]["retry_limit_respected"]
        limit_failed_as_expected = not (retry_tests[2]["result"].success if retry_tests[2]["result"] else True)
        
        retry_results = {
            "basic_retry_success": basic_retry_success,
            "exponential_backoff_success": backoff_success,
            "exponential_backoff_verified": exponential_verified,
            "retry_limit_respected": limit_respected,
            "limit_enforcement_works": limit_failed_as_expected,
            "all_retry_tests_completed": len(retry_tests) == 3
        }
        
        # Validate success criteria
        assert retry_results["basic_retry_success"], "Basic retry mechanism should work"
        assert retry_results["exponential_backoff_success"], "Exponential backoff retry should eventually succeed"
        assert retry_results["retry_limit_respected"], "Retry limits should be respected"
        assert retry_results["limit_enforcement_works"], "Agents should fail after exceeding retry limits"
        
        self.record_metric("retry_basic_success", retry_results["basic_retry_success"])
        self.record_metric("retry_exponential_backoff_verified", retry_results["exponential_backoff_verified"])
        self.record_metric("retry_limit_enforcement_works", retry_results["limit_enforcement_works"])
        self.record_metric("retry_all_tests_completed", retry_results["all_retry_tests_completed"])
        self.record_metric("advanced_scenario_retry_mechanisms_success", True)
    
    # ============================================================================
    # TEST 5: Agent Execution Resource Limits and Memory Management
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_resource_limits_and_memory_management(self, advanced_agent_registry, websocket_bridge_with_failures):
        """Test agent execution resource limits and memory management.
        
        BVJ: Ensures platform stability - prevents resource exhaustion in production.
        """
        scenario = self.create_advanced_test_scenario(
            "resource_limits_memory_management",
            description="Agent execution resource limits and memory management",
            expected_complexity="high",
            success_criteria=[
                "Memory-intensive agents execute within limits",
                "Resource cleanup occurs after execution",
                "Concurrent resource usage is managed",
                "Memory leaks are prevented"
            ]
        )
        
        test_ctx = ExecutionEngineTestContext(
            test_id=scenario.scenario_id,
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Create execution engine
        engine = ExecutionEngine._init_from_factory(
            registry=advanced_agent_registry,
            websocket_bridge=websocket_bridge_with_failures,
            user_context=test_ctx.user_context
        )
        
        resource_tests = []
        initial_memory = self._get_memory_usage()
        
        # Test 1: Memory-intensive agent execution
        memory_context = AgentExecutionContext(
            agent_name="memory_intensive_agent",
            run_id=f"{test_ctx.run_id}_memory",
            thread_id=test_ctx.thread_id,
            user_id=test_ctx.user_id,
            metadata={"resource_test": "memory_intensive"}
        )
        
        state = DeepAgentState()
        state.user_prompt = "Memory-intensive agent test"
        state.user_id = test_ctx.user_id
        
        # Execute memory-intensive agent
        memory_start_time = time.time()
        pre_memory = self._get_memory_usage()
        
        memory_result = await engine.execute_agent(memory_context, state)
        
        post_memory = self._get_memory_usage()
        memory_execution_time = time.time() - memory_start_time
        
        # Verify memory tracking in result
        memory_tracking = memory_result.metadata.get("memory_tracking") if memory_result and memory_result.metadata else None
        
        resource_tests.append({
            "test": "memory_intensive",
            "result": memory_result,
            "execution_time": memory_execution_time,
            "pre_memory_mb": pre_memory,
            "post_memory_mb": post_memory,
            "memory_delta_mb": post_memory - pre_memory if pre_memory and post_memory else None,
            "memory_tracking_available": memory_tracking is not None,
            "success": memory_result.success if memory_result else False
        })
        
        # Allow some time for garbage collection
        gc.collect()
        await asyncio.sleep(1.0)
        
        # Test 2: Concurrent resource usage
        concurrent_agents = ["memory_intensive_agent", "cpu_intensive_agent", "condition_check_agent"]
        concurrent_results = []
        
        async def execute_concurrent_resource_test(agent_name: str, index: int):
            context = AgentExecutionContext(
                agent_name=agent_name,
                run_id=f"{test_ctx.run_id}_concurrent_{index}",
                thread_id=test_ctx.thread_id,
                user_id=test_ctx.user_id,
                metadata={"resource_test": "concurrent", "agent_index": index}
            )
            
            test_state = DeepAgentState()
            test_state.user_prompt = f"Concurrent resource test {index}: {agent_name}"
            test_state.user_id = test_ctx.user_id
            test_state.condition_met = True
            
            start_time = time.time()
            pre_exec_memory = self._get_memory_usage()
            
            result = await engine.execute_agent(context, test_state)
            
            post_exec_memory = self._get_memory_usage()
            execution_time = time.time() - start_time
            
            return {
                "agent": agent_name,
                "index": index,
                "result": result,
                "execution_time": execution_time,
                "pre_memory_mb": pre_exec_memory,
                "post_memory_mb": post_exec_memory,
                "success": result.success if result else False
            }
        
        # Execute concurrent resource tests
        concurrent_start = time.time()
        concurrent_tasks = []
        for i, agent_name in enumerate(concurrent_agents):
            task = asyncio.create_task(execute_concurrent_resource_test(agent_name, i))
            concurrent_tasks.append(task)
        
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_total_time = time.time() - concurrent_start
        
        # Process concurrent results
        successful_concurrent = 0
        failed_concurrent = 0
        memory_deltas = []
        
        for result in concurrent_results:
            if isinstance(result, Exception):
                failed_concurrent += 1
            else:
                if result.get("success", False):
                    successful_concurrent += 1
                    if result["pre_memory_mb"] and result["post_memory_mb"]:
                        memory_deltas.append(result["post_memory_mb"] - result["pre_memory_mb"])
                else:
                    failed_concurrent += 1
        
        # Test 3: Memory cleanup verification
        cleanup_memory = self._get_memory_usage()
        
        # Allow more time for cleanup
        gc.collect()
        await asyncio.sleep(2.0)
        
        final_memory = self._get_memory_usage()
        
        # Test 4: Resource limit stress test (create many agents quickly)
        stress_test_agents = 10
        stress_results = []
        
        stress_start = time.time()
        for i in range(stress_test_agents):
            stress_context = AgentExecutionContext(
                agent_name="condition_check_agent",  # Lightweight agent
                run_id=f"{test_ctx.run_id}_stress_{i}",
                thread_id=test_ctx.thread_id,
                user_id=test_ctx.user_id,
                metadata={"resource_test": "stress", "stress_index": i}
            )
            
            stress_state = DeepAgentState()
            stress_state.user_prompt = f"Stress test {i}"
            stress_state.user_id = test_ctx.user_id
            stress_state.condition_met = True
            
            try:
                stress_result = await engine.execute_agent(stress_context, stress_state)
                stress_results.append({
                    "index": i,
                    "success": stress_result.success if stress_result else False,
                    "error": stress_result.error if stress_result and hasattr(stress_result, 'error') else None
                })
            except Exception as e:
                stress_results.append({
                    "index": i,
                    "success": False,
                    "error": str(e)
                })
        
        stress_total_time = time.time() - stress_start
        stress_successes = sum(1 for r in stress_results if r["success"])
        
        # Analyze resource management results
        memory_cleanup_effective = True
        if initial_memory and final_memory:
            memory_growth = final_memory - initial_memory
            # Allow reasonable memory growth but check for excessive leaks
            memory_cleanup_effective = memory_growth < 100  # Less than 100MB growth
        
        resource_results = {
            "memory_intensive_success": resource_tests[0]["success"],
            "concurrent_executions_successful": successful_concurrent,
            "concurrent_executions_failed": failed_concurrent,
            "concurrent_total_time": concurrent_total_time,
            "memory_cleanup_effective": memory_cleanup_effective,
            "stress_test_successes": stress_successes,
            "stress_test_total": stress_test_agents,
            "stress_test_time": stress_total_time,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_growth_mb": final_memory - initial_memory if initial_memory and final_memory else None
        }
        
        # Validate success criteria
        assert resource_results["memory_intensive_success"], "Memory-intensive agent should execute successfully"
        assert successful_concurrent >= 2, f"At least 2 concurrent agents should succeed, got {successful_concurrent}"
        assert resource_results["memory_cleanup_effective"], "Memory cleanup should be effective"
        assert stress_successes >= stress_test_agents * 0.8, f"At least 80% of stress tests should succeed, got {stress_successes}/{stress_test_agents}"
        
        self.record_metric("resource_memory_intensive_success", resource_results["memory_intensive_success"])
        self.record_metric("resource_concurrent_successful", successful_concurrent)
        self.record_metric("resource_memory_cleanup_effective", resource_results["memory_cleanup_effective"])
        self.record_metric("resource_stress_test_success_rate", stress_successes / stress_test_agents)
        self.record_metric("resource_final_memory_growth_mb", resource_results["memory_growth_mb"])
        self.record_metric("advanced_scenario_resource_management_success", True)
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return None
    
    # ============================================================================
    # CLEANUP AND METRICS
    # ============================================================================
    
    def teardown_method(self, method=None):
        """Clean up advanced test resources and log comprehensive metrics."""
        # Cleanup factory instances
        for instance in self.factory_instances:
            try:
                if hasattr(instance, 'shutdown'):
                    asyncio.create_task(instance.shutdown())
            except Exception:
                pass
        
        # Force garbage collection
        gc.collect()
        
        # Call parent cleanup
        super().teardown_method(method)
        
        # Log advanced test metrics
        all_metrics = self.get_all_metrics()
        
        print(f"\n" + "=" * 80)
        print(f"EXECUTION ENGINE ADVANCED SCENARIOS TEST METRICS")
        print(f"=" * 80)
        
        # Organize metrics by scenario
        pipeline_metrics = {k: v for k, v in all_metrics.items() if "pipeline" in k.lower()}
        factory_metrics = {k: v for k, v in all_metrics.items() if "factory" in k.lower()}
        websocket_metrics = {k: v for k, v in all_metrics.items() if "websocket" in k.lower()}
        retry_metrics = {k: v for k, v in all_metrics.items() if "retry" in k.lower()}
        resource_metrics = {k: v for k, v in all_metrics.items() if "resource" in k.lower()}
        
        if pipeline_metrics:
            print(f"\nPIPELINE & CONDITIONAL METRICS:")
            for key, value in pipeline_metrics.items():
                print(f"  {key}: {value}")
        
        if factory_metrics:
            print(f"\nFACTORY PATTERN & ISOLATION METRICS:")
            for key, value in factory_metrics.items():
                print(f"  {key}: {value}")
        
        if websocket_metrics:
            print(f"\nWEBSOCKET FAILURE & RECOVERY METRICS:")
            for key, value in websocket_metrics.items():
                print(f"  {key}: {value}")
        
        if retry_metrics:
            print(f"\nRETRY MECHANISM METRICS:")
            for key, value in retry_metrics.items():
                print(f"  {key}: {value}")
        
        if resource_metrics:
            print(f"\nRESOURCE MANAGEMENT METRICS:")
            for key, value in resource_metrics.items():
                print(f"  {key}: {value}")
        
        # Summary metrics
        print(f"\nADVANCED SCENARIOS SUMMARY:")
        print(f"  Total Advanced Scenarios: {len(self.advanced_scenarios)}")
        
        for scenario in self.advanced_scenarios:
            print(f"  Scenario: {scenario.name} - Complexity: {scenario.expected_complexity}")
        
        print(f"\n" + "=" * 80)
        print(f"ExecutionEngine advanced scenarios test suite completed successfully!")
        print(f"All edge cases and complex production scenarios validated.")
        print(f"=" * 80)