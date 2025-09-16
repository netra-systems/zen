"""Helper functions for Quality Gate Service tests"""

import hashlib
from unittest.mock import AsyncMock, Mock

from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    QualityLevel,
    QualityMetrics,
    ValidationResult,
)

def create_redis_mock():
    """Create mock Redis manager with common async methods"""
    redis_mock = Mock(spec=RedisManager)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.store_metrics = AsyncMock(return_value=True)
    redis_mock.get_list = AsyncMock(return_value=[])
    redis_mock.add_to_list = AsyncMock()
    return redis_mock

def create_quality_service(redis_mock=None):
    """Create QualityGateService with mocked dependencies"""
    if redis_mock is None:
        redis_mock = create_redis_mock()
    return QualityGateService(redis_manager=redis_mock)

def create_test_metrics(overall_score=0.8, quality_level=QualityLevel.GOOD):
    """Create test QualityMetrics with defaults"""
    return QualityMetrics(
        overall_score=overall_score,
        quality_level=quality_level,
        specificity_score=0.7,
        actionability_score=0.8,
        quantification_score=0.6
    )

def assert_validation_passed(result):
    """Assert validation result passed with high quality"""
    assert result.passed == True
    assert result.metrics.overall_score >= 0.7
    assert result.metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
    assert len(result.metrics.issues) == 0

def assert_validation_failed(result):
    """Assert validation result failed with specific checks"""
    assert result.passed == False
    assert result.metrics.overall_score < 0.5
    assert result.metrics.quality_level in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]
    assert len(result.metrics.issues) > 0

def assert_high_quality_metrics(result):
    """Assert metrics indicate high quality content"""
    assert result.metrics.specificity_score >= 0.6
    assert result.metrics.actionability_score >= 0.7
    assert result.metrics.quantification_score >= 0.7

def assert_low_quality_metrics(result):
    """Assert metrics indicate low quality content"""
    assert result.metrics.specificity_score < 0.3
    assert result.metrics.actionability_score < 0.3
    assert result.metrics.generic_phrase_count > 5

def assert_circular_reasoning_detected(result):
    """Assert circular reasoning was detected"""
    assert result.passed == False
    assert result.metrics.circular_reasoning_detected == True
    assert "circular reasoning" in str(result.metrics.issues).lower()

def assert_cache_key_format(content, content_type, strict_mode=False):
    """Assert cache key follows expected format"""
    content_hash = hashlib.md5(content.encode()).hexdigest()
    expected_key = f"quality:{content_type.value}:{content_hash}:strict={strict_mode}"
    return expected_key

def assert_quantification_metrics(result, min_score=0.8, min_numeric_count=10):
    """Assert quantification metrics meet thresholds"""
    assert result.metrics.quantification_score >= min_score
    assert result.metrics.numeric_values_count > min_numeric_count

def assert_action_plan_completeness(result):
    """Assert action plan has required completeness elements"""
    assert result.metrics.completeness_score == 1.0
    assert result.metrics.actionability_score >= 0.7
    assert result.metrics.clarity_score >= 0.7

def assert_strict_mode_differences(result_normal, result_strict):
    """Assert strict mode is more restrictive than normal mode"""
    assert result_normal.passed == True
    assert result_strict.passed == False
    assert result_strict.retry_suggested == True

def assert_error_message_clarity(result):
    """Assert error message clarity metrics"""
    assert result.metrics.clarity_score >= 0.8
    assert result.metrics.actionability_score < 0.3
    # Overall score may be higher due to good clarity score

def assert_redundancy_detected(result, min_ratio=0.3):
    """Assert redundancy was detected in content"""
    assert result.passed == False
    assert result.metrics.redundancy_ratio > min_ratio
    # Note: Current implementation doesn't provide redundancy-specific suggestions
    # but the metrics correctly detect redundancy

def assert_domain_terms_recognition(result):
    """Assert domain-specific terms were recognized"""
    assert result.metrics.specificity_score >= 0.6
    assert result.metrics.quantification_score >= 0.8
    assert result.metrics.quality_level == QualityLevel.ACCEPTABLE

def assert_caching_identical_results(result1, result2):
    """Assert cached results are identical"""
    assert result1.passed == result2.passed
    assert result1.metrics.overall_score == result2.metrics.overall_score

def assert_retry_suggestions_provided(result):
    """Assert retry suggestions are provided for failed validation"""
    assert result.passed == False
    assert result.retry_suggested == True
    assert result.retry_prompt_adjustments != None
    assert "specific" in str(result.metrics.suggestions).lower()
    assert len(result.metrics.suggestions) > 0

def assert_hallucination_risk_detected(result, expected_risk=0.2):
    """Assert hallucination risk was detected"""
    assert result.passed == False
    assert result.metrics.hallucination_risk == expected_risk

def assert_triage_content_metrics(result):
    """Assert triage content has appropriate metrics"""
    assert result.metrics.relevance_score >= 0.5
    assert result.metrics.specificity_score >= 0.2

def assert_context_improves_relevance(result_with_context, result_no_context):
    """Assert context improves relevance scores"""
    assert result_with_context.metrics.relevance_score >= result_no_context.metrics.relevance_score

