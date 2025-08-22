"""Fixture helpers for Quality Gate Service tests"""

import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.quality_gate_service import (
    ContentType,
    QualityGateService,
    QualityLevel,
    QualityMetrics,
    ValidationResult,
)
from netra_backend.tests.helpers.quality_gate_helpers import (
    create_quality_service,
    create_redis_mock,
)

@pytest.fixture
def redis_mock():
    """Mock Redis manager fixture"""
    return create_redis_mock()

@pytest.fixture
def quality_service(redis_mock):
    """Create QualityGateService instance with mocked dependencies"""
    return create_quality_service(redis_mock)

def setup_novelty_mocks_fresh(quality_service, content):
    """Setup novelty mocks for fresh content"""
    quality_service.redis_manager.get_list = AsyncMock(return_value=[])
    quality_service.redis_manager.add_to_list = AsyncMock()

def setup_novelty_mocks_duplicate(quality_service, content):
    """Setup novelty mocks for duplicate content"""
    content_hash = hashlib.md5(content.encode()).hexdigest()
    quality_service.redis_manager.get_list = AsyncMock(return_value=[content_hash])

def setup_redis_error_mocks(quality_service):
    """Setup Redis mocks to simulate errors"""
    quality_service.redis_manager.set = AsyncMock(side_effect=Exception("Redis error"))

def setup_validation_error_mock(quality_service):
    """Setup mock to simulate validation errors"""
    return patch.object(quality_service.metrics_calculator, 'calculate_metrics', side_effect=Exception("Test error"))

def create_borderline_metrics():
    """Create borderline quality metrics for threshold testing"""
    return QualityMetrics(
        overall_score=0.6,
        specificity_score=0.6,
        actionability_score=0.6,
        quantification_score=0.6,
        relevance_score=0.6,
        completeness_score=0.6,
        clarity_score=0.6,
        redundancy_ratio=0.2,
        generic_phrase_count=2,
        circular_reasoning_detected=False,
        hallucination_risk=0.2
    )

def create_low_specificity_metrics():
    """Create metrics with low specificity for suggestion testing"""
    return QualityMetrics(
        specificity_score=0.3,
        actionability_score=0.8,
        quantification_score=0.2,
        generic_phrase_count=5,
        circular_reasoning_detected=True,
        redundancy_ratio=0.4
    )

def create_poor_metrics():
    """Create poor quality metrics for prompt adjustment testing"""
    return QualityMetrics(
        specificity_score=0.2,
        actionability_score=0.3,
        quantification_score=0.1,
        generic_phrase_count=7,
        circular_reasoning_detected=True
    )

def create_good_metrics():
    """Create good quality metrics for threshold testing"""
    return QualityMetrics(
        overall_score=0.8,
        specificity_score=0.9,
        actionability_score=0.9,
        quantification_score=0.8,
        relevance_score=0.8,
        completeness_score=0.9,
        clarity_score=0.8,
        redundancy_ratio=0.1,
        generic_phrase_count=1,
        circular_reasoning_detected=False,
        hallucination_risk=0.1
    )

def create_test_quality_metrics():
    """Create test metrics for storage testing"""
    return QualityMetrics(
        overall_score=0.8,
        quality_level=QualityLevel.GOOD,
        specificity_score=0.7,
        actionability_score=0.8,
        quantification_score=0.6
    )

def create_weighted_score_metrics():
    """Create metrics for weighted score calculation testing"""
    return QualityMetrics(
        specificity_score=0.8,
        actionability_score=0.9,
        quantification_score=0.7,
        relevance_score=0.6,
        completeness_score=0.8,
        novelty_score=0.9,
        clarity_score=0.7,
        generic_phrase_count=1,
        circular_reasoning_detected=False,
        hallucination_risk=0.1,
        redundancy_ratio=0.1
    )

def create_optimization_weights():
    """Create optimization content type weights"""
    return {
        'specificity': 0.25,
        'actionability': 0.25,
        'quantification': 0.20,
        'relevance': 0.15,
        'completeness': 0.10,
        'clarity': 0.05
    }

def add_multiple_test_metrics(quality_service, count=10):
    """Add multiple test metrics to service for statistics testing"""
    for i in range(count):
        metrics = QualityMetrics(
            overall_score=0.7 + (i * 0.02),  # Scores from 0.7 to 0.88
            quality_level=QualityLevel.GOOD if i > 5 else QualityLevel.ACCEPTABLE
        )
        yield metrics

def create_memory_overflow_metrics(count=1050):
    """Create metrics that exceed memory limits"""
    for i in range(count):
        yield QualityMetrics(overall_score=0.5 + (i * 0.0001))

def setup_pattern_test_texts():
    """Setup test texts for pattern testing"""
    return {
        'generic': "it is important to note that generally speaking",
        'vague': "you might want to consider optimizing",
        'circular': "optimize by optimizing the system"
    }

def setup_domain_content_for_recognition():
    """Setup domain content for term recognition testing"""
    return """
    The inference latency was reduced from 150ms to 95ms using quantization.
    Batch size increased from 16 to 32, improving GPU utilization to 87%.
    KV cache optimization saved 2.1GB of memory per request.
    Throughput increased to 4,200 QPS with p95 latency under 120ms.
    """

def setup_quality_level_test_cases():
    """Setup test cases for quality level classification"""
    return [
        (0.95, QualityLevel.EXCELLENT),
        (0.85, QualityLevel.GOOD),
        (0.65, QualityLevel.ACCEPTABLE),
        (0.45, QualityLevel.POOR),
        (0.25, QualityLevel.UNACCEPTABLE),
    ]

def setup_content_type_test_cases():
    """Setup test cases for different content types"""
    return list(ContentType)