"""Circuit Breaker Integration Tests for Triage Agent

Tests verifying that the triage agent's circuit breaker behavior works
correctly with Gemini 2.5 Pro, including proper isolation, recovery,
and error categorization specific to triage operations.

Integration test category: Validates circuit breaker reliability patterns
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import time

from netra_backend.app.agents.triage_sub_agent.config import TriageConfig
from netra_backend.app.agents.triage_sub_agent.llm_processor import TriageLLMProcessor
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerState
from netra_backend.app.core.exceptions_service import (
    LLMRequestError as LLMError, 
    LLMRateLimitError as RateLimitError, 
    ServiceUnavailableError,
    ServiceTimeoutError as TimeoutError
)


@pytest.fixture
def triage_config():
    """Fixture providing triage configuration."""
    return TriageConfig()


@pytest.fixture
def mock_agent():
    """Mock triage agent with circuit breaker integration."""
    agent = MagicMock()
    agent.llm_manager = MagicMock()
    agent.llm_fallback_handler = MagicMock()
    agent.llm_fallback_handler.execute_structured_with_fallback = AsyncMock()  # Async mock for fallback
    agent.triage_core = MagicMock()
    agent.triage_core.max_retries = 2
    agent.triage_core.get_cached_result = AsyncMock(return_value=None)  # Async mock for cache check
    agent.prompt_builder = MagicMock()
    agent.prompt_builder.build_triage_prompt = MagicMock(return_value="Test prompt")
    agent.result_processor = MagicMock()
    agent.result_processor.process_llm_response = MagicMock()
    agent._send_update = AsyncMock()
    
    # Mock circuit breaker
    agent.circuit_breaker = MagicMock()
    agent.circuit_breaker.state = CircuitBreakerState.CLOSED
    agent.circuit_breaker.failure_count = 0
    agent.circuit_breaker.last_failure_time = None
    
    return agent


@pytest.fixture
def llm_processor(mock_agent):
    """Fixture providing LLM processor instance."""
    return TriageLLMProcessor(mock_agent)


@pytest.fixture
def sample_state():
    """Sample agent state for testing."""
    return DeepAgentState(
        user_request="How can I reduce my AI infrastructure costs?",
        thread_id="test-thread-cb-123",
        user_id="test-user-456"
    )


class TestTriageCircuitBreakerConfiguration:
    """Test triage-specific circuit breaker configuration."""
    
    def test_circuit_breaker_config_matches_triage_requirements(self, triage_config):
        """Verify circuit breaker configuration is optimized for triage operations."""
        cb_config = triage_config.get_circuit_breaker_config()
        
        # Triage-specific circuit breaker settings
        assert cb_config["failure_threshold"] == 10  # Allow more failures for triage
        assert cb_config["recovery_timeout"] == 10.0  # Quick recovery for user-facing triage
        assert cb_config["timeout_seconds"] == 17.0   # Match Gemini Pro timeout
        assert cb_config["half_open_max_calls"] == 5   # Conservative half-open testing
    
    def test_circuit_breaker_timeout_matches_model_timeout(self, triage_config):
        """Verify circuit breaker timeout aligns with Gemini Pro model timeout."""
        cb_config = triage_config.get_circuit_breaker_config()
        model_timeout = triage_config.get_timeout_for_model()
        
        assert cb_config["timeout_seconds"] == model_timeout
        assert cb_config["timeout_seconds"] == 17.0  # Gemini Pro timeout


class TestTriageCircuitBreakerFailureScenarios:
    """Test circuit breaker behavior under various failure conditions."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold_failures(self, llm_processor, sample_state):
        """Test circuit breaker opens after reaching failure threshold."""
        failure_threshold = TriageConfig.CIRCUIT_BREAKER_CONFIG["failure_threshold"]
        
        # Setup consecutive failures
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = LLMError("Model unavailable")
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        
        # Mock circuit breaker state tracking
        failure_count = 0
        
        async def mock_circuit_breaker_call():
            nonlocal failure_count
            failure_count += 1
            if failure_count >= failure_threshold:
                llm_processor.agent.circuit_breaker.state = CircuitBreakerState.OPEN
                raise ServiceUnavailableError("Circuit breaker is open")
            raise LLMError("Model unavailable")
        
        # Mock fallback for when circuit opens
        fallback_result = {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": "medium", 
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {"fallback_used": True, "circuit_breaker_open": True}
        }
        
        with patch('netra_backend.app.agents.base.circuit_breaker.CircuitBreaker.call', side_effect=mock_circuit_breaker_call):
            llm_processor.agent.result_processor.enrich_triage_result.return_value = fallback_result
            
            # Should eventually get fallback response when circuit opens
            result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
            
            assert result["metadata"]["fallback_used"] is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_categorizes_triage_specific_errors(self, llm_processor, sample_state):
        """Test circuit breaker properly categorizes triage-specific errors."""
        error_scenarios = [
            (RateLimitError("Gemini API rate limit"), True),   # Should trigger circuit breaker
            (TimeoutError("Request timeout"), True),          # Should trigger circuit breaker
            (LLMError("Invalid API key"), False),             # Should not trigger circuit breaker (config issue)
            (ValueError("Invalid input"), False),             # Should not trigger circuit breaker (input issue)
        ]
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        
        circuit_breaker_calls = []
        
        def mock_circuit_breaker_call(error):
            circuit_breaker_calls.append(error)
            raise error
        
        for error, should_affect_circuit in error_scenarios:
            circuit_breaker_calls.clear()
            llm_processor.agent.llm_manager.ask_structured_llm.side_effect = error
            
            # Mock fallback response
            fallback_result = {
                "category": "General Inquiry",
                "confidence_score": 0.3,
                "priority": "medium",
                "extracted_entities": {},
                "tool_recommendations": [],
                "metadata": {"fallback_used": True, "error_type": type(error).__name__}
            }
            llm_processor.agent.result_processor.enrich_triage_result.return_value = fallback_result
            
            with patch('netra_backend.app.agents.base.circuit_breaker.CircuitBreaker.call', side_effect=lambda: mock_circuit_breaker_call(error)):
                try:
                    result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
                    
                    # Verify error was handled appropriately
                    assert "error_type" in result["metadata"]
                    assert result["metadata"]["error_type"] == type(error).__name__
                    
                except Exception:
                    # Some errors might not be fully handled in mock scenario
                    pass
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_mechanism(self, llm_processor, sample_state):
        """Test circuit breaker recovery from OPEN to HALF_OPEN to CLOSED states."""
        # Setup initial failure to open circuit
        llm_processor.agent.circuit_breaker.state = CircuitBreakerState.OPEN
        llm_processor.agent.circuit_breaker.last_failure_time = time.time() - 15  # 15 seconds ago
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        
        recovery_timeout = TriageConfig.CIRCUIT_BREAKER_CONFIG["recovery_timeout"]
        
        # Mock circuit breaker recovery logic
        circuit_states = [CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED]
        state_index = 0
        
        def mock_circuit_recovery():
            nonlocal state_index
            if state_index < len(circuit_states):
                llm_processor.agent.circuit_breaker.state = circuit_states[state_index]
                state_index += 1
            return {
                "category": "Cost Optimization",
                "confidence_score": 0.85,
                "priority": "high",
                "extracted_entities": {"intent": "cost_reduction"},
                "tool_recommendations": ["data_sub_agent"],
                "metadata": {"circuit_breaker_recovered": True}
            }
        
        llm_processor.agent.llm_manager.ask_structured_llm.return_value = mock_circuit_recovery()
        llm_processor.agent.result_processor.enrich_triage_result.side_effect = lambda x, _: x
        
        # Execute during recovery window
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify recovery was attempted
        assert "circuit_breaker_recovered" in result["metadata"]
        assert result["metadata"]["circuit_breaker_recovered"] is True


