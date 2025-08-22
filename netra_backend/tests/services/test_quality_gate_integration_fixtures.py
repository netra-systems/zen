"""Fixtures Tests - Split from test_quality_gate_integration.py"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.redis_manager import RedisManager

# Add project root to path
from netra_backend.app.services.quality_gate_service import QualityGateService
from ..helpers.shared_test_types import (
    TestIntegrationScenarios as SharedTestIntegrationScenarios,
)

# Add project root to path


class TestSyntaxFix:
    """Test class for orphaned methods"""

    @pytest.fixture
    def service(self):
        mock_redis = AsyncMock(spec=RedisManager)
        mock_redis.get_list = AsyncMock(return_value=[])
        mock_redis.add_to_list = AsyncMock()
        mock_redis.store_metrics = AsyncMock()
        return QualityGateService(redis_manager=mock_redis)