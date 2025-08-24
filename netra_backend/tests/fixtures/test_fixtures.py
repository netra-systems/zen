"""General test fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

@pytest.fixture
def mock_database():
    """Create a mock database."""
    # Mock: Generic component isolation for controlled unit testing
    db = MagicMock()
    # Mock: Service component isolation for predictable testing behavior
    db.query = MagicMock(return_value=[])
    return db

@pytest.fixture
def mock_cache():
    """Create a mock cache."""
    # Mock: Generic component isolation for controlled unit testing
    cache = MagicMock()
    # Mock: Service component isolation for predictable testing behavior
    cache.get = MagicMock(return_value=None)
    # Mock: Generic component isolation for controlled unit testing
    cache.set = MagicMock()
    return cache
