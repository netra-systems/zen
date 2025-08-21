"""
Metrics calculation tests for Quality Gate Service
Tests individual metric calculation methods
"""

import pytest
from netra_backend.app.services.quality_gate_service import ContentType, QualityMetrics
from netra_backend.tests.helpers.quality_gate_fixtures import redis_mock, quality_service
from netra_backend.tests.helpers.quality_gate_content import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    get_high_specificity_content,
    get_low_specificity_content,
    get_high_actionability_content,
    get_low_actionability_content,
    get_high_quantification_content,
    get_low_quantification_content,
    get_optimization_context,
    get_relevant_context,
    get_irrelevant_context,
    get_complete_optimization_content,
    get_complete_action_plan_simple,
    get_clear_content,
    get_unclear_content,
    get_high_redundancy_content,
    get_low_redundancy_content,
    get_high_hallucination_risk_content,
    get_low_hallucination_risk_content
)
from netra_backend.tests.helpers.quality_gate_helpers import (
    assert_specificity_score_range,
    assert_actionability_score_range,
    assert_quantification_score_range,
    assert_relevance_with_context,
    assert_completeness_by_content_type,
    assert_clarity_score_approximation,
    assert_redundancy_algorithm_behavior,
    assert_hallucination_risk_range
)
from netra_backend.tests.helpers.quality_gate_fixtures import (
    setup_novelty_mocks_fresh,
    setup_novelty_mocks_duplicate
)


class TestQualityGateMetrics:
    """Test suite for QualityGateService metrics calculation"""
    async def test_calculate_specificity_scores(self, quality_service):
        """Test specificity calculation for various content types"""
        high_spec_content = get_high_specificity_content()
        low_spec_content = get_low_specificity_content()
        
        high_score = await quality_service.metrics_calculator.calculate_specificity(high_spec_content, ContentType.OPTIMIZATION)
        low_score = await quality_service.metrics_calculator.calculate_specificity(low_spec_content, ContentType.OPTIMIZATION)
        
        assert_specificity_score_range(high_score, high_quality=True)
        assert_specificity_score_range(low_score, high_quality=False)
    async def test_calculate_actionability_scores(self, quality_service):
        """Test actionability calculation"""
        high_action_content = get_high_actionability_content()
        low_action_content = get_low_actionability_content()
        
        high_score = await quality_service.metrics_calculator.calculate_actionability(high_action_content, ContentType.ACTION_PLAN)
        low_score = await quality_service.metrics_calculator.calculate_actionability(low_action_content, ContentType.ACTION_PLAN)
        
        assert_actionability_score_range(high_score, high_quality=True)
        assert_actionability_score_range(low_score, high_quality=False)
    async def test_calculate_quantification_scores(self, quality_service):
        """Test quantification calculation"""
        high_quant_content = get_high_quantification_content()
        low_quant_content = get_low_quantification_content()
        
        high_score = await quality_service.metrics_calculator.calculate_quantification(high_quant_content)
        low_score = await quality_service.metrics_calculator.calculate_quantification(low_quant_content)
        
        assert_quantification_score_range(high_score, high_quality=True)
        assert_quantification_score_range(low_score, high_quality=False)
    async def test_calculate_relevance_with_context(self, quality_service):
        """Test relevance calculation with user context"""
        content = get_optimization_context()
        relevant_context = get_relevant_context()
        irrelevant_context = get_irrelevant_context()
        
        relevant_score = await quality_service.metrics_calculator.calculate_relevance(content, relevant_context)
        irrelevant_score = await quality_service.metrics_calculator.calculate_relevance(content, irrelevant_context)
        no_context_score = await quality_service.metrics_calculator.calculate_relevance(content, None)
        
        assert_relevance_with_context(relevant_score, has_context=True)
        assert irrelevant_score == 0.0
        assert no_context_score == 0.5
    async def test_calculate_completeness_by_content_type(self, quality_service):
        """Test completeness calculation for different content types"""
        opt_content = get_complete_optimization_content()
        action_content = get_complete_action_plan_simple()
        
        opt_score = await quality_service.metrics_calculator.calculate_completeness(opt_content, ContentType.OPTIMIZATION)
        action_score = await quality_service.metrics_calculator.calculate_completeness(action_content, ContentType.ACTION_PLAN)
        
        assert_completeness_by_content_type(opt_score, ContentType.OPTIMIZATION)
        assert_completeness_by_content_type(action_score, ContentType.ACTION_PLAN)
    async def test_calculate_novelty_with_redis(self, quality_service):
        """Test novelty calculation with Redis caching"""
        content = "Unique content for novelty testing"
        
        setup_novelty_mocks_fresh(quality_service, content)
        fresh_score = await quality_service.metrics_calculator.calculate_novelty(content)
        assert fresh_score >= 0.7
        
        setup_novelty_mocks_duplicate(quality_service, content)
        duplicate_score = await quality_service.metrics_calculator.calculate_novelty(content)
        assert duplicate_score == 0.0
    async def test_calculate_clarity_scores(self, quality_service):
        """Test clarity calculation"""
        clear_content = get_clear_content()
        unclear_content = get_unclear_content()
        
        clear_score = await quality_service.metrics_calculator.calculate_clarity(clear_content)
        unclear_score = await quality_service.metrics_calculator.calculate_clarity(unclear_content)
        
        assert clear_score >= 0.7
        # Unclear content has very long sentences and complex structure
        # Should score low (around 0.3) due to clarity penalties
        assert_clarity_score_approximation(unclear_score, 0.3)
    async def test_calculate_redundancy_detection(self, quality_service):
        """Test redundancy detection"""
        redundant_content = get_high_redundancy_content()
        diverse_content = get_low_redundancy_content()
        
        redundant_score = await quality_service.metrics_calculator.calculate_redundancy(redundant_content)
        diverse_score = await quality_service.metrics_calculator.calculate_redundancy(diverse_content)
        
        assert_redundancy_algorithm_behavior(redundant_score)
        assert_redundancy_algorithm_behavior(diverse_score)
    async def test_calculate_hallucination_risk(self, quality_service):
        """Test hallucination risk detection"""
        risky_content = get_high_hallucination_risk_content()
        safe_content = get_low_hallucination_risk_content()
        
        risky_score = await quality_service.metrics_calculator.calculate_hallucination_risk(risky_content, None)
        safe_score = await quality_service.metrics_calculator.calculate_hallucination_risk(safe_content, {"data_source": "benchmark"})
        
        assert_hallucination_risk_range(risky_score, high_risk=True)
        assert_hallucination_risk_range(safe_score, high_risk=False)
    async def test_novelty_without_redis(self, quality_service):
        """Test novelty calculation when Redis is not available"""
        quality_service.redis_manager = None
        score = await quality_service.metrics_calculator.calculate_novelty("test content")
        assert score == 0.8