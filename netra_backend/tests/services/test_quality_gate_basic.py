"""
Basic validation tests for Quality Gate Service
Tests fundamental validation functionality
"""

import sys
from pathlib import Path

import pytest

from netra_backend.app.services.quality_gate_service import ContentType
from netra_backend.tests.helpers.quality_gate_content import (
    get_borderline_quality_content,
    get_circular_reasoning_content,
    get_high_quality_optimization_content,
    get_low_quality_generic_content,
    get_optimization_context,
    get_relevant_context,
)
from netra_backend.tests.helpers.quality_gate_fixtures import (
    quality_service,
    redis_mock,
    setup_quality_level_test_cases,
    setup_validation_error_mock,
)
from netra_backend.tests.helpers.quality_gate_helpers import (
    assert_circular_reasoning_detected,
    assert_context_improves_relevance,
    assert_error_handling_result,
    assert_high_quality_metrics,
    assert_low_quality_metrics,
    assert_quality_level_classification,
    assert_strict_mode_differences,
    assert_validation_failed,
    assert_validation_passed,
)

class TestQualityGateBasic:
    """Test suite for basic QualityGateService validation"""
    async def test_validate_high_quality_optimization_content(self, quality_service):
        """Test validation of high-quality optimization content"""
        content = get_high_quality_optimization_content()
        result = await quality_service.validate_content(content, content_type=ContentType.OPTIMIZATION)
        
        assert_validation_passed(result)
        assert_high_quality_metrics(result)
    async def test_validate_low_quality_generic_content(self, quality_service):
        """Test detection of low-quality generic content"""
        content = get_low_quality_generic_content()
        result = await quality_service.validate_content(content, content_type=ContentType.OPTIMIZATION)
        
        assert_validation_failed(result)
        assert_low_quality_metrics(result)
    async def test_detect_circular_reasoning(self, quality_service):
        """Test detection of circular reasoning patterns"""
        content = get_circular_reasoning_content()
        result = await quality_service.validate_content(content, content_type=ContentType.ACTION_PLAN)
        
        assert_circular_reasoning_detected(result)
    async def test_validate_with_strict_mode(self, quality_service):
        """Test strict mode validation with higher thresholds"""
        content = get_borderline_quality_content()
        
        result_normal = await quality_service.validate_content(content, content_type=ContentType.GENERAL, strict_mode=False)
        result_strict = await quality_service.validate_content(content, content_type=ContentType.GENERAL, strict_mode=True)
        
        assert_strict_mode_differences(result_normal, result_strict)
    async def test_context_aware_validation(self, quality_service):
        """Test validation with additional context provided"""
        content = get_optimization_context()
        context = get_relevant_context()
        
        result_no_context = await quality_service.validate_content(content, content_type=ContentType.OPTIMIZATION)
        result_with_context = await quality_service.validate_content(content, content_type=ContentType.OPTIMIZATION, context=context)
        
        assert_context_improves_relevance(result_with_context, result_no_context)
    async def test_quality_level_classification(self, quality_service):
        """Test proper classification of quality levels"""
        test_cases = setup_quality_level_test_cases()
        
        for score, expected_level in test_cases:
            assert_quality_level_classification(quality_service, score, expected_level)
    async def test_error_handling_in_validation(self, quality_service):
        """Test error handling during content validation"""
        with setup_validation_error_mock(quality_service):
            result = await quality_service.validate_content("test content")
            assert_error_handling_result(result)