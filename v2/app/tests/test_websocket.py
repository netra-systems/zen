from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_websocket_handshake():
    with client.websocket_connect("/ws/123") as websocket:
        assert websocket.accepted