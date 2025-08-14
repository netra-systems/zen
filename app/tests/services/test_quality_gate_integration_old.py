"""Tests for Quality Gate Service integration scenarios and error handling"""

import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.quality_gate_service import (
    QualityGateService,
    QualityMetrics,
    QualityLevel,
    ValidationResult,
    ContentType
)
from app.redis_manager import RedisManager
from app.tests.helpers.shared_test_types import TestErrorHandling as SharedTestErrorHandling, TestIntegrationScenarios as SharedTestIntegrationScenarios
from app.tests.helpers.quality_gate_comprehensive_helpers import (
    combine_optimization_content,
    setup_optimization_workflow_context,
    setup_poor_content_for_improvement,
    setup_improved_content_after_adjustments,
    assert_optimization_workflow_passed,
    assert_optimization_workflow_metrics,
    assert_optimization_workflow_quality_indicators,
    assert_optimization_workflow_no_retry,
    assert_poor_content_failure,
    assert_improvement_cycle_comparison,
    create_mixed_content_batch,
    setup_slow_validation_mock,
    add_quality_distribution_metrics,
    add_recent_metrics_overflow,
    add_metrics_to_memory_limit,
    create_metrics_storage_error,
    setup_validation_error_patch,
    setup_threshold_error_patch
)


class TestMetricsStorage:
    """Test metrics storage and retrieval"""
    
    def _create_redis_mock(self):
        """Create Redis mock for storage testing"""
        return AsyncMock(spec=RedisManager)
        
    def _create_quality_service_with_mock(self, mock_redis):
        """Create quality service with Redis mock"""
        return QualityGateService(redis_manager=mock_redis)
        
    @pytest.mark.asyncio
    async def test_store_metrics_memory_limit(self):
        """Test that metrics history is limited properly"""
        mock_redis = self._create_redis_mock()
        quality_service = self._create_quality_service_with_mock(mock_redis)
        
        add_metrics_to_memory_limit(quality_service)
        
        new_metrics = QualityMetrics(overall_score=0.9)
        await quality_service._store_metrics(new_metrics, ContentType.OPTIMIZATION)
        
        assert len(quality_service.metrics_history[ContentType.OPTIMIZATION]) == 1000
        assert quality_service.metrics_history[ContentType.OPTIMIZATION][-1]['overall_score'] == 0.9
        
    @pytest.mark.asyncio
    async def test_store_metrics_redis_with_ttl(self):
        """Test Redis storage with TTL"""
        mock_redis = self._create_redis_mock()
        quality_service = self._create_quality_service_with_mock(mock_redis)
        
        metrics = QualityMetrics(overall_score=0.75)
        
        await quality_service._store_metrics(metrics, ContentType.DATA_ANALYSIS)
        
        mock_redis.store_metrics.assert_called_once()
        call_args = mock_redis.store_metrics.call_args
        
        assert "quality_metrics:data_analysis" in call_args[0]
        assert call_args[1][1] == metrics.__dict__
        assert call_args[1][2] == 86400  # 24 hour TTL


