"""Fixtures Tests - Split from test_quality_gate_integration.py"""

import sys
from pathlib import Path

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
        mock_redis = AsyncMock(spec=RedisManager)
        mock_redis.get_list = AsyncMock(return_value=[])
        mock_redis.add_to_list = AsyncMock()
        mock_redis.store_metrics = AsyncMock()
        return QualityGateService(redis_manager=mock_redis)