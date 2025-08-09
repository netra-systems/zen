import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (RequestModel, Workload, DataSource, TimeRange,
                         User, WebSocketMessage)
from app.auth.auth_dependencies import ActiveUserWsDep
from app.services.agent_service import AgentService, get_agent_service
from app.dependencies import get_security_service
from app.services.security_service import SecurityService
import uuid
from unittest.mock import AsyncMock, MagicMock
import asyncio

@pytest.fixture
def mock_agent_service():
    mock = MagicMock(spec=AgentService)
    mock.handle_websocket_message = AsyncMock()
    return mock

@pytest.fixture
def mock_security_service():
    mock = MagicMock(spec=SecurityService)
    mock.decode_access_token = MagicMock(return_value={"sub": str(uuid.uuid4())})
    mock.get_user_by_id = AsyncMock(return_value=User(id=str(uuid.uuid4()), email="dev@example.com", is_active=True, is_superuser=False))
    return mock

@pytest.fixture(scope="function")
def client(mock_agent_service, mock_security_service):
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_service
    app.dependency_overrides[get_security_service] = lambda: mock_security_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}

async def test_websocket_sends_message_to_agent_service(client, mock_agent_service):
    user_id = str(uuid.uuid4())

    with client.websocket_connect(f"/ws?token=test") as websocket:
        request_model = RequestModel(
            id="test_req",
            user_id=user_id,
            query="Analyze my data and suggest optimizations.",
            workloads=[
                Workload(
                    run_id="test_run",
                    query="Test workload query",
                    data_source=DataSource(source_table="test_table"),
                    time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
                )
            ]
        )

        analysis_request_payload = {"request": request_model.model_dump()}
        ws_message = {"type": "start_agent", "payload": analysis_request_payload}
        
        websocket.send_json(ws_message)
        
        await asyncio.sleep(0.1)

    mock_agent_service.handle_websocket_message.assert_called_once()
    

import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (RequestModel, Workload, DataSource, TimeRange,
                         User, WebSocketMessage)
from app.auth.auth_dependencies import get_current_user_ws
from app.services.agent_service import AgentService, get_agent_service
import uuid
from unittest.mock import AsyncMock, MagicMock
import asyncio

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

async def test_websocket_sends_message_to_agent_service(client, mock_agent_service):
    user_id = str(uuid.uuid4())
    token = "test_token"
    # Override the dependency to return a mock user
    app.dependency_overrides[get_current_user_ws] = lambda: User(id=user_id, email="dev@example.com")

    with client.websocket_connect(f"/ws/{token}") as websocket:
        request_model = RequestModel(
            id="test_req",
            user_id=user_id,
            query="Analyze my data and suggest optimizations.",
            workloads=[
                Workload(
                    run_id="test_run",
                    query="Test workload query",
                    data_source=DataSource(source_table="test_table"),
                    time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
                )
            ]
        )

        analysis_request_payload = {"request": request_model.model_dump()}
        ws_message = {"type": "start_agent", "payload": analysis_request_payload}
        
        websocket.send_json(ws_message)
        
        # Allow time for the message to be processed
        await asyncio.sleep(0.1)

    mock_agent_service.handle_websocket_message.assert_called_once()
    app.dependency_overrides = {}


async def test_websocket_receives_message_from_server(client, mock_agent_service):
    user_id = str(uuid.uuid4())
    token = "test_token"
    app.dependency_overrides[get_current_user_ws] = lambda: User(id=user_id, email="dev@example.com")

    with client.websocket_connect(f"/ws/{token}") as websocket:
        # Mock the agent service sending a message
        message_to_send = {"type": "test_message", "payload": {"test": "data"}}
        
        async def send_message_after_connect():
            # This needs to be imported here to avoid circular dependency issues with the mock
            from app.ws_manager import manager
            await asyncio.sleep(0.1) # allow connection to be established
            await manager.send_message(user_id, message_to_send)

        # Run the send_message_after_connect in the background
        asyncio.create_task(send_message_after_connect())

        received_message = websocket.receive_json()
        assert received_message == message_to_send

    app.dependency_overrides = {}