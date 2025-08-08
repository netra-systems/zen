
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.asyncio
async def test_websocket_e2e():
    client = TestClient(app)
    with client.websocket_connect("/ws/test_run_123?token=test_token") as websocket:
        websocket.send_text("test message")
        data = websocket.receive_json()
        assert data == {"message": "test message"}
