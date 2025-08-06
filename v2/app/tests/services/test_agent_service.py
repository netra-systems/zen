import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.agent_service import AgentService


def test_agent_service_is_in_app_state():
    """
    Tests that the AgentService is correctly initialized and available in the app state.
    """
    with TestClient(app) as client:
        agent_service = client.app.state.agent_service
        assert isinstance(agent_service, AgentService)


@pytest.mark.asyncio
async def test_agent_service_initialization():
    """
    Tests the initialization of the AgentService and its supervisor.
    """
    with TestClient(app) as client:
        agent_service = client.app.state.agent_service
        assert agent_service.supervisor is not None
