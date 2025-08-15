"""
Unit tests for Fallback Response Service
Tests context-aware fallback response generation for various failure scenarios
"""

import pytest
from unittest.mock import Mock, patch
import json
import re

from app.services.fallback_response_service import FallbackResponseService
from app.services.fallback_response.models import (
    FailureReason,
    FallbackContext
)
from app.services.quality_gate_service import ContentType, QualityMetrics, QualityLevel


class TestFallbackResponseService:
    """Test suite for Fallback Response Service"""
    
    @pytest.fixture
    def fallback_service(self):
        """Create FallbackResponseService instance"""
        return FallbackResponseService()
    
    @pytest.fixture
    def sample_quality_metrics(self):
        """Create sample quality metrics for testing"""
        return QualityMetrics(
            specificity_score=0.3,
            actionability_score=0.2,
            quantification_score=0.1,
            relevance_score=0.4,
            completeness_score=0.3,
            overall_score=0.26,
            quality_level=QualityLevel.UNACCEPTABLE,
            generic_phrase_count=5,
            circular_reasoning_detected=True,
            issues=["Too generic", "No specific metrics", "Circular reasoning detected"],
            suggestions=["Add specific metrics", "Provide concrete steps"]
        )
    
    async def test_generate_optimization_fallback_low_quality(self, fallback_service, sample_quality_metrics):
        """Test fallback generation for low-quality optimization content"""
        context = FallbackContext(
            agent_name="optimization_agent",
            content_type=ContentType.OPTIMIZATION,
            failure_reason=FailureReason.LOW_QUALITY,
            user_request="Optimize my GPU workload",
            attempted_action="generate_optimization_plan",
            quality_metrics=sample_quality_metrics
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Verify response quality
        assert response != None
        # Handle both string and dict responses
        if isinstance(response, dict):
            response_text = response.get('response', '')
        else:
            response_text = response
        assert len(response_text) > 100  # Should be substantial
        assert "specific" in response_text.lower() or "information" in response_text.lower()
        assert "GPU workload" in response_text  # Should reference the context
        
        # Should include actionable requests for information
        assert any(term in response_text for term in ["metrics", "performance", "constraints"])
    
    async def test_generate_data_analysis_fallback_parsing_error(self, fallback_service):
        """Test fallback for data analysis parsing errors"""
        context = FallbackContext(
            agent_name="data_agent",
            content_type=ContentType.DATA_ANALYSIS,
            failure_reason=FailureReason.PARSING_ERROR,
            user_request="Analyze system logs",
            attempted_action="parse_log_data",
            error_details="JSONDecodeError: Expecting value: line 1 column 1"
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Verify appropriate error guidance
        assert response != None
        # Handle both string and dict responses
        if isinstance(response, dict):
            response_text = response.get('response', '')
        else:
            response_text = response
        assert "system logs" in response_text
        assert any(term in response_text.lower() for term in ["format", "json", "csv", "parsing", "data"])
        assert any(term in response_text.lower() for term in ["verify", "check", "validate"])
    
    async def test_generate_action_plan_fallback_context_missing(self, fallback_service):
        """Test fallback for action plan with missing context"""
        context = FallbackContext(
            agent_name="action_agent",
            content_type=ContentType.ACTION_PLAN,
            failure_reason=FailureReason.CONTEXT_MISSING,
            user_request="Create deployment plan",
            attempted_action="generate_action_plan"
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should ask for specific context
        assert response != None
        assert "deployment plan" in response
        assert any(term in response.lower() for term in ["objectives", "timeline", "resources", "requirements"])
    
    async def test_generate_report_fallback_validation_failed(self, fallback_service):
        """Test fallback for report with validation failure"""
        context = FallbackContext(
            agent_name="reporting_agent",
            content_type=ContentType.REPORT,
            failure_reason=FailureReason.VALIDATION_FAILED,
            user_request="Generate performance report",
            attempted_action="compile_report",
            error_details="Missing required data fields"
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should provide helpful error recovery
        assert response != None
        assert "performance report" in response
        assert any(term in response.lower() for term in ["data", "missing", "required", "fields"])
    
    async def test_generate_triage_fallback_timeout(self, fallback_service):
        """Test fallback for triage timeout scenario"""
        context = FallbackContext(
            agent_name="triage_agent",
            content_type=ContentType.TRIAGE,
            failure_reason=FailureReason.TIMEOUT,
            user_request="Diagnose system issue",
            attempted_action="analyze_request",
            retry_count=2
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should acknowledge timeout and provide alternatives
        assert response != None
        assert "system issue" in response
        assert context.retry_count == 2  # Should consider retry count
        assert any(term in response.lower() for term in ["time", "simpler", "break down", "specific"])
    
    async def test_generate_error_message_fallback_llm_error(self, fallback_service):
        """Test fallback for error message generation with LLM error"""
        context = FallbackContext(
            agent_name="error_handler",
            content_type=ContentType.ERROR_MESSAGE,
            failure_reason=FailureReason.LLM_ERROR,
            user_request="Explain error code 500",
            attempted_action="generate_error_explanation",
            error_details="LLM API connection failed"
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should provide helpful error information despite LLM failure
        assert response != None
        assert "error" in response.lower()
        # Should acknowledge the limitation
        assert any(term in response.lower() for term in ["technical", "issue", "try"])
    
    async def test_generate_fallback_with_circular_reasoning(self, fallback_service):
        """Test fallback specifically for circular reasoning detection"""
        context = FallbackContext(
            agent_name="optimization_agent",
            content_type=ContentType.OPTIMIZATION,
            failure_reason=FailureReason.CIRCULAR_REASONING,
            user_request="Improve model performance",
            attempted_action="suggest_improvements"
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should provide concrete, non-circular suggestions
        assert response != None
        assert "model performance" in response
        # Should include specific steps or techniques
        assert any(term in response.lower() for term in ["measure", "identify", "apply", "specific", "concrete"])
        # Should NOT contain circular phrases
        assert "optimize by optimizing" not in response.lower()
        assert "improve by improving" not in response.lower()
    
    async def test_generate_fallback_with_hallucination_risk(self, fallback_service):
        """Test fallback for high hallucination risk scenarios"""
        metrics = QualityMetrics(
            hallucination_risk=0.8,
            overall_score=0.3,
            quality_level=QualityLevel.UNACCEPTABLE,
            issues=["High hallucination risk detected", "Unverifiable claims"]
        )
        
        context = FallbackContext(
            agent_name="data_agent",
            content_type=ContentType.DATA_ANALYSIS,
            failure_reason=FailureReason.HALLUCINATION_RISK,
            user_request="Analyze future trends",
            attempted_action="predict_trends",
            quality_metrics=metrics
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should acknowledge uncertainty and provide grounded response
        assert response != None
        assert "future trends" in response
        assert any(term in response.lower() for term in ["data", "evidence", "based", "verify"])
    
    async def test_generate_fallback_with_rate_limit(self, fallback_service):
        """Test fallback for rate limit scenarios"""
        context = FallbackContext(
            agent_name="generation_agent",
            content_type=ContentType.GENERAL,
            failure_reason=FailureReason.RATE_LIMIT,
            user_request="Generate comprehensive analysis",
            attempted_action="call_llm",
            error_details="Rate limit exceeded: 429"
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should acknowledge rate limit and provide alternatives
        assert response != None
        assert any(term in response.lower() for term in ["moment", "shortly", "wait", "try"])
        assert any(term in response.lower() for term in ["alternative", "meanwhile", "instead"])
    
    async def test_generate_fallback_considers_retry_count(self, fallback_service):
        """Test that fallback responses adapt based on retry count"""
        base_context = FallbackContext(
            agent_name="optimization_agent",
            content_type=ContentType.OPTIMIZATION,
            failure_reason=FailureReason.LOW_QUALITY,
            user_request="Optimize system",
            attempted_action="generate_optimization",
            retry_count=0
        )
        
        # First attempt
        response1 = fallback_service.generate_fallback(base_context)
        
        # Third attempt
        base_context.retry_count = 2
        response2 = fallback_service.generate_fallback(base_context)
        
        # Responses should be different and escalate appropriately
        assert response1 != response2
        assert len(response2) > 0  # Should still provide helpful response
        
        # Later response might be more direct or suggest different approach
        if base_context.retry_count > 1:
            assert any(term in response2.lower() for term in ["different", "alternative", "simpler", "break"])
    
    async def test_generate_fallback_includes_diagnostic_tips(self, fallback_service):
        """Test that fallback includes relevant diagnostic tips"""
        context = FallbackContext(
            agent_name="data_agent",
            content_type=ContentType.DATA_ANALYSIS,
            failure_reason=FailureReason.PARSING_ERROR,
            user_request="Process CSV data",
            attempted_action="parse_csv",
            error_details="ValueError: could not convert string to float"
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should include diagnostic tips
        assert response != None
        assert "CSV data" in response
        # Should mention common CSV issues
        assert any(term in response.lower() for term in ["format", "encoding", "delimiter", "types"])
    
    async def test_generate_fallback_with_previous_responses(self, fallback_service):
        """Test fallback that considers previous failed responses"""
        context = FallbackContext(
            agent_name="optimization_agent",
            content_type=ContentType.OPTIMIZATION,
            failure_reason=FailureReason.LOW_QUALITY,
            user_request="Optimize database queries",
            attempted_action="suggest_query_optimization",
            retry_count=1,
            previous_responses=["Use indexes to improve query performance"]
        )
        
        response = await fallback_service.generate_fallback(context)
        
        # Should provide different suggestions than previous attempts
        assert response != None
        assert "database queries" in response
        # Should not repeat the exact same suggestion
        assert response != context.previous_responses[0]
    
    async def test_format_response_with_placeholders(self, fallback_service):
        """Test that response formatting handles placeholders correctly"""
        template = "I need help with {context} to resolve {issue}."
        
        formatted = fallback_service._format_response(
            template,
            context="GPU optimization",
            issue="memory overflow"
        )
        
        assert formatted == "I need help with GPU optimization to resolve memory overflow."
        assert "{" not in formatted  # No unresolved placeholders
        assert "}" not in formatted
    
    def test_get_diagnostic_tips_for_failure_reason(self, fallback_service):
        """Test retrieval of diagnostic tips based on failure reason"""
        tips = fallback_service._get_diagnostic_tips(FailureReason.PARSING_ERROR)
        
        assert tips != None
        assert len(tips) > 0
        assert all(isinstance(tip, str) for tip in tips)
        assert any("format" in tip.lower() or "structure" in tip.lower() for tip in tips)
    
    async def test_get_recovery_suggestions(self, fallback_service):
        """Test generation of recovery suggestions"""
        suggestions = fallback_service._get_recovery_suggestions(
            ContentType.OPTIMIZATION,
            FailureReason.LOW_QUALITY
        )
        
        assert suggestions != None
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)
        assert any("specific" in s.lower() or "provide" in s.lower() for s in suggestions)
    
    async def test_fallback_response_quality(self, fallback_service):
        """Test that fallback responses meet quality standards"""
        # Test various scenarios
        scenarios = [
            (ContentType.OPTIMIZATION, FailureReason.LOW_QUALITY),
            (ContentType.DATA_ANALYSIS, FailureReason.CONTEXT_MISSING),
            (ContentType.ACTION_PLAN, FailureReason.CIRCULAR_REASONING),
            (ContentType.REPORT, FailureReason.GENERIC_CONTENT),
            (ContentType.ERROR_MESSAGE, FailureReason.LLM_ERROR),
        ]
        
        for content_type, failure_reason in scenarios:
            context = FallbackContext(
                agent_name="test_agent",
                content_type=content_type,
                failure_reason=failure_reason,
                user_request="Test request",
                attempted_action="test_action"
            )
            
            response = await fallback_service.generate_fallback(context)
            
            # Quality checks
            assert response != None
            assert len(response) >= 50  # Minimum length
            assert response.strip() == response  # No extra whitespace
            assert not response.startswith("I apologize")  # No unnecessary apologies
            assert "Test request" in response  # References user context
            
            # Should not contain generic AI slop phrases
            generic_phrases = [
                "it is important to note",
                "generally speaking",
                "it goes without saying"
            ]
            for phrase in generic_phrases:
                assert phrase not in response.lower()
    
    def test_fallback_service_initialization(self, fallback_service):
        """Test that service initializes with proper templates"""
        assert fallback_service.response_templates != None
        assert len(fallback_service.response_templates) > 0
        
        assert fallback_service.diagnostic_tips != None
        assert len(fallback_service.diagnostic_tips) > 0
        
        assert fallback_service.recovery_suggestions != None
        assert len(fallback_service.recovery_suggestions) > 0
        
        # Verify template structure
        for key, templates in fallback_service.response_templates.items():
            assert isinstance(key, tuple)
            assert len(key) == 2  # (ContentType, FailureReason)
            assert isinstance(templates, list)
            assert len(templates) > 0
            assert all(isinstance(t, str) for t in templates)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])