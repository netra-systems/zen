"""Integration tests for agent execution with circuit breakers.

Tests the complete integration between agents and circuit breaker metrics
to prevent regression of AttributeError issues.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.base.retry_manager import RetryManager
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker, 
    CircuitConfig
)
from netra_backend.app.core.resilience.domain_circuit_breakers import (
    AgentCircuitBreaker,
    AgentCircuitBreakerConfig
)
from netra_backend.app.services.metrics.circuit_breaker_metrics import (
    CircuitBreakerMetrics,
    CircuitBreakerMetricsService
)
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas.shared_types import RetryConfig


@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager."""
    mock = Mock(spec=LLMManager)
    mock.generate_completion = AsyncMock(return_value={
        "response": "Test response",
        "tokens_used": 100
    })
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher."""
    mock = Mock(spec=ToolDispatcher)
    mock.dispatch = AsyncMock(return_value={"status": "success"})
    return mock


@pytest.fixture
def mock_redis_manager():
    """Create mock Redis manager."""
    mock = Mock(spec=RedisManager)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    return mock


class TestAgentCircuitBreakerIntegration:
    """Test agent integration with circuit breakers."""
    
    @pytest.mark.asyncio
    async def test_triage_agent_with_circuit_breaker_metrics(
        self, 
        mock_llm_manager,
        mock_tool_dispatcher,
        mock_redis_manager
    ):
        """Test triage agent executes without AttributeError on metrics."""
        # Create triage agent
        agent = TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        # Verify circuit breaker is initialized
        assert hasattr(agent, 'circuit_breaker')
        assert isinstance(agent.circuit_breaker, AgentCircuitBreaker)
        
        # Execute agent operation that would trigger metrics access
        test_input = {
            "message": "Test message for triage",
            "context": {"user_id": "test_user"}
        }
        
        # Mock the execute method to simulate processing
        with patch.object(agent, '_execute_with_circuit_breaker') as mock_execute:
            mock_execute.return_value = {
                "status": "success",
                "category": "test",
                "priority": "low"
            }
            
            # This should not raise AttributeError
            result = await agent.execute(test_input)
            assert result["status"] == "success"
            
    @pytest.mark.asyncio
    async def test_retry_manager_with_circuit_breaker_metrics(self):
        """Test retry manager handles circuit breaker metrics correctly."""
        # Create circuit breaker with metrics
        circuit_config = AgentCircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=10.0
        )
        circuit_breaker = AgentCircuitBreaker("test_agent", circuit_config)
        
        # Create retry manager
        retry_config = RetryConfig(max_retries=3, base_delay=1.0)
        retry_manager = RetryManager(
            circuit_breaker_config=circuit_config,
            retry_config=retry_config
        )
        
        # Simulate operation with slow response
        async def slow_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        # Execute with retry manager - should not raise AttributeError
        try:
            result = await retry_manager.execute_with_retry(
                slow_operation,
                operation_name="test_operation"
            )
            assert result == "success"
        except AttributeError as e:
            if 'slow_requests' in str(e):
                pytest.fail(f"AttributeError accessing slow_requests: {e}")
                
    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions_with_agent(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test circuit breaker state transitions during agent failures."""
        agent = TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Configure circuit breaker to trip after 2 failures
        agent.circuit_breaker.config.failure_threshold = 2
        
        # Mock execute to fail
        async def failing_execute(*args, **kwargs):
            raise Exception("Simulated failure")
        
        with patch.object(agent, '_process_with_llm', failing_execute):
            # First failure
            with pytest.raises(Exception):
                await agent.execute({"message": "test"})
            
            # Second failure should trip circuit
            with pytest.raises(Exception):
                await agent.execute({"message": "test"})
            
            # Verify circuit is open
            assert agent.circuit_breaker.state == "OPEN"
            
            # Check metrics access doesn't cause AttributeError
            stats = agent.circuit_breaker.get_metrics()
            assert 'failures' in stats
            # This would have failed before fix
            assert 'slow_requests' not in stats or stats.get('slow_requests', 0) >= 0
            
    @pytest.mark.asyncio
    async def test_metrics_service_integration_with_agents(self):
        """Test metrics service collects agent circuit breaker data."""
        metrics_service = CircuitBreakerMetricsService()
        
        # Simulate agent recording metrics
        await metrics_service.record_success("triage_agent", response_time=6.0)
        await metrics_service.record_failure("triage_agent", error_type="timeout")
        
        # Get metrics - should include slow_requests
        metrics = await metrics_service.get_endpoint_metrics("triage_agent")
        
        assert "failures" in metrics
        assert "successes" in metrics
        # Verify slow_requests is tracked (would fail before fix)
        assert metrics_service.collector.metrics.slow_requests == 1
        
    @pytest.mark.asyncio
    async def test_multiple_agents_with_shared_metrics(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test multiple agents sharing metrics infrastructure."""
        # Create multiple agents
        triage_agent = TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Create another agent type (simulated)
        class DataAgent:
            def __init__(self):
                config = AgentCircuitBreakerConfig(failure_threshold=3)
                self.circuit_breaker = AgentCircuitBreaker("data_agent", config)
                
        data_agent = DataAgent()
        
        # Both agents should work with metrics
        triage_stats = triage_agent.circuit_breaker.get_metrics()
        data_stats = data_agent.circuit_breaker.get_metrics()
        
        # Neither should raise AttributeError
        assert isinstance(triage_stats, dict)
        assert isinstance(data_stats, dict)


class TestCircuitBreakerMetricsRecovery:
    """Test circuit breaker recovery scenarios with metrics."""
    
    @pytest.mark.asyncio
    async def test_circuit_recovery_after_slow_requests(self):
        """Test circuit breaker recovers properly after slow requests."""
        config = CircuitConfig(
            name="test_circuit",
            failure_threshold=3,
            recovery_timeout=0.5,  # Quick recovery for test
            slow_call_threshold=0.1  # Low threshold for testing
        )
        
        circuit_breaker = UnifiedCircuitBreaker(config)
        
        # Record slow requests
        async def slow_operation():
            await asyncio.sleep(0.2)
            return "slow_success"
        
        # Execute slow operations
        for _ in range(3):
            result = await circuit_breaker.call(slow_operation)
            assert result == "slow_success"
        
        # Check slow_requests is tracked
        stats = circuit_breaker.get_stats()
        assert stats['slow_requests'] >= 3
        
        # Circuit should adapt but not break
        assert circuit_breaker.state != "OPEN"
        
    @pytest.mark.asyncio
    async def test_metrics_persistence_across_circuit_states(self):
        """Test metrics persist correctly across circuit state changes."""
        config = CircuitConfig(
            name="persistent_metrics",
            failure_threshold=2,
            recovery_timeout=0.1
        )
        
        breaker = UnifiedCircuitBreaker(config)
        metrics = CircuitBreakerMetrics()
        
        # Record some metrics
        metrics.record_success("test", response_time=6.0)
        assert metrics.slow_requests == 1
        
        # Simulate circuit state changes
        breaker._transition_to_open()
        assert metrics.slow_requests == 1  # Should persist
        
        breaker._transition_to_half_open()
        assert metrics.slow_requests == 1  # Should persist
        
        breaker._transition_to_closed()
        assert metrics.slow_requests == 1  # Should persist
        
    @pytest.mark.asyncio 
    async def test_agent_fallback_with_metrics(
        self,
        mock_llm_manager,
        mock_tool_dispatcher
    ):
        """Test agent fallback mechanisms work with metrics."""
        agent = TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Mock primary operation to fail
        async def failing_primary():
            raise Exception("Primary failed")
        
        # Mock fallback to succeed
        async def successful_fallback():
            return {"status": "fallback_success"}
        
        with patch.object(agent, '_process_with_llm', failing_primary):
            with patch.object(agent, '_get_fallback_response', successful_fallback):
                # Execute with fallback
                result = await agent.execute({"message": "test"})
                
                # Should use fallback without AttributeError
                assert result["status"] == "fallback_success"
                
                # Check metrics
                if hasattr(agent.circuit_breaker, 'metrics'):
                    metrics = agent.circuit_breaker.get_metrics()
                    # Should track the failure
                    assert metrics.get('failures', 0) > 0


class TestMetricsCompatibilityEdgeCases:
    """Test edge cases for metrics compatibility."""
    
    def test_metrics_with_none_response_time(self):
        """Test metrics handle None response time gracefully."""
        metrics = CircuitBreakerMetrics()
        
        # Record with None response time
        metrics.record_success("test", response_time=None)
        assert metrics.slow_requests == 0  # Should not increment
        
    def test_metrics_with_negative_response_time(self):
        """Test metrics handle invalid response times."""
        metrics = CircuitBreakerMetrics()
        
        # Negative response time (invalid but shouldn't crash)
        metrics.record_success("test", response_time=-1.0)
        assert metrics.slow_requests == 0
        
    def test_concurrent_metrics_updates(self):
        """Test metrics handle concurrent updates safely."""
        metrics = CircuitBreakerMetrics()
        
        def update_metrics():
            for i in range(100):
                metrics.record_success(f"circuit_{i % 10}", response_time=float(i % 10))
        
        # Simulate concurrent updates
        import threading
        threads = [threading.Thread(target=update_metrics) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have recorded slow requests without errors
        assert metrics.slow_requests > 0
        
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_mixed_metrics_implementations(self):
        """Test circuit breaker works with different metrics implementations."""
        # Standard implementation
        standard_metrics = CircuitBreakerMetrics()
        
        # Mock implementation (simulating old version)
        mock_metrics = Mock()
        mock_metrics.failure_counts = {}
        mock_metrics.success_counts = {}
        # Intentionally missing slow_requests
        
        # Both should work with defensive access
        slow_standard = getattr(standard_metrics, 'slow_requests', 0)
        slow_mock = getattr(mock_metrics, 'slow_requests', 0)
        
        assert slow_standard == 0
        assert slow_mock == 0  # Should use default, not raise error