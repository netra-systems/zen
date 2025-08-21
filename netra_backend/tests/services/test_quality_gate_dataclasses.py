"""Tests for Quality Gate Service dataclasses and basic functionality"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.quality_gate_service import (

# Add project root to path
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from netra_backend.tests.helpers.quality_gate_fixtures import (
    quality_service,
    redis_mock
)
from netra_backend.tests.helpers.quality_gate_helpers import (
    assert_validation_passed,
    create_test_metrics
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
        
    def test_quality_metrics_defaults_extended(self):
        """Test extended QualityMetrics default values"""
        metrics = QualityMetrics()
        
        assert metrics.completeness_score == 0.0
        assert metrics.novelty_score == 0.0
        assert metrics.clarity_score == 0.0
        assert metrics.generic_phrase_count == 0
        
    def test_quality_metrics_defaults_boolean_fields(self):
        """Test QualityMetrics boolean default values"""
        metrics = QualityMetrics()
        
        assert metrics.circular_reasoning_detected == False
        assert metrics.hallucination_risk == 0.0
        assert metrics.redundancy_ratio == 0.0
        assert metrics.word_count == 0
        
    def test_quality_metrics_defaults_final_fields(self):
        """Test QualityMetrics final default fields"""
        metrics = QualityMetrics()
        
        assert metrics.sentence_count == 0
        assert metrics.numeric_values_count == 0
        assert metrics.specific_terms_count == 0
        assert metrics.overall_score == 0.0
        
    def test_quality_metrics_defaults_lists_and_level(self):
        """Test QualityMetrics list and level defaults"""
        metrics = QualityMetrics()
        
        assert metrics.quality_level == QualityLevel.UNACCEPTABLE
        assert metrics.issues == []
        assert metrics.suggestions == []
        
    def test_quality_metrics_custom_values_setup(self):
        """Test QualityMetrics with custom values setup"""
        issues = ["Issue 1", "Issue 2"]
        suggestions = ["Suggestion 1"]
        
        metrics = QualityMetrics(
            specificity_score=0.8,
            actionability_score=0.9,
            generic_phrase_count=3,
            circular_reasoning_detected=True
        )
        
        assert metrics.specificity_score == 0.8
        assert metrics.actionability_score == 0.9
        
    def test_quality_metrics_custom_values_validation(self):
        """Test QualityMetrics custom values validation"""
        issues = ["Issue 1", "Issue 2"]
        suggestions = ["Suggestion 1"]
        
        metrics = QualityMetrics(
            generic_phrase_count=3,
            circular_reasoning_detected=True,
            issues=issues,
            suggestions=suggestions
        )
        
        assert metrics.generic_phrase_count == 3
        assert metrics.circular_reasoning_detected == True
        assert metrics.issues == issues
        assert metrics.suggestions == suggestions


class TestValidationResultDataclass:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_initialization_basic(self):
        """Test ValidationResult basic initialization"""
        metrics = QualityMetrics(overall_score=0.75)
        
        result = ValidationResult(
            passed=True,
            metrics=metrics,
            retry_suggested=False
        )
        
        assert result.passed == True
        assert result.metrics == metrics
        assert result.retry_suggested == False
        
    def test_validation_result_initialization_extended(self):
        """Test ValidationResult extended initialization"""
        metrics = QualityMetrics(overall_score=0.75)
        
        result = ValidationResult(
            passed=True,
            metrics=metrics,
            retry_prompt_adjustments={"temperature": 0.5},
            fallback_response="Fallback content"
        )
        
        assert result.retry_prompt_adjustments == {"temperature": 0.5}
        assert result.fallback_response == "Fallback content"
        
    def test_validation_result_defaults_setup(self):
        """Test ValidationResult default values setup"""
        metrics = QualityMetrics()
        result = ValidationResult(passed=False, metrics=metrics)
        
        assert result.passed == False
        assert result.metrics == metrics
        
    def test_validation_result_defaults_validation(self):
        """Test ValidationResult default values validation"""
        metrics = QualityMetrics()
        result = ValidationResult(passed=False, metrics=metrics)
        
        assert result.retry_suggested == False
        assert result.retry_prompt_adjustments == None
        assert result.fallback_response == None


class TestCompleteMetricsCalculation:
    """Test the complete metrics calculation workflow"""
    
    @pytest.fixture
    def quality_service(self):
        """Create QualityGateService instance"""
        return QualityGateService(redis_manager=None)
    
    def _create_optimization_content(self):
        """Create optimization content for testing"""
        return """
        Performance Optimization Report:
        
        Current State: The system processes 500 requests per second with 200ms p95 latency.
        GPU utilization sits at 65% with 12GB memory usage.
        
        Proposed Changes:
        1. Enable batch processing with batch_size=32 (currently 8)
        2. Implement KV cache with 2GB allocation
        3. Use INT8 quantization for 50% memory reduction
        """
        
    def _create_optimization_context(self):
        """Create context for optimization testing"""
        return {
            "user_request": "optimize system performance",
            "data_source": "production metrics"
        }
    async def test_calculate_metrics_complete_workflow_setup(self, quality_service):
        """Test complete metrics calculation setup"""
        content = self._create_optimization_content()
        context = self._create_optimization_context()
        
        metrics = await quality_service.metrics_calculator.calculate_metrics(
            content,
            ContentType.OPTIMIZATION,
            context
        )
        
        assert metrics.word_count >= 50
        assert metrics.sentence_count > 3
    async def test_calculate_metrics_complete_workflow_basic(self, quality_service):
        """Test complete metrics calculation basic checks"""
        content = self._create_optimization_content()
        context = self._create_optimization_context()
        
        metrics = await quality_service.metrics_calculator.calculate_metrics(
            content,
            ContentType.OPTIMIZATION,
            context
        )
        
        assert metrics.generic_phrase_count == 0
        assert metrics.circular_reasoning_detected == False
        assert metrics.specificity_score > 0.5
        assert metrics.actionability_score > 0.4
    async def test_calculate_metrics_complete_workflow_scores(self, quality_service):
        """Test complete metrics calculation score validation"""
        content = self._create_optimization_content()
        context = self._create_optimization_context()
        
        metrics = await quality_service.metrics_calculator.calculate_metrics(
            content,
            ContentType.OPTIMIZATION,
            context
        )
        
        assert metrics.quantification_score > 0.6
        assert metrics.relevance_score > 0.3
        assert metrics.completeness_score >= 0.2
        assert metrics.novelty_score > 0
    async def test_calculate_metrics_complete_workflow_final(self, quality_service):
        """Test complete metrics calculation final validation"""
        content = self._create_optimization_content()
        context = self._create_optimization_context()
        
        metrics = await quality_service.metrics_calculator.calculate_metrics(
            content,
            ContentType.OPTIMIZATION,
            context
        )
        
        assert metrics.clarity_score > 0.5
        assert metrics.redundancy_ratio < 0.3
        assert metrics.hallucination_risk < 0.3
        assert metrics.overall_score >= 0.0
        assert isinstance(metrics.quality_level, QualityLevel)
        assert len(metrics.suggestions) >= 0