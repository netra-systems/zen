"""Tests for Quality Gate Service hallucination risk and scoring calculations"""

import sys
from pathlib import Path

import pytest

from netra_backend.app.services.quality_gate_service import (
    QualityGateService,
    QualityMetrics,
)
from netra_backend.tests.helpers.quality_gate_comprehensive_helpers import (
    create_all_penalties_metrics,
    create_claims_with_evidence_content,
    create_context_with_data_source,
    create_multiple_impossible_claims_content,
)

class TestHallucinationRisk:
    """Test hallucination risk detection"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    @pytest.mark.asyncio
    async def test_hallucination_specific_numbers_with_context(self, quality_service):
        """Test hallucination risk with specific numbers but with data source"""
        content = "The system processes exactly 12345.678 requests per second."
        context = create_context_with_data_source()
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_hallucination_risk(content, context)
        assert score < 0.2  # Should be low with data source
    @pytest.mark.asyncio
    async def test_hallucination_claims_with_evidence(self, quality_service):
        """Test hallucination risk for claims with evidence"""
        content = create_claims_with_evidence_content()
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_hallucination_risk(content, None)
        assert score < 0.3  # Should be low with citations
    @pytest.mark.asyncio
    async def test_hallucination_multiple_impossible_claims(self, quality_service):
        """Test hallucination risk with multiple impossible claims"""
        content = create_multiple_impossible_claims_content()
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_hallucination_risk(content, None)
        assert score > 0.3  # Should be elevated for impossible claims (current algorithm returns 0.4)

class TestWeightedScoring:
    """Test weighted score calculation with penalties"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    def _create_perfect_metrics(self):
        """Create perfect metrics for testing"""
        return QualityMetrics(
            specificity_score=1.0,
            actionability_score=1.0,
            quantification_score=1.0,
            relevance_score=1.0,
            completeness_score=1.0,
            novelty_score=1.0,
            clarity_score=1.0
        )
        
    def _create_basic_weights(self):
        """Create basic weight distribution"""
        return {
            'specificity': 0.2,
            'actionability': 0.2,
            'quantification': 0.2,
            'relevance': 0.2,
            'completeness': 0.2
        }
        
    def test_weighted_score_no_penalties(self, quality_service):
        """Test weighted score without penalties"""
        metrics = self._create_perfect_metrics()
        weights = self._create_basic_weights()
        
        score = quality_service.validator.calculate_weighted_score(metrics, weights)
        assert score == 1.0  # Perfect score
        
    def _create_penalty_weights(self):
        """Create weight distribution for penalty testing"""
        return {'specificity': 0.5, 'actionability': 0.5}
        
    def test_weighted_score_all_penalties(self, quality_service):
        """Test weighted score with all penalties applied"""
        metrics = create_all_penalties_metrics()
        weights = self._create_penalty_weights()
        
        score = quality_service.validator.calculate_weighted_score(metrics, weights)
        assert score < 0.5  # Should be heavily penalized
        
    def test_weighted_score_zero_weight(self, quality_service):
        """Test weighted score with zero total weight"""
        metrics = QualityMetrics()
        weights = {}  # No weights
        
        score = quality_service.validator.calculate_weighted_score(metrics, weights)
        assert score == 0.0  # Should handle zero weight gracefully