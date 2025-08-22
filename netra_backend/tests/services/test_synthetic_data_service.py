"""Test synthetic data generation service for testing and development."""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
from app.services.synthetic_data_service import (
    GenerationStatus,
    # Add project root to path
    SyntheticDataService,
    WorkloadCategory,
)


@pytest.fixture
def synthetic_data_service():
    """Create a test synthetic data service instance."""
    return SyntheticDataService()


class TestSyntheticDataService:
    """Test synthetic data service basic functionality."""

    def test_service_initialization(self, synthetic_data_service):
        """Test service initializes correctly."""
        assert isinstance(synthetic_data_service, SyntheticDataService)
        assert synthetic_data_service.active_jobs == {}
        assert synthetic_data_service.corpus_cache == {}
        assert hasattr(synthetic_data_service, 'default_tools')

    def test_workload_categories_enum(self):
        """Test workload category enum values."""
        categories = [category.value for category in WorkloadCategory]
        expected_categories = [
            "simple_chat", "rag_pipeline", "tool_use", 
            "multi_turn_tool_use", "failed_request", "custom_domain"
        ]
        assert all(cat in categories for cat in expected_categories)

    def test_generation_status_enum(self):
        """Test generation status enum values."""
        statuses = [status.value for status in GenerationStatus]
        expected_statuses = ["initiated", "running", "completed", "failed", "cancelled"]
        assert all(status in statuses for status in expected_statuses)


