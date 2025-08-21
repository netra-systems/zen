"""Tests for Quality Gate Service - Storage and Statistics

This module tests metrics storage, quality statistics, and batch validation functionality.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from netra_backend.app.services.quality_gate_service import (
    QualityGateService,
    QualityLevel,
    ContentType,
    QualityMetrics,
    ValidationResult
)
from redis_manager import RedisManager


class TestMetricsStorage:
    """Test metrics storage and retrieval"""
    
    @pytest.fixture
    def mock_redis(self):
        return AsyncMock(spec=RedisManager)
        
    @pytest.fixture
    def quality_service(self, mock_redis):
        return QualityGateService(redis_manager=mock_redis)
    async def test_store_metrics_memory_limit(self, quality_service):
        """Test that metrics history is limited properly"""
        # Pre-fill with 1000 entries
        for i in range(1000):
            quality_service.metrics_history[ContentType.OPTIMIZATION].append({
                'timestamp': f'2024-01-01T{i:04d}',
                'overall_score': 0.5
            })
        
        # Add one more
        new_metrics = QualityMetrics(overall_score=0.9)
        await quality_service._store_metrics(new_metrics, ContentType.OPTIMIZATION)
        
        # Should still be 1000
        assert len(quality_service.metrics_history[ContentType.OPTIMIZATION]) == 1000
        # Last one should be the new one
        assert quality_service.metrics_history[ContentType.OPTIMIZATION][-1]['overall_score'] == 0.9
    async def test_store_metrics_redis_with_ttl(self, quality_service, mock_redis):
        """Test Redis storage with TTL"""
        metrics = QualityMetrics(overall_score=0.75)
        
        await quality_service._store_metrics(metrics, ContentType.DATA_ANALYSIS)
        
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        
        # Check key contains content type
        assert "quality_metrics:data_analysis" in call_args[0][0]
        # Check value is JSON serialized metrics
        import json
        parsed_metrics = json.loads(call_args[0][1])
        assert parsed_metrics['overall_score'] == metrics.overall_score
        # Check TTL is 24 hours
        assert call_args[1]['ex'] == 86400


class TestQualityStats:
    """Test quality statistics calculation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    async def test_get_quality_stats_empty(self, quality_service):
        """Test stats when no metrics exist"""
        stats = await quality_service.get_quality_stats()
        assert stats == {}
    async def test_get_quality_stats_distribution(self, quality_service):
        """Test quality distribution in stats"""
        # Add metrics with different quality levels
        for level, score in [
            (QualityLevel.EXCELLENT, 0.95),
            (QualityLevel.GOOD, 0.75),
            (QualityLevel.ACCEPTABLE, 0.55),
            (QualityLevel.POOR, 0.35),
            (QualityLevel.UNACCEPTABLE, 0.25)
        ]:
            quality_service.metrics_history[ContentType.REPORT].append({
                'timestamp': '2024-01-01',
                'overall_score': score,
                'quality_level': level.value
            })
        
        stats = await quality_service.get_quality_stats(ContentType.REPORT)
        
        report_stats = stats[ContentType.REPORT.value]
        assert report_stats['count'] == 5
        assert report_stats['min_score'] == 0.25
        assert report_stats['max_score'] == 0.95
        
        # Check distribution
        dist = report_stats['quality_distribution']
        assert dist[QualityLevel.EXCELLENT.value] == 1
        assert dist[QualityLevel.GOOD.value] == 1
        assert dist[QualityLevel.ACCEPTABLE.value] == 1
        assert dist[QualityLevel.POOR.value] == 1
        assert dist[QualityLevel.UNACCEPTABLE.value] == 1
    async def test_get_quality_stats_recent_only(self, quality_service):
        """Test that stats use only recent entries"""
        # Add 150 metrics
        for i in range(150):
            quality_service.metrics_history[ContentType.TRIAGE].append({
                'timestamp': f'2024-01-{i+1:03d}',
                'overall_score': 0.5 + (i * 0.001),
                'quality_level': 'acceptable'
            })
        
        stats = await quality_service.get_quality_stats(ContentType.TRIAGE)
        
        # Should only use last 100
        triage_stats = stats[ContentType.TRIAGE.value]
        assert triage_stats['count'] == 100


class TestBatchValidation:
    """Test batch validation functionality"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    async def test_validate_batch_empty(self, quality_service):
        """Test batch validation with empty list"""
        results = await quality_service.validate_batch([])
        assert results == []
    async def test_validate_batch_mixed_types(self, quality_service):
        """Test batch validation with mixed content types"""
        contents = [
            ("Error: Out of memory", ContentType.ERROR_MESSAGE),
            ("SELECT * FROM users", ContentType.DATA_ANALYSIS),
            ("Step 1: Install package", ContentType.ACTION_PLAN),
            ("Report summary here", ContentType.REPORT),
            ("Route to optimization team", ContentType.TRIAGE),
            ("General content", ContentType.GENERAL),
            ("Reduce latency by 50ms", ContentType.OPTIMIZATION)
        ]
        
        results = await quality_service.validate_batch(contents)
        
        assert len(results) == 7
        assert all(isinstance(r, ValidationResult) for r in results)
    async def test_validate_batch_parallel_execution(self, quality_service):
        """Test that batch validation runs in parallel"""
        # Mock validation to take time
        async def slow_validate(*args, **kwargs):
            await asyncio.sleep(0.1)
            return ValidationResult(
                passed=True,
                metrics=QualityMetrics()
            )
        
        with patch.object(quality_service, 'validate_content', side_effect=slow_validate):
            contents = [("Content", ContentType.GENERAL)] * 5
            
            start = time.time()
            results = await quality_service.validate_batch(contents)
            elapsed = time.time() - start
            
            assert len(results) == 5
            # Should be much less than 0.5s (sequential would take 0.5s)
            assert elapsed < 0.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])