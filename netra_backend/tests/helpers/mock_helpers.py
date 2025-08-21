"""Mock setup helper functions for Quality Gate Service tests"""

import asyncio
from unittest.mock import AsyncMock, patch

from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.quality_gate_service import (
    QualityGateService,
    QualityMetrics,
    ValidationResult,
)


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
        quality_service.metrics_calculator,
        'calculate_metrics',
        side_effect=ValueError("Calculation error")
    )


def setup_threshold_error_patch(quality_service):
    """Setup patch for threshold checking error"""
    return patch.object(
        quality_service.validator,
        'check_thresholds',
        side_effect=KeyError("Missing threshold")
    )


def setup_slow_validation_mock():
    """Setup mock for slow validation testing"""
    async def slow_validate(content: str, content_type=None, context=None):
        await asyncio.sleep(0.1)
        return ValidationResult(
            passed=True,
            metrics=QualityMetrics()
        )
    return slow_validate


def create_metrics_storage_error(quality_service):
    """Create error condition for metrics storage"""
    quality_service.metrics_history = None