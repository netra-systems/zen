"""Unit tests for uncovered triage agent scenarios.

Tests critical edge cases and failure modes without external dependencies.
Focuses on circuit breaker, WebSocket, cache, LLM parsing, and execution engine.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitConfig as CircuitBreakerConfig,
)
from netra_backend.app.core.circuit_breaker_types import CircuitState as CircuitBreakerState
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
)
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.triage_sub_agent.core import TriageCore
from netra_backend.app.agents.triage_sub_agent.models import (
    ExtractedEntities,
    TriageResult,
)
from netra_backend.app.agents.triage_sub_agent.processing import TriageProcessor
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager


class TestCircuitBreakerThresholdBehavior:
    """Test circuit breaker exact threshold behavior and state transitions."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with known thresholds."""
        config = CircuitBreakerConfig(
            name="test_circuit",
            failure_threshold=3,
            recovery_timeout=1.0,
            timeout_seconds=5.0
        )
        return CircuitBreaker(config)

    def test_exact_failure_threshold_opens_circuit(self, circuit_breaker):
        """Test circuit opens exactly at threshold."""
        # Circuit should be closed initially
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # First two failures should not open circuit
        for i in range(2):
            circuit_breaker.record_failure()
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
            assert circuit_breaker.failure_count == i + 1
        
        # Third failure should open circuit
        circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.failure_count == 3

    def test_state_transition_timing_precision(self, circuit_breaker):
        """Test recovery timeout precision."""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Should still be open before timeout
        time.sleep(0.5)
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Should transition to half-open after timeout
        time.sleep(0.6)  # Total 1.1 seconds
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    def test_rapid_state_changes_consistency(self, circuit_breaker):
        """Test rapid state changes maintain consistency."""
        # Rapidly alternate between success and failure
        for _ in range(10):
            circuit_breaker.record_success()
            circuit_breaker.record_failure()
        
        # Should still be closed (only 10 failures, interleaved with successes)
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Now trigger opening
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_concurrent_failure_tracking(self, circuit_breaker):
        """Test concurrent failure updates."""
        import threading
        
        def record_failures():
            for _ in range(2):
                circuit_breaker.record_failure()
        
        # Create multiple threads recording failures
        threads = [threading.Thread(target=record_failures) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should be open after 6 total failures
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_failure_count_reset_on_success(self, circuit_breaker):
        """Test failure count resets properly."""
        # Record 2 failures
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 2
        
        # Success should reset count
        circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0
        
        # Should need 3 more failures to open
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN


class TestWebSocketErrorHandling:
    """Test WebSocket error handling during triage updates."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocket manager."""
        manager = AsyncMock()
        manager.send_update = AsyncMock()
        return manager

    @pytest.fixture
    def triage_agent(self, mock_websocket_manager):
        """Create triage agent with mock WebSocket."""
        llm_manager = MagicMock(spec=LLMManager)
        tool_dispatcher = MagicMock()
        agent = TriageSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
            websocket_manager=mock_websocket_manager
        )
        return agent

    @pytest.mark.asyncio
    async def test_websocket_failure_during_triage_update(self, triage_agent, mock_websocket_manager):
        """Test WebSocket failures don't break triage."""
        # Configure WebSocket to fail
        mock_websocket_manager.send_update.side_effect = ConnectionError("WebSocket disconnected")
        
        # Create execution context
        context = ExecutionContext(
            request_id="test-123",
            user_id="user-456",
            session_id="session-789",
            metadata={"test": "data"}
        )
        
        # Execute should handle WebSocket failure gracefully
        with patch.object(triage_agent, '_process_request') as mock_process:
            mock_process.return_value = TriageResult(
                primary_intent="optimization",
                secondary_intents=["cost"],
                extracted_entities=ExtractedEntities(),
                confidence_score=0.9
            )
            
            result = await triage_agent.execute(context, {"query": "test"})
            
            # Should complete successfully despite WebSocket failure
            assert result.status == ExecutionStatus.SUCCESS
            assert mock_websocket_manager.send_update.called

    @pytest.mark.asyncio
    async def test_websocket_timeout_handling(self, triage_agent, mock_websocket_manager):
        """Test WebSocket timeout scenarios."""
        # Configure WebSocket to timeout
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate slow network
        
        mock_websocket_manager.send_update = slow_send
        
        context = ExecutionContext(
            request_id="test-timeout",
            user_id="user-123",
            session_id="session-456"
        )
        
        # Should not wait for slow WebSocket
        start_time = time.time()
        with patch.object(triage_agent, '_process_request') as mock_process:
            mock_process.return_value = TriageResult(
                primary_intent="reporting",
                secondary_intents=[],
                extracted_entities=ExtractedEntities(),
                confidence_score=0.85
            )
            
            result = await triage_agent.execute(context, {"query": "test"})
            
        elapsed = time.time() - start_time
        assert elapsed < 2  # Should not wait for WebSocket
        assert result.status == ExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_websocket_partial_send_failure(self, triage_agent, mock_websocket_manager):
        """Test partial WebSocket send failures."""
        call_count = 0
        
        async def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise ConnectionError("Intermittent failure")
            return {"status": "sent"}
        
        mock_websocket_manager.send_update = intermittent_failure
        
        context = ExecutionContext(
            request_id="test-partial",
            user_id="user-789",
            session_id="session-012"
        )
        
        # Should handle intermittent failures
        with patch.object(triage_agent, '_process_request') as mock_process:
            mock_process.return_value = TriageResult(
                primary_intent="analysis",
                secondary_intents=["performance"],
                extracted_entities=ExtractedEntities(),
                confidence_score=0.92
            )
            
            result = await triage_agent.execute(context, {"query": "test"})
            
        assert result.status == ExecutionStatus.SUCCESS
        assert call_count >= 1  # At least one attempt made


