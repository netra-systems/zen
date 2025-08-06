from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_websocket_handshake():
    with client.websocket_connect("/ws/123") as websocket:
        websocket.send_text("handshake")
        data = websocket.receive_text()
        assert data == "handshake_ack"
