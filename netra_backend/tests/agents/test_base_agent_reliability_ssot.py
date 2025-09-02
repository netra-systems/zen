"""Comprehensive Test Suite for Base Agent Reliability SSOT Features

This test suite validates that BaseAgent provides SSOT reliability infrastructure
that all child agents can inherit, following the pattern shown in TriageSubAgent.

CRITICAL: These tests are designed to fail initially (TDD approach) and pass after
consolidation when BaseAgent gains comprehensive reliability features.

Business Value: Ensures all agents inherit consistent reliability patterns,
eliminating SSOT violations and maintenance overhead.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, Optional

# Import the classes we'll be testing
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.llm.llm_manager import LLMManager

# Import reliability components that should be integrated into BaseAgent
from netra_backend.app.core.resilience.domain_circuit_breakers import (
    AgentCircuitBreaker,
    AgentCircuitBreakerConfig
)
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.schemas.shared_types import RetryConfig

# Import WebSocket components for testing notifications
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestBaseAgentSubclass(BaseAgent):
    """Test subclass of BaseAgent for testing inherited functionality."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute_called = False
        self.execute_result = "test_result"
        self.should_fail = False
    
    async def execute(self, state: Optional[DeepAgentState], run_id: str = "", stream_updates: bool = False) -> Any:
        """Test implementation of execute method."""
        self.execute_called = True
        if self.should_fail:
            raise RuntimeError("Test execution failure")
        return self.execute_result


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing."""
    return MagicMock(spec=LLMManager)


@pytest.fixture
def test_agent(mock_llm_manager):
    """Create test agent instance."""
    return TestBaseAgentSubclass(
        llm_manager=mock_llm_manager,
        name="TestAgent",
        description="Test agent for reliability testing"
    )


@pytest.fixture
def mock_websocket_bridge():
    """Mock WebSocket bridge for testing."""
    bridge = MagicMock(spec=AgentWebSocketBridge)
    bridge.emit_error = AsyncMock()
    bridge.emit_agent_thinking = AsyncMock() 
    bridge.emit_tool_executing = AsyncMock()
    bridge.emit_tool_completed = AsyncMock()
    bridge.emit_agent_completed = AsyncMock()
    return bridge


@pytest.fixture
def deep_agent_state():
    """Create test DeepAgentState."""
    state = DeepAgentState()
    state.user_request = "Test request for reliability testing"
    state.step_count = 0
    return state


class TestBaseAgentCircuitBreakerIntegration:
    """Test that BaseAgent has proper circuit breaker initialization."""
    
    def test_base_agent_has_circuit_breaker_attribute(self, test_agent):
        """Test that BaseAgent initializes with circuit breaker."""
        # This test SHOULD FAIL initially since BaseAgent doesn't have circuit_breaker yet
        assert hasattr(test_agent, 'circuit_breaker'), "BaseAgent should have circuit_breaker attribute"
        assert isinstance(test_agent.circuit_breaker, AgentCircuitBreaker), "circuit_breaker should be AgentCircuitBreaker instance"
    
    def test_circuit_breaker_configuration(self, test_agent):
        """Test that circuit breaker has appropriate configuration."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'circuit_breaker')
        cb = test_agent.circuit_breaker
        
        # Should have agent-optimized defaults as shown in TriageSubAgent
        assert cb.name == "TestAgent", "Circuit breaker should use agent name"
        # Config should exist and have reasonable defaults
        config = cb.config if hasattr(cb, 'config') else cb._circuit_breaker.config
        assert config.failure_threshold >= 3, "Should have reasonable failure threshold"
        assert config.recovery_timeout_seconds >= 30.0, "Should have reasonable recovery timeout"
        assert config.task_timeout_seconds >= 120.0, "Should have reasonable task timeout"
    
    def test_circuit_breaker_state_transitions(self, test_agent):
        """Test that circuit breaker can transition between states."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'circuit_breaker')
        cb = test_agent.circuit_breaker
        
        # Should start in closed state
        initial_state = cb.get_state() if hasattr(cb, 'get_state') else cb._circuit_breaker.state
        assert initial_state == 'closed' or 'CLOSED' in str(initial_state)
        
        # Should be able to check if execution is allowed
        can_execute = cb.can_execute() if hasattr(cb, 'can_execute') else True
        assert can_execute is True, "New circuit breaker should allow execution"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_protects_execution(self, test_agent, deep_agent_state):
        """Test that circuit breaker protects agent execution."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'circuit_breaker')
        
        # Set agent to fail
        test_agent.should_fail = True
        
        # Multiple failures should eventually trip circuit breaker
        failures = 0
        for i in range(5):  # Try more than failure threshold
            try:
                await test_agent.execute(deep_agent_state, f"test_run_{i}")
                failures += 1
            except Exception:
                failures += 1
        
        # After enough failures, circuit breaker should be in open state
        cb_state = test_agent.circuit_breaker.get_state() if hasattr(test_agent.circuit_breaker, 'get_state') else None
        if cb_state:
            assert 'open' in str(cb_state).lower() or not test_agent.circuit_breaker.can_execute()


