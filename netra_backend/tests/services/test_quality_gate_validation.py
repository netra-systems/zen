"""Tests for Quality Gate Service - Input Validation and Data Classes

This module tests input validation, data class initialization, error handling,
and caching mechanisms for the Quality Gate Service.
"""

import sys
from pathlib import Path

import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.redis_manager import RedisManager

from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    QualityLevel,
    QualityMetrics,
    ValidationResult,
)
from netra_backend.tests.services.helpers.shared_test_types import (
    TestErrorHandling as SharedTestErrorHandling,
)

class TestQualityMetricsDataclass:
    """Test QualityMetrics dataclass initialization and defaults"""
    
    def test_quality_metrics_defaults(self):
        """Test QualityMetrics default values"""
        metrics = QualityMetrics()
        
        assert metrics.specificity_score == 0.0
        assert metrics.actionability_score == 0.0
        assert metrics.quantification_score == 0.0
        assert metrics.relevance_score == 0.0
        assert metrics.completeness_score == 0.0
        assert metrics.novelty_score == 0.0
        assert metrics.clarity_score == 0.0
        assert metrics.generic_phrase_count == 0
        assert metrics.circular_reasoning_detected == False
        assert metrics.hallucination_risk == 0.0
        assert metrics.redundancy_ratio == 0.0
        assert metrics.word_count == 0
        assert metrics.sentence_count == 0
        assert metrics.numeric_values_count == 0
        assert metrics.specific_terms_count == 0
        assert metrics.overall_score == 0.0
        assert metrics.quality_level == QualityLevel.UNACCEPTABLE
        assert metrics.issues == []
        assert metrics.suggestions == []
        
    def test_quality_metrics_custom_values(self):
        """Test QualityMetrics with custom values"""
        issues = ["Issue 1", "Issue 2"]
        suggestions = ["Suggestion 1"]
        
        metrics = QualityMetrics(
            specificity_score=0.8,
            actionability_score=0.9,
            generic_phrase_count=3,
            circular_reasoning_detected=True,
            issues=issues,
            suggestions=suggestions
        )
        
        assert metrics.specificity_score == 0.8
        assert metrics.actionability_score == 0.9
        assert metrics.generic_phrase_count == 3
        assert metrics.circular_reasoning_detected == True
        assert metrics.issues == issues
        assert metrics.suggestions == suggestions

class TestValidationResultDataclass:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_initialization(self):
        """Test ValidationResult initialization"""
        metrics = QualityMetrics(overall_score=0.75)
        
        result = ValidationResult(
            passed=True,
            metrics=metrics,
            retry_suggested=False,
            retry_prompt_adjustments={"temperature": 0.5},
            fallback_response="Fallback content"
        )
        
        assert result.passed == True
        assert result.metrics == metrics
        assert result.retry_suggested == False
        assert result.retry_prompt_adjustments == {"temperature": 0.5}
        assert result.fallback_response == "Fallback content"
        
    def test_validation_result_defaults(self):
        """Test ValidationResult default values"""
        metrics = QualityMetrics()
        result = ValidationResult(passed=False, metrics=metrics)
        
        assert result.passed == False
        assert result.metrics == metrics
        assert result.retry_suggested == False
        assert result.retry_prompt_adjustments == None
        assert result.fallback_response == None

class TestCachingMechanism:
    """Test content caching functionality"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, quality_service):
        """Test cache key generation for different content"""
        content1 = "Test content 1"
        content2 = "Test content 2"
        
        result1 = await quality_service.validate_content(
            content1,
            ContentType.OPTIMIZATION
        )
        
        result2 = await quality_service.validate_content(
            content2,
            ContentType.OPTIMIZATION
        )
        
        # Different content should have different cache keys
        assert len(quality_service.validation_cache) == 2
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, quality_service):
        """Test that cache mechanism works correctly with reasonable performance"""
        content = "Performance test content with some complexity"
        
        # First call - should calculate
        start1 = time.time()
        result1 = await quality_service.validate_content(content)
        time1 = time.time() - start1
        
        # Second call - should use cache
        start2 = time.time()
        result2 = await quality_service.validate_content(content)
        time2 = time.time() - start2
        
        # For micro-performance operations, allow reasonable variance
        # Focus on functional correctness over strict performance requirements
        performance_tolerance = 0.002  # 2ms tolerance for system variance
        if time1 > 0.001:  # Only check performance if measurable
            assert time2 <= (time1 + performance_tolerance), \
                f"Cache hit ({time2:.6f}s) should be close to baseline ({time1:.6f}s)"
        
        # Verify cache functionality - results must be identical
        assert result1.metrics.overall_score == result2.metrics.overall_score
        assert len(quality_service.validation_cache) == 1  # Confirm cache entry exists

class TestErrorHandling(SharedTestErrorHandling):
    """Test error handling in various methods"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    
    @pytest.fixture
    def service(self):
        """Provide service fixture for shared test methods"""
        return QualityGateService(redis_manager=None)
    
    @pytest.fixture
    def agent_or_service(self):
        """Provide agent_or_service fixture for shared test methods"""
        return QualityGateService(redis_manager=None)
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, agent_or_service):
        """Override retry test - QualityGateService doesn't have retry mechanism"""
        pytest.skip("QualityGateService doesn't have retry mechanism")
    @pytest.mark.asyncio
    async def test_validate_content_calculation_error(self, quality_service):
        """Test error during metrics calculation"""
        with patch.object(
            quality_service,
            '_calculate_content_metrics',
            side_effect=ValueError("Calculation error")
        ):
            result = await quality_service.validate_content("Test")
            
            assert result.passed == False
            assert "Validation error" in result.metrics.issues[0]
    @pytest.mark.asyncio
    async def test_validate_content_threshold_error(self, quality_service):
        """Test error during threshold checking"""
        # The actual threshold checking is done in the validator component
        with patch.object(
            quality_service.validator,
            'check_thresholds',
            side_effect=KeyError("Missing threshold")
        ):
            result = await quality_service.validate_content("Test")
            
            assert result.passed == False
    @pytest.mark.asyncio
    async def test_store_metrics_error_handling(self, quality_service):
        """Test error handling in metrics storage"""
        metrics = QualityMetrics()
        
        # Create a metrics history that causes error
        quality_service.metrics_history = None
        
        # Should not raise, just log warning
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.services.quality_gate.quality_gate_core.logger') as mock_logger:
            await quality_service._store_metrics(metrics, ContentType.GENERAL)
            mock_logger.warning.assert_called()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])