class TestQualityStats:
    """Test quality statistics calculation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_get_quality_stats_empty(self, quality_service):
        """Test stats when no metrics exist"""
        stats = await quality_service.get_quality_stats()
        assert stats == {}
        
    def _assert_distribution_stats(self, stats):
        """Assert distribution statistics are correct"""
        report_stats = stats[ContentType.REPORT.value]
        assert report_stats['count'] == 5
        assert report_stats['min_score'] == 0.25
        assert report_stats['max_score'] == 0.95
        
    def _assert_quality_levels(self, stats):
        """Assert quality level distribution"""
        dist = stats[ContentType.REPORT.value]['quality_distribution']
        assert dist[QualityLevel.EXCELLENT.value] == 1
        assert dist[QualityLevel.GOOD.value] == 1
        assert dist[QualityLevel.ACCEPTABLE.value] == 1
        assert dist[QualityLevel.POOR.value] == 1
        assert dist[QualityLevel.UNACCEPTABLE.value] == 1
        
    @pytest.mark.asyncio
    async def test_get_quality_stats_distribution(self, quality_service):
        """Test quality distribution in stats"""
        add_quality_distribution_metrics(quality_service)
        
        stats = await quality_service.get_quality_stats(ContentType.REPORT)
        
        self._assert_distribution_stats(stats)
        self._assert_quality_levels(stats)
        
    @pytest.mark.asyncio
    async def test_get_quality_stats_recent_only(self, quality_service):
        """Test that stats use only recent entries"""
        add_recent_metrics_overflow(quality_service, 150)
        
        stats = await quality_service.get_quality_stats(ContentType.TRIAGE)
        
        triage_stats = stats[ContentType.TRIAGE.value]
        assert triage_stats['count'] == 100


class TestBatchValidation:
    """Test batch validation functionality"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_validate_batch_empty(self, quality_service):
        """Test batch validation with empty list"""
        results = await quality_service.validate_batch([])
        assert results == []
        
    @pytest.mark.asyncio
    async def test_validate_batch_mixed_types(self, quality_service):
        """Test batch validation with mixed content types"""
        contents = create_mixed_content_batch()
        
        results = await quality_service.validate_batch(contents)
        
        assert len(results) == 7
        assert all(isinstance(r, ValidationResult) for r in results)
        
    @pytest.mark.asyncio
    async def test_validate_batch_parallel_execution(self, quality_service):
        """Test that batch validation runs in parallel"""
        slow_validate = setup_slow_validation_mock()
        
        with patch.object(quality_service, 'validate_content', side_effect=slow_validate):
            contents = [("Content", ContentType.GENERAL)] * 5
            
            start = time.time()
            results = await quality_service.validate_batch(contents)
            elapsed = time.time() - start
            
            assert len(results) == 5
            assert elapsed < 0.3


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
        
        await quality_service.validate_content(content1, ContentType.OPTIMIZATION)
        await quality_service.validate_content(content2, ContentType.OPTIMIZATION)
        
        assert len(quality_service.validation_cache) == 2
        
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, quality_service):
        """Test that cache hits are faster than calculations"""
        content = "Performance test content with some complexity"
        
        start1 = time.time()
        result1 = await quality_service.validate_content(content)
        time1 = time.time() - start1
        
        start2 = time.time()
        result2 = await quality_service.validate_content(content)
        time2 = time.time() - start2
        
        assert time2 < time1 / 2
        assert result1.metrics.overall_score == result2.metrics.overall_score


class TestErrorHandling(SharedTestErrorHandling):
    """Test error handling in various methods"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_validate_content_calculation_error(self, quality_service):
        """Test error during metrics calculation"""
        with setup_validation_error_patch(quality_service):
            result = await quality_service.validate_content("Test")
            
            assert result.passed == False
            assert "Validation error" in result.metrics.issues[0]
            
    @pytest.mark.asyncio
    async def test_validate_content_threshold_error(self, quality_service):
        """Test error during threshold checking"""
        with setup_threshold_error_patch(quality_service):
            result = await quality_service.validate_content("Test")
            
            assert result.passed == False
            
    @pytest.mark.asyncio
    async def test_store_metrics_error_handling(self, quality_service):
        """Test error handling in metrics storage"""
        metrics = QualityMetrics()
        
        create_metrics_storage_error(quality_service)
        
        with patch('app.services.quality_gate_service.logger') as mock_logger:
            await quality_service._store_metrics(metrics, ContentType.GENERAL)
            mock_logger.warning.assert_called()


class TestIntegrationScenarios(SharedTestIntegrationScenarios):
    """Test complete integration scenarios"""
    
    def _create_mock_redis_for_integration(self):
        """Create Redis mock for integration testing"""
        mock_redis = AsyncMock(spec=RedisManager)
        mock_redis.get_list = AsyncMock(return_value=[])
        mock_redis.add_to_list = AsyncMock()
        mock_redis.store_metrics = AsyncMock()
        return mock_redis
        
    @pytest.fixture
    def quality_service(self):
        mock_redis = self._create_mock_redis_for_integration()
        return QualityGateService(redis_manager=mock_redis)
        
    @pytest.mark.asyncio
    async def test_complete_optimization_workflow(self, quality_service):
        """Test complete workflow for optimization content"""
        content = combine_optimization_content()
        context = setup_optimization_workflow_context()
        
        result = await quality_service.validate_content(
            content,
            ContentType.OPTIMIZATION,
            context,
            strict_mode=False
        )
        
        assert_optimization_workflow_passed(result)
        assert_optimization_workflow_metrics(result)
        assert_optimization_workflow_quality_indicators(result)
        assert_optimization_workflow_no_retry(result)
        
    @pytest.mark.asyncio
    async def test_poor_content_improvement_cycle(self, quality_service):
        """Test improvement cycle for poor content"""
        poor_content = setup_poor_content_for_improvement()
        
        result1 = await quality_service.validate_content(
            poor_content,
            ContentType.OPTIMIZATION
        )
        
        assert_poor_content_failure(result1)
        
        improved_content = setup_improved_content_after_adjustments()
        
        result2 = await quality_service.validate_content(
            improved_content,
            ContentType.OPTIMIZATION
        )
        
        assert_improvement_cycle_comparison(result1, result2)