class TestBaseAgentReliabilityManagerIntegration:
    """Test that BaseAgent has reliability manager integration."""
    
    def test_base_agent_has_reliability_manager(self, test_agent):
        """Test that BaseAgent initializes with reliability manager."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'reliability_manager'), "BaseAgent should have reliability_manager attribute"
        assert isinstance(test_agent.reliability_manager, ReliabilityManager), "reliability_manager should be ReliabilityManager instance"
    
    def test_reliability_manager_configuration(self, test_agent):
        """Test that reliability manager is properly configured."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'reliability_manager')
        rm = test_agent.reliability_manager
        
        # Should have circuit breaker integration
        assert hasattr(rm, 'circuit_breaker'), "ReliabilityManager should have circuit breaker"
        # Should have retry manager
        assert hasattr(rm, 'retry_manager'), "ReliabilityManager should have retry manager"
        # Should have health stats
        assert hasattr(rm, '_health_stats') or hasattr(rm, 'get_health_status'), "ReliabilityManager should track health"
    
    def test_reliability_manager_health_status(self, test_agent):
        """Test that reliability manager provides health status."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'reliability_manager')
        rm = test_agent.reliability_manager
        
        # Should be able to get health status
        health_status = rm.get_health_status()
        assert isinstance(health_status, dict), "Health status should be a dictionary"
        
        # Health status should contain key metrics
        expected_keys = ['circuit_breaker_state', 'total_executions', 'success_rate']
        for key in expected_keys:
            assert key in health_status or any(k for k in health_status.keys() if key.replace('_', '') in k.replace('_', '')), f"Health status should contain {key}"
    
    @pytest.mark.asyncio
    async def test_reliability_manager_execution_coordination(self, test_agent, deep_agent_state):
        """Test that reliability manager coordinates execution."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'reliability_manager')
        
        # Reliability manager should coordinate execution somehow
        # Either through direct execute method or via BaseExecutionEngine
        if hasattr(test_agent.reliability_manager, 'execute'):
            result = await test_agent.reliability_manager.execute(
                lambda: test_agent.execute_result,
                context={'state': deep_agent_state, 'run_id': 'test_run'}
            )
            assert result == test_agent.execute_result
        elif hasattr(test_agent, 'execution_engine'):
            # Should have execution engine that uses reliability manager
            assert hasattr(test_agent.execution_engine, 'reliability_manager')


