"""
Unit tests for Quality Gate Service - AI Slop Prevention
Tests comprehensive quality validation for AI-generated outputs
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import hashlib

from app.services.quality_gate_service import (
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from app.redis_manager import RedisManager


class TestQualityGateService:
    """Test suite for QualityGateService"""
    
    @pytest.fixture
    def redis_mock(self):
        """Mock Redis manager"""
        redis_mock = Mock(spec=RedisManager)
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock(return_value=True)
        redis_mock.expire = AsyncMock(return_value=True)
        return redis_mock
    
    @pytest.fixture
    def quality_service(self, redis_mock):
        """Create QualityGateService instance with mocked dependencies"""
        return QualityGateService(redis_manager=redis_mock)
    
    @pytest.mark.asyncio
    async def test_validate_high_quality_optimization_content(self, quality_service):
        """Test validation of high-quality optimization content"""
        # High-quality content with specifics
        content = """
        Based on the analysis, we can optimize GPU utilization by:
        1. Increasing batch size from 16 to 32, reducing latency by 23ms (15% improvement)
        2. Implementing KV cache optimization, saving 2.3GB memory per request
        3. Enabling tensor parallelism across 4 GPUs, achieving 3.8x throughput increase
        4. Adjusting temperature from 1.0 to 0.7 for more deterministic outputs
        
        These changes will reduce cost per token from $0.002 to $0.0014 (30% reduction)
        and improve p95 latency from 150ms to 115ms.
        """
        
        result = await quality_service.validate_content(
            content,
            content_type=ContentType.OPTIMIZATION
        )
        
        assert result.passed is True
        assert result.metrics.overall_score >= 0.7
        assert result.metrics.specificity_score >= 0.8
        assert result.metrics.actionability_score >= 0.8
        assert result.metrics.quantification_score >= 0.7
        assert result.metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        assert len(result.metrics.issues) == 0
    
    @pytest.mark.asyncio
    async def test_validate_low_quality_generic_content(self, quality_service):
        """Test detection of low-quality generic content"""
        # Generic, vague content (AI slop)
        content = """
        It is important to note that generally speaking, you might want to consider
        looking into optimization. Throughout history, we have seen that in general,
        things can be improved. You could try to enhance performance by making it better.
        It goes without saying that at the end of the day, optimization is about
        optimizing things. Needless to say, you should think about improving the system.
        """
        
        result = await quality_service.validate_content(
            content,
            content_type=ContentType.OPTIMIZATION
        )
        
        assert result.passed is False
        assert result.metrics.overall_score < 0.5
        assert result.metrics.generic_phrase_count > 5
        assert result.metrics.specificity_score < 0.3
        assert result.metrics.actionability_score < 0.3
        assert result.metrics.quality_level in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]
        assert len(result.metrics.issues) > 0
        assert any("generic" in issue.lower() for issue in result.metrics.issues)
    
    @pytest.mark.asyncio
    async def test_detect_circular_reasoning(self, quality_service):
        """Test detection of circular reasoning patterns"""
        content = """
        To improve performance, you should improve the performance metrics.
        Optimize the system by optimizing its components.
        For better results, use better algorithms to get better outcomes.
        """
        
        result = await quality_service.validate_content(
            content,
            content_type=ContentType.ACTION_PLAN
        )
        
        assert result.passed is False
        assert result.metrics.circular_reasoning_detected is True
        assert "circular reasoning" in str(result.metrics.issues).lower()
    
    @pytest.mark.asyncio
    async def test_validate_data_analysis_with_metrics(self, quality_service):
        """Test validation of data analysis content with quantitative metrics"""
        content = """
        Analysis of the past 7 days shows:
        - Average GPU utilization: 78.3% (peak: 95%, trough: 42%)
        - Memory consumption: 14.2GB average, 18.7GB p95
        - Request latency: p50=45ms, p95=120ms, p99=280ms
        - Total requests processed: 1.2M with 99.94% success rate
        - Cost breakdown: $1,234 compute, $567 storage, $89 network
        
        Key finding: 65% of latency spikes correlate with batch sizes > 48
        """
        
        result = await quality_service.validate_content(
            content,
            content_type=ContentType.DATA_ANALYSIS
        )
        
        assert result.passed is True
        assert result.metrics.quantification_score >= 0.8
        assert result.metrics.numeric_values_count > 10
        assert result.metrics.specificity_score >= 0.7
    
    @pytest.mark.asyncio
    async def test_validate_action_plan_completeness(self, quality_service):
        """Test validation of action plan for completeness and actionability"""
        content = """
        Action Plan for GPU Optimization:
        
        Week 1:
        - [ ] Deploy KV cache optimization to staging (2 days)
        - [ ] Run A/B test with 10% traffic (3 days)
        - [ ] Monitor metrics: latency, memory usage, error rates
        
        Week 2:
        - [ ] Analyze results and adjust parameters
        - [ ] Gradual rollout: 25% -> 50% -> 100%
        - [ ] Set up alerts for p95 > 150ms
        
        Success Criteria:
        - Reduce p95 latency by at least 20%
        - Maintain 99.9% uptime
        - Cost per request < $0.0015
        """
        
        result = await quality_service.validate_content(
            content,
            content_type=ContentType.ACTION_PLAN
        )
        
        assert result.passed is True
        assert result.metrics.actionability_score >= 0.8
        assert result.metrics.completeness_score >= 0.7
        assert result.metrics.clarity_score >= 0.7
    
    @pytest.mark.asyncio
    async def test_validate_with_strict_mode(self, quality_service):
        """Test strict mode validation with higher thresholds"""
        # Borderline quality content
        content = """
        The system could benefit from some optimization.
        Consider increasing batch size and reducing latency.
        Memory usage is high and should be addressed.
        """
        
        # Should pass in normal mode
        result_normal = await quality_service.validate_content(
            content,
            content_type=ContentType.GENERAL,
            strict_mode=False
        )
        
        # Should fail in strict mode
        result_strict = await quality_service.validate_content(
            content,
            content_type=ContentType.GENERAL,
            strict_mode=True
        )
        
        assert result_normal.passed is True
        assert result_strict.passed is False
        assert result_strict.retry_suggested is True
    
    @pytest.mark.asyncio
    async def test_validate_error_message_clarity(self, quality_service):
        """Test validation of error messages for clarity and actionability"""
        # Good error message
        good_error = """
        Error: GPU memory exceeded (18.5GB used, 16GB available)
        
        Cause: Batch size 64 with model size 7B exceeds available VRAM
        
        Solutions:
        1. Reduce batch size to 32 or less
        2. Enable gradient checkpointing to save ~30% memory
        3. Use mixed precision training (fp16) to halve memory usage
        
        Run with --batch-size 32 --gradient-checkpoint to retry
        """
        
        result = await quality_service.validate_content(
            good_error,
            content_type=ContentType.ERROR_MESSAGE
        )
        
        assert result.passed is True
        assert result.metrics.clarity_score >= 0.8
        assert result.metrics.actionability_score >= 0.7
    
    @pytest.mark.asyncio
    async def test_validate_report_redundancy(self, quality_service):
        """Test detection of redundant content in reports"""
        # Report with high redundancy
        redundant_report = """
        Executive Summary:
        The system needs optimization to improve performance.
        
        Introduction:
        This report discusses how the system needs optimization to improve performance.
        
        Analysis:
        Our analysis shows the system needs optimization to improve performance.
        
        Findings:
        We found that the system needs optimization to improve performance.
        
        Conclusion:
        In conclusion, the system needs optimization to improve performance.
        """
        
        result = await quality_service.validate_content(
            redundant_report,
            content_type=ContentType.REPORT
        )
        
        assert result.passed is False
        assert result.metrics.redundancy_ratio > 0.5
        assert "redundant" in str(result.metrics.issues).lower()
    
    @pytest.mark.asyncio
    async def test_domain_specific_term_recognition(self, quality_service):
        """Test recognition of domain-specific terms that indicate quality"""
        content = """
        Implemented flash attention with 8-bit quantization, reducing memory footprint
        by 42% while maintaining 98.5% accuracy. The KV cache optimization leverages
        tensor parallelism across 4 A100 GPUs, achieving 3,200 tokens/second throughput
        with p99 latency of 89ms. Cost per million tokens dropped from $2.10 to $1.35.
        """
        
        result = await quality_service.validate_content(
            content,
            content_type=ContentType.OPTIMIZATION
        )
        
        assert result.passed is True
        assert result.metrics.specific_terms_count >= 10
        assert result.metrics.specificity_score >= 0.8
        assert result.metrics.quality_level == QualityLevel.EXCELLENT
    
    @pytest.mark.asyncio
    async def test_caching_mechanism(self, quality_service):
        """Test that validation results are cached properly"""
        content = "Test content for caching validation"
        
        # First call should calculate metrics
        result1 = await quality_service.validate_content(content)
        
        # Second call should use cache
        result2 = await quality_service.validate_content(content)
        
        # Results should be identical
        assert result1.passed == result2.passed
        assert result1.metrics.overall_score == result2.metrics.overall_score
        
        # Verify cache was used (check that the content is in cache)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        cache_key = f"quality:{ContentType.GENERAL.value}:{content_hash}"
        assert cache_key in quality_service.validation_cache
    
    @pytest.mark.asyncio
    async def test_retry_suggestions_for_failed_validation(self, quality_service):
        """Test that retry suggestions are provided for failed validations"""
        vague_content = "You should probably optimize things to make them better."
        
        result = await quality_service.validate_content(
            vague_content,
            content_type=ContentType.OPTIMIZATION
        )
        
        assert result.passed is False
        assert result.retry_suggested is True
        assert result.retry_prompt_adjustments is not None
        assert "specific" in str(result.metrics.suggestions).lower()
        assert len(result.metrics.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_hallucination_risk_detection(self, quality_service):
        """Test detection of potential hallucination risks"""
        # Content with potential hallucination indicators
        risky_content = """
        According to the non-existent study by Dr. Fakename at Imaginary University,
        the XYZ-9000 algorithm (which I just invented) can achieve 110% accuracy
        and negative latency. This revolutionary approach violates no laws of physics
        and has been proven in -1 production environments.
        """
        
        result = await quality_service.validate_content(
            risky_content,
            content_type=ContentType.DATA_ANALYSIS
        )
        
        assert result.passed is False
        assert result.metrics.hallucination_risk > 0.5
        assert any("hallucination" in issue.lower() or "unrealistic" in issue.lower() 
                  for issue in result.metrics.issues)
    
    @pytest.mark.asyncio
    async def test_triage_content_validation(self, quality_service):
        """Test validation of triage content with appropriate thresholds"""
        triage_content = """
        Request Category: Performance Optimization
        Priority: High
        
        Analysis: User experiencing high latency (>500ms) on inference requests.
        Root cause appears to be inefficient batch processing with current configuration.
        
        Recommended next steps:
        1. Analyze current batch size and GPU utilization metrics
        2. Review model architecture for optimization opportunities
        3. Investigate caching strategies for repeated requests
        """
        
        result = await quality_service.validate_content(
            triage_content,
            content_type=ContentType.TRIAGE
        )
        
        assert result.passed is True
        assert result.metrics.relevance_score >= 0.7
        assert result.metrics.specificity_score >= 0.6
    
    @pytest.mark.asyncio
    async def test_context_aware_validation(self, quality_service):
        """Test validation with additional context provided"""
        content = "Increase batch size to 32"
        
        # Without context - might fail for being too brief
        result_no_context = await quality_service.validate_content(
            content,
            content_type=ContentType.OPTIMIZATION
        )
        
        # With context - should pass
        context = {
            "previous_discussion": "User asked for quick optimization tips",
            "current_batch_size": 16,
            "constraints": "Limited to configuration changes only"
        }
        
        result_with_context = await quality_service.validate_content(
            content,
            content_type=ContentType.OPTIMIZATION,
            context=context
        )
        
        # With context, brief specific answers should be acceptable
        assert result_with_context.metrics.relevance_score >= result_no_context.metrics.relevance_score
    
    @pytest.mark.asyncio
    async def test_quality_level_classification(self, quality_service):
        """Test proper classification of quality levels"""
        test_cases = [
            (0.95, QualityLevel.EXCELLENT),
            (0.85, QualityLevel.GOOD),
            (0.65, QualityLevel.ACCEPTABLE),
            (0.45, QualityLevel.POOR),
            (0.25, QualityLevel.UNACCEPTABLE),
        ]
        
        for score, expected_level in test_cases:
            # Create metrics with specific overall score
            metrics = QualityMetrics(overall_score=score)
            metrics.quality_level = quality_service._classify_quality_level(score)
            
            assert metrics.quality_level == expected_level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])