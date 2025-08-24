import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from netra_backend.app.main import app

client = TestClient(app)


@pytest.fixture
def mock_auth_client():
    # Mock: Component isolation for testing without external dependencies
    with patch(
        "netra_backend.app.clients.auth_client.auth_client.validate_token_jwt"
    ) as mock_validate:
        mock_validate.return_value = {"valid": True, "user_id": "test_user"}
        yield mock_validate


def test_websocket_connection_success(mock_auth_client):
    with client.websocket_connect(
        "/ws", headers={"Authorization": "Bearer valid_token"}
    ) as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connection_established"


def test_websocket_connection_failure_no_token():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as websocket:
            pass


def test_websocket_send_receive(mock_auth_client):
    with client.websocket_connect(
        "/ws", headers={"Authorization": "Bearer valid_token"}
    ) as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "pong"


async def test_websocket_heartbeat(mock_auth_client):
    with client.websocket_connect(
        "/ws", headers={"Authorization": "Bearer valid_token"}
    ) as websocket:
        await asyncio.sleep(50)  # Wait for heartbeat
        data = websocket.receive_json(timeout=5)
        assert data["type"] == "heartbeat"
