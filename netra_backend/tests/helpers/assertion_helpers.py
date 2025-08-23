"""Assertion helper functions for Quality Gate Service tests"""

from netra_backend.app.services.quality_gate_service import QualityLevel

def assert_complete_workflow_metrics(metrics):
    """Assert metrics for complete workflow testing"""
    assert metrics.word_count > 100
    assert metrics.sentence_count > 5
    assert metrics.generic_phrase_count == 0
    assert metrics.circular_reasoning_detected == False
    assert metrics.specificity_score > 0.7
    assert metrics.actionability_score > 0.6
    assert metrics.quantification_score > 0.8

def assert_complete_workflow_scores(metrics):
    """Assert scores for complete workflow testing"""
    assert metrics.relevance_score > 0.5
    assert metrics.completeness_score >= 0.6
    assert metrics.novelty_score > 0
    assert metrics.clarity_score > 0.6
    assert metrics.redundancy_ratio < 0.3
    assert metrics.hallucination_risk < 0.3
    assert metrics.overall_score > 0.6

def assert_complete_workflow_quality(metrics):
    """Assert quality level for complete workflow"""
    assert metrics.quality_level in [QualityLevel.GOOD, QualityLevel.EXCELLENT]
    assert len(metrics.suggestions) >= 0

def assert_optimization_workflow_passed(result):
    """Assert optimization workflow passed validation"""
    assert result.passed == True
    assert result.metrics.overall_score > 0.8
    assert result.metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]

def assert_optimization_workflow_metrics(result):
    """Assert optimization workflow has high metrics"""
    assert result.metrics.specificity_score > 0.8
    assert result.metrics.actionability_score > 0.8
    assert result.metrics.quantification_score > 0.8
    assert result.metrics.completeness_score > 0.8
    assert result.metrics.clarity_score > 0.7

def assert_optimization_workflow_quality_indicators(result):
    """Assert optimization workflow has quality indicators"""
    assert result.metrics.generic_phrase_count < 2
    assert result.metrics.circular_reasoning_detected == False
    assert result.metrics.hallucination_risk < 0.3
    assert result.metrics.redundancy_ratio < 0.2

def assert_optimization_workflow_no_retry(result):
    """Assert optimization workflow needs no retry"""
    assert result.retry_suggested == False
    assert result.retry_prompt_adjustments == None

def assert_poor_content_failure(result):
    """Assert poor content validation failed"""
    assert result.passed == False
    assert result.retry_suggested == True
    assert result.retry_prompt_adjustments != None

def assert_improvement_cycle_comparison(result1, result2):
    """Assert improvement cycle shows better results"""
    assert result2.passed == True
    assert result2.metrics.overall_score > result1.metrics.overall_score
    assert result2.metrics.generic_phrase_count < result1.metrics.generic_phrase_count