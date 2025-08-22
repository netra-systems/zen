"""General test fixtures."""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_database():
    """Create a mock database."""
    db = MagicMock()
    db.query = MagicMock(return_value=[])
    return db

@pytest.fixture
def mock_cache():
    """Create a mock cache."""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    return cache
