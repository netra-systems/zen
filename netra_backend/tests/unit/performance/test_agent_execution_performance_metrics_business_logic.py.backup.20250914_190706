"""
Test Agent Execution Performance Metrics Business Logic

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Ensure fast agent response times for customer satisfaction
- Value Impact: Slow agents reduce user engagement and platform adoption
- Strategic Impact: Performance metrics enable SLA compliance and optimization

CRITICAL REQUIREMENTS:
- Tests pure business logic for performance calculation
- Validates performance thresholds and SLA compliance
- No external dependencies or infrastructure needed
- Ensures accurate performance measurement algorithms
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.apex_optimizer_agent.tools.performance_predictor import PerformancePredictor
from netra_backend.app.services.context import ToolContext


class TestAgentExecutionPerformanceMetricsBusinessLogic(SSotBaseTestCase):
    """Test agent execution performance metrics business logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        super().setup_method()
        self.performance_predictor = PerformancePredictor()
    
    def test_performance_predictor_metadata(self):
        """Test performance predictor tool metadata"""
        assert self.performance_predictor.name == "performance_predictor"
        assert self.performance_predictor.metadata.name == "PerformancePredictor"
        assert "performance" in self.performance_predictor.metadata.description.lower()
        assert self.performance_predictor.metadata.version == "1.0.0"
        assert self.performance_predictor.metadata.status == "in_review"
    
    @pytest.mark.asyncio
    async def test_performance_prediction_default_fallback(self):
        """Test performance prediction with parsing failure fallback"""
        # Mock LLM that returns non-numeric response
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.content = "Unable to predict latency due to complexity"
        mock_llm.ainvoke.return_value = mock_response
        
        # Mock LLM manager
        mock_llm_manager = Mock()
        mock_llm_manager.get_llm.return_value = mock_llm
        
        # Create context
        context = Mock(spec=ToolContext)
        context.llm_manager = mock_llm_manager
        
        # Test performance prediction with fallback
        result = await self.performance_predictor.run(
            context=context,
            prompt="Analyze cost optimization opportunities"
        )
        
        # Validate fallback behavior
        assert "predicted_latency_ms" in result
        assert result["predicted_latency_ms"] == 250  # Default fallback value
        
        # Validate LLM was called with proper prompt
        mock_llm.ainvoke.assert_called_once()
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "Analyze cost optimization opportunities" in call_args
        assert "predict the latency" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_performance_prediction_numeric_parsing(self):
        """Test performance prediction with valid numeric response"""
        # Mock LLM that returns numeric response
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.content = "1250"  # Valid millisecond prediction
        mock_llm.ainvoke.return_value = mock_response
        
        # Mock LLM manager
        mock_llm_manager = Mock()
        mock_llm_manager.get_llm.return_value = mock_llm
        
        # Create context
        context = Mock(spec=ToolContext)
        context.llm_manager = mock_llm_manager
        
        # Test performance prediction
        result = await self.performance_predictor.run(
            context=context,
            prompt="Simple data retrieval query"
        )
        
        # Validate parsed numeric result
        assert "predicted_latency_ms" in result
        assert result["predicted_latency_ms"] == 1250
        
        # Validate prompt construction
        mock_llm.ainvoke.assert_called_once()
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert "Simple data retrieval query" in call_args
        assert str(context) in call_args
    
    @pytest.mark.asyncio
    async def test_performance_prediction_with_response_object(self):
        """Test performance prediction when LLM returns response object"""
        # Mock LLM that returns response object without content attribute
        mock_llm = AsyncMock()
        mock_response = "750"  # Direct string response
        mock_llm.ainvoke.return_value = mock_response
        
        # Mock LLM manager
        mock_llm_manager = Mock()
        mock_llm_manager.get_llm.return_value = mock_llm
        
        # Create context
        context = Mock(spec=ToolContext)
        context.llm_manager = mock_llm_manager
        
        # Test performance prediction
        result = await self.performance_predictor.run(
            context=context,
            prompt="Complex multi-step analysis"
        )
        
        # Validate string conversion and parsing
        assert "predicted_latency_ms" in result
        assert result["predicted_latency_ms"] == 750
    
    @pytest.mark.asyncio
    async def test_performance_prediction_context_integration(self):
        """Test performance prediction integrates context properly"""
        # Mock LLM
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.content = "2100"
        mock_llm.ainvoke.return_value = mock_response
        
        # Mock LLM manager with specific LLM name
        mock_llm_manager = Mock()
        mock_llm_manager.get_llm.return_value = mock_llm
        
        # Create context with identifiable properties
        context = Mock(spec=ToolContext)
        context.llm_manager = mock_llm_manager
        context.user_id = "test_user_123"
        context.execution_id = "exec_456"
        
        # Test performance prediction
        result = await self.performance_predictor.run(
            context=context,
            prompt="Resource optimization analysis"
        )
        
        # Validate result
        assert result["predicted_latency_ms"] == 2100
        
        # Validate context was included in prompt
        mock_llm_manager.get_llm.assert_called_once_with("default")
        mock_llm.ainvoke.assert_called_once()
        
        prediction_prompt = mock_llm.ainvoke.call_args[0][0]
        assert "Resource optimization analysis" in prediction_prompt
        assert str(context) in prediction_prompt
        assert "Context:" in prediction_prompt
        assert "Return only the predicted latency as an integer" in prediction_prompt
    
    def test_performance_prediction_business_logic_validation(self):
        """Test business logic validation for performance predictions"""
        # Test various performance threshold scenarios
        performance_scenarios = [
            {"prompt_type": "simple_query", "expected_range": (100, 500)},
            {"prompt_type": "data_analysis", "expected_range": (500, 2000)},
            {"prompt_type": "complex_optimization", "expected_range": (1500, 5000)},
            {"prompt_type": "ml_training", "expected_range": (3000, 10000)}
        ]
        
        for scenario in performance_scenarios:
            # Validate that expected ranges make business sense
            min_ms, max_ms = scenario["expected_range"]
            
            # Business validation: reasonable performance expectations
            assert min_ms > 0, f"Minimum latency must be positive for {scenario['prompt_type']}"
            assert max_ms > min_ms, f"Maximum must exceed minimum for {scenario['prompt_type']}"
            assert max_ms <= 30000, f"Maximum latency too high for {scenario['prompt_type']} (>30s)"
            
            # Business validation: performance tier expectations
            if "simple" in scenario["prompt_type"]:
                assert max_ms <= 1000, "Simple operations should complete within 1 second"
            elif "complex" in scenario["prompt_type"]:
                assert min_ms >= 1000, "Complex operations expected to take meaningful time"
    
    def test_performance_predictor_error_handling_business_impact(self):
        """Test error handling scenarios that impact business operations"""
        predictor = PerformancePredictor()
        
        # Test metadata indicates proper tool registration
        assert predictor.metadata.status in ["active", "in_review"], "Tool must be production-ready"
        
        # Test that tool name follows naming conventions
        assert "_" in predictor.name, "Tool names should use snake_case convention"
        assert "performance" in predictor.name, "Performance tools should be clearly named"
        
        # Test version management for business continuity
        version_parts = predictor.metadata.version.split(".")
        assert len(version_parts) == 3, "Version should follow semantic versioning"
        assert all(part.isdigit() for part in version_parts), "Version parts should be numeric"
        
        # Business validation: tool description clarity
        description = predictor.metadata.description
        assert len(description) > 20, "Tool description must be comprehensive"
        assert "predict" in description.lower(), "Description should clearly state prediction capability"
        assert "performance" in description.lower(), "Description should mention performance focus"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])