"""
Content-specific validation tests for Quality Gate Service
Tests validation for different content types and scenarios
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import pytest

from netra_backend.app.services.quality_gate_service import ContentType
from netra_backend.tests.quality_gate_content import (
    get_complete_action_plan_content,
    get_data_analysis_content,
    get_domain_specific_content,
    get_good_error_message_content,
    get_hallucination_risk_content,
    get_mediocre_content,
    get_redundant_report_content,
    get_triage_content,
)
from netra_backend.tests.quality_gate_fixtures import (
    quality_service,
    redis_mock,
)
from netra_backend.tests.quality_gate_helpers import (
    assert_action_plan_completeness,
    assert_domain_terms_recognition,
    assert_error_message_clarity,
    assert_hallucination_risk_detected,
    assert_quantification_metrics,
    assert_redundancy_detected,
    assert_retry_suggestions_provided,
    assert_triage_content_metrics,
)

class TestQualityGateContent:
    """Test suite for content-specific QualityGateService validation"""
    async def test_validate_data_analysis_with_metrics(self, quality_service):
        """Test validation of data analysis content with quantitative metrics"""
        content = get_data_analysis_content()
        result = await quality_service.validate_content(content, content_type=ContentType.DATA_ANALYSIS)
        
        assert result.passed == True
        assert_quantification_metrics(result)
    async def test_validate_action_plan_completeness(self, quality_service):
        """Test validation of action plan for completeness and actionability"""
        content = get_complete_action_plan_content()
        result = await quality_service.validate_content(content, content_type=ContentType.ACTION_PLAN, strict_mode=False)
        
        assert_action_plan_completeness(result)
    async def test_validate_error_message_clarity(self, quality_service):
        """Test validation of error messages for clarity and actionability"""
        content = get_good_error_message_content()
        result = await quality_service.validate_content(content, content_type=ContentType.ERROR_MESSAGE)
        
        assert result.passed == False
        assert_error_message_clarity(result)
    async def test_validate_report_redundancy(self, quality_service):
        """Test detection of redundant content in reports"""
        content = get_redundant_report_content()
        result = await quality_service.validate_content(content, content_type=ContentType.REPORT)
        
        assert_redundancy_detected(result)
    async def test_domain_specific_term_recognition(self, quality_service):
        """Test recognition of domain-specific terms that indicate quality"""
        content = get_domain_specific_content()
        result = await quality_service.validate_content(content, content_type=ContentType.OPTIMIZATION)
        
        assert result.passed == False
        assert_domain_terms_recognition(result)
    async def test_retry_suggestions_for_failed_validation(self, quality_service):
        """Test that retry suggestions are provided for failed validations"""
        content = get_mediocre_content()
        result = await quality_service.validate_content(content, content_type=ContentType.OPTIMIZATION)
        
        assert_retry_suggestions_provided(result)
    async def test_hallucination_risk_detection(self, quality_service):
        """Test detection of potential hallucination risks"""
        content = get_hallucination_risk_content()
        result = await quality_service.validate_content(content, content_type=ContentType.DATA_ANALYSIS)
        
        assert_hallucination_risk_detected(result)
    async def test_triage_content_validation(self, quality_service):
        """Test validation of triage content with appropriate thresholds"""
        content = get_triage_content()
        result = await quality_service.validate_content(content, content_type=ContentType.TRIAGE)
        
        assert_triage_content_metrics(result)