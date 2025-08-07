import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_db_session():
    """Provides a mock database session."""
    return MagicMock()

@pytest.fixture
def mock_llm_connector():
    """Provides a mock LLM connector."""
    return MagicMock()

from app.schemas import AnalysisRequest

@pytest.fixture
def mock_request():
    """Provides a mock analysis request."""
    return AnalysisRequest(
        user_id="test_user",
        query="test query",
        workloads=[
            {
                "query": "test query",
                "run_id": "test_run_id"
            }
        ]
    )