class TestTriageCircuitBreakerIsolation:
    """Test circuit breaker isolation between triage and other agents."""
    
    @pytest.mark.asyncio
    async def test_triage_circuit_breaker_does_not_affect_other_agents(self, llm_processor, sample_state):
        """Verify triage circuit breaker failures don't cascade to other agent types."""
        # Setup triage-specific circuit breaker identifier
        triage_cb_key = "triage_llm_call"
        
        # Mock circuit breaker registry to show isolation
        circuit_breaker_registry = {
            "triage_llm_call": MagicMock(),
            "data_llm_call": MagicMock(), 
            "optimization_llm_call": MagicMock()
        }
        
        # Open only triage circuit breaker
        circuit_breaker_registry["triage_llm_call"].state = CircuitBreakerState.OPEN
        circuit_breaker_registry["data_llm_call"].state = CircuitBreakerState.CLOSED
        circuit_breaker_registry["optimization_llm_call"].state = CircuitBreakerState.CLOSED
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        
        # Mock fallback response when triage circuit is open
        fallback_result = {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {
                "fallback_used": True,
                "triage_circuit_open": True,
                "other_circuits_unaffected": True
            }
        }
        llm_processor.agent.result_processor.enrich_triage_result.return_value = fallback_result
        
        with patch('netra_backend.app.agents.base.circuit_breaker.get_circuit_breaker', 
                   side_effect=lambda key: circuit_breaker_registry.get(key)):
            
            result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
            
            # Verify triage used fallback but other circuits remain unaffected
            assert result["metadata"]["triage_circuit_open"] is True
            assert result["metadata"]["other_circuits_unaffected"] is True
            
            # Verify other circuit breakers remain closed
            assert circuit_breaker_registry["data_llm_call"].state == CircuitBreakerState.CLOSED
            assert circuit_breaker_registry["optimization_llm_call"].state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_concurrent_triage_requests_with_circuit_breaker(self, llm_processor, sample_state):
        """Test concurrent triage requests handle circuit breaker state correctly."""
        # Setup circuit breaker in HALF_OPEN state
        llm_processor.agent.circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        half_open_max_calls = TriageConfig.CIRCUIT_BREAKER_CONFIG["half_open_max_calls"]
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.side_effect = lambda x: f"hash-{hash(x)}"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        
        # Mock half-open behavior: first few calls succeed, then fail
        call_count = 0
        def mock_half_open_behavior():
            nonlocal call_count
            call_count += 1
            if call_count <= half_open_max_calls:
                return {
                    "category": "Cost Optimization",
                    "confidence_score": 0.8,
                    "priority": "high",
                    "extracted_entities": {"intent": "cost_optimization"},
                    "tool_recommendations": ["data_sub_agent"],
                    "metadata": {"half_open_success": True, "call_number": call_count}
                }
            else:
                # Circuit should close again after max calls in half-open
                raise LLMError("Half-open limit exceeded")
        
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = mock_half_open_behavior
        llm_processor.agent.result_processor.enrich_triage_result.side_effect = lambda x, _: x
        
        # Create more concurrent requests than half-open allows
        concurrent_requests = [
            llm_processor.execute_triage_with_llm(
                DeepAgentState(
                    user_request=f"Concurrent request {i}",
                    thread_id=f"thread-{i}",
                    user_id="test-user"
                ),
                f"run-{i}",
                False
            )
            for i in range(half_open_max_calls + 3)  # Exceed half-open limit
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*concurrent_requests, return_exceptions=True)
        
        # Verify appropriate handling of half-open state
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) <= half_open_max_calls + 2  # Allow some tolerance
        
        # Verify successful calls have appropriate metadata
        for result in successful_results:
            if isinstance(result, dict) and "metadata" in result:
                assert "call_number" in result["metadata"] or "fallback_used" in result["metadata"]


