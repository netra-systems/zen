import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.apex_optimizer_agent.agent import NetraOptimizerAgent
from app.db.models_clickhouse import AnalysisRequest

@pytest.fixture
def mock_db_session():
    """Provides a mock database session."""
    session = MagicMock()
    session.info = {"user_id": "test_user"}
    return session

@pytest.fixture
def mock_llm_connector():
    """Provides a mock LLM connector."""
    connector = MagicMock()
    connector.generate_text_async = AsyncMock(return_value='{"key": "value"}')
    return connector
