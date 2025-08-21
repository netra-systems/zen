"""Fixtures Tests - Split from test_quality_gate_integration.py"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.services.quality_gate_service import QualityGateService
from app.redis_manager import RedisManager
from app.tests.helpers.shared_test_types import TestIntegrationScenarios as SharedTestIntegrationScenarios


class TestSyntaxFix:
    """Test class for orphaned methods"""

    @pytest.fixture
    def service(self):
        mock_redis = AsyncMock(spec=RedisManager)
        mock_redis.get_list = AsyncMock(return_value=[])
        mock_redis.add_to_list = AsyncMock()
        mock_redis.store_metrics = AsyncMock()
        return QualityGateService(redis_manager=mock_redis)