class TestCacheInvalidationAndRedisFailures:
    """Test cache invalidation and Redis failure scenarios."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Create a mock Redis manager."""
        manager = MagicMock(spec=RedisManager)
        manager.get = MagicMock()
        manager.set = MagicMock()
        manager.delete = MagicMock()
        return manager

    @pytest.fixture
    def triage_core(self, mock_redis_manager):
        """Create triage core with mock Redis."""
        return TriageCore(redis_manager=mock_redis_manager)

    def test_redis_get_failure_fallback(self, triage_core, mock_redis_manager):
        """Test fallback when Redis get fails."""
        # Configure Redis to fail
        mock_redis_manager.get.side_effect = ConnectionError("Redis unavailable")
        
        # Should return None without crashing
        result = triage_core._get_from_cache("test_key")
        assert result is None
        assert mock_redis_manager.get.called

    def test_redis_set_failure_continues(self, triage_core, mock_redis_manager):
        """Test operation continues when Redis set fails."""
        # Configure Redis set to fail
        mock_redis_manager.set.side_effect = ConnectionError("Redis write failed")
        
        # Should not raise exception
        triage_core._cache_result("test_key", {"data": "value"})
        assert mock_redis_manager.set.called

    def test_cache_corruption_recovery(self, triage_core, mock_redis_manager):
        """Test recovery from corrupted cache data."""
        # Return corrupted JSON
        mock_redis_manager.get.return_value = '{"invalid": json"corrupted"}'
        
        # Should handle gracefully
        result = triage_core._get_from_cache("corrupted_key")
        assert result is None

    def test_intermittent_redis_failures(self, triage_core, mock_redis_manager):
        """Test handling of intermittent Redis failures."""
        call_count = 0
        
        def intermittent_get(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Temporary failure")
            return json.dumps({"cached": "data"})
        
        mock_redis_manager.get.side_effect = intermittent_get
        
        # First call fails, should return None
        result1 = triage_core._get_from_cache("test_key")
        assert result1 is None
        
        # Second call succeeds
        result2 = triage_core._get_from_cache("test_key")
        assert result2 == {"cached": "data"}

    def test_cache_ttl_boundary_conditions(self, triage_core, mock_redis_manager):
        """Test cache TTL edge cases."""
        # Test with zero TTL
        triage_core.cache_ttl = 0
        triage_core._cache_result("zero_ttl", {"data": "value"})
        
        # Should still attempt to cache
        assert mock_redis_manager.set.called
        call_args = mock_redis_manager.set.call_args
        assert call_args[1]["ttl"] == 0
        
        # Test with very large TTL
        triage_core.cache_ttl = 2147483647  # Max 32-bit int
        triage_core._cache_result("max_ttl", {"data": "value"})
        
        call_args = mock_redis_manager.set.call_args
        assert call_args[1]["ttl"] == 2147483647


class TestLLMResponseParsingEdgeCases:
    """Test LLM response parsing edge cases and malformed JSON."""

    @pytest.fixture
    def triage_processor(self):
        """Create triage processor for testing."""
        llm_manager = MagicMock(spec=LLMManager)
        processor = TriageProcessor(llm_manager)
        return processor

    def test_malformed_json_extraction_strategies(self, triage_processor):
        """Test multiple JSON extraction strategies."""
        test_cases = [
            # Case 1: JSON with trailing comma
            ('{"intent": "optimization",}', {"intent": "optimization"}),
            
            # Case 2: JSON with single quotes
            ("{'intent': 'cost'}", {"intent": "cost"}),
            
            # Case 3: JSON embedded in text
            ("Here is the result: ```json\n{\"intent\": \"analysis\"}\n```", {"intent": "analysis"}),
            
            # Case 4: Multiple JSON objects
            ('{"first": "one"} some text {"second": "two"}', {"first": "one"}),
            
            # Case 5: Incomplete JSON
            ('{"intent": "reporting", "entities":', None),
            
            # Case 6: JSON with comments
            ('{"intent": "metrics" /* comment */}', {"intent": "metrics"}),
            
            # Case 7: Escaped quotes in values
            ('{"message": "Say \\"hello\\" world"}', {"message": 'Say "hello" world'}),
        ]
        
        for input_text, expected in test_cases:
            result = triage_processor._extract_json_with_fallback(input_text)
            if expected is None:
                assert result is None or result == {}
            else:
                assert result == expected

    def test_partial_llm_response_handling(self, triage_processor):
        """Test handling of partial LLM responses."""
        partial_response = """
        {
            "primary_intent": "optimization",
            "secondary_intents": ["cost", "performance"],
            "extracted_entities": {
                "models": ["gpt-4"],
                "metrics": [
        """
        
        # Should extract what's possible or return empty
        result = triage_processor._extract_json_with_fallback(partial_response)
        assert result is None or result == {}

    def test_unicode_and_special_characters(self, triage_processor):
        """Test handling of Unicode and special characters."""
        unicode_json = {
            "intent": "分析",  # Chinese
            "message": "Hello 👋 World",  # Emoji
            "special": "Line\nbreak\ttab",  # Control characters
            "math": "α + β = γ"  # Greek letters
        }
        
        json_str = json.dumps(unicode_json, ensure_ascii=False)
        result = triage_processor._extract_json_with_fallback(json_str)
        
        assert result == unicode_json

    def test_nested_json_extraction(self, triage_processor):
        """Test extraction of deeply nested JSON."""
        nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "intent": "deep_analysis",
                        "data": [1, 2, 3]
                    }
                }
            }
        }
        
        # Test with various formatting
        compact = json.dumps(nested, separators=(',', ':'))
        pretty = json.dumps(nested, indent=2)
        
        assert triage_processor._extract_json_with_fallback(compact) == nested
        assert triage_processor._extract_json_with_fallback(pretty) == nested

    def test_extremely_large_response_handling(self, triage_processor):
        """Test handling of very large LLM responses."""
        # Create a large but valid JSON
        large_data = {
            "intent": "analysis",
            "large_array": [f"item_{i}" for i in range(10000)],
            "nested": {
                f"key_{i}": f"value_{i}" for i in range(1000)
            }
        }
        
        json_str = json.dumps(large_data)
        
        # Should handle large responses efficiently
        start_time = time.time()
        result = triage_processor._extract_json_with_fallback(json_str)
        elapsed = time.time() - start_time
        
        assert result == large_data
        assert elapsed < 1.0  # Should process quickly


