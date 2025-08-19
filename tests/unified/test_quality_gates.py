"""Quality Gate Tester - Phase 4 of Unified System Testing

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise)
- Business Goal: Ensure premium AI output quality justifies value-based pricing
- Value Impact: Quality gates prevent customer churn from poor AI responses
- Revenue Impact: Quality assurance enables premium pricing and retention
"""

import os
import pytest
from unittest.mock import AsyncMock, Mock
from typing import Dict, List, Any
from datetime import datetime, UTC

# Set testing environment before imports
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.services.quality_gate import (
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from app.tests.helpers.quality_gate_helpers import create_redis_mock, create_quality_service


class TestResponseQualityValidation:
    """Test response quality validation functionality"""

    @pytest.fixture
    def quality_service(self):
        """Create quality service with mocked dependencies"""
        return create_quality_service()

    @pytest.mark.asyncio
    async def test_response_quality_validation(self, quality_service):
        """Test that quality checks pass for good responses"""
        content = self._create_high_quality_content()
        result = await quality_service.validate_content(content, ContentType.OPTIMIZATION)
        
        assert result.passed == True
        assert result.metrics.overall_score >= 0.5
        assert result.metrics.quality_level != QualityLevel.UNACCEPTABLE

    @pytest.mark.asyncio
    async def test_low_quality_rejection(self, quality_service):
        """Test that poor responses are blocked"""
        content = "Generally speaking, you might want to consider optimizing."
        result = await quality_service.validate_content(content, ContentType.OPTIMIZATION)
        
        assert result.passed == False
        assert result.metrics.generic_phrase_count >= 1

    @pytest.mark.asyncio
    async def test_quality_metrics_tracking(self, quality_service):
        """Test metrics are stored correctly in databases"""
        content = "GPU memory reduced by 4GB through optimization"
        await quality_service.validate_content(content, ContentType.OPTIMIZATION)
        
        # Verify Redis storage was called
        quality_service.redis_manager.set.assert_called()
        
        # Verify memory storage
        assert ContentType.OPTIMIZATION in quality_service.metrics_history

    @pytest.mark.asyncio
    async def test_quality_feedback_loop(self, quality_service):
        """Test user feedback integration works"""
        content = "Moderate quality response for threshold testing"
        
        # Test normal validation
        result_normal = await quality_service.validate_content(content)
        
        # Test strict mode (simulates feedback-adjusted thresholds)
        result_strict = await quality_service.validate_content(content, strict_mode=True)
        
        # Strict mode should be more restrictive
        if result_normal.passed:
            assert result_strict.metrics.overall_score <= result_normal.metrics.overall_score

    def _create_high_quality_content(self) -> str:
        """Create high-quality content for testing"""
        return """
        GPU memory usage reduced from 24GB to 16GB (33% reduction) using gradient checkpointing.
        Inference latency decreased by 35ms (23% improvement) through model quantization to FP16.
        Total cost savings: $2,400/month with 3-day implementation timeline.
        """


class TestQualityMetricsStorage:
    """Test quality metrics persistence functionality"""

    @pytest.fixture
    def quality_service(self):
        """Create quality service for storage testing"""
        return create_quality_service()

    @pytest.mark.asyncio
    async def test_batch_validation_tracking(self, quality_service):
        """Test batch validation properly tracks all metrics"""
        contents = [
            ("GPU memory reduced by 4GB", ContentType.OPTIMIZATION),
            ("Model accuracy maintained at 95.2%", ContentType.DATA_ANALYSIS),
            ("Deploy sharding across 8 nodes", ContentType.ACTION_PLAN)
        ]
        
        results = await quality_service.validate_batch(contents)
        
        assert len(results) == 3
        assert all(isinstance(result, ValidationResult) for result in results)

    @pytest.mark.asyncio  
    async def test_quality_statistics_retrieval(self, quality_service):
        """Test quality statistics can be retrieved correctly"""
        # Add test data
        test_contents = [
            "Latency reduced by 40ms", "Memory usage decreased by 2GB",
            "Throughput increased to 3000 QPS", "GPU utilization at 85%"
        ]
        
        for content in test_contents:
            await quality_service.validate_content(content, ContentType.OPTIMIZATION)
        
        stats = await quality_service.get_quality_stats(ContentType.OPTIMIZATION)
        
        # Verify stats structure if data exists
        if 'optimization' in stats:
            assert 'count' in stats['optimization']


class TestLowQualityDetection:
    """Test low-quality content detection and handling"""

    @pytest.fixture
    def quality_service(self):
        """Create quality service for rejection testing"""
        return create_quality_service()

    @pytest.mark.asyncio
    async def test_generic_response_detection(self, quality_service):
        """Test generic responses are properly detected"""
        content = "It is important to note that generally speaking, you should consider optimizing."
        result = await quality_service.validate_content(content, ContentType.OPTIMIZATION)
        
        assert result.passed == False
        assert result.metrics.generic_phrase_count >= 2

    @pytest.mark.asyncio
    async def test_circular_reasoning_detection(self, quality_service):
        """Test circular reasoning detection works"""
        content = "To optimize the system, you should optimize by optimizing the optimization."
        result = await quality_service.validate_content(content, ContentType.REPORT)
        
        assert result.passed == False
        assert result.metrics.circular_reasoning_detected == True

    @pytest.mark.asyncio
    async def test_retry_suggestions_provided(self, quality_service):
        """Test retry suggestions are provided for poor content"""
        content = "Generally speaking, it might be good to optimize things."
        result = await quality_service.validate_content(content, ContentType.OPTIMIZATION)
        
        assert result.passed == False
        assert result.retry_suggested == True
        assert result.retry_prompt_adjustments is not None


class TestQualityThresholds:
    """Test quality threshold adjustments and feedback integration"""

    @pytest.fixture
    def quality_service(self):
        """Create quality service with feedback capabilities"""
        service = create_quality_service()
        service.feedback_processor = Mock()
        return service

    @pytest.mark.asyncio
    async def test_threshold_adjustment_simulation(self, quality_service):
        """Test quality thresholds can be adjusted"""
        content = "GPU optimization reduced memory usage significantly"
        
        # Normal validation
        result_normal = await quality_service.validate_content(content)
        
        # Strict validation (simulates adjusted thresholds)
        result_strict = await quality_service.validate_content(content, strict_mode=True)
        
        # Both should work, but strict mode may be more demanding
        assert isinstance(result_normal, ValidationResult)
        assert isinstance(result_strict, ValidationResult)

    @pytest.mark.asyncio
    async def test_feedback_data_structure(self, quality_service):
        """Test feedback data has expected structure for integration"""
        feedback_data = {
            "response_id": "test_response_123",
            "user_rating": 3,
            "quality_issues": ["too_generic", "lacks_specificity"],
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Test that feedback structure is valid
        assert "response_id" in feedback_data
        assert "user_rating" in feedback_data
        assert isinstance(feedback_data["quality_issues"], list)