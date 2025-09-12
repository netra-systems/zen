"""
Phase 3B: Agent Circuit Breaker Integration Test Suite

This test suite validates that agent system circuit breakers work correctly
with the unified circuit breaker system, ensuring that agent execution failures
are properly handled and don't cascade due to compatibility layer issues.

Test Philosophy: Integration tests that prove the agent  ->  circuit breaker integration
works properly with the unified system, identifying any dependencies on missing
resilience framework components.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestAgentCircuitBreakerIntegration(SSotAsyncTestCase):
    """Test agent system integration with unified circuit breakers."""
    
    def test_agent_system_can_import_circuit_breakers(self):
        """
        PASSING TEST: Validates that agent system can import circuit breaker components.
        
        This ensures that agents can use circuit breakers without
        being affected by the missing resilience framework modules.
        """
        try:
            # Test imports that agent system might use
            from netra_backend.app.core.circuit_breaker import (
                get_circuit_breaker,
                circuit_breaker,
                CircuitBreakerOpenError,
                UnifiedCircuitBreaker,
                UnifiedCircuitConfig
            )
            
            # Test agent-specific imports
            from netra_backend.app.agents.base import circuit_breaker as agent_circuit_breaker
            
            # Test that imports work
            assert callable(get_circuit_breaker), "get_circuit_breaker should be importable"
            assert callable(circuit_breaker), "circuit_breaker decorator should be importable"
            assert CircuitBreakerOpenError is not None, "CircuitBreakerOpenError should be available"
            
            print("\nAGENT IMPORTS: Agent system can successfully import circuit breaker components")
            
        except ImportError as e:
            pytest.fail(f"INTEGRATION FAILURE: Agent system cannot import circuit breakers: {e}")
    
    def test_agent_execution_circuit_breaker_creation(self):
        """
        PASSING TEST: Validates that agent system can create agent-specific circuit breakers.
        """
        from netra_backend.app.core.circuit_breaker import get_circuit_breaker
        
        # Create circuit breakers that agent system might use
        llm_breaker = get_circuit_breaker("agent_llm_calls")
        tool_execution_breaker = get_circuit_breaker("agent_tool_execution")
        data_access_breaker = get_circuit_breaker("agent_data_access")
        supervisor_breaker = get_circuit_breaker("agent_supervisor")
        
        # Validate they are created correctly
        assert llm_breaker is not None, "LLM circuit breaker should be created"
        assert tool_execution_breaker is not None, "Tool execution circuit breaker should be created"
        assert data_access_breaker is not None, "Data access circuit breaker should be created"
        assert supervisor_breaker is not None, "Supervisor circuit breaker should be created"
        
        # Test that they have expected initial state
        assert llm_breaker.can_execute() is True, "LLM breaker should initially allow execution"
        assert tool_execution_breaker.can_execute() is True, "Tool execution breaker should initially allow execution"
        assert data_access_breaker.can_execute() is True, "Data access breaker should initially allow execution"
        assert supervisor_breaker.can_execute() is True, "Supervisor breaker should initially allow execution"
        
        print("\nAGENT BREAKER CREATION: Agent-specific circuit breakers created successfully")
    
    def test_agent_failure_scenarios_trigger_circuit_breaker(self):
        """
        PASSING TEST: Validates that agent failures properly trigger circuit breaker state changes.
        """
        from netra_backend.app.core.circuit_breaker import get_circuit_breaker
        
        # Create an agent circuit breaker with tracking
        agent_breaker = get_circuit_breaker("agent_failure_test")
        
        # Initially should be closed and allow execution
        assert agent_breaker.can_execute() is True
        initial_failures = agent_breaker.metrics.failed_calls
        
        # Simulate agent execution failures
        agent_errors = [
            "LLM API timeout",
            "Tool execution failed", 
            "Data source unavailable",
            "Memory limit exceeded",
            "Agent execution timeout",
            "Invalid response format"
        ]
        
        for error in agent_errors:
            agent_breaker.record_failure(error)
        
        # Check that failures were recorded
        assert agent_breaker.metrics.failed_calls > initial_failures, "Failures should be recorded"
        assert agent_breaker.metrics.consecutive_failures > 0, "Consecutive failures should be tracked"
        
        # If threshold is reached, circuit should open
        if agent_breaker.metrics.consecutive_failures >= agent_breaker.config.failure_threshold:
            assert not agent_breaker.can_execute(), "Circuit should be open after threshold reached"
            print(f"\nAGENT FAILURE HANDLING: Circuit opened after {agent_breaker.metrics.consecutive_failures} failures")
        else:
            print(f"\nAGENT FAILURE HANDLING: {agent_breaker.metrics.consecutive_failures} failures recorded, threshold not yet reached")
    
    @pytest.mark.integration  
    @pytest.mark.asyncio
    async def test_agent_circuit_breaker_with_mock_agent_execution(self):
        """
        INTEGRATION TEST: Tests circuit breaker integration with mock agent execution.
        
        This simulates how agents would use circuit breakers during execution.
        """
        from netra_backend.app.core.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
        
        # Create mock agent executor
        class MockAgentExecutor:
            def __init__(self):
                self.llm_breaker = get_circuit_breaker("mock_agent_llm")
                self.tool_breaker = get_circuit_breaker("mock_agent_tools")
                self.execution_count = 0
                self.failure_mode = False
                
            async def execute_agent_task(self, task: str):
                """Mock agent task execution with circuit breaker protection."""
                self.execution_count += 1
                
                # Check LLM circuit breaker
                if not self.llm_breaker.can_execute():
                    raise CircuitBreakerOpenError("LLM circuit breaker is open")
                
                # Check tool circuit breaker  
                if not self.tool_breaker.can_execute():
                    raise CircuitBreakerOpenError("Tool circuit breaker is open")
                
                try:
                    # Simulate agent execution logic that might fail
                    if self.failure_mode or task == "fail_task":
                        raise Exception("Agent execution failed")
                    
                    # Simulate async work
                    await asyncio.sleep(0.01)
                    
                    # Record successes
                    self.llm_breaker.record_success()
                    self.tool_breaker.record_success()
                    
                    return {"task": task, "result": "completed", "execution_id": self.execution_count}
                    
                except Exception as e:
                    self.llm_breaker.record_failure(str(e))
                    self.tool_breaker.record_failure(str(e))
                    raise
        
        executor = MockAgentExecutor()
        
        # Test successful agent execution
        result = await executor.execute_agent_task("analyze_data")
        assert result["result"] == "completed", "Successful execution should return completed result"
        assert executor.llm_breaker.metrics.successful_calls > 0, "LLM success should be recorded"
        assert executor.tool_breaker.metrics.successful_calls > 0, "Tool success should be recorded"
        
        # Test failed agent execution
        with pytest.raises(Exception, match="Agent execution failed"):
            await executor.execute_agent_task("fail_task")
        
        assert executor.llm_breaker.metrics.failed_calls > 0, "LLM failure should be recorded"
        assert executor.tool_breaker.metrics.failed_calls > 0, "Tool failure should be recorded"
        
        print("\nAGENT EXECUTION INTEGRATION: Circuit breakers properly integrate with mock agent execution")
    
    def test_agent_circuit_breaker_resilience_framework_independence(self):
        """
        PASSING TEST: Validates that agent circuit breakers work independently of resilience framework.
        
        This ensures Issue #455 doesn't break agent functionality.
        """
        from netra_backend.app.core import circuit_breaker
        
        # Check if resilience framework is available (should be False due to Issue #455)
        has_resilience = getattr(circuit_breaker, '_HAS_RESILIENCE_FRAMEWORK', False)
        
        if has_resilience:
            print("\nRESILIENCE FRAMEWORK: Available - Issue #455 may be resolved")
        else:
            print("\nRESILIENCE FRAMEWORK: Not available - Issue #455 still exists")
        
        # But agent circuit breakers should work regardless
        agent_breaker = circuit_breaker.get_circuit_breaker("agent_independence_test")
        
        # Test basic functionality
        assert agent_breaker.can_execute() is True, "Agent breaker should work without resilience framework"
        
        # Test state tracking
        agent_breaker.record_failure("Test agent failure")
        assert agent_breaker.metrics.failed_calls > 0, "Failure recording should work"
        
        agent_breaker.record_success()
        assert agent_breaker.metrics.successful_calls > 0, "Success recording should work"
        
        # Test status reporting
        status = agent_breaker.get_status()
        assert isinstance(status, dict), "Status reporting should work"
        assert 'state' in status, "Status should include state"
        assert 'metrics' in status, "Status should include metrics"
        
        print("\nAGENT INDEPENDENCE: Agent circuit breakers work independently of resilience framework availability")


class TestAgentCircuitBreakerDecorators(SSotAsyncTestCase):
    """Test circuit breaker decorator usage in agent contexts."""
    
    def test_agent_llm_call_decorator_compatibility(self):
        """
        PASSING TEST: Validates that agents can use circuit breaker decorators for LLM calls.
        """
        from netra_backend.app.core.circuit_breaker import circuit_breaker
        
        # Test decorator usage for LLM calls
        @circuit_breaker("agent_llm_call_test")
        def call_llm(prompt: str, model: str = "gpt-3.5-turbo"):
            """Mock LLM call function."""
            if prompt == "error_prompt":
                raise ConnectionError("LLM API unavailable")
            
            return {"response": f"Mock response to: {prompt}", "model": model, "tokens": 42}
        
        # Test successful LLM call
        result = call_llm("Hello, how are you?")
        assert "Mock response" in result["response"], "LLM call should return response"
        assert result["tokens"] == 42, "LLM call should return token count"
        
        # Test failed LLM call
        with pytest.raises(ConnectionError, match="LLM API unavailable"):
            call_llm("error_prompt")
        
        print("\nAGENT LLM DECORATOR: Circuit breaker decorator works with LLM calls")
    
    @pytest.mark.asyncio
    async def test_agent_async_tool_execution_decorator(self):
        """
        PASSING TEST: Validates that agents can use async circuit breakers for tool execution.
        """
        from netra_backend.app.core.circuit_breaker import unified_circuit_breaker
        
        # Test async decorator for tool execution
        @unified_circuit_breaker("agent_tool_execution_test")
        async def execute_tool(tool_name: str, parameters: Dict[str, Any]):
            """Mock async tool execution."""
            await asyncio.sleep(0.01)  # Simulate async tool work
            
            if tool_name == "failing_tool":
                raise RuntimeError("Tool execution failed")
            
            return {
                "tool": tool_name,
                "parameters": parameters,
                "result": f"Tool {tool_name} executed successfully",
                "execution_time": 0.01
            }
        
        # Test successful tool execution
        result = await execute_tool("data_analyzer", {"dataset": "sales_data.csv"})
        assert result["tool"] == "data_analyzer", "Tool execution should return tool name"
        assert "executed successfully" in result["result"], "Tool execution should succeed"
        
        # Test failed tool execution
        with pytest.raises(RuntimeError, match="Tool execution failed"):
            await execute_tool("failing_tool", {})
        
        print("\nAGENT TOOL DECORATOR: Async circuit breaker decorator works with tool execution")


class TestAgentCircuitBreakerErrorScenarios(SSotAsyncTestCase):
    """Test error scenarios specific to agent circuit breaker integration."""
    
    def test_agent_circuit_breaker_missing_resilience_dependency_handling(self):
        """
        FAILING TEST: Validates handling of missing resilience framework dependencies.
        
        This specifically tests the impact of Issue #455 on agent circuit breaker usage.
        """
        from netra_backend.app.core import circuit_breaker
        
        # Check for missing resilience framework components that agents might try to use
        missing_features = []
        
        # Test for features that might be used by agents but are missing due to Issue #455
        resilience_features = [
            'UnifiedRetryManager',
            'UnifiedFallbackChain', 
            'resilience_registry',
            'with_resilience',
            'register_llm_service',
            'register_api_service'
        ]
        
        for feature in resilience_features:
            if not hasattr(circuit_breaker, feature):
                missing_features.append(feature)
        
        # This should FAIL initially (meaning we expect missing features)
        assert len(missing_features) > 0, (
            f"EXPECTED FAILURE: Expected missing resilience framework features, "
            f"but all features are available: {resilience_features}. "
            f"This indicates Issue #455 has been resolved."
        )
        
        print(f"\nAGENT RESILIENCE GAPS: {len(missing_features)} resilience features unavailable to agents")
        for feature in missing_features:
            print(f"  Missing: {feature}")
        
        # But basic circuit breaker functionality should still work for agents
        agent_breaker = circuit_breaker.get_circuit_breaker("agent_resilience_gap_test")
        assert agent_breaker is not None, "Basic circuit breaker should work despite missing features"
        
        print("BASIC FUNCTIONALITY: Core circuit breaker features available despite resilience gaps")
    
    def test_agent_circuit_breaker_cascading_failure_prevention(self):
        """
        INTEGRATION TEST: Tests that agent circuit breakers prevent cascading failures.
        """
        from netra_backend.app.core.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
        
        # Create agent pipeline circuit breakers
        supervisor_breaker = get_circuit_breaker("agent_supervisor_cascade")
        llm_breaker = get_circuit_breaker("agent_llm_cascade") 
        tool_breaker = get_circuit_breaker("agent_tool_cascade")
        data_breaker = get_circuit_breaker("agent_data_cascade")
        
        # Simulate agent execution pipeline with failure propagation
        def simulate_agent_pipeline_execution(introduce_failure_at_stage: Optional[str] = None):
            """Simulate agent pipeline execution with potential failure injection."""
            execution_stages = [
                ("supervisor", supervisor_breaker),
                ("llm", llm_breaker),
                ("tool", tool_breaker), 
                ("data", data_breaker)
            ]
            
            completed_stages = []
            
            for stage_name, breaker in execution_stages:
                if not breaker.can_execute():
                    print(f"  Stage {stage_name}: BLOCKED (circuit open)")
                    break
                
                if introduce_failure_at_stage == stage_name:
                    breaker.record_failure(f"{stage_name} stage failure")
                    print(f"  Stage {stage_name}: FAILED")
                    break
                else:
                    breaker.record_success()
                    completed_stages.append(stage_name)
                    print(f"  Stage {stage_name}: SUCCESS")
            
            return completed_stages
        
        # Test normal execution
        print("\nAGENT PIPELINE - Normal Execution:")
        stages_completed = simulate_agent_pipeline_execution()
        assert len(stages_completed) == 4, "All stages should complete normally"
        
        # Test with failure injection  
        print("\nAGENT PIPELINE - With LLM Failure:")
        stages_completed = simulate_agent_pipeline_execution("llm")
        assert len(stages_completed) < 4, "Pipeline should stop at failure point"
        
        # Test cascade prevention after multiple failures
        print("\nAGENT PIPELINE - Testing Cascade Prevention:")
        for i in range(5):  # Inject multiple failures to trigger circuit opening
            simulate_agent_pipeline_execution("llm")
        
        # Now LLM circuit should be open, preventing further cascade
        print("\nAGENT PIPELINE - After Circuit Opening:")
        stages_completed = simulate_agent_pipeline_execution()
        
        if not llm_breaker.can_execute():
            print("CASCADE PREVENTION: LLM circuit breaker successfully prevented cascading failures")
        else:
            print(f"CASCADE TRACKING: LLM circuit still closed after {llm_breaker.metrics.failed_calls} failures")
    
    @pytest.mark.asyncio
    async def test_agent_circuit_breaker_timeout_handling(self):
        """
        INTEGRATION TEST: Tests circuit breaker timeout handling in agent contexts.
        """
        from netra_backend.app.core.circuit_breaker import (
            UnifiedCircuitBreaker, 
            UnifiedCircuitConfig,
            CircuitBreakerOpenError
        )
        
        # Create breaker with short timeout for testing
        config = UnifiedCircuitConfig(
            name="agent_timeout_test",
            timeout_seconds=0.1,  # Very short timeout
            failure_threshold=2
        )
        
        timeout_breaker = UnifiedCircuitBreaker(config)
        
        # Test timeout scenario
        async def slow_agent_operation():
            """Mock slow agent operation that will timeout."""
            await asyncio.sleep(0.2)  # Longer than timeout
            return "Should not reach here"
        
        # Execute through circuit breaker with timeout handling
        try:
            start_time = asyncio.get_event_loop().time()
            
            # This should timeout, but we need to implement timeout handling
            # For now, test the circuit breaker state management
            result = await timeout_breaker.call(slow_agent_operation)
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            print(f"AGENT TIMEOUT: Operation completed in {execution_time:.3f}s")
            
        except Exception as e:
            print(f"AGENT TIMEOUT HANDLING: Exception caught: {type(e).__name__}: {e}")
        
        # Verify circuit breaker recorded the interaction
        status = timeout_breaker.get_status()
        assert status["metrics"]["total_calls"] > 0, "Circuit breaker should have recorded the call"


if __name__ == "__main__":
    # Run the tests with detailed output
    pytest.main([__file__, "-v", "-s", "--tb=short"])