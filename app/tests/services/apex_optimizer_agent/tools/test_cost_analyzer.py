# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:55:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Ultra-thinking test generation for 97% coverage goal
# Git: v6 | be70ff77 | dirty
# Change: Test | Scope: Module | Risk: Low
# Session: ultra-think-test-gen | Seq: 1
# Review: Pending | Score: 95
# ================================
"""
Comprehensive unit tests for cost_analyzer tool.
Designed with ultra-thinking to achieve 97% test coverage.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import List
import asyncio

from app.services.apex_optimizer_agent.tools.cost_analyzer import cost_analyzer
from app.services.context import ToolContext


class TestCostAnalyzer:
    """Comprehensive test suite for cost_analyzer tool"""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext with test data"""
        context = Mock(spec=ToolContext)
        
        # Mock logs with request data
        mock_log1 = Mock()
        mock_log1.request.prompt_text = "Test prompt 1"
        mock_log1.model_dump.return_value = {
            "model": "gpt-4",
            "tokens": 1000,
            "timestamp": "2025-08-10T12:00:00Z"
        }
        
        mock_log2 = Mock()
        mock_log2.request.prompt_text = "Test prompt 2"
        mock_log2.model_dump.return_value = {
            "model": "gpt-3.5-turbo",
            "tokens": 500,
            "timestamp": "2025-08-10T12:01:00Z"
        }
        
        mock_log3 = Mock()
        mock_log3.request.prompt_text = "Test prompt 3"
        mock_log3.model_dump.return_value = {
            "model": "claude-3-opus",
            "tokens": 2000,
            "timestamp": "2025-08-10T12:02:00Z"
        }
        
        context.logs = [mock_log1, mock_log2, mock_log3]
        
        # Mock cost_estimator
        context.cost_estimator = Mock()
        context.cost_estimator.execute = AsyncMock()
        
        return context
    async def test_cost_analyzer_basic_functionality(self, mock_context):
        """Test basic cost analysis with multiple logs"""
        # Setup mock responses
        mock_context.cost_estimator.execute.side_effect = [
            {"estimated_cost_usd": 0.05},
            {"estimated_cost_usd": 0.02},
            {"estimated_cost_usd": 0.08}
        ]
        
        # Execute
        result = await cost_analyzer(mock_context)
        
        # Verify
        assert result == "Analyzed current costs. Total estimated cost: $0.15"
        assert mock_context.cost_estimator.execute.call_count == 3
        
        # Verify correct parameters were passed
        calls = mock_context.cost_estimator.execute.call_args_list
        assert calls[0][0][0] == "Test prompt 1"
        assert calls[1][0][0] == "Test prompt 2"
        assert calls[2][0][0] == "Test prompt 3"
    async def test_cost_analyzer_empty_logs(self, mock_context):
        """Test cost analyzer with empty logs"""
        mock_context.logs = []
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $0.00"
        assert mock_context.cost_estimator.execute.call_count == 0
    async def test_cost_analyzer_single_log(self, mock_context):
        """Test cost analyzer with single log entry"""
        mock_context.logs = [mock_context.logs[0]]
        mock_context.cost_estimator.execute.return_value = {"estimated_cost_usd": 0.123456}
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $0.12"
        assert mock_context.cost_estimator.execute.call_count == 1
    async def test_cost_analyzer_large_costs(self, mock_context):
        """Test cost analyzer with large cost values"""
        mock_context.cost_estimator.execute.side_effect = [
            {"estimated_cost_usd": 100.50},
            {"estimated_cost_usd": 250.75},
            {"estimated_cost_usd": 500.25}
        ]
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $851.50"
    async def test_cost_analyzer_zero_costs(self, mock_context):
        """Test cost analyzer when all costs are zero"""
        mock_context.cost_estimator.execute.return_value = {"estimated_cost_usd": 0.0}
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $0.00"
    async def test_cost_analyzer_fractional_cents(self, mock_context):
        """Test cost analyzer with fractional cent values"""
        mock_context.cost_estimator.execute.side_effect = [
            {"estimated_cost_usd": 0.001},
            {"estimated_cost_usd": 0.002},
            {"estimated_cost_usd": 0.003}
        ]
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $0.01"
    async def test_cost_analyzer_exception_handling(self, mock_context):
        """Test cost analyzer handles exceptions from cost_estimator"""
        mock_context.cost_estimator.execute.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await cost_analyzer(mock_context)
        
        assert str(exc_info.value) == "API Error"
    async def test_cost_analyzer_async_execution(self, mock_context):
        """Test that cost analyzer properly awaits async operations"""
        call_order = []
        
        async def mock_execute(prompt, log_data):
            call_order.append(f"execute_{prompt[:10]}")
            await asyncio.sleep(0.01)  # Simulate async work
            return {"estimated_cost_usd": 0.01}
        
        mock_context.cost_estimator.execute = mock_execute
        
        result = await cost_analyzer(mock_context)
        
        assert len(call_order) == 3
        assert "$0.03" in result  # Total cost for 3 logs at 0.01 each
    async def test_cost_analyzer_concurrent_logs(self, mock_context):
        """Test cost analyzer with many logs to verify performance"""
        # Create 100 mock logs
        large_logs = []
        for i in range(100):
            mock_log = Mock()
            mock_log.request.prompt_text = f"Test prompt {i}"
            mock_log.model_dump.return_value = {"model": "gpt-4", "tokens": 100}
            large_logs.append(mock_log)
        
        mock_context.logs = large_logs
        mock_context.cost_estimator.execute.return_value = {"estimated_cost_usd": 0.01}
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $1.00"
        assert mock_context.cost_estimator.execute.call_count == 100
    async def test_cost_analyzer_negative_costs(self, mock_context):
        """Test cost analyzer with negative costs (credits/refunds)"""
        mock_context.cost_estimator.execute.side_effect = [
            {"estimated_cost_usd": 0.10},
            {"estimated_cost_usd": -0.05},  # Credit
            {"estimated_cost_usd": 0.15}
        ]
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $0.20"
    async def test_cost_analyzer_mixed_model_types(self, mock_context):
        """Test cost analyzer with different model types and configurations"""
        # Setup logs with different model configurations
        mock_logs = []
        for i, config in enumerate([
            {"model": "gpt-4", "tokens": 1000, "type": "completion"},
            {"model": "gpt-3.5-turbo", "tokens": 500, "type": "chat"},
            {"model": "claude-3-opus", "tokens": 2000, "type": "completion"},
            {"model": "text-embedding-ada-002", "tokens": 100, "type": "embedding"},
            {"model": "dall-e-3", "tokens": 0, "type": "image"}
        ]):
            mock_log = Mock()
            mock_log.request.prompt_text = f"Test prompt {i}"
            mock_log.model_dump.return_value = config
            mock_logs.append(mock_log)
        
        mock_context.logs = mock_logs
        mock_context.cost_estimator.execute.side_effect = [
            {"estimated_cost_usd": 0.03},   # GPT-4
            {"estimated_cost_usd": 0.002},  # GPT-3.5
            {"estimated_cost_usd": 0.15},   # Claude
            {"estimated_cost_usd": 0.0001}, # Embedding
            {"estimated_cost_usd": 0.04}    # DALL-E
        ]
        
        result = await cost_analyzer(mock_context)
        
        assert result == "Analyzed current costs. Total estimated cost: $0.22"
        assert mock_context.cost_estimator.execute.call_count == 5
    async def test_cost_analyzer_partial_failure(self, mock_context):
        """Test cost analyzer when some cost estimations fail"""
        mock_context.cost_estimator.execute.side_effect = [
            {"estimated_cost_usd": 0.05},
            Exception("API temporarily unavailable"),
            {"estimated_cost_usd": 0.08}
        ]
        
        # This should raise the exception when it hits the second log
        with pytest.raises(Exception) as exc_info:
            await cost_analyzer(mock_context)
        
        assert "API temporarily unavailable" in str(exc_info.value)
        # Verify it attempted to process the first log
        assert mock_context.cost_estimator.execute.call_count == 2
    async def test_cost_analyzer_rounding_edge_cases(self, mock_context):
        """Test cost analyzer rounding behavior at boundaries"""
        test_cases = [
            ([0.004, 0.004, 0.004], "$0.01"),  # Sum is 0.012, displays as $0.01
            ([0.005, 0.005, 0.005], "$0.01"),  # Sum is 0.015, displays as $0.01
            ([0.994, 0.001, 0.001], "$1.00"),  # Sum is 0.996, displays as $1.00
            ([0.995, 0.001, 0.001], "$1.00"),  # Sum is 0.997, displays as $1.00
        ]
        
        for costs, expected in test_cases:
            mock_context.cost_estimator.execute.side_effect = [
                {"estimated_cost_usd": cost} for cost in costs
            ]
            
            result = await cost_analyzer(mock_context)
            assert expected in result, f"Failed for costs {costs}"
            mock_context.cost_estimator.execute.reset_mock()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.apex_optimizer_agent.tools.cost_analyzer"])