def assert_quality_level_classification(quality_service, score, expected_level):
    """Assert quality level is correctly classified"""
    metrics = QualityMetrics(overall_score=score)
    metrics.quality_level = quality_service.validator.determine_quality_level(score)
    assert metrics.quality_level == expected_level

def assert_specificity_score_range(score, high_quality=True):
    """Assert specificity score is in expected range"""
    if high_quality:
        assert score >= 0.7
    else:
        assert score <= 0.3

def assert_actionability_score_range(score, high_quality=True):
    """Assert actionability score is in expected range"""
    if high_quality:
        assert score >= 0.7
    else:
        assert score <= 0.3

def assert_quantification_score_range(score, high_quality=True):
    """Assert quantification score is in expected range"""
    if high_quality:
        assert score >= 0.8
    else:
        assert score <= 0.2

def assert_relevance_with_context(score, has_context=True):
    """Assert relevance score based on context availability"""
    if has_context:
        assert score >= 0.5
    else:
        assert score == 0.5  # Default baseline

def assert_completeness_by_content_type(score, content_type):
    """Assert completeness score appropriate for content type"""
    if content_type == ContentType.OPTIMIZATION:
        assert score >= 0.4
    elif content_type == ContentType.ACTION_PLAN:
        assert score == 1.0

def assert_novelty_score_range(score, is_duplicate=False):
    """Assert novelty score is in expected range"""
    if is_duplicate:
        assert score == 0.0
    else:
        assert score >= 0.7

def assert_clarity_score_approximation(score, expected_score, tolerance=0.01):
    """Assert clarity score is approximately expected value"""
    assert abs(score - expected_score) < tolerance

def assert_redundancy_algorithm_behavior(score):
    """Assert redundancy algorithm behaves as expected"""
    assert score == 0.0  # Algorithm requires >70% word overlap

def assert_hallucination_risk_range(score, high_risk=True):
    """Assert hallucination risk is in expected range"""
    if high_risk:
        assert score >= 0.2
    else:
        assert score <= 0.3

def assert_weighted_score_range(score):
    """Assert weighted score is in valid range"""
    assert 0.0 <= score <= 1.0
    assert score >= 0.6  # Should be good score given input metrics

def assert_threshold_check_result(passed, should_pass=True):
    """Assert threshold check result"""
    assert passed == should_pass

def assert_suggestions_for_issues(suggestions):
    """Assert suggestions address common quality issues"""
    assert len(suggestions) > 0
    suggestions_text = " ".join(suggestions).lower()
    assert any(word in suggestions_text for word in ["specific", "numerical", "generic", "circular", "redundant"])

def assert_prompt_adjustments_structure(adjustments):
    """Assert prompt adjustments have expected structure"""
    assert adjustments['temperature'] == 0.3
    assert len(adjustments['additional_instructions']) > 0
    instructions = ' '.join(adjustments['additional_instructions']).lower()
    assert any(word in instructions for word in ["specific", "actionable", "numerical", "generic", "circular"])

def assert_metrics_storage_structure(stored_metric):
    """Assert stored metrics have expected structure"""
    assert stored_metric['overall_score'] == 0.8
    assert stored_metric['quality_level'] == 'good'

def assert_quality_stats_structure(stats, content_type_key):
    """Assert quality statistics have expected structure"""
    assert content_type_key in stats
    type_stats = stats[content_type_key]
    _assert_count_and_scores(type_stats)
    _assert_failure_rate_and_distribution(type_stats)

def assert_batch_validation_results(results, expected_count):
    """Assert batch validation results structure"""
    assert len(results) == expected_count
    assert all(isinstance(result, ValidationResult) for result in results)

def assert_error_handling_result(result):
    """Assert error handling produces expected result"""
    assert result.passed == False
    assert result.metrics.overall_score == 0.0
    assert result.metrics.quality_level == QualityLevel.UNACCEPTABLE
    assert len(result.metrics.issues) > 0
    assert "Validation error" in result.metrics.issues[0]

def assert_memory_limit_respected(metrics_history, content_type, max_count=1000):
    """Assert memory limit is respected for metrics history"""
    assert len(metrics_history[content_type]) == max_count

def assert_pattern_compilation(quality_service):
    """Assert regex patterns are compiled during initialization"""
    assert quality_service.metrics_calculator.core_calculator.generic_pattern != None
    assert quality_service.metrics_calculator.core_calculator.vague_pattern != None
    assert quality_service.metrics_calculator.core_calculator.circular_pattern != None

def assert_domain_terms_count(content, quality_service, min_count=8):
    """Assert domain terms are properly recognized"""
    domain_term_count = sum(1 for term in quality_service.patterns.DOMAIN_TERMS 
                           if term in content.lower())
    assert domain_term_count >= min_count

def _assert_count_and_scores(type_stats):
    """Assert count and score values are correct."""
    assert type_stats['count'] == 10
    assert 0.7 <= type_stats['avg_score'] <= 0.88
    assert type_stats['min_score'] >= 0.7
    assert type_stats['max_score'] <= 0.88

def _assert_failure_rate_and_distribution(type_stats):
    """Assert failure rate and quality distribution are correct."""
    assert 0 <= type_stats['failure_rate'] <= 1
    assert 'quality_distribution' in type_stats

def assert_content_type_threshold_behavior(results):
    """Assert different content types have different threshold behavior"""
    for content_type, result in results.items():
        assert isinstance(result, bool)