import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.agent_service import AgentService, get_agent_service
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_agent_service():
    mock = MagicMock(spec=AgentService)
    mock.handle_websocket_message = AsyncMock()
    return mock

@pytest.fixture(scope="function")
def client(mock_agent_service):
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}