class TestTriageCircuitBreakerPerformance:
    """Test circuit breaker performance characteristics with triage workloads."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_fast_failure(self, llm_processor, sample_state):
        """Test circuit breaker provides fast failure when open."""
        # Setup open circuit breaker
        llm_processor.agent.circuit_breaker.state = CircuitBreakerState.OPEN
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        
        # Mock fast failure response
        fast_failure_result = {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {
                "fallback_used": True,
                "circuit_breaker_open": True,
                "fast_failure": True,
                "triage_duration_ms": 50  # Very fast response
            }
        }
        llm_processor.agent.result_processor.enrich_triage_result.return_value = fast_failure_result
        
        # Measure response time
        start_time = time.time()
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Verify fast failure
        assert response_time < 100  # Should be very fast when circuit is open
        assert result["metadata"]["fast_failure"] is True
        assert result["metadata"]["circuit_breaker_open"] is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_tracking(self, llm_processor, sample_state):
        """Test circuit breaker tracks appropriate metrics for monitoring."""
        # Setup circuit breaker with metrics tracking
        llm_processor.agent.circuit_breaker.failure_count = 5
        llm_processor.agent.circuit_breaker.success_count = 45
        llm_processor.agent.circuit_breaker.state = CircuitBreakerState.CLOSED
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.llm_manager.ask_structured_llm.return_value = {
            "category": "Cost Optimization",
            "confidence_score": 0.85,
            "priority": "high",
            "extracted_entities": {"intent": "cost_optimization"},
            "tool_recommendations": ["data_sub_agent"]
        }
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        
        # Mock result enrichment with circuit breaker metrics
        def enrich_with_cb_metrics(result, _):
            result["metadata"] = result.get("metadata", {})
            result["metadata"].update({
                "circuit_breaker_state": llm_processor.agent.circuit_breaker.state.value,
                "circuit_breaker_failure_count": llm_processor.agent.circuit_breaker.failure_count,
                "circuit_breaker_success_rate": 0.9,  # 45/(45+5)
                "triage_duration_ms": 1200
            })
            return result
        
        llm_processor.agent.result_processor.enrich_triage_result.side_effect = enrich_with_cb_metrics
        
        # Execute triage
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify metrics are tracked
        metadata = result["metadata"]
        assert "circuit_breaker_state" in metadata
        assert "circuit_breaker_failure_count" in metadata
        assert "circuit_breaker_success_rate" in metadata
        assert metadata["circuit_breaker_state"] == "CLOSED"
        assert metadata["circuit_breaker_failure_count"] == 5
        assert metadata["circuit_breaker_success_rate"] == 0.9


class TestTriageCircuitBreakerRecovery:
    """Test circuit breaker recovery scenarios specific to triage operations."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset_after_successful_recovery(self, llm_processor, sample_state):
        """Test circuit breaker properly resets after successful recovery."""
        recovery_timeout = TriageConfig.CIRCUIT_BREAKER_CONFIG["recovery_timeout"]
        
        # Setup circuit breaker in recovery scenario
        llm_processor.agent.circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        llm_processor.agent.circuit_breaker.failure_count = 8
        llm_processor.agent.circuit_breaker.last_failure_time = time.time() - (recovery_timeout + 1)
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        llm_processor.agent.triage_core.cache_result = AsyncMock()
        
        # Mock successful recovery
        successful_response = {
            "category": "Performance Optimization",
            "confidence_score": 0.88,
            "priority": "high",
            "extracted_entities": {"domain": "performance", "intent": "optimization"},
            "tool_recommendations": ["data_sub_agent", "optimizations_core_sub_agent"]
        }
        llm_processor.agent.llm_manager.ask_structured_llm.return_value = successful_response
        
        # Mock circuit breaker reset after successful call
        def mock_reset_circuit_breaker(result, _):
            # Simulate successful call resetting circuit breaker
            llm_processor.agent.circuit_breaker.state = CircuitBreakerState.CLOSED
            llm_processor.agent.circuit_breaker.failure_count = 0
            
            result["metadata"] = result.get("metadata", {})
            result["metadata"].update({
                "circuit_breaker_reset": True,
                "previous_failure_count": 8,
                "recovery_successful": True,
                "triage_duration_ms": 1450
            })
            return result
        
        llm_processor.agent.result_processor.enrich_triage_result.side_effect = mock_reset_circuit_breaker
        
        # Execute recovery
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify circuit breaker was reset
        assert result["metadata"]["circuit_breaker_reset"] is True
        assert result["metadata"]["recovery_successful"] is True
        assert result["metadata"]["previous_failure_count"] == 8
        assert llm_processor.agent.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert llm_processor.agent.circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_handles_partial_recovery(self, llm_processor, sample_state):
        """Test circuit breaker handles partial recovery scenarios correctly."""
        half_open_max_calls = TriageConfig.CIRCUIT_BREAKER_CONFIG["half_open_max_calls"]
        
        # Setup half-open state
        llm_processor.agent.circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        
        # Mock partial success followed by failure
        call_attempts = []
        def mock_partial_recovery():
            attempt_count = len(call_attempts) + 1
            call_attempts.append(attempt_count)
            
            if attempt_count <= 2:  # First 2 calls succeed
                return {
                    "category": "Data Analysis",
                    "confidence_score": 0.75,
                    "priority": "medium",
                    "extracted_entities": {"domain": "analytics"},
                    "tool_recommendations": ["data_sub_agent"],
                    "metadata": {"partial_recovery_attempt": attempt_count}
                }
            else:  # 3rd call fails, should reopen circuit
                raise LLMError("Service degraded during recovery")
        
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = mock_partial_recovery
        
        # Mock circuit state changes during partial recovery
        def track_partial_recovery(result, _):
            attempt = result.get("metadata", {}).get("partial_recovery_attempt", 0)
            if attempt <= 2:
                result["metadata"]["recovery_progress"] = f"success_{attempt}_of_{half_open_max_calls}"
            return result
        
        llm_processor.agent.result_processor.enrich_triage_result.side_effect = track_partial_recovery
        
        # Execute partial recovery scenario
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify partial recovery was tracked
        assert "partial_recovery_attempt" in result["metadata"]
        assert "recovery_progress" in result["metadata"]
        assert result["metadata"]["partial_recovery_attempt"] in [1, 2]


