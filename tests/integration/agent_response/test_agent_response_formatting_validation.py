"""Integration Tests for Agent Response Formatting and Structure Validation

Tests the formatting, structure, and quality validation of agent responses
to ensure they meet business requirements and user expectations.

Business Value Justification (BVJ):
- Segment: All segments - Quality/User Experience
- Business Goal: Ensure AI responses are well-formatted and valuable
- Value Impact: Maintains high-quality user interactions (90% of platform value)
- Strategic Impact: Protects brand reputation and user satisfaction
"""

import asyncio
import pytest
import json
from typing import Dict, Any, List, Union
from dataclasses import dataclass
from unittest.mock import patch

from test_framework.ssot.base_test_case import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import (
    TypedAgentResult,
    AgentExecutionResult,
    JsonCompatibleDict
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ResponseFormatValidation:
    """Response format validation result."""
    is_valid: bool
    format_type: str
    validation_errors: List[str]
    quality_score: float  # 0.0 to 1.0


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseFormattingValidation(BaseIntegrationTest):
    """Test agent response formatting and structure validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.env = self.get_env()  # Use SSOT environment from base class
        self.test_user_id = "test_user_formatting"
        self.test_thread_id = "thread_formatting_001"
        
    def _validate_json_response_structure(self, response: Any) -> ResponseFormatValidation:
        """Validate JSON response structure and quality."""
        errors = []
        quality_score = 1.0
        
        if not isinstance(response, (dict, list)):
            errors.append("Response must be JSON-compatible (dict or list)")
            quality_score -= 0.5
            
        if isinstance(response, dict):
            # Check for required business fields
            if not response:
                errors.append("Response dictionary cannot be empty")
                quality_score -= 0.3
                
            # Check for meaningful content
            text_fields = [v for v in response.values() if isinstance(v, str)]
            if not text_fields:
                errors.append("Response should contain descriptive text fields")
                quality_score -= 0.2
                
            # Check for structure indicators
            if "result" in response or "data" in response or "analysis" in response:
                quality_score += 0.1  # Bonus for structured response
                
        elif isinstance(response, list):
            if not response:
                errors.append("Response list cannot be empty")
                quality_score -= 0.3
                
        return ResponseFormatValidation(
            is_valid=len(errors) == 0,
            format_type="json",
            validation_errors=errors,
            quality_score=max(0.0, quality_score)
        )
        
    def _validate_text_response_quality(self, response: str) -> ResponseFormatValidation:
        """Validate text response quality and structure."""
        errors = []
        quality_score = 1.0
        
        if not response or not response.strip():
            errors.append("Text response cannot be empty")
            quality_score = 0.0
            return ResponseFormatValidation(False, "text", errors, quality_score)
            
        # Length checks
        if len(response.strip()) < 10:
            errors.append("Response too short to be meaningful")
            quality_score -= 0.4
            
        if len(response) > 10000:
            errors.append("Response too long for good user experience")
            quality_score -= 0.2
            
        # Content quality checks
        sentences = response.split('.')
        if len(sentences) < 2:
            errors.append("Response should contain multiple sentences")
            quality_score -= 0.2
            
        # Check for actionable content
        action_indicators = ["recommend", "suggest", "should", "can", "could", "will", "analysis", "insight"]
        if not any(indicator in response.lower() for indicator in action_indicators):
            errors.append("Response should contain actionable insights")
            quality_score -= 0.3
            
        return ResponseFormatValidation(
            is_valid=len(errors) == 0,
            format_type="text",
            validation_errors=errors,
            quality_score=max(0.0, quality_score)
        )
        
    async def test_data_helper_agent_response_format_validation(self):
        """
        Test DataHelperAgent response format meets business requirements.
        
        BVJ: Free/Early/Mid - User Experience/Conversion
        Validates that data analysis responses are well-formatted and actionable,
        crucial for demonstrating platform value to potential customers.
        """
        # GIVEN: A user execution context and data query
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            data_query = "Analyze customer acquisition trends and provide recommendations"
            
            # WHEN: Agent generates response
            result = await agent.run(context, query=data_query)
            
            # THEN: Response format is validated
            assert result is not None, "DataHelperAgent must generate response"
            
            if isinstance(result, TypedAgentResult):
                assert result.success, "DataHelper execution must succeed"
                response_data = result.result
                
                # Validate format based on response type
                if isinstance(response_data, str):
                    validation = self._validate_text_response_quality(response_data)
                else:
                    validation = self._validate_json_response_structure(response_data)
                
                # Business quality requirements
                assert validation.quality_score >= 0.6, \
                    f"Response quality {validation.quality_score:.2f} below business threshold. Errors: {validation.validation_errors}"
                
                # Record quality metrics
                self.record_metric("response_quality_score", validation.quality_score)
                self.record_metric("response_format_valid", 1 if validation.is_valid else 0)
                self.record_metric("response_format_errors", len(validation.validation_errors))
                
                if not validation.is_valid:
                    logger.warning(f"Response format issues: {validation.validation_errors}")
                else:
                    logger.info(f"✅ DataHelper response format validated (quality: {validation.quality_score:.2f})")
                    
    async def test_optimization_agent_response_structure_validation(self):
        """
        Test OptimizationsCoreSubAgent response structure for technical users.
        
        BVJ: Mid/Enterprise - Technical Value/Expansion
        Validates that optimization recommendations are structured appropriately
        for technical users who need detailed, actionable insights.
        """
        # GIVEN: A user execution context and optimization query
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = OptimizationsCoreSubAgent()
            optimization_query = "Recommend infrastructure optimizations for scaling AI workloads"
            
            # WHEN: Agent generates optimization response
            result = await agent.run(context, query=optimization_query)
            
            # THEN: Response structure meets technical requirements
            assert result is not None, "OptimizationsCore must generate response"
            
            if isinstance(result, TypedAgentResult):
                assert result.success, "Optimization execution must succeed"
                response_data = result.result
                
                # Technical responses should be structured
                if isinstance(response_data, dict):
                    validation = self._validate_json_response_structure(response_data)
                    
                    # Additional technical validation
                    technical_indicators = ["optimization", "performance", "infrastructure", "scaling"]
                    response_str = json.dumps(response_data).lower()
                    technical_relevance = sum(1 for indicator in technical_indicators if indicator in response_str)
                    
                    assert technical_relevance >= 2, \
                        "Optimization response must contain relevant technical content"
                    
                elif isinstance(response_data, str):
                    validation = self._validate_text_response_quality(response_data)
                    
                    # Check for technical structure
                    assert "optimization" in response_data.lower() or "performance" in response_data.lower(), \
                        "Optimization response must be relevant to query"
                
                assert validation.quality_score >= 0.7, \
                    f"Technical response quality {validation.quality_score:.2f} below standard"
                
                logger.info(f"✅ Optimization response structure validated (quality: {validation.quality_score:.2f})")
                
    async def test_response_consistency_across_multiple_queries(self):
        """
        Test response format consistency across multiple queries.
        
        BVJ: All segments - User Experience/Brand
        Validates that agents maintain consistent response quality and format
        across different types of queries, ensuring reliable user experience.
        """
        # GIVEN: Multiple query types for consistency testing
        queries = [
            "What are the latest AI trends?",
            "How can I optimize my infrastructure costs?",
            "Provide a summary of database performance metrics",
            "Recommend security improvements for cloud deployment"
        ]
        
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            response_validations = []
            
            # WHEN: Agent handles multiple query types
            for query in queries:
                result = await agent.run(context, query=query)
                
                if isinstance(result, TypedAgentResult) and result.success:
                    response_data = result.result
                    
                    if isinstance(response_data, str):
                        validation = self._validate_text_response_quality(response_data)
                    else:
                        validation = self._validate_json_response_structure(response_data)
                        
                    response_validations.append(validation)
            
            # THEN: Response quality is consistent
            assert len(response_validations) >= 2, "Multiple responses needed for consistency test"
            
            quality_scores = [v.quality_score for v in response_validations]
            avg_quality = sum(quality_scores) / len(quality_scores)
            quality_variance = sum((score - avg_quality) ** 2 for score in quality_scores) / len(quality_scores)
            
            # Consistency requirements
            assert avg_quality >= 0.6, f"Average response quality {avg_quality:.2f} below threshold"
            assert quality_variance < 0.1, f"Response quality variance {quality_variance:.3f} too high (inconsistent)"
            
            logger.info(f"✅ Response consistency validated (avg quality: {avg_quality:.2f}, variance: {quality_variance:.3f})")
            
    async def test_error_response_format_maintains_user_experience(self):
        """
        Test error response format maintains good user experience.
        
        BVJ: All segments - User Experience/Support
        Validates that even error responses are well-formatted and helpful,
        preventing user frustration and support burden.
        """
        # GIVEN: A user execution context and problematic query
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            
            # Test various error conditions
            error_scenarios = [
                {"query": "", "description": "empty query"},
                {"query": "x" * 5000, "description": "extremely long query"},
                {"query": "@@##$$%%", "description": "special characters query"}
            ]
            
            for scenario in error_scenarios:
                # WHEN: Agent handles error scenario
                result = await agent.run(context, query=scenario["query"])
                
                # THEN: Error response is well-formatted
                if isinstance(result, TypedAgentResult):
                    if not result.success:
                        # Error case - validate error format
                        assert result.error is not None, f"Error must be captured for {scenario['description']}"
                        assert len(result.error) > 0, f"Error message must be informative for {scenario['description']}"
                        assert len(result.error) < 500, f"Error message should be concise for {scenario['description']}"
                        
                        logger.info(f"✅ Error response well-formatted for {scenario['description']}")
                    else:
                        # Success case - validate graceful handling
                        if result.result is not None:
                            logger.info(f"✅ Agent handled {scenario['description']} gracefully")
                            
    async def test_response_metadata_completeness_for_analytics(self):
        """
        Test response metadata completeness for analytics and monitoring.
        
        BVJ: Platform/Internal - Analytics/Monitoring
        Validates that responses include proper metadata for business intelligence,
        performance monitoring, and user behavior analysis.
        """
        # GIVEN: A user execution context for metadata testing
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            query = "Test query for metadata validation"
            
            # WHEN: Agent generates response with metadata
            result = await agent.run(context, query=query)
            
            # THEN: Response includes complete metadata
            assert result is not None, "Response required for metadata validation"
            
            if isinstance(result, TypedAgentResult):
                # Validate required metadata fields
                assert hasattr(result, 'timestamp'), "Response must include timestamp"
                assert hasattr(result, 'execution_time_ms'), "Response must include execution time"
                assert hasattr(result, 'success'), "Response must include success indicator"
                
                # Validate metadata quality
                if result.execution_time_ms is not None:
                    assert result.execution_time_ms >= 0, "Execution time must be non-negative"
                    assert result.execution_time_ms < 60000, "Execution time should be reasonable (<60s)"
                
                assert result.timestamp is not None, "Timestamp must be set"
                
                # Optional metadata validation
                if hasattr(result, 'agent_name') and result.agent_name:
                    assert len(result.agent_name) > 0, "Agent name must be informative"
                
                if hasattr(result, 'metadata') and result.metadata:
                    assert isinstance(result.metadata, dict), "Metadata must be dictionary"
                    
                logger.info("✅ Response metadata completeness validated")
                
    def teardown_method(self):
        """Clean up test resources."""
        super().teardown_method()