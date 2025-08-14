"""Tests for Quality Gate Service threshold checking and suggestion generation"""

import pytest
from app.services.quality_gate_service import (
    QualityGateService,
    QualityMetrics,
    ContentType
)
from app.tests.helpers.quality_gate_comprehensive_helpers import (
    create_all_specific_checks_metrics,
    create_high_hallucination_metrics,
    create_all_issues_metrics,
    create_borderline_optimization_metrics,
    create_borderline_action_plan_metrics,
    create_prompt_adjustment_metrics
)


class TestThresholdChecking:
    """Test threshold checking for all scenarios"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    def test_threshold_all_specific_checks(self, quality_service):
        """Test all specific threshold checks"""
        metrics = create_all_specific_checks_metrics()
        
        passed = quality_service.validator.check_thresholds(
            metrics,
            ContentType.OPTIMIZATION,
            strict_mode=False
        )
        assert passed == False
        
    def test_threshold_hallucination_critical_failure(self, quality_service):
        """Test critical failure due to high hallucination risk"""
        metrics = create_high_hallucination_metrics()
        
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
        
    def _assert_suggestions_for_common_issues(self, suggestions):
        """Assert suggestions address common issues"""
        assert len(suggestions) >= 6
        assert any("specific" in s for s in suggestions)
        assert any("action" in s for s in suggestions)
        assert any("numerical" in s for s in suggestions)
        
    def _assert_suggestions_for_quality_issues(self, suggestions):
        """Assert suggestions address quality issues"""
        assert any("generic" in s for s in suggestions)
        assert any("circular" in s for s in suggestions)
        assert any("redundant" in s for s in suggestions)
        
    def test_suggestions_all_issues(self, quality_service):
        """Test suggestions for all possible issues"""
        metrics = create_all_issues_metrics()
        
        suggestions = quality_service.validator.generate_suggestions(
            metrics,
            ContentType.OPTIMIZATION
        )
        
        self._assert_suggestions_for_common_issues(suggestions)
        self._assert_suggestions_for_quality_issues(suggestions)
        
    def test_suggestions_optimization_specific(self, quality_service):
        """Test optimization-specific suggestions"""
        metrics = create_borderline_optimization_metrics()
        
        suggestions = quality_service.validator.generate_suggestions(
            metrics,
            ContentType.OPTIMIZATION
        )
        
        assert any("before/after" in s for s in suggestions)
        
    def test_suggestions_action_plan_specific(self, quality_service):
        """Test action plan-specific suggestions"""
        metrics = create_borderline_action_plan_metrics()
        
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
        
    def _assert_adjustment_structure(self, adjustments):
        """Assert adjustment structure is correct"""
        assert adjustments['temperature'] == 0.3
        assert len(adjustments['additional_instructions']) == 5
        
    def _assert_adjustment_content(self, adjustments):
        """Assert adjustment content addresses issues"""
        instructions_text = ' '.join(adjustments['additional_instructions'])
        assert "specific" in instructions_text
        assert "step-by-step" in instructions_text or "actionable" in instructions_text
        assert "numerical" in instructions_text
        
    def _assert_adjustment_advanced_content(self, adjustments):
        """Assert advanced adjustment content"""
        instructions_text = ' '.join(adjustments['additional_instructions'])
        assert "generic" in instructions_text
        assert "HOW" in instructions_text  # From circular reasoning
        
    def test_prompt_adjustments_all_issues(self, quality_service):
        """Test prompt adjustments for all issue types"""
        metrics = create_prompt_adjustment_metrics()
        
        adjustments = quality_service.validator.generate_prompt_adjustments(metrics)
        
        self._assert_adjustment_structure(adjustments)
        self._assert_adjustment_content(adjustments)
        self._assert_adjustment_advanced_content(adjustments)