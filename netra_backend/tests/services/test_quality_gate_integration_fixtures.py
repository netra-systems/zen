"""Fixtures Tests - Split from test_quality_gate_integration.py"""

import sys
from pathlib import Path

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch, Mock, patch

import pytest

from netra_backend.app.redis_manager import RedisManager

from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.tests.services.helpers.shared_test_types import (
    TestIntegrationScenarios as SharedTestIntegrationScenarios,
)

class TestSyntaxFix:
    """Test class for orphaned methods"""

    @pytest.fixture
    def service(self):
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis = AsyncMock(spec=RedisManager)
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis.get_list = AsyncMock(return_value=[])
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis.add_to_list = AsyncMock()
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        mock_redis.store_metrics = AsyncMock()
        return QualityGateService(redis_manager=mock_redis)