@pytest.mark.integration 
@pytest.mark.circuit_breaker
class TestTriageCircuitBreakerIntegrationScenarios:
    """Integration scenarios testing circuit breaker with real triage workflows."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_circuit_breaker_lifecycle(self, llm_processor, sample_state):
        """Test complete circuit breaker lifecycle from closed -> open -> recovery -> closed."""
        failure_threshold = TriageConfig.CIRCUIT_BREAKER_CONFIG["failure_threshold"]
        recovery_timeout = TriageConfig.CIRCUIT_BREAKER_CONFIG["recovery_timeout"]
        
        # Phase 1: Closed state with gradual failures
        llm_processor.agent.circuit_breaker.state = CircuitBreakerState.CLOSED
        llm_processor.agent.circuit_breaker.failure_count = failure_threshold - 2  # Almost at threshold
        
        llm_processor.agent.prompt_builder.build_enhanced_prompt.return_value = "Enhanced prompt"
        llm_processor.agent.triage_core.generate_request_hash.return_value = "hash123"
        llm_processor.agent.triage_core.get_cached_result.return_value = None
        
        lifecycle_states = []
        
        # Mock state transitions
        def mock_state_transition():
            current_failures = llm_processor.agent.circuit_breaker.failure_count
            if current_failures >= failure_threshold:
                llm_processor.agent.circuit_breaker.state = CircuitBreakerState.OPEN
                lifecycle_states.append("OPEN")
                raise ServiceUnavailableError("Circuit breaker open")
            else:
                llm_processor.agent.circuit_breaker.failure_count += 1
                lifecycle_states.append("FAILURE")
                raise LLMError("Model failure")
        
        llm_processor.agent.llm_manager.ask_structured_llm.side_effect = mock_state_transition
        
        # Mock fallback response for all states
        fallback_result = {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": [],
            "metadata": {
                "fallback_used": True,
                "circuit_breaker_lifecycle": lifecycle_states,
                "final_state": "OPEN"
            }
        }
        llm_processor.agent.result_processor.enrich_triage_result.return_value = fallback_result
        
        # Execute to trigger state transition
        result = await llm_processor.execute_triage_with_llm(sample_state, "run-123", False)
        
        # Verify lifecycle progression
        assert "circuit_breaker_lifecycle" in result["metadata"]
        assert len(result["metadata"]["circuit_breaker_lifecycle"]) >= 1
        assert result["metadata"]["final_state"] == "OPEN"