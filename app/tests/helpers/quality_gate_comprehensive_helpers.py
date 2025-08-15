"""Comprehensive helper functions for Quality Gate Service tests"""

import re
import hashlib
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from collections import defaultdict

from app.services.quality_gate_service import (
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from app.redis_manager import RedisManager


# =============================================================================
# SETUP HELPERS (≤8 lines each)
# =============================================================================

def setup_large_optimization_content():
    """Create comprehensive optimization content for testing"""
    return """
    Performance Optimization Report:
    
    Current State: The system processes 500 requests per second with 200ms p95 latency.
    GPU utilization sits at 65% with 12GB memory usage.
    
    Proposed Changes:
    1. Enable batch processing with batch_size=32 (currently 8)
    2. Implement KV cache with 2GB allocation
    3. Use INT8 quantization for 50% memory reduction
    
    Implementation:
    ```bash
    pip install optimization-toolkit
    python optimize.py --batch-size 32 --quantize int8
    ```
    
    Expected Results:
    - Throughput: 500 RPS → 1500 RPS (200% increase)
    - Latency: 200ms → 120ms (40% reduction)
    - Memory: 12GB → 6GB (50% reduction)
    - Cost: $1000/month → $600/month
    
    Trade-offs: 0.5% accuracy loss acceptable for 3x performance gain.
    """


def setup_specificity_test_content():
    """Create content with all specificity indicators"""
    return """
    Configure batch_size=64, learning_rate=0.001, temperature=0.7, top_k=50.
    Using quantization and pruning for optimization.
    Achieve 250ms latency, 95% GPU utilization, 3200 QPS throughput.
    Set context_window=4096, max_tokens=2048, num_beams=4.
    """


def setup_actionability_test_content():
    """Create content with file paths and URLs"""
    return """
    1. Edit /etc/config/model.yaml
    2. Download weights from https://models.example.com/weights.bin
    3. Run the script at C:\\Users\\model\\optimize.py
    """


def setup_code_block_content():
    """Create content with code blocks"""
    return """
    Execute the following:
    ```python
    model.compile(optimizer='adam')
    model.fit(data, epochs=10)
    ```
    Then run: `python train.py --epochs 10`
    """


def setup_quantification_patterns_content():
    """Create content with all quantification patterns"""
    return """
    Results show 85% accuracy improvement.
    Latency reduced by 150ms (from 200ms to 50ms).
    Memory usage: 4.5GB, storage: 250MB.
    Processing 1500 tokens per second.
    Throughput increased to 2000 QPS.
    Performance improved by 3.5x.
    Cost decreased by 40% monthly.
    """


def setup_relevance_test_context():
    """Create context for relevance testing"""
    return {
        "user_request": "How to speed up neural network training with multiple graphics cards"
    }


def setup_completeness_report_content():
    """Create content for completeness testing"""
    return """
    Summary: System performance analyzed.
    Findings: Identified three bottlenecks.
    Recommendations: Implement caching and optimization.
    Conclusion: 40% improvement expected.
    Metrics: Latency 200ms, throughput 1000 QPS.
    """


def setup_completeness_general_content():
    """Create general content for completeness testing"""
    return """
    The system needs optimization. However, there are trade-offs to consider.
    This is because performance improvements may affect accuracy.
    We have analyzed the situation thoroughly.
    """


# =============================================================================
# MOCK SETUP HELPERS (≤8 lines each)
# =============================================================================

def setup_redis_mock_with_error():
    """Setup Redis mock to simulate errors"""
    mock_redis = AsyncMock(spec=RedisManager)
    mock_redis.get_list.side_effect = Exception("Redis connection failed")
    return mock_redis


def setup_redis_mock_with_large_cache():
    """Setup Redis mock with large cache list"""
    mock_redis = AsyncMock(spec=RedisManager)
    mock_redis.get_list.return_value = [f"hash{i}" for i in range(100)]
    return mock_redis


def setup_quality_service_with_redis_error():
    """Create quality service with Redis error simulation"""
    mock_redis = setup_redis_mock_with_error()
    return QualityGateService(redis_manager=mock_redis)


def setup_quality_service_with_large_cache():
    """Create quality service with large cache simulation"""
    mock_redis = setup_redis_mock_with_large_cache()
    return QualityGateService(redis_manager=mock_redis)


def setup_validation_error_patch(quality_service):
    """Setup patch for validation error testing"""
    return patch.object(
        quality_service,
        '_calculate_metrics',
        side_effect=ValueError("Calculation error")
    )


def setup_threshold_error_patch(quality_service):
    """Setup patch for threshold checking error"""
    return patch.object(
        quality_service,
        '_check_thresholds',
        side_effect=KeyError("Missing threshold")
    )


# =============================================================================
# METRICS CREATION HELPERS (≤8 lines each)
# =============================================================================

def create_all_penalties_metrics():
    """Create metrics with all penalties applied"""
    return QualityMetrics(
        specificity_score=0.8,
        actionability_score=0.8,
        generic_phrase_count=10,  # High penalty
        circular_reasoning_detected=True,  # -0.2
        hallucination_risk=0.8,  # -0.15
        redundancy_ratio=0.5  # -0.1
    )


def create_all_specific_checks_metrics():
    """Create metrics that fail all specific threshold checks"""
    return QualityMetrics(
        overall_score=0.4,
        specificity_score=0.4,
        actionability_score=0.4,
        quantification_score=0.4,
        relevance_score=0.4,
        completeness_score=0.4,
        clarity_score=0.4,
        redundancy_ratio=0.5,
        generic_phrase_count=10
    )


def create_all_issues_metrics():
    """Create metrics with all possible issues"""
    return QualityMetrics(
        specificity_score=0.3,
        actionability_score=0.3,
        quantification_score=0.3,
        generic_phrase_count=5,
        circular_reasoning_detected=True,
        redundancy_ratio=0.4,
        completeness_score=0.3
    )


def create_prompt_adjustment_metrics():
    """Create metrics for prompt adjustment testing"""
    return QualityMetrics(
        specificity_score=0.2,
        actionability_score=0.2,
        quantification_score=0.2,
        generic_phrase_count=8,
        circular_reasoning_detected=True
    )


def create_borderline_optimization_metrics():
    """Create borderline metrics for optimization suggestions"""
    return QualityMetrics(
        quantification_score=0.3,
        completeness_score=0.8
    )


def create_borderline_action_plan_metrics():
    """Create borderline metrics for action plan suggestions"""
    return QualityMetrics(
        completeness_score=0.3,
        actionability_score=0.8
    )


def create_high_hallucination_metrics():
    """Create metrics with high hallucination risk"""
    return QualityMetrics(
        overall_score=0.9,
        hallucination_risk=0.8  # Above 0.7 threshold
    )


# =============================================================================
# ASSERTION HELPERS (≤8 lines each)
# =============================================================================

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


# =============================================================================
# BATCH VALIDATION HELPERS (≤8 lines each)
# =============================================================================

def create_mixed_content_batch():
    """Create batch with mixed content types"""
    return [
        ("Error: Out of memory", ContentType.ERROR_MESSAGE),
        ("SELECT * FROM users", ContentType.DATA_ANALYSIS),
        ("Step 1: Install package", ContentType.ACTION_PLAN),
        ("Report summary here", ContentType.REPORT),
        ("Route to optimization team", ContentType.TRIAGE),
        ("General content", ContentType.GENERAL),
        ("Reduce latency by 50ms", ContentType.OPTIMIZATION)
    ]


def setup_slow_validation_mock():
    """Setup mock for slow validation testing"""
    async def slow_validate(*args, **kwargs):
        await asyncio.sleep(0.1)
        return ValidationResult(
            passed=True,
            metrics=QualityMetrics()
        )
    return slow_validate


# =============================================================================
# CLARITY CONTENT HELPERS (≤8 lines each)
# =============================================================================

def create_very_long_sentence():
    """Create sentence with 50+ words for clarity testing"""
    return " ".join(["word"] * 50) + "."


def create_excessive_acronyms_content():
    """Create content with many unexplained acronyms"""
    return "Use API, SDK, CLI, GUI, REST, SOAP, XML, JSON, YAML, CSV for integration."


def create_nested_parentheses_content():
    """Create content with nested parentheses"""
    return "The system (which includes components (like cache (Redis) and database)) is complex."


# =============================================================================
# REDUNDANCY CONTENT HELPERS (≤8 lines each)
# =============================================================================

def create_high_overlap_content():
    """Create content with high word overlap for redundancy testing"""
    return """
    The optimization improves system performance significantly today.
    System performance optimization improves significantly with results today.
    Performance optimization system significantly improves results today.
    """


# =============================================================================
# HALLUCINATION CONTENT HELPERS (≤8 lines each)
# =============================================================================

def create_multiple_impossible_claims_content():
    """Create content with multiple impossible claims"""
    return """
    Achieve 100% improvement with zero latency.
    Perfect accuracy guaranteed with infinite throughput.
    No cost solution with unlimited scaling.
    """


def create_claims_with_evidence_content():
    """Create content with evidence-based claims"""
    return "Studies show improvement according to Smith et al. (2023) [1]."


def create_context_with_data_source():
    """Create context with data source for hallucination testing"""
    return {"data_source": "production_metrics"}


# =============================================================================
# QUALITY STATS HELPERS (≤8 lines each)
# =============================================================================

def add_quality_distribution_metrics(quality_service):
    """Add metrics with different quality levels for distribution testing"""
    levels_scores = [
        (QualityLevel.EXCELLENT, 0.95),
        (QualityLevel.GOOD, 0.75),
        (QualityLevel.ACCEPTABLE, 0.55),
        (QualityLevel.POOR, 0.35),
        (QualityLevel.UNACCEPTABLE, 0.25)
    ]
    for level, score in levels_scores:
        quality_service.metrics_history[ContentType.REPORT].append({
            'timestamp': '2024-01-01',
            'overall_score': score,
            'quality_level': level.value
        })


def add_recent_metrics_overflow(quality_service, count=150):
    """Add metrics that exceed recent entry limits"""
    for i in range(count):
        quality_service.metrics_history[ContentType.TRIAGE].append({
            'timestamp': f'2024-01-{i+1:03d}',
            'overall_score': 0.5 + (i * 0.001),
            'quality_level': 'acceptable'
        })


def add_metrics_to_memory_limit(quality_service, count=1000):
    """Add metrics up to memory limit"""
    for i in range(count):
        quality_service.metrics_history[ContentType.OPTIMIZATION].append({
            'timestamp': f'2024-01-01T{i:04d}',
            'overall_score': 0.5
        })


# =============================================================================
# ERROR HANDLING HELPERS (≤8 lines each)
# =============================================================================

def create_metrics_storage_error(quality_service):
    """Create error condition for metrics storage"""
    quality_service.metrics_history = None


def setup_poor_content_for_improvement():
    """Create poor content for improvement cycle testing"""
    return """
    You should probably consider maybe optimizing things.
    It's important to note that optimization is important.
    To improve performance, improve the performance.
    Generally speaking, things could be better.
    """


def setup_improved_content_after_adjustments():
    """Create improved content based on prompt adjustments"""
    return """
    Optimization Plan:
    1. Set batch_size=32 for 40% throughput increase
    2. Enable GPU caching to reduce memory transfers by 2GB
    3. Implement quantization for 50% model size reduction
    
    Expected results: 200ms latency reduction, $500/month cost savings
    """


# =============================================================================
# COMPREHENSIVE INTEGRATION CONTENT (≤8 lines each)
# =============================================================================

def setup_complete_optimization_workflow_content():
    """Create complete optimization workflow content (part 1)"""
    return """
    System Optimization Plan
    
    Current Performance Baseline:
    - Request latency: 450ms p95, 200ms p50
    - Throughput: 1,200 requests per second
    - GPU utilization: 45% average, 78% peak
    - Memory usage: 14GB / 16GB available
    - Monthly cost: $3,500 for compute resources
    
    Identified Bottlenecks:
    1. Inefficient batch processing (batch_size=4)
    2. No caching for repeated queries
    3. Synchronous I/O operations blocking GPU
    """


def setup_optimization_strategy_content():
    """Create optimization strategy content (part 2)"""
    return """
    Optimization Strategy:
    
    Phase 1 - Quick Wins (Week 1):
    - Increase batch_size to 32
    - Enable KV cache with 2GB allocation
    - Implement async I/O handlers
    
    Implementation Steps:
    ```bash
    # Update configuration
    sed -i 's/batch_size=4/batch_size=32/' config.yaml
    
    # Install caching layer
    pip install redis-cache==2.1.0
    python setup_cache.py --size 2GB --ttl 3600
    
    # Deploy async handlers
    git checkout feature/async-io
    python deploy.py --service inference --async
    ```
    """


def setup_optimization_outcomes_content():
    """Create optimization outcomes content (part 3)"""
    return """
    Phase 2 - Advanced Optimizations (Week 2):
    - Implement INT8 quantization
    - Enable tensor parallelism across 4 GPUs
    - Use Flash Attention 2 for transformer layers
    
    Expected Outcomes:
    - Latency: 450ms → 180ms p95 (60% reduction)
    - Throughput: 1,200 → 3,600 RPS (3x increase)
    - GPU utilization: 45% → 85% (better resource usage)
    - Memory: 14GB → 8GB (43% reduction)
    - Cost: $3,500 → $2,100/month (40% savings)
    
    Success Metrics:
    - All API endpoints respond < 200ms p95
    - Zero downtime during migration
    - Accuracy degradation < 0.5%
    
    Rollback Plan:
    - Keep previous deployment in blue-green setup
    - Monitor error rates, rollback if > 1%
    - Maintain config backups in git
    
    Trade-offs:
    - 0.3% accuracy loss from quantization
    - Increased complexity in deployment
    - Initial 2-day migration effort required
    """


def setup_optimization_workflow_context():
    """Create context for optimization workflow testing"""
    return {
        "user_request": "Create a detailed plan to optimize our inference system",
        "data_source": "production_metrics",
        "constraints": "Must maintain 99.9% uptime"
    }


# =============================================================================
# VALIDATION AND ASSERTION COMBINE HELPERS (≤8 lines each)
# =============================================================================

def combine_optimization_content():
    """Combine all optimization content parts"""
    part1 = setup_complete_optimization_workflow_content()
    part2 = setup_optimization_strategy_content()
    part3 = setup_optimization_outcomes_content()
    return f"{part1}\n\n{part2}\n\n{part3}"


def assert_improvement_cycle_comparison(result1, result2):
    """Assert improvement cycle shows better results"""
    assert result2.passed == True
    assert result2.metrics.overall_score > result1.metrics.overall_score
    assert result2.metrics.generic_phrase_count < result1.metrics.generic_phrase_count