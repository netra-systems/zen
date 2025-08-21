"""Tests for Quality Gate Service completeness and novelty calculations"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import re
import pytest
from unittest.mock import patch

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.quality_gate_service import (

# Add project root to path
    QualityGateService,
    ContentType,
    QualityMetrics
)
from redis_manager import RedisManager
from netra_backend.tests.helpers.quality_gate_comprehensive_helpers import (
    setup_completeness_report_content,
    setup_completeness_general_content,
    setup_redis_mock_with_error,
    setup_redis_mock_with_large_cache
)


class TestCompletenessCalculation:
    """Test completeness calculation for all content types"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    async def test_completeness_report_type(self, quality_service):
        """Test completeness for report content type"""
        content = setup_completeness_report_content()
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_completeness(
            content,
            ContentType.REPORT
        )
        assert score == 1.0  # Has all required elements
    async def test_completeness_general_type(self, quality_service):
        """Test completeness for general content type"""
        content = setup_completeness_general_content()
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_completeness(
            content,
            ContentType.GENERAL
        )
        assert score > 0  # Should calculate based on general criteria


class TestNoveltyCalculation:
    """Test novelty calculation with Redis integration"""
    
    def _create_quality_service_with_mock(self, mock_redis):
        """Create quality service with specified Redis mock"""
        return QualityGateService(redis_manager=mock_redis)
    async def test_novelty_redis_error_handling(self):
        """Test novelty calculation when Redis operations fail"""
        content = "Test content"
        
        mock_redis = setup_redis_mock_with_error()
        quality_service = self._create_quality_service_with_mock(mock_redis)
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_novelty(content)
        assert score == 0.5  # Should return default on error
    async def test_novelty_large_cache(self):
        """Test novelty with large cache list"""
        content = "Unique content"
        
        mock_redis = setup_redis_mock_with_large_cache()
        quality_service = self._create_quality_service_with_mock(mock_redis)
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_novelty(content)
        assert score == 0.8  # Should be novel if not in cache