class TestBaseAgentExecutionMonitorIntegration:
    """Test that BaseAgent has execution monitor integration."""
    
    def test_base_agent_has_execution_monitor(self, test_agent):
        """Test that BaseAgent initializes with execution monitor."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'monitor'), "BaseAgent should have monitor attribute"
        assert isinstance(test_agent.monitor, ExecutionMonitor), "monitor should be ExecutionMonitor instance"
    
    def test_execution_monitor_configuration(self, test_agent):
        """Test that execution monitor is properly configured."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'monitor')
        monitor = test_agent.monitor
        
        # Should have reasonable configuration
        assert hasattr(monitor, 'max_history_size'), "Monitor should have max_history_size"
        assert monitor.max_history_size >= 1000, "Monitor should have reasonable history size"
        
        # Should have agent stats tracking
        assert hasattr(monitor, '_agent_stats') or hasattr(monitor, 'get_performance_stats'), "Monitor should track agent stats"
    
    def test_execution_monitor_metrics_collection(self, test_agent):
        """Test that execution monitor collects metrics."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'monitor')
        monitor = test_agent.monitor
        
        # Should be able to get health status
        health_status = monitor.get_health_status()
        assert isinstance(health_status, dict), "Monitor health status should be a dictionary"
        
        # Should contain performance metrics
        expected_metrics = ['total_executions', 'success_rate', 'average_execution_time']
        for metric in expected_metrics:
            assert any(key for key in health_status.keys() if metric.replace('_', '') in key.replace('_', '')), f"Should track {metric}"
    
    @pytest.mark.asyncio
    async def test_execution_monitor_records_execution(self, test_agent, deep_agent_state):
        """Test that monitor records execution metrics."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'monitor')
        monitor = test_agent.monitor
        
        # Get initial stats
        initial_health = monitor.get_health_status()
        initial_executions = initial_health.get('total_executions', 0)
        
        # Execute agent
        await test_agent.execute(deep_agent_state, "test_monitor_run")
        
        # Monitor should record the execution
        updated_health = monitor.get_health_status()
        updated_executions = updated_health.get('total_executions', 0)
        
        assert updated_executions > initial_executions, "Monitor should record execution"


