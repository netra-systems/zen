"""Tests for Quality Gate Service - Threshold Checking and Suggestions

This module tests threshold checking, suggestion generation, and prompt adjustments.
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


class TestThresholdChecking:
    """Test threshold checking for all scenarios"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    def test_threshold_all_specific_checks(self, quality_service):
        """Test all specific threshold checks"""
        metrics = QualityMetrics(
            overall_score=0.4,  # Below min_score
            specificity_score=0.4,  # Below min_specificity
            actionability_score=0.4,  # Below min_actionability
            quantification_score=0.4,  # Below min_quantification
            relevance_score=0.4,  # Below min_relevance
            completeness_score=0.4,  # Below min_completeness
            clarity_score=0.4,  # Below min_clarity
            redundancy_ratio=0.5,  # Above max_redundancy
            generic_phrase_count=10  # Above max_generic_phrases
        )
        
        # Should fail for optimization type
        passed = quality_service.validator.check_thresholds(
            metrics,
            ContentType.OPTIMIZATION,
            strict_mode=False
        )
        assert passed == False
        
    def test_threshold_hallucination_critical_failure(self, quality_service):
        """Test critical failure due to high hallucination risk"""
        metrics = QualityMetrics(
            overall_score=0.9,
            hallucination_risk=0.8  # Above 0.7 threshold
        )
        
        passed = quality_service.validator.check_thresholds(
            metrics,
            ContentType.GENERAL,
            strict_mode=False
        )
        assert passed == False


class TestSuggestionGeneration:
    """Test suggestion generation for all issue types"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    def test_suggestions_all_issues(self, quality_service):
        """Test suggestions for all possible issues"""
        metrics = QualityMetrics(
            specificity_score=0.3,
            actionability_score=0.3,
            quantification_score=0.3,
            generic_phrase_count=5,
            circular_reasoning_detected=True,
            redundancy_ratio=0.4,
            completeness_score=0.3
        )
        
        suggestions = quality_service.validator.generate_suggestions(
            metrics,
            ContentType.OPTIMIZATION
        )
        
        # Should have suggestions for all issues
        assert len(suggestions) >= 6
        assert any("specific" in s for s in suggestions)
        assert any("action" in s for s in suggestions)
        assert any("numerical" in s for s in suggestions)
        assert any("generic" in s for s in suggestions)
        assert any("circular" in s for s in suggestions)
        assert any("redundant" in s for s in suggestions)
        
    def test_suggestions_optimization_specific(self, quality_service):
        """Test optimization-specific suggestions"""
        metrics = QualityMetrics(
            quantification_score=0.3,
            completeness_score=0.8
        )
        
        suggestions = quality_service.validator.generate_suggestions(
            metrics,
            ContentType.OPTIMIZATION
        )
        
        assert any("before/after" in s for s in suggestions)
        
    def test_suggestions_action_plan_specific(self, quality_service):
        """Test action plan-specific suggestions"""
        metrics = QualityMetrics(
            completeness_score=0.3,
            actionability_score=0.8
        )
        
        suggestions = quality_service.validator.generate_suggestions(
            metrics,
            ContentType.ACTION_PLAN
        )
        
        assert any("verification" in s or "success criteria" in s for s in suggestions)


class TestPromptAdjustments:
    """Test prompt adjustment generation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    def test_prompt_adjustments_all_issues(self, quality_service):
        """Test prompt adjustments for all issue types"""
        metrics = QualityMetrics(
            specificity_score=0.2,
            actionability_score=0.2,
            quantification_score=0.2,
            generic_phrase_count=8,
            circular_reasoning_detected=True
        )
        
        adjustments = quality_service.validator.generate_prompt_adjustments(metrics)
        
        assert adjustments['temperature'] == 0.3
        assert len(adjustments['additional_instructions']) == 5
        
        instructions_text = ' '.join(adjustments['additional_instructions'])
        assert "specific" in instructions_text
        assert "step-by-step" in instructions_text or "actionable" in instructions_text
        assert "numerical" in instructions_text
        assert "generic" in instructions_text
        assert "HOW" in instructions_text  # From circular reasoning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])