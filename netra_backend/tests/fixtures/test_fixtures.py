"""General test fixtures."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import MagicMock

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
