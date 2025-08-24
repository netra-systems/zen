"""Critical Pydantic Validation Tests for Agent System

This addresses CRITICAL validation errors where LLM returns strings instead of dicts.
"""

from netra_backend.app.monitoring.metrics_collector import PerformanceMetric
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import ValidationError

from netra_backend.app.agents.data_sub_agent.models import (

    AnomalyDetectionResponse,

    CorrelationAnalysis,

    DataAnalysisResponse,

    DataQualityMetrics,

    PerformanceMetrics,

    UsagePattern,

)
from netra_backend.app.agents.optimizations_core_sub_agent import (

    OptimizationsCoreSubAgent,

)
from netra_backend.app.agents.state import (

    ActionPlanResult,

    AgentMetadata,

    DeepAgentState,

    OptimizationsResult,

    PlanStep,

)
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent

from netra_backend.app.agents.triage_sub_agent.models import (

    Complexity,

    ExtractedEntities,

    Priority,

    ToolRecommendation,

    TriageMetadata,

    TriageResult,

    UserIntent,

)
from netra_backend.app.llm.llm_manager import LLMManager

class TestPydanticValidationCritical:

    """Test Pydantic validation issues seen in production"""
    
    @pytest.fixture

    def mock_llm_manager(self):

        """Create mock LLM manager"""

        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm = Mock(spec=LLMManager)

        return llm
    
    @pytest.fixture

    def mock_tool_dispatcher(self):

        """Create mock tool dispatcher"""
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        return Mock(spec=ToolDispatcher)

    @pytest.mark.asyncio

    async def test_triage_malformed_parameters_fallback_handling(self):

        """Test production fallback behavior for malformed tool parameters"""
        # This tests the actual production scenario: malformed strings get converted to empty dicts

        invalid_llm_response = {

            "category": "Cost Optimization",

            "confidence_score": 0.95,

            "priority": "medium",

            "complexity": "moderate",

            "tool_recommendations": [

                {

                    "tool_name": "optimize_performance",

                    "relevance_score": 0.9,
                    # Malformed JSON triggers fallback to empty dict

                    "parameters": '{ "performance_goal": "3x", "budget_constraint": '

                },

                {

                    "tool_name": "analyze_metrics",

                    "relevance_score": 0.8,
                    # Invalid string triggers fallback to empty dict

                    "parameters": 'invalid_json_string'

                }

            ]

        }
        
        # Should succeed with fallback handling (production behavior)

        result = TriageResult(**invalid_llm_response)
        
        # Verify fallback behavior: malformed strings become empty dicts

        assert result.tool_recommendations[0].parameters == {}

        assert result.tool_recommendations[1].parameters == {}

    @pytest.mark.asyncio

    async def test_triage_string_parameters_recovery(self):

        """Test recovery from string parameters by parsing JSON"""
        # Real production pattern: LLM returns stringified JSON

        invalid_response_str = json.dumps({

            "category": "Cost Optimization",

            "tool_recommendations": [{

                "tool_name": "optimize",

                "relevance_score": 0.8,

                "parameters": '{"key": "value"}'  # String that needs parsing

            }]

        })
        
        # Production recovery function

        def fix_string_parameters(data: Dict[str, Any]) -> Dict[str, Any]:

            """Fix string parameters in tool recommendations"""

            if "tool_recommendations" in data:

                for rec in data["tool_recommendations"]:

                    if isinstance(rec.get("parameters"), str):

                        try:

                            rec["parameters"] = json.loads(rec["parameters"])

                        except json.JSONDecodeError:

                            rec["parameters"] = {}

            return data
        
        # Parse and fix

        parsed = json.loads(invalid_response_str)

        fixed = fix_string_parameters(parsed)
        
        # Should now validate

        result = TriageResult(**fixed)

        assert result.tool_recommendations[0].parameters == {"key": "value"}

    @pytest.mark.asyncio

    async def test_optimizations_result_recommendations_dict_error(self):

        """Test exact error: recommendations as dict instead of list of strings"""
        # This is the EXACT error from production logs

        invalid_response = {

            "optimization_type": "general",

            "recommendations": [
                # ERROR: This is a dict, not a string!

                {"type": "general", "description": "Optimize", "priority": "medium", "fallback": True}

            ]

        }
        
        # This should NOT raise validation error - the validator should handle dict to string conversion

        result = OptimizationsResult(**invalid_response)
        
        # Verify the dict was converted to a string properly

        assert len(result.recommendations) == 1

        assert isinstance(result.recommendations[0], str)
        # The validator should convert the dict to its description or string representation

        assert "Optimize" in result.recommendations[0] or "general" in result.recommendations[0]

    @pytest.mark.asyncio

    async def test_optimizations_fallback_format_error(self):

        """Test the fallback optimization format that's failing"""
        # The fallback is returning wrong format

        fallback_response = {

            "optimization_type": "general",

            "recommendations": [

                {"type": "general", "description": "Optimize", "priority": "medium"}

            ],

            "confidence_score": 0.5

        }
        
        # Fix function that should be implemented

        def fix_recommendations_format(data: Dict[str, Any]) -> Dict[str, Any]:

            """Convert dict recommendations to strings"""

            if "recommendations" in data and isinstance(data["recommendations"], list):

                fixed_recs = []

                for rec in data["recommendations"]:

                    if isinstance(rec, dict):
                        # Convert dict to string description

                        desc = rec.get("description", str(rec))

                        fixed_recs.append(desc)

                    else:

                        fixed_recs.append(str(rec))

                data["recommendations"] = fixed_recs

            return data
        
        # Fix and validate

        fixed = fix_recommendations_format(fallback_response)

        result = OptimizationsResult(**fixed)

        assert result.recommendations == ["Optimize"]

    @pytest.mark.asyncio

    async def test_usage_pattern_enum_validation_error(self):

        """Test UsagePattern enum validation with invalid values"""

        invalid_pattern = {

            "pattern_type": "unknown_pattern",  # Invalid enum value

            "confidence": 0.8

        }

        with pytest.raises(ValidationError) as exc_info:

            UsagePattern(**invalid_pattern)

        assert "Input should be" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_data_quality_metrics_range_validation(self):

        """Test DataQualityMetrics field range validation"""
        # Completeness over 100%

        invalid_quality = {

            "completeness": 150.0,  # Over 100%

            "accuracy": 95.0,

            "consistency": 88.0,

            "timeliness": 92.0,

            "overall_score": 93.5

        }

        with pytest.raises(ValidationError) as exc_info:

            DataQualityMetrics(**invalid_quality)

        assert "less than or equal to 100" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_correlation_analysis_validation_error(self):

        """Test CorrelationAnalysis nested validation failures"""
        # Correlation coefficients as string instead of list

        invalid_correlation = {

            "metric_pairs": [],

            "correlation_coefficients": "[0.95, 0.87]"

        }

        with pytest.raises(ValidationError) as exc_info:

            CorrelationAnalysis(**invalid_correlation)

        assert "Input should be a valid list" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_plan_step_dependency_validation_error(self):

        """Test PlanStep dependencies validation with malformed data"""

        invalid_step = {

            "step_id": "1",

            "description": "test step",

            "dependencies": "step2,step3"  # String instead of list

        }

        with pytest.raises(ValidationError) as exc_info:

            PlanStep(**invalid_step)

        assert "Input should be a valid list" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_batch_processing_nested_validation(self):

        """Test batch processing validation patterns"""
        # Errors as string instead of list

        invalid_batch = {

            "total_items": 100,

            "successful_items": 95,

            "failed_items": 5,

            "errors": "error1,error2,error3"  # String instead of list

        }

        with pytest.raises(ValidationError) as exc_info:
            from netra_backend.app.agents.data_sub_agent.models import (

                BatchProcessingResult,

            )

            BatchProcessingResult(**invalid_batch)

        assert "Input should be a valid list" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_data_analysis_nested_validation_error(self):

        """Test DataAnalysisResponse nested field validation failures"""
        # Performance metrics as string instead of object

        invalid_response = {

            "query": "test query",

            "performance_metrics": '{"latency_p50": 10.5}'

        }

        with pytest.raises(ValidationError) as exc_info:

            DataAnalysisResponse(**invalid_response)

        assert "Input should be a valid dictionary" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_action_plan_nested_validation_error(self):

        """Test ActionPlanResult PlanStep validation failures"""
        # Plan steps as string instead of PlanStep objects

        invalid_response = {

            "plan_steps": '[{"step_id": "1", "description": "test"}]'

        }

        with pytest.raises(ValidationError) as exc_info:

            ActionPlanResult(**invalid_response)

        assert "Input should be a valid list" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_real_llm_truncation_pattern(self):

        """Test LLM response truncation causing malformed JSON"""
        # Simulates LLM hitting token limit mid-JSON

        truncated_json = '{"category": "Cost Optimization", "tool_recomme'

        with pytest.raises(json.JSONDecodeError):

            json.loads(truncated_json)
    
    def _create_string_to_dict_recovery(self, data: Dict[str, Any]) -> Dict[str, Any]:

        """Recovery function for string-to-dict conversion"""

        if "performance_metrics" in data and isinstance(data["performance_metrics"], str):

            try:

                data["performance_metrics"] = json.loads(data["performance_metrics"])

            except json.JSONDecodeError:

                data["performance_metrics"] = None

        return data

    @pytest.mark.asyncio

    async def test_comprehensive_nested_recovery(self):

        """Test comprehensive nested field recovery patterns"""

        test_data = {

            "query": "test",

            "performance_metrics": '{"latency_p50": 10.5, "latency_p95": 15.0, "latency_p99": 20.0, "throughput_avg": 100.0, "throughput_peak": 150.0, "error_rate": 0.1}'

        }

        fixed_data = self._create_string_to_dict_recovery(test_data)

        result = DataAnalysisResponse(**fixed_data)

        assert result.performance_metrics.latency_p50 == 10.5

        assert result.performance_metrics.throughput_avg == 100.0

        assert result.performance_metrics.error_rate == 0.1

    @pytest.mark.asyncio

    async def test_llm_retry_with_validation_error(self, mock_llm_manager):

        """Test retry mechanism when ValidationError occurs"""
        # Mock first call fails, second succeeds, with extra fallback responses

        valid_response = TriageResult(category="Cost Optimization")

        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager.ask_structured_llm = AsyncMock(side_effect=[

            ValidationError.from_exception_data("ValidationError", []),

            valid_response,

            valid_response  # Extra response in case of additional calls

        ])
        
        # Mock ask_llm for fallback scenarios

        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager.ask_llm = AsyncMock(return_value='{"category": "General Inquiry"}')
        
        # Should retry and succeed on second attempt
        from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent

        # Mock: LLM service isolation for fast testing without API calls or rate limits
        agent = TriageSubAgent(mock_llm_manager, Mock())

        state = DeepAgentState(user_request="test")
        
        await agent.execute(state, "test_run", False)
        # Should call at least 2 times (first fails, second succeeds)

        assert mock_llm_manager.ask_structured_llm.call_count >= 2

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s"])