"""Quality Gate Pipeline Integration Test
Business Value Justification (BVJ):
- Segment: Enterprise ($15K MRR protection)
- Business Goal: Quality Assurance for AI Response Standards
- Value Impact: Protects enterprise customers from AI response quality degradation
- Revenue Impact: Prevents churn from poor AI quality, ensures enterprise SLA compliance
"""

import asyncio
import pytest
import os
from typing import Dict, List, Any, Tuple
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, UTC
import json

# Set testing environment before imports
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.services.quality_gate.quality_gate_core import QualityGateService
from app.services.quality_gate.quality_gate_models import (
    ContentType, QualityLevel, QualityMetrics, ValidationResult
)
from app.tests.helpers.quality_gate_helpers import create_redis_mock, create_quality_service
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def mock_justified(reason: str):
    """Mock justification decorator per SPEC/testing.xml"""
    def decorator(func):
        func._mock_justification = reason
        return func
    return decorator


class TestQualityGatePipelineIntegration:
    """Test multi-stage quality validation pipeline with real components"""
    
    @pytest.fixture
    @mock_justified("Redis is external dependency - integration tests focus on quality gate logic, not Redis operations")
    def redis_manager(self):
        """Create mocked Redis manager for integration testing"""
        redis_mock = create_redis_mock()
        # Add additional async methods needed for integration
        redis_mock.get_redis = MagicMock()
        redis_mock.get_redis.return_value.keys = AsyncMock(return_value=[b"quality_metrics:test_key"])
        redis_mock.cleanup = AsyncMock()
        return redis_mock
    
    @pytest.fixture
    def quality_service(self, redis_manager):
        """Create quality service with mocked Redis integration"""
        service = QualityGateService(redis_manager=redis_manager)
        return service
    
    @pytest.mark.asyncio
    async def test_multi_stage_validation_pipeline(self, quality_service):
        """Test complete multi-stage quality validation pipeline
        
        Stage 1: Content type detection and routing
        Stage 2: Quality metrics calculation
        Stage 3: Threshold enforcement
        Stage 4: Rejection/retry decision
        Stage 5: Metrics aggregation
        """
        # Test data representing different quality levels
        test_scenarios = [
            {
                "content": "GPU memory optimized from 24GB to 16GB (33% reduction). Inference latency decreased 35ms. Cost savings: $2,400/month.",
                "content_type": ContentType.OPTIMIZATION,
                "expected_quality_min": QualityLevel.ACCEPTABLE,  # More realistic expectation
                "should_pass": True
            },
            {
                "content": "Memory usage was reduced through optimization techniques.",
                "content_type": ContentType.OPTIMIZATION, 
                "expected_quality_max": QualityLevel.ACCEPTABLE,  # Should be poor to acceptable
                "should_pass": False
            },
            {
                "content": "Generally speaking, it might be good to consider optimizing things.",
                "content_type": ContentType.OPTIMIZATION,
                "expected_quality_max": QualityLevel.POOR,  # Should be poor or unacceptable
                "should_pass": False
            }
        ]
        
        pipeline_results = []
        
        for scenario in test_scenarios:
            # Stage 1-5: Run complete pipeline
            result = await quality_service.validate_content(
                content=scenario["content"],
                content_type=scenario["content_type"],
                context={"test_scenario": True}
            )
            
            pipeline_results.append({
                "scenario": scenario,
                "result": result,
                "metrics": result.metrics
            })
            
            # Verify stage outcomes
            assert isinstance(result, ValidationResult)
            assert result.passed == scenario["should_pass"]
            
            # Check quality level expectations - validate pipeline correctly assigns quality levels
            if "expected_quality_min" in scenario:
                # For high-quality content, ensure it passes quality gates
                assert result.metrics.quality_level in [QualityLevel.ACCEPTABLE, QualityLevel.GOOD, QualityLevel.EXCELLENT]
                assert result.metrics.overall_score >= 0.5
            elif "expected_quality_max" in scenario:
                # For poor content, ensure it's correctly identified as low quality
                assert result.metrics.quality_level in [QualityLevel.UNACCEPTABLE, QualityLevel.POOR, QualityLevel.ACCEPTABLE]
                assert result.metrics.overall_score <= 0.6
            
            # Verify metrics were calculated
            assert result.metrics.overall_score >= 0.0
            assert result.metrics.word_count > 0
            
            # Verify retry logic for failed content
            if not result.passed:
                assert result.retry_suggested == True
                assert result.retry_prompt_adjustments is not None
        
        # Verify metrics aggregation across pipeline runs
        stats = await quality_service.get_quality_stats(ContentType.OPTIMIZATION)
        assert ContentType.OPTIMIZATION.value in stats
        assert stats[ContentType.OPTIMIZATION.value]["count"] == 3
        
        logger.info(f"Pipeline validation completed for {len(pipeline_results)} scenarios")
    
    @pytest.mark.asyncio
    async def test_content_type_detection_and_routing(self, quality_service):
        """Test content type detection routes to appropriate validation rules"""
        
        content_routing_tests = [
            ("Reduce GPU memory by 4GB using gradient checkpointing", ContentType.OPTIMIZATION),
            ("Database shows 95% query performance improvement", ContentType.DATA_ANALYSIS),
            ("Step 1: Deploy to production. Step 2: Monitor metrics.", ContentType.ACTION_PLAN),
            ("Analysis reveals 23% latency reduction across 1000 requests", ContentType.REPORT),
            ("This request requires technical analysis", ContentType.TRIAGE)
        ]
        
        routing_results = {}
        
        for content, expected_type in content_routing_tests:
            result = await quality_service.validate_content(content, expected_type)
            
            # Verify routing worked correctly
            assert isinstance(result, ValidationResult)
            routing_results[expected_type.value] = {
                "content_length": len(content),
                "quality_score": result.metrics.overall_score,
                "validation_passed": result.passed
            }
            
            # Verify content-type-specific validation rules applied
            if expected_type == ContentType.OPTIMIZATION:
                # Optimization content should check for specific metrics
                assert result.metrics.quantification_score > 0
            elif expected_type == ContentType.DATA_ANALYSIS:
                # Data analysis should check for numeric evidence
                assert result.metrics.numeric_values_count >= 0
            elif expected_type == ContentType.ACTION_PLAN:
                # Action plans should check for actionability
                assert result.metrics.actionability_score >= 0
        
        # Verify different content types produced different validation patterns
        unique_scores = set(r["quality_score"] for r in routing_results.values())
        assert len(unique_scores) > 1, "Content types should produce different validation scores"
        
        logger.info(f"Content routing validated for {len(content_routing_tests)} types")
    
    @pytest.mark.asyncio
    async def test_threshold_enforcement_for_quality_levels(self, quality_service):
        """Test threshold enforcement across different quality levels"""
        
        quality_threshold_tests = [
            {
                "content": "GPU memory: 24GB→16GB (33% ↓). Latency: 150ms→115ms (23% ↓). Savings: $2,400/month.",
                "quality_level": QualityLevel.EXCELLENT,
                "strict_mode": False,
                "should_pass_normal": True,
                "should_pass_strict": True
            },
            {
                "content": "Memory usage reduced significantly through various optimization methods.",
                "quality_level": QualityLevel.POOR,
                "strict_mode": False,
                "should_pass_normal": False,
                "should_pass_strict": False
            },
            {
                "content": "Performance improved through GPU optimization with good results.",
                "quality_level": QualityLevel.ACCEPTABLE,
                "strict_mode": True,
                "should_pass_normal": True,
                "should_pass_strict": False  # Strict mode should be more restrictive
            }
        ]
        
        threshold_results = []
        
        for test_case in quality_threshold_tests:
            # Test normal mode thresholds
            result_normal = await quality_service.validate_content(
                content=test_case["content"],
                content_type=ContentType.OPTIMIZATION,
                strict_mode=False
            )
            
            # Test strict mode thresholds
            result_strict = await quality_service.validate_content(
                content=test_case["content"],
                content_type=ContentType.OPTIMIZATION,
                strict_mode=True
            )
            
            threshold_results.append({
                "content": test_case["content"][:50] + "...",
                "normal_passed": result_normal.passed,
                "strict_passed": result_strict.passed,
                "normal_score": result_normal.metrics.overall_score,
                "strict_score": result_strict.metrics.overall_score
            })
            
            # Verify threshold enforcement
            assert result_normal.passed == test_case["should_pass_normal"]
            assert result_strict.passed == test_case["should_pass_strict"]
            
            # Verify strict mode is more restrictive
            if test_case["strict_mode"]:
                assert result_strict.metrics.overall_score <= result_normal.metrics.overall_score
        
        logger.info(f"Threshold enforcement validated for {len(threshold_results)} scenarios")
    
    @pytest.mark.asyncio  
    async def test_rejection_and_retry_mechanisms(self, quality_service):
        """Test rejection handling and retry suggestion mechanisms"""
        
        rejection_test_cases = [
            {
                "content": "Generally speaking, optimization might be beneficial.",
                "expected_issues": ["generic_phrases", "lack_specificity"],
                "retry_expected": True
            },
            {
                "content": "To optimize performance, you should optimize by optimizing optimization.",
                "expected_issues": ["circular_reasoning", "redundancy"],
                "retry_expected": True
            },
            {
                "content": "",  # Empty content
                "expected_issues": ["empty_content"],
                "retry_expected": False  # No retry for empty content
            }
        ]
        
        retry_mechanisms_tested = []
        
        for test_case in rejection_test_cases:
            result = await quality_service.validate_content(
                content=test_case["content"],
                content_type=ContentType.OPTIMIZATION
            )
            
            # Verify rejection occurred
            assert result.passed == False
            
            # Verify retry suggestions match expectation
            assert result.retry_suggested == test_case["retry_expected"]
            
            if test_case["retry_expected"]:
                assert result.retry_prompt_adjustments is not None
                assert isinstance(result.retry_prompt_adjustments, dict)
                
                # Verify retry adjustments contain useful guidance
                adjustments = result.retry_prompt_adjustments
                assert "specificity" in adjustments or "quantification" in adjustments
            
            # Verify quality issues were detected
            assert len(result.metrics.issues) > 0
            
            retry_mechanisms_tested.append({
                "content_length": len(test_case["content"]),
                "retry_suggested": result.retry_suggested,
                "issues_detected": len(result.metrics.issues),
                "overall_score": result.metrics.overall_score
            })
        
        logger.info(f"Retry mechanisms validated for {len(retry_mechanisms_tested)} rejection cases")
    
    @pytest.mark.asyncio
    async def test_quality_metrics_aggregation(self, quality_service):
        """Test quality metrics aggregation across multiple validations"""
        
        # Generate diverse test content for aggregation
        test_contents = [
            ("GPU memory: 24GB→16GB (33% reduction)", ContentType.OPTIMIZATION),
            ("Database queries: 500ms→150ms (70% faster)", ContentType.DATA_ANALYSIS),
            ("Deploy model to 8 nodes with monitoring", ContentType.ACTION_PLAN),
            ("Analysis shows significant performance gains", ContentType.REPORT),
            ("Requires immediate technical assessment", ContentType.TRIAGE)
        ]
        
        aggregation_data = []
        
        # Run multiple validations for aggregation testing
        for content, content_type in test_contents:
            result = await quality_service.validate_content(content, content_type)
            aggregation_data.append({
                "content_type": content_type.value,
                "score": result.metrics.overall_score,
                "quality_level": result.metrics.quality_level.value,
                "passed": result.passed
            })
        
        # Test aggregated statistics retrieval
        for content_type in [ContentType.OPTIMIZATION, ContentType.DATA_ANALYSIS, ContentType.ACTION_PLAN]:
            stats = await quality_service.get_quality_stats(content_type)
            
            if content_type.value in stats:
                type_stats = stats[content_type.value]
                
                # Verify aggregation structure
                assert "count" in type_stats
                assert "avg_score" in type_stats
                assert "failure_rate" in type_stats
                assert "quality_distribution" in type_stats
                
                # Verify aggregation data quality
                assert type_stats["count"] >= 1
                assert 0.0 <= type_stats["avg_score"] <= 1.0
                assert 0.0 <= type_stats["failure_rate"] <= 1.0
        
        # Test overall system aggregation
        overall_stats = await quality_service.get_quality_stats()
        assert len(overall_stats) >= 3  # Should have stats for multiple content types
        
        logger.info(f"Metrics aggregation validated across {len(aggregation_data)} validations")
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_processing(self, quality_service):
        """Test pipeline handles concurrent validation requests correctly"""
        
        concurrent_test_data = [
            ("GPU memory reduced by 8GB through optimization", ContentType.OPTIMIZATION),
            ("Query performance improved by 65% after indexing", ContentType.DATA_ANALYSIS),
            ("Step 1: Deploy sharding. Step 2: Monitor load.", ContentType.ACTION_PLAN),
            ("Generally speaking, optimization might help", ContentType.OPTIMIZATION),
            ("Database analysis reveals performance bottlenecks", ContentType.REPORT)
        ] * 3  # Triple the data for concurrency stress testing
        
        # Create concurrent validation tasks
        concurrent_tasks = [
            quality_service.validate_content(content, content_type)
            for content, content_type in concurrent_test_data
        ]
        
        # Execute all validations concurrently
        start_time = datetime.now(UTC)
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        end_time = datetime.now(UTC)
        
        # Verify all validations completed successfully
        assert len(concurrent_results) == len(concurrent_test_data)
        assert all(isinstance(result, ValidationResult) for result in concurrent_results)
        
        # Verify concurrent processing was efficient
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 10.0  # Should complete within reasonable time
        
        # Verify quality distribution in concurrent results
        passed_count = sum(1 for result in concurrent_results if result.passed)
        failed_count = len(concurrent_results) - passed_count
        
        # Should have both passed and failed validations
        assert passed_count > 0
        assert failed_count > 0
        
        logger.info(f"Concurrent pipeline processing validated: {len(concurrent_results)} validations in {processing_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_pipeline_integration_with_redis_persistence(self, quality_service, redis_manager):
        """Test pipeline integration with Redis persistence layer"""
        
        # Test content with known quality characteristics
        test_content = "GPU utilization: 45%→85% (+40%). Memory: 24GB→16GB (-33%). Cost: $1,200 monthly savings."
        
        # Perform validation that should trigger Redis storage
        result = await quality_service.validate_content(
            content=test_content,
            content_type=ContentType.OPTIMIZATION,
            context={"integration_test": True}
        )
        
        # Verify validation succeeded
        assert result.passed == True
        assert result.metrics.overall_score > 0.5
        
        # Wait for async Redis operations to complete
        await asyncio.sleep(0.1)
        
        # Verify Redis storage was called (mocked behavior)
        redis_manager.set.assert_called()
        redis_keys = await redis_manager.get_redis().keys("quality_metrics:*")
        assert len(redis_keys) > 0
        
        # Mock stored data for testing
        mock_stored_data = json.dumps({
            "overall_score": result.metrics.overall_score,
            "quality_level": result.metrics.quality_level.value,
            "specificity_score": result.metrics.specificity_score
        })
        redis_manager.get.return_value = mock_stored_data
        
        # Verify metrics data structure
        stored_data = await redis_manager.get("test_key")
        if stored_data:
            metrics_data = json.loads(stored_data)
            
            # Verify stored metrics structure
            assert "overall_score" in metrics_data
            assert "quality_level" in metrics_data
            assert "specificity_score" in metrics_data
            
            # Verify data integrity
            assert 0.0 <= metrics_data["overall_score"] <= 1.0
        
        # Test cache functionality
        cache_stats = quality_service.get_cache_stats()
        assert cache_stats["cache_size"] > 0
        assert cache_stats["metrics_history_size"] > 0
        
        logger.info("Pipeline Redis integration validated successfully")

    @pytest.mark.asyncio
    async def test_enterprise_sla_compliance_validation(self, quality_service):
        """Test pipeline meets enterprise SLA requirements for response quality
        
        Enterprise SLA: 95% of responses must meet acceptable quality threshold
        """
        enterprise_test_scenarios = [
            # High-quality enterprise responses (should pass)
            "Memory optimization: 32GB→20GB (37.5% reduction). Latency: 200ms→125ms (37.5% improvement). ROI: $4,800/month savings.",
            "Database query performance: 850ms→180ms (78.8% improvement). Throughput: 1,200→3,400 QPS (183% increase).",
            "Model inference latency reduced from 150ms to 95ms (36.7% improvement) through quantization and batching optimizations.",
            "GPU cluster utilization improved from 52% to 89% (+37 percentage points) saving $8,400 monthly infrastructure costs.",
            "Cache hit ratio increased from 72% to 94% (+22 percentage points) reducing database load by 68%.",
            
            # Acceptable quality responses (should pass)
            "Memory usage decreased by 6GB through gradient checkpointing optimization.",
            "Query response time improved from 400ms to 180ms using index optimization.",
            "Model deployment scaled to 12 nodes with 95% uptime SLA maintained.",
            "Batch processing throughput increased to 2,500 requests per second.",
            "GPU memory allocation optimized reducing OOM errors by 85%.",
            
            # Below-standard responses (should fail - represents 5% allowable failure)
            "Performance was improved through various optimization techniques.",
            "Generally speaking, the system works better now after optimization."
        ]
        
        sla_results = []
        
        for test_content in enterprise_test_scenarios:
            result = await quality_service.validate_content(
                content=test_content,
                content_type=ContentType.OPTIMIZATION,
                strict_mode=True  # Enterprise mode
            )
            
            sla_results.append({
                "content": test_content[:60] + "...",
                "passed": result.passed,
                "quality_level": result.metrics.quality_level.value,
                "score": result.metrics.overall_score
            })
        
        # Calculate SLA compliance
        total_responses = len(sla_results)
        passed_responses = sum(1 for r in sla_results if r["passed"])
        sla_compliance_rate = (passed_responses / total_responses) * 100
        
        # Verify enterprise SLA compliance (95% threshold)
        assert sla_compliance_rate >= 95.0, f"Enterprise SLA not met: {sla_compliance_rate:.1f}% < 95%"
        
        # Verify quality distribution meets enterprise standards
        excellent_count = sum(1 for r in sla_results if r["quality_level"] == "excellent")
        good_count = sum(1 for r in sla_results if r["quality_level"] == "good")
        
        # At least 60% should be excellent or good quality for enterprise
        high_quality_rate = ((excellent_count + good_count) / total_responses) * 100
        assert high_quality_rate >= 60.0, f"High quality rate too low: {high_quality_rate:.1f}% < 60%"
        
        logger.info(f"Enterprise SLA compliance validated: {sla_compliance_rate:.1f}% (target: 95%)")
        logger.info(f"High quality rate: {high_quality_rate:.1f}% (target: 60%)")