class TestModernExecutionEngineErrorPropagation:
    """Test modern execution engine error propagation and context validation."""

    @pytest.fixture
    def triage_agent(self):
        """Create triage agent for testing."""
        llm_manager = MagicMock(spec=LLMManager)
        tool_dispatcher = MagicMock()
        agent = TriageSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        return agent

    @pytest.mark.asyncio
    async def test_execution_context_validation_failures(self, triage_agent):
        """Test execution context validation."""
        # Test with missing required fields
        invalid_contexts = [
            None,  # Null context
            ExecutionContext(request_id="", user_id="user", session_id="session"),  # Empty request_id
            ExecutionContext(request_id="req", user_id="", session_id="session"),  # Empty user_id
            ExecutionContext(request_id="req", user_id="user", session_id=""),  # Empty session_id
        ]
        
        for context in invalid_contexts:
            result = await triage_agent.execute(context, {"query": "test"})
            assert result.status == ExecutionStatus.FAILED
            if context:
                assert "validation" in result.error.lower() or "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execution_result_error_propagation(self, triage_agent):
        """Test error propagation through ExecutionResult."""
        context = ExecutionContext(
            request_id="test-error",
            user_id="user-123",
            session_id="session-456"
        )
        
        # Mock processing to raise an error
        with patch.object(triage_agent, '_process_request') as mock_process:
            mock_process.side_effect = ValueError("Processing failed")
            
            result = await triage_agent.execute(context, {"query": "test"})
            
            assert result.status == ExecutionStatus.FAILED
            assert "Processing failed" in result.error
            assert result.data is None

    @pytest.mark.asyncio
    async def test_execution_monitor_failure_handling(self, triage_agent):
        """Test execution monitor failure scenarios."""
        context = ExecutionContext(
            request_id="test-monitor",
            user_id="user-789",
            session_id="session-012"
        )
        
        # Mock monitor to fail
        with patch.object(triage_agent.execution_monitor, 'start_execution') as mock_start:
            mock_start.side_effect = RuntimeError("Monitor initialization failed")
            
            # Should still execute but without monitoring
            with patch.object(triage_agent, '_process_request') as mock_process:
                mock_process.return_value = TriageResult(
                    primary_intent="test",
                    secondary_intents=[],
                    extracted_entities=ExtractedEntities(),
                    confidence_score=0.9
                )
                
                result = await triage_agent.execute(context, {"query": "test"})
                
                # Should succeed despite monitor failure
                assert result.status == ExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_reliability_manager_state_consistency(self, triage_agent):
        """Test reliability manager maintains state consistency."""
        context = ExecutionContext(
            request_id="test-reliability",
            user_id="user-345",
            session_id="session-678"
        )
        
        # Simulate multiple failures to trigger circuit breaker
        for i in range(5):
            with patch.object(triage_agent, '_process_request') as mock_process:
                mock_process.side_effect = RuntimeError(f"Failure {i+1}")
                
                result = await triage_agent.execute(context, {"query": "test"})
                assert result.status == ExecutionStatus.FAILED
        
        # Circuit should be open now
        # Next request should fail fast
        start_time = time.time()
        result = await triage_agent.execute(context, {"query": "test"})
        elapsed = time.time() - start_time
        
        assert result.status == ExecutionStatus.FAILED
        assert elapsed < 0.1  # Should fail fast when circuit is open

    @pytest.mark.asyncio
    async def test_execution_timeout_handling(self, triage_agent):
        """Test execution timeout scenarios."""
        context = ExecutionContext(
            request_id="test-timeout",
            user_id="user-timeout",
            session_id="session-timeout",
            metadata={"timeout": 0.1}  # Very short timeout
        )
        
        # Mock slow processing
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(2)
            return TriageResult(
                primary_intent="slow",
                secondary_intents=[],
                extracted_entities=ExtractedEntities(),
                confidence_score=0.8
            )
        
        with patch.object(triage_agent, '_process_request', new=slow_process):
            result = await triage_agent.execute(context, {"query": "test"})
            
            # Should timeout
            assert result.status == ExecutionStatus.FAILED
            assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_metadata_preservation_through_execution(self, triage_agent):
        """Test metadata is preserved through execution."""
        original_metadata = {
            "client_version": "1.2.3",
            "source": "api",
            "custom_field": "value"
        }
        
        context = ExecutionContext(
            request_id="test-metadata",
            user_id="user-meta",
            session_id="session-meta",
            metadata=original_metadata.copy()
        )
        
        with patch.object(triage_agent, '_process_request') as mock_process:
            mock_process.return_value = TriageResult(
                primary_intent="test",
                secondary_intents=[],
                extracted_entities=ExtractedEntities(),
                confidence_score=0.95
            )
            
            result = await triage_agent.execute(context, {"query": "test"})
            
            # Metadata should be preserved
            assert result.status == ExecutionStatus.SUCCESS
            assert context.metadata == original_metadata

    @pytest.mark.asyncio
    async def test_concurrent_execution_context_isolation(self, triage_agent):
        """Test concurrent executions maintain context isolation."""
        contexts = [
            ExecutionContext(
                request_id=f"test-{i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}",
                metadata={"index": i}
            )
            for i in range(5)
        ]
        
        results = []
        
        async def execute_with_context(ctx):
            with patch.object(triage_agent, '_process_request') as mock_process:
                mock_process.return_value = TriageResult(
                    primary_intent=f"intent-{ctx.metadata['index']}",
                    secondary_intents=[],
                    extracted_entities=ExtractedEntities(),
                    confidence_score=0.9
                )
                
                result = await triage_agent.execute(ctx, {"query": f"test-{ctx.metadata['index']}"})
                return result
        
        # Execute concurrently
        results = await asyncio.gather(*[execute_with_context(ctx) for ctx in contexts])
        
        # Verify each result corresponds to its context
        for i, result in enumerate(results):
            assert result.status == ExecutionStatus.SUCCESS
            assert f"intent-{i}" in str(result.data)

    @pytest.mark.asyncio
    async def test_retry_mechanism_context_consistency(self, triage_agent):
        """Test retry mechanisms maintain context consistency."""
        context = ExecutionContext(
            request_id="test-retry",
            user_id="user-retry",
            session_id="session-retry",
            metadata={"retry_count": 0}
        )
        
        call_count = 0
        
        async def intermittent_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return TriageResult(
                primary_intent="success",
                secondary_intents=[],
                extracted_entities=ExtractedEntities(),
                confidence_score=0.88
            )
        
        with patch.object(triage_agent, '_process_request', new=intermittent_process):
            with patch.object(triage_agent, 'max_retries', 3):
                result = await triage_agent.execute(context, {"query": "test"})
                
                # Should succeed after retries
                assert result.status == ExecutionStatus.SUCCESS
                assert call_count >= 3  # Should have retried