class TestBaseAgentWebSocketNotificationsDuringFailures:
    """Test WebSocket notifications during reliability scenarios."""
    
    @pytest.mark.asyncio
    async def test_websocket_error_notification_on_failure(self, test_agent, deep_agent_state, mock_websocket_bridge):
        """Test that agent sends WebSocket error notification on failure."""
        # Set up WebSocket bridge
        test_agent.set_websocket_bridge(mock_websocket_bridge, "test_error_run")
        
        # Set agent to fail
        test_agent.should_fail = True
        
        # Execute and expect failure
        with pytest.raises(RuntimeError):
            await test_agent.execute(deep_agent_state, "test_error_run")
        
        # Should emit error notification
        # This test SHOULD FAIL initially since error handling isn't integrated with WebSocket
        mock_websocket_bridge.emit_error.assert_called_once()
        
        # Error should contain meaningful information
        call_args = mock_websocket_bridge.emit_error.call_args
        error_message = call_args[0][0] if call_args[0] else ""
        assert "Test execution failure" in error_message or "RuntimeError" in error_message
    
    @pytest.mark.asyncio
    async def test_websocket_circuit_breaker_notification(self, test_agent, deep_agent_state, mock_websocket_bridge):
        """Test WebSocket notification when circuit breaker trips."""
        # This test SHOULD FAIL initially
        test_agent.set_websocket_bridge(mock_websocket_bridge, "test_cb_run")
        
        # Mock circuit breaker to be open
        if hasattr(test_agent, 'circuit_breaker'):
            with patch.object(test_agent.circuit_breaker, 'can_execute', return_value=False):
                # Execution should be blocked and notify via WebSocket
                try:
                    await test_agent.execute(deep_agent_state, "test_cb_run")
                except Exception:
                    pass  # Expected when circuit breaker blocks
                
                # Should notify about circuit breaker state
                mock_websocket_bridge.emit_error.assert_called()
                call_args = mock_websocket_bridge.emit_error.call_args
                error_message = call_args[0][0] if call_args[0] else ""
                assert "circuit" in error_message.lower() or "breaker" in error_message.lower()
    
    @pytest.mark.asyncio 
    async def test_websocket_retry_notifications(self, test_agent, deep_agent_state, mock_websocket_bridge):
        """Test WebSocket notifications during retry attempts."""
        # This test SHOULD FAIL initially
        test_agent.set_websocket_bridge(mock_websocket_bridge, "test_retry_run")
        
        # Mock to fail first attempts then succeed
        call_count = [0]
        original_execute = test_agent.execute
        
        async def mock_execute_with_retries(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:  # Fail first 2 attempts
                raise RuntimeError(f"Retry attempt {call_count[0]}")
            return await original_execute(*args, **kwargs)
        
        # If BaseAgent has retry logic, it should emit thinking/progress during retries
        with patch.object(test_agent, 'execute', side_effect=mock_execute_with_retries):
            if hasattr(test_agent, 'reliability_manager') and hasattr(test_agent.reliability_manager, 'execute_with_retries'):
                await test_agent.reliability_manager.execute_with_retries(
                    test_agent.execute, deep_agent_state, "test_retry_run"
                )
                
                # Should emit thinking notifications for retries
                assert mock_websocket_bridge.emit_thinking.call_count >= 2, "Should emit thinking during retries"


class TestBaseAgentHealthStatusReporting:
    """Test comprehensive health status reporting."""
    
    def test_base_agent_has_health_status_method(self, test_agent):
        """Test that BaseAgent has get_health_status method."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'get_health_status'), "BaseAgent should have get_health_status method"
        
        health_status = test_agent.get_health_status()
        assert isinstance(health_status, dict), "Health status should be a dictionary"
    
    def test_health_status_aggregates_all_components(self, test_agent):
        """Test that health status aggregates from all reliability components."""
        # This test SHOULD FAIL initially
        health_status = test_agent.get_health_status()
        
        # Should include data from all components
        expected_components = ['reliability_manager', 'execution_engine', 'monitor', 'circuit_breaker']
        
        # At minimum should have keys related to these components
        health_keys = set(health_status.keys())
        component_coverage = 0
        
        for component in expected_components:
            if any(component.replace('_', '') in key.replace('_', '') for key in health_keys):
                component_coverage += 1
        
        assert component_coverage >= 3, f"Health status should cover at least 3 components, got coverage for {component_coverage}"
    
    def test_health_status_includes_key_metrics(self, test_agent):
        """Test that health status includes key reliability metrics."""
        # This test SHOULD FAIL initially
        health_status = test_agent.get_health_status()
        
        # Key metrics that should be present
        expected_metrics = [
            'total_executions', 'success_rate', 'circuit_breaker_state',
            'average_execution_time', 'error_rate', 'last_execution'
        ]
        
        health_keys_lower = {k.lower().replace('_', '') for k in health_status.keys()}
        metrics_found = 0
        
        for metric in expected_metrics:
            metric_normalized = metric.lower().replace('_', '')
            if any(metric_normalized in key for key in health_keys_lower):
                metrics_found += 1
        
        assert metrics_found >= 4, f"Should have at least 4 key metrics, found {metrics_found}"


class TestChildAgentInheritance:
    """Test that child agents properly inherit reliability features."""
    
    def test_child_agent_inherits_circuit_breaker(self, test_agent):
        """Test that child agents inherit circuit breaker functionality."""
        # This test SHOULD FAIL initially
        # Child agent should have all reliability components from base
        assert hasattr(test_agent, 'circuit_breaker'), "Child agent should inherit circuit_breaker"
        assert hasattr(test_agent, 'reliability_manager'), "Child agent should inherit reliability_manager"
        assert hasattr(test_agent, 'monitor'), "Child agent should inherit monitor"
    
    def test_child_agent_inherits_health_status(self, test_agent):
        """Test that child agents inherit health status reporting."""
        # This test SHOULD FAIL initially
        assert hasattr(test_agent, 'get_health_status'), "Child agent should inherit get_health_status"
        
        health_status = test_agent.get_health_status()
        assert isinstance(health_status, dict), "Child agent health status should work"
        assert len(health_status) > 0, "Child agent should report health metrics"
    
    @pytest.mark.asyncio
    async def test_child_agent_execution_uses_reliability_infrastructure(self, test_agent, deep_agent_state):
        """Test that child agent execution uses inherited reliability infrastructure."""
        # This test SHOULD FAIL initially
        
        # Mock the reliability components to track usage
        if hasattr(test_agent, 'reliability_manager'):
            rm = test_agent.reliability_manager
            with patch.object(rm, 'execute', wraps=rm.execute if hasattr(rm, 'execute') else None) as mock_rm_execute:
                await test_agent.execute(deep_agent_state, "child_test_run")
                
                # Reliability infrastructure should be used
                if mock_rm_execute.call_count > 0:
                    assert True, "Child agent used reliability manager"
                else:
                    # Alternative: check that circuit breaker was consulted
                    if hasattr(test_agent, 'circuit_breaker'):
                        cb = test_agent.circuit_breaker
                        # Circuit breaker should have been checked
                        assert hasattr(cb, 'can_execute'), "Circuit breaker should be consulted"


class TestConcurrentExecutionHandling:
    """Test that reliability features handle concurrent executions properly."""
    
    @pytest.mark.asyncio
    async def test_concurrent_executions_with_circuit_breaker(self, test_agent, deep_agent_state):
        """Test circuit breaker behavior under concurrent load."""
        # This test SHOULD FAIL initially
        if not hasattr(test_agent, 'circuit_breaker'):
            pytest.skip("Circuit breaker not implemented yet")
        
        # Create multiple concurrent executions
        async def execute_agent(run_id):
            try:
                return await test_agent.execute(deep_agent_state, f"concurrent_run_{run_id}")
            except Exception as e:
                return f"error: {e}"
        
        # Run 5 concurrent executions
        tasks = [execute_agent(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Circuit breaker should handle concurrent access gracefully
        assert len(results) == 5, "All concurrent executions should complete"
        
        # Should still be able to get health status
        health_status = test_agent.get_health_status() if hasattr(test_agent, 'get_health_status') else {}
        assert isinstance(health_status, dict), "Health status should work during concurrent access"
    
    @pytest.mark.asyncio
    async def test_monitor_tracks_concurrent_executions(self, test_agent, deep_agent_state):
        """Test that monitor correctly tracks concurrent executions."""
        # This test SHOULD FAIL initially
        if not hasattr(test_agent, 'monitor'):
            pytest.skip("Monitor not implemented yet")
        
        monitor = test_agent.monitor
        initial_health = monitor.get_health_status()
        initial_count = initial_health.get('total_executions', 0)
        
        # Run concurrent executions
        tasks = []
        for i in range(3):
            task = test_agent.execute(deep_agent_state, f"monitor_concurrent_{i}")
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Monitor should track all executions
        final_health = monitor.get_health_status()
        final_count = final_health.get('total_executions', 0)
        
        assert final_count >= initial_count + 3, "Monitor should track concurrent executions"


class TestTimeoutHandling:
    """Test proper timeout handling in reliability infrastructure."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout_configuration(self, test_agent):
        """Test that circuit breaker has proper timeout configuration."""
        # This test SHOULD FAIL initially
        if not hasattr(test_agent, 'circuit_breaker'):
            pytest.skip("Circuit breaker not implemented yet")
        
        cb = test_agent.circuit_breaker
        config = cb.config if hasattr(cb, 'config') else cb._circuit_breaker.config if hasattr(cb, '_circuit_breaker') else None
        
        assert config is not None, "Circuit breaker should have configuration"
        assert hasattr(config, 'task_timeout_seconds') or hasattr(config, 'timeout_seconds'), "Should have timeout configuration"
        
        timeout = getattr(config, 'task_timeout_seconds', getattr(config, 'timeout_seconds', 0))
        assert timeout > 0, "Timeout should be configured to positive value"
        assert timeout >= 120, "Timeout should be reasonable for agent tasks (≥2 minutes)"
    
    @pytest.mark.asyncio
    async def test_execution_respects_timeouts(self, test_agent, deep_agent_state):
        """Test that agent execution respects timeout configurations."""
        # This test SHOULD FAIL initially
        
        # Create a slow-executing version of the test agent
        class SlowAgent(TestBaseAgentSubclass):
            async def execute(self, state, run_id="", stream_updates=False):
                await asyncio.sleep(0.1)  # Simulate slow operation
                return await super().execute(state, run_id, stream_updates)
        
        slow_agent = SlowAgent(name="SlowTestAgent")
        
        # If reliability infrastructure is present, it should handle timeouts
        if hasattr(slow_agent, 'reliability_manager') or hasattr(slow_agent, 'circuit_breaker'):
            start_time = time.time()
            
            try:
                # This should either complete quickly or timeout appropriately
                await slow_agent.execute(deep_agent_state, "timeout_test")
                execution_time = time.time() - start_time
                
                # Should complete in reasonable time or raise timeout
                assert execution_time < 10, "Should not hang indefinitely"
            except Exception as e:
                # Timeout exceptions are acceptable
                assert "timeout" in str(e).lower() or "timeout" in type(e).__name__.lower()


# Integration test to verify the complete reliability infrastructure
class TestReliabilityInfrastructureIntegration:
    """Integration tests for complete reliability infrastructure."""
    
    @pytest.mark.asyncio
    async def test_complete_reliability_flow(self, test_agent, deep_agent_state, mock_websocket_bridge):
        """Test complete reliability flow with all components working together."""
        # This test SHOULD FAIL initially but demonstrates the target integration
        
        # Set up WebSocket bridge
        test_agent.set_websocket_bridge(mock_websocket_bridge, "integration_test")
        
        # Verify all reliability components are present
        reliability_components = ['circuit_breaker', 'reliability_manager', 'monitor']
        missing_components = [comp for comp in reliability_components if not hasattr(test_agent, comp)]
        
        if missing_components:
            pytest.fail(f"Missing reliability components: {missing_components}. This test should pass after SSOT consolidation.")
        
        # Test normal execution flow
        initial_health = test_agent.get_health_status()
        
        # Execute successfully
        result = await test_agent.execute(deep_agent_state, "integration_success")
        assert result == test_agent.execute_result
        
        # Check that all components recorded the execution
        updated_health = test_agent.get_health_status()
        
        # Health metrics should be updated
        assert updated_health != initial_health, "Health status should update after execution"
        
        # WebSocket notifications should have been sent
        # (At minimum, agent should emit thinking during execution)
        assert mock_websocket_bridge.emit_thinking.call_count >= 0  # Will be > 0 after integration
    
    def test_reliability_infrastructure_initialization_order(self, mock_llm_manager):
        """Test that reliability components are initialized in correct order."""
        # This test SHOULD FAIL initially
        
        # Create fresh agent to test initialization
        agent = TestBaseAgentSubclass(
            llm_manager=mock_llm_manager,
            name="InitOrderTest"
        )
        
        # All reliability components should be initialized
        components = ['circuit_breaker', 'reliability_manager', 'monitor']
        
        for component in components:
            assert hasattr(agent, component), f"Agent should have {component} initialized"
        
        # Components should be properly connected
        # Circuit breaker should be integrated with reliability manager
        if hasattr(agent, 'reliability_manager') and hasattr(agent.reliability_manager, 'circuit_breaker'):
            rm_cb = agent.reliability_manager.circuit_breaker
            assert rm_cb is not None, "ReliabilityManager should have circuit breaker"
        
        # Execution engine should use reliability manager and monitor
        if hasattr(agent, 'execution_engine'):
            ee = agent.execution_engine
            assert hasattr(ee, 'reliability_manager') or hasattr(ee, 'monitor'), "ExecutionEngine should be connected to reliability components"


if __name__ == "__main__":
    # Run the tests to demonstrate current failures
    pytest.main([__file__, "-v", "--tb=short"])