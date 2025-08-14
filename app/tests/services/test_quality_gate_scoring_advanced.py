"""Tests for Quality Gate Service - Advanced Scoring Algorithms

This module tests advanced scoring implementations including novelty, clarity,
redundancy, hallucination risk, and weighted scoring calculations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from app.services.quality_gate_service import (
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from app.redis_manager import RedisManager


class TestNoveltyCalculation:
    """Test novelty calculation with Redis integration"""
    
    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock(spec=RedisManager)
        return mock
        
    @pytest.fixture
    def quality_service(self, mock_redis):
        return QualityGateService(redis_manager=mock_redis)
        
    @pytest.mark.asyncio
    async def test_novelty_redis_error_handling(self, quality_service, mock_redis):
        """Test novelty calculation when Redis operations fail"""
        content = "Test content"
        
        # Simulate Redis error
        mock_redis.get_list.side_effect = Exception("Redis connection failed")
        
        score = await quality_service._calculate_novelty(content)
        assert score == 0.5  # Should return default on error
        
    @pytest.mark.asyncio
    async def test_novelty_large_cache(self, quality_service, mock_redis):
        """Test novelty with large cache list"""
        content = "Unique content"
        
        # Simulate large cache
        mock_redis.get_list.return_value = ["hash" + str(i) for i in range(100)]
        
        score = await quality_service._calculate_novelty(content)
        assert score == 0.8  # Should be novel if not in cache


class TestClarityCalculation:
    """Test clarity calculation edge cases"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_clarity_very_long_sentences(self, quality_service):
        """Test clarity with very long sentences"""
        # Create a sentence with 50+ words
        long_sentence = " ".join(["word"] * 50) + "."
        
        score = await quality_service._calculate_clarity(long_sentence)
        assert score < 0.6  # Should be penalized for length
        
    @pytest.mark.asyncio
    async def test_clarity_excessive_acronyms(self, quality_service):
        """Test clarity with many unexplained acronyms"""
        content = "Use API, SDK, CLI, GUI, REST, SOAP, XML, JSON, YAML, CSV for integration."
        
        score = await quality_service._calculate_clarity(content)
        assert score < 0.95  # Should be slightly penalized
        
    @pytest.mark.asyncio
    async def test_clarity_nested_parentheses(self, quality_service):
        """Test clarity with nested parentheses"""
        content = "The system (which includes components (like cache (Redis) and database)) is complex."
        
        score = await quality_service._calculate_clarity(content)
        assert score < 0.95  # Should be penalized
        
    @pytest.mark.asyncio
    async def test_clarity_no_sentences(self, quality_service):
        """Test clarity calculation with no proper sentences"""
        content = "optimization performance metrics"
        
        score = await quality_service._calculate_clarity(content)
        assert score >= 0  # Should handle gracefully


class TestRedundancyCalculation:
    """Test redundancy calculation edge cases"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_redundancy_single_sentence(self, quality_service):
        """Test redundancy with single sentence"""
        content = "This is a single sentence."
        
        score = await quality_service._calculate_redundancy(content)
        assert score == 0.0  # No redundancy possible
        
    @pytest.mark.asyncio
    async def test_redundancy_empty_sentences(self, quality_service):
        """Test redundancy with empty sentence splits"""
        content = "First. . . Last."
        
        score = await quality_service._calculate_redundancy(content)
        assert score >= 0  # Should handle empty splits
        
    @pytest.mark.asyncio
    async def test_redundancy_high_overlap(self, quality_service):
        """Test redundancy with high word overlap"""
        content = """
        The optimization improves system performance significantly.
        System performance improves significantly with the optimization.
        Significant performance improvements come from system optimization.
        """
        
        score = await quality_service._calculate_redundancy(content)
        assert score > 0.4  # Should detect high redundancy


class TestHallucinationRisk:
    """Test hallucination risk detection"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_hallucination_specific_numbers_with_context(self, quality_service):
        """Test hallucination risk with specific numbers but with data source"""
        content = "The system processes exactly 12345.678 requests per second."
        context = {"data_source": "production_metrics"}
        
        score = await quality_service._calculate_hallucination_risk(content, context)
        assert score < 0.2  # Should be low with data source
        
    @pytest.mark.asyncio
    async def test_hallucination_claims_with_evidence(self, quality_service):
        """Test hallucination risk for claims with evidence"""
        content = "Studies show improvement according to Smith et al. (2023) [1]."
        
        score = await quality_service._calculate_hallucination_risk(content, None)
        assert score < 0.3  # Should be low with citations
        
    @pytest.mark.asyncio
    async def test_hallucination_multiple_impossible_claims(self, quality_service):
        """Test hallucination risk with multiple impossible claims"""
        content = """
        Achieve 100% improvement with zero latency.
        Perfect accuracy guaranteed with infinite throughput.
        No cost solution with unlimited scaling.
        """
        
        score = await quality_service._calculate_hallucination_risk(content, None)
        assert score > 0.8  # Should be very high


class TestWeightedScoring:
    """Test weighted score calculation with penalties"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    def test_weighted_score_no_penalties(self, quality_service):
        """Test weighted score without penalties"""
        metrics = QualityMetrics(
            specificity_score=1.0,
            actionability_score=1.0,
            quantification_score=1.0,
            relevance_score=1.0,
            completeness_score=1.0,
            novelty_score=1.0,
            clarity_score=1.0
        )
        
        weights = {
            'specificity': 0.2,
            'actionability': 0.2,
            'quantification': 0.2,
            'relevance': 0.2,
            'completeness': 0.2
        }
        
        score = quality_service._calculate_weighted_score(metrics, weights)
        assert score == 1.0  # Perfect score
        
    def test_weighted_score_all_penalties(self, quality_service):
        """Test weighted score with all penalties applied"""
        metrics = QualityMetrics(
            specificity_score=0.8,
            actionability_score=0.8,
            generic_phrase_count=10,  # High penalty
            circular_reasoning_detected=True,  # -0.2
            hallucination_risk=0.8,  # -0.15
            redundancy_ratio=0.5  # -0.1
        )
        
        weights = {'specificity': 0.5, 'actionability': 0.5}
        
        score = quality_service._calculate_weighted_score(metrics, weights)
        assert score < 0.5  # Should be heavily penalized
        
    def test_weighted_score_zero_weight(self, quality_service):
        """Test weighted score with zero total weight"""
        metrics = QualityMetrics()
        weights = {}  # No weights
        
        score = quality_service._calculate_weighted_score(metrics, weights)
        assert score == 0.0  # Should handle zero weight gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])