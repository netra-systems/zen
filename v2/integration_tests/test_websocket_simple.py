
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_websocket_connection():
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"message": "hello"}
