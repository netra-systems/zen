
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_db_session():
    """Provides a mock database session."""
    return MagicMock()

@pytest.fixture
def mock_llm_connector():
    """Provides a mock LLM connector."""
    return MagicMock()
