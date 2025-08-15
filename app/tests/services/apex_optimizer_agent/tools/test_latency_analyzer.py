# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:56:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Ultra-thinking test generation for 97% coverage goal
# Git: v6 | be70ff77 | dirty
# Change: Test | Scope: Module | Risk: Low
# Session: ultra-think-test-gen | Seq: 2
# Review: Pending | Score: 95
# ================================
"""
Comprehensive unit tests for latency_analyzer tool.
Designed with ultra-thinking to achieve 97% test coverage.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List
import asyncio
import statistics

from app.services.apex_optimizer_agent.tools.latency_analyzer import latency_analyzer
from app.services.context import ToolContext


class TestLatencyAnalyzer:
    """Comprehensive test suite for latency_analyzer tool"""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext with test data"""
        context = Mock(spec=ToolContext)
        
        # Mock logs with request data
        mock_log1 = Mock()
        mock_log1.request.prompt_text = "Fast query"
        mock_log1.model_dump.return_value = {
            "model": "gpt-3.5-turbo",
            "tokens": 100,
            "timestamp": "2025-08-10T12:00:00Z"
        }
        
        mock_log2 = Mock()
        mock_log2.request.prompt_text = "Medium query"
        mock_log2.model_dump.return_value = {
            "model": "gpt-4",
            "tokens": 500,
            "timestamp": "2025-08-10T12:01:00Z"
        }
        
        mock_log3 = Mock()
        mock_log3.request.prompt_text = "Slow query"
        mock_log3.model_dump.return_value = {
            "model": "claude-3-opus",
            "tokens": 2000,
            "timestamp": "2025-08-10T12:02:00Z"
        }
        
        context.logs = [mock_log1, mock_log2, mock_log3]
        
        # Mock performance_predictor
        context.performance_predictor = Mock()
        context.performance_predictor.execute = AsyncMock()
        
        return context

    @pytest.mark.asyncio
    async def test_latency_analyzer_basic_functionality(self, mock_context):
        """Test basic latency analysis with multiple logs"""
        # Setup mock responses
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": 100.0},
            {"predicted_latency_ms": 250.0},
            {"predicted_latency_ms": 500.0}
        ]
        
        # Execute
        result = await latency_analyzer(mock_context)
        
        # Verify
        expected_avg = (100.0 + 250.0 + 500.0) / 3
        assert result == f"Analyzed current latency. Average predicted latency: {expected_avg:.2f}ms"
        assert mock_context.performance_predictor.execute.call_count == 3
        
        # Verify correct parameters were passed
        calls = mock_context.performance_predictor.execute.call_args_list
        assert calls[0][0][0] == "Fast query"
        assert calls[1][0][0] == "Medium query"
        assert calls[2][0][0] == "Slow query"

    @pytest.mark.asyncio
    async def test_latency_analyzer_empty_logs(self, mock_context):
        """Test latency analyzer with empty logs"""
        mock_context.logs = []
        
        result = await latency_analyzer(mock_context)
        
        assert result == "Analyzed current latency. Average predicted latency: 0.00ms"
        assert mock_context.performance_predictor.execute.call_count == 0

    @pytest.mark.asyncio
    async def test_latency_analyzer_single_log(self, mock_context):
        """Test latency analyzer with single log entry"""
        mock_context.logs = [mock_context.logs[0]]
        mock_context.performance_predictor.execute.return_value = {"predicted_latency_ms": 123.456}
        
        result = await latency_analyzer(mock_context)
        
        assert result == "Analyzed current latency. Average predicted latency: 123.46ms"
        assert mock_context.performance_predictor.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_latency_analyzer_high_latency_values(self, mock_context):
        """Test latency analyzer with high latency values"""
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": 5000.0},
            {"predicted_latency_ms": 10000.0},
            {"predicted_latency_ms": 15000.0}
        ]
        
        result = await latency_analyzer(mock_context)
        
        assert result == "Analyzed current latency. Average predicted latency: 10000.00ms"

    @pytest.mark.asyncio
    async def test_latency_analyzer_zero_latency(self, mock_context):
        """Test latency analyzer when all latencies are zero"""
        mock_context.performance_predictor.execute.return_value = {"predicted_latency_ms": 0.0}
        
        result = await latency_analyzer(mock_context)
        
        assert result == "Analyzed current latency. Average predicted latency: 0.00ms"

    @pytest.mark.asyncio
    async def test_latency_analyzer_sub_millisecond_latency(self, mock_context):
        """Test latency analyzer with sub-millisecond values"""
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": 0.1},
            {"predicted_latency_ms": 0.2},
            {"predicted_latency_ms": 0.3}
        ]
        
        result = await latency_analyzer(mock_context)
        
        assert result == "Analyzed current latency. Average predicted latency: 0.20ms"

    @pytest.mark.asyncio
    async def test_latency_analyzer_exception_handling(self, mock_context):
        """Test latency analyzer handles exceptions from performance_predictor"""
        mock_context.performance_predictor.execute.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await latency_analyzer(mock_context)
        
        assert str(exc_info.value) == "API Error"

    @pytest.mark.asyncio
    async def test_latency_analyzer_async_execution(self, mock_context):
        """Test that latency analyzer properly awaits async operations"""
        call_order = []
        
        async def mock_execute(prompt, log_data):
            call_order.append(f"execute_{prompt[:10]}")
            await asyncio.sleep(0.01)  # Simulate async work
            return {"predicted_latency_ms": 100.0}
        
        mock_context.performance_predictor.execute = mock_execute
        
        result = await latency_analyzer(mock_context)
        
        assert len(call_order) == 3
        assert "Average predicted latency" in result

    @pytest.mark.asyncio
    async def test_latency_analyzer_large_dataset(self, mock_context):
        """Test latency analyzer with many logs to verify performance"""
        # Create 1000 mock logs
        large_logs = []
        for i in range(1000):
            mock_log = Mock()
            mock_log.request.prompt_text = f"Query {i}"
            mock_log.model_dump.return_value = {"model": "gpt-4", "tokens": 100}
            large_logs.append(mock_log)
        
        mock_context.logs = large_logs
        mock_context.performance_predictor.execute.return_value = {"predicted_latency_ms": 100.0}
        
        result = await latency_analyzer(mock_context)
        
        assert result == "Analyzed current latency. Average predicted latency: 100.00ms"
        assert mock_context.performance_predictor.execute.call_count == 1000

    @pytest.mark.asyncio
    async def test_latency_analyzer_varied_latencies(self, mock_context):
        """Test latency analyzer with varied latency patterns"""
        # Simulate realistic latency distribution
        latencies = [50, 75, 100, 150, 200, 250, 500, 1000, 2000, 5000]
        mock_logs = []
        
        for i, latency in enumerate(latencies):
            mock_log = Mock()
            mock_log.request.prompt_text = f"Query {i}"
            mock_log.model_dump.return_value = {"model": "various", "tokens": 100}
            mock_logs.append(mock_log)
        
        mock_context.logs = mock_logs
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": float(lat)} for lat in latencies
        ]
        
        result = await latency_analyzer(mock_context)
        
        expected_avg = sum(latencies) / len(latencies)
        assert result == f"Analyzed current latency. Average predicted latency: {expected_avg:.2f}ms"

    @pytest.mark.asyncio
    async def test_latency_analyzer_partial_failure(self, mock_context):
        """Test latency analyzer when some predictions fail"""
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": 100.0},
            Exception("Prediction service unavailable"),
            {"predicted_latency_ms": 200.0}
        ]
        
        # This should raise the exception when it hits the second log
        with pytest.raises(Exception) as exc_info:
            await latency_analyzer(mock_context)
        
        assert "Prediction service unavailable" in str(exc_info.value)
        # Verify it attempted to process the first log
        assert mock_context.performance_predictor.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_latency_analyzer_edge_case_rounding(self, mock_context):
        """Test latency analyzer rounding behavior at boundaries"""
        test_cases = [
            ([99.994, 99.995, 99.996], 100.00),  # Average is 99.995, rounds to 100.00
            ([0.004, 0.005, 0.006], 0.01),      # Small values round up
            ([1000.444, 1000.445, 1000.446], 1000.45),  # Average is 1000.445, rounds to 1000.45
        ]
        
        for latencies, expected_avg in test_cases:
            mock_context.performance_predictor.execute.side_effect = [
                {"predicted_latency_ms": lat} for lat in latencies
            ]
            
            result = await latency_analyzer(mock_context)
            assert f"{expected_avg:.2f}ms" in result, f"Failed for latencies {latencies}"
            mock_context.performance_predictor.execute.reset_mock()

    @pytest.mark.asyncio
    async def test_latency_analyzer_negative_latencies(self, mock_context):
        """Test latency analyzer with negative latencies (should not happen but test robustness)"""
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": 100.0},
            {"predicted_latency_ms": -50.0},  # Negative (error case)
            {"predicted_latency_ms": 200.0}
        ]
        
        result = await latency_analyzer(mock_context)
        
        # Average should still be calculated: (100 - 50 + 200) / 3 = 83.33
        assert result == "Analyzed current latency. Average predicted latency: 83.33ms"

    @pytest.mark.asyncio
    async def test_latency_analyzer_mixed_response_formats(self, mock_context):
        """Test latency analyzer with different response formats"""
        # Test handling of different numeric types
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": 100},      # int
            {"predicted_latency_ms": 200.5},    # float
            {"predicted_latency_ms": "300.0"}   # string (should cause error)
        ]
        
        # This should fail when trying to add string to numbers
        with pytest.raises(TypeError):
            await latency_analyzer(mock_context)

    @pytest.mark.asyncio
    async def test_latency_analyzer_extreme_values(self, mock_context):
        """Test latency analyzer with extreme values"""
        mock_context.performance_predictor.execute.side_effect = [
            {"predicted_latency_ms": 0.00001},      # Very small
            {"predicted_latency_ms": 999999999.99}, # Very large
            {"predicted_latency_ms": 100.0}         # Normal
        ]
        
        result = await latency_analyzer(mock_context)
        
        # Should handle extreme values correctly
        expected_avg = (0.00001 + 999999999.99 + 100.0) / 3
        assert "Average predicted latency:" in result
        assert "ms" in result

    @pytest.mark.asyncio
    async def test_latency_analyzer_concurrent_execution_timing(self, mock_context):
        """Test timing of sequential execution"""
        start_time = asyncio.get_event_loop().time()
        
        async def slow_execute(prompt, log_data):
            await asyncio.sleep(0.1)  # 100ms delay
            return {"predicted_latency_ms": 100.0}
        
        mock_context.performance_predictor.execute = slow_execute
        
        result = await latency_analyzer(mock_context)
        
        elapsed_time = asyncio.get_event_loop().time() - start_time
        
        # Should take at least 0.3 seconds (3 * 0.1) for sequential execution
        # Allow small timing variance (±10ms) for system scheduling variations
        assert elapsed_time >= 0.29
        assert "Average predicted latency: 100.00ms" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.apex_optimizer_agent.tools.latency_analyzer"])