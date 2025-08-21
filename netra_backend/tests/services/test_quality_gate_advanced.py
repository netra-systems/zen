"""
Advanced features tests for Quality Gate Service
Tests caching, batch processing, statistics, and system behavior
"""

import pytest
import hashlib
from unittest.mock import patch
from netra_backend.app.services.quality_gate_service import ContentType, QualityLevel
from netra_backend.tests.helpers.quality_gate_fixtures import (
    redis_mock,
    quality_service,
    create_test_quality_metrics,
    create_weighted_score_metrics,
    create_optimization_weights,
    create_borderline_metrics,
    add_multiple_test_metrics,
    create_memory_overflow_metrics,
    setup_redis_error_mocks,
    setup_pattern_test_texts,
    setup_domain_content_for_recognition,
    setup_content_type_test_cases
)
from netra_backend.tests.helpers.quality_gate_content import (
    get_batch_validation_contents,
    get_batch_validation_context,
    get_brief_optimization_contents
)
from netra_backend.tests.helpers.quality_gate_helpers import (
    assert_cache_key_format,
    assert_caching_identical_results,
    assert_weighted_score_range,
    assert_threshold_check_result,
    assert_suggestions_for_issues,
    assert_prompt_adjustments_structure,
    assert_metrics_storage_structure,
    assert_quality_stats_structure,
    assert_batch_validation_results,
    assert_memory_limit_respected,
    assert_pattern_compilation,
    assert_domain_terms_count,
    assert_content_type_threshold_behavior
)


class TestQualityGateAdvanced:
    """Test suite for advanced QualityGateService features"""
    async def test_caching_mechanism(self, quality_service):
        """Test that validation results are cached properly"""
        content = "Test content for caching validation"
        
        result1 = await quality_service.validate_content(content)
        result2 = await quality_service.validate_content(content)
        
        assert_caching_identical_results(result1, result2)
        cache_key = assert_cache_key_format(content, ContentType.GENERAL)
        assert cache_key in quality_service.validation_cache

    def test_get_weights_for_content_types(self, quality_service):
        """Test weight calculation for different content types"""
        opt_weights = quality_service.validator.get_weights_for_type(ContentType.OPTIMIZATION)
        data_weights = quality_service.validator.get_weights_for_type(ContentType.DATA_ANALYSIS)
        action_weights = quality_service.validator.get_weights_for_type(ContentType.ACTION_PLAN)
        
        assert opt_weights['specificity'] == 0.25
        assert data_weights['quantification'] == 0.30
        assert action_weights['actionability'] == 0.35

    def test_calculate_weighted_score(self, quality_service):
        """Test weighted score calculation"""
        metrics = create_weighted_score_metrics()
        weights = create_optimization_weights()
        
        score = quality_service.validator.calculate_weighted_score(metrics, weights)
        assert_weighted_score_range(score)

    def test_check_thresholds_all_content_types(self, quality_service):
        """Test threshold checking for all content types"""
        good_metrics = create_borderline_metrics()
        content_types = setup_content_type_test_cases()
        
        results = {}
        for content_type in content_types:
            results[content_type] = quality_service.validator.check_thresholds(good_metrics, content_type, strict_mode=False)
        
        assert_content_type_threshold_behavior(results)

    def test_generate_suggestions_for_issues(self, quality_service):
        """Test suggestion generation for various quality issues"""
        from netra_backend.tests.helpers.quality_gate_fixtures import create_low_specificity_metrics
        low_spec_metrics = create_low_specificity_metrics()
        
        suggestions = quality_service.validator.generate_suggestions(low_spec_metrics, ContentType.OPTIMIZATION)
        assert_suggestions_for_issues(suggestions)

    def test_generate_prompt_adjustments(self, quality_service):
        """Test prompt adjustment generation"""
        from netra_backend.tests.helpers.quality_gate_fixtures import create_poor_metrics
        poor_metrics = create_poor_metrics()
        
        adjustments = quality_service.validator.generate_prompt_adjustments(poor_metrics)
        assert_prompt_adjustments_structure(adjustments)
    async def test_store_metrics_in_memory_and_redis(self, quality_service):
        """Test metrics storage in both memory and Redis"""
        metrics = create_test_quality_metrics()
        
        await quality_service._store_metrics(metrics, ContentType.OPTIMIZATION)
        
        assert ContentType.OPTIMIZATION in quality_service.metrics_history
        stored_metric = quality_service.metrics_history[ContentType.OPTIMIZATION][0]
        assert_metrics_storage_structure(stored_metric)
    async def test_get_quality_stats(self, quality_service):
        """Test quality statistics retrieval"""
        metrics_generator = add_multiple_test_metrics(quality_service)
        for metrics in metrics_generator:
            await quality_service._store_metrics(metrics, ContentType.OPTIMIZATION)
        
        stats = await quality_service.get_quality_stats(ContentType.OPTIMIZATION)
        assert_quality_stats_structure(stats, 'optimization')
    async def test_validate_batch_processing(self, quality_service):
        """Test batch validation of multiple contents"""
        contents = get_batch_validation_contents()
        results = await quality_service.validate_batch(contents)
        
        assert_batch_validation_results(results, 3)
    async def test_validate_batch_with_context(self, quality_service):
        """Test batch validation with shared context"""
        contents = get_brief_optimization_contents()
        context = get_batch_validation_context()
        
        results = await quality_service.validate_batch(contents, context)
        assert_batch_validation_results(results, 2)
    async def test_memory_metrics_limit(self, quality_service):
        """Test that metrics history respects memory limits"""
        metrics_generator = create_memory_overflow_metrics()
        for metrics in metrics_generator:
            await quality_service._store_metrics(metrics, ContentType.GENERAL)
        
        assert_memory_limit_respected(quality_service.metrics_history, ContentType.GENERAL)

    def test_pattern_compilation_in_init(self, quality_service):
        """Test that regex patterns are compiled during initialization"""
        assert_pattern_compilation(quality_service)
        
        test_texts = setup_pattern_test_texts()
        core_calc = quality_service.metrics_calculator.core_calculator
        assert core_calc.generic_pattern.search(test_texts['generic']) != None
        assert core_calc.vague_pattern.search(test_texts['vague']) != None
        assert core_calc.circular_pattern.search(test_texts['circular']) != None
    async def test_redis_manager_error_handling(self, quality_service):
        """Test handling of Redis manager errors"""
        setup_redis_error_mocks(quality_service)
        metrics = create_test_quality_metrics()
        
        with patch('app.services.quality_gate.quality_gate_core.logger') as mock_logger:
            await quality_service._store_metrics(metrics, ContentType.GENERAL)
            mock_logger.warning.assert_called()

    def test_domain_terms_recognition(self, quality_service):
        """Test that domain-specific terms are properly recognized"""
        content = setup_domain_content_for_recognition()
        assert_domain_terms_count(content, quality_service)
    async def test_content_type_specific_thresholds(self, quality_service):
        """Test that different content types have appropriate thresholds"""
        borderline_metrics = create_borderline_metrics()
        content_types = setup_content_type_test_cases()
        
        results = {}
        for content_type in content_types:
            results[content_type] = quality_service.validator.check_thresholds(borderline_metrics, content_type, strict_mode=False)
        
        assert_content_type_threshold_behavior(results)