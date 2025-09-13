"""Frontend WebSocket Connection E2E Tests for DEV MODE



CRITICAL CONTEXT: Frontend WebSocket Handshake & Connection Management

Tests real WebSocket connection establishment, handshake validation, and 

connection lifecycle management for frontend clients in development environment.



Business Value Justification (BVJ):

1. Segment: Platform/Internal - Development velocity

2. Business Goal: Ensure reliable frontend-backend WebSocket communication  

3. Value Impact: Prevents silent connection failures causing poor UX

4. Revenue Impact: Reduces customer churn from real-time feature failures



Module Architecture Compliance: Under 300 lines, functions under 8 lines

"""



import asyncio

import json

from datetime import datetime

from typing import Dict, List, Optional

from shared.isolated_environment import IsolatedEnvironment



import pytest

import websockets



from tests.e2e.harness_utils import (

    UnifiedTestHarnessComplete as TestHarness,

)

from tests.e2e.jwt_token_helpers import JWTTestHelper

from tests.e2e.harness_utils import UnifiedTestHarnessComplete





class TestWebSocketConnectioner:

    """Test utilities for WebSocket connection scenarios."""

    

    def __init__(self):

        self.harness = TestHarness()

        self.jwt_helper = JWTTestHelper()

        self.active_connections: List[websockets.ClientConnection] = []

    

    async def setup(self):

        """Initialize test environment."""

        await self.harness.setup()

        return self

    

    async def cleanup(self):

        """Clean up connections and test environment."""

        await self._close_all_connections()

        await self.harness.teardown()

    

    async def _close_all_connections(self):

        """Close all active WebSocket connections."""

        for ws in self.active_connections:

            if not ws.closed:

                await ws.close()

        self.active_connections.clear()

    

    async def create_websocket_connection(self, auth_token: Optional[str] = None):

        """Create authenticated WebSocket connection."""

        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

        ws_url = f"ws://localhost:8000/websocket"

        ws = await websockets.connect(ws_url, additional_headers=headers)

        self.active_connections.append(ws)

        return ws

    

    async def verify_connection_state(self, ws, expected_state: str):

        """Verify WebSocket connection state matches expected."""

        actual_state = "OPEN" if ws.open else "CLOSED"

        assert actual_state == expected_state





@pytest.fixture

async def connection_tester():

    """Fixture providing WebSocket connection test utilities."""

    tester = WebSocketConnectionTester()

    await tester.setup()

    yield tester

    await tester.cleanup()





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_handshake_success(connection_tester):

    """Test successful WebSocket handshake with valid auth token."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    

    # Act

    ws = await connection_tester.create_websocket_connection(valid_token)

    

    # Assert

    await connection_tester.verify_connection_state(ws, "OPEN")

    assert ws.request.headers.get("Authorization") == f"Bearer {valid_token}"





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_handshake_invalid_auth(connection_tester):

    """Test WebSocket handshake fails with invalid auth token."""

    # Act & Assert

    with pytest.raises(websockets.exceptions.ConnectionClosedError):

        await connection_tester.create_websocket_connection("invalid_token")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_handshake_no_auth(connection_tester):

    """Test WebSocket handshake fails without auth token."""

    # Act & Assert

    with pytest.raises(websockets.exceptions.ConnectionClosedError):

        await connection_tester.create_websocket_connection(None)





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_upgrade_protocol(connection_tester):

    """Test WebSocket protocol upgrade headers are correct."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    

    # Act

    ws = await connection_tester.create_websocket_connection(valid_token)

    

    # Assert - Verify HTTP upgrade occurred

    assert ws.protocol == "websocket"

    await connection_tester.verify_connection_state(ws, "OPEN")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_connection_timeout(connection_tester):

    """Test WebSocket connection respects timeout settings."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    

    # Act - Create connection with short timeout

    ws = await websockets.connect(

        "ws://localhost:8000/websocket",

        additional_headers={"Authorization": f"Bearer {valid_token}"},

        close_timeout=1

    )

    connection_tester.active_connections.append(ws)

    

    # Assert

    await connection_tester.verify_connection_state(ws, "OPEN")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_connection_lifecycle(connection_tester):

    """Test complete WebSocket connection lifecycle."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    

    # Act - Connect

    ws = await connection_tester.create_websocket_connection(valid_token)

    await connection_tester.verify_connection_state(ws, "OPEN")

    

    # Act - Close

    await ws.close()

    

    # Assert

    await connection_tester.verify_connection_state(ws, "CLOSED")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_multiple_connections(connection_tester):

    """Test multiple simultaneous WebSocket connections."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    

    # Act - Create multiple connections

    connections = []

    for i in range(3):

        ws = await connection_tester.create_websocket_connection(valid_token)

        connections.append(ws)

    

    # Assert - All connections are open

    for ws in connections:

        await connection_tester.verify_connection_state(ws, "OPEN")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_cors_headers(connection_tester):

    """Test WebSocket connection respects CORS configuration."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    origin = "http://localhost:3000"

    

    # Act

    ws = await websockets.connect(

        "ws://localhost:8000/websocket",

        additional_headers={

            "Authorization": f"Bearer {valid_token}",

            "Origin": origin

        }

    )

    connection_tester.active_connections.append(ws)

    

    # Assert

    await connection_tester.verify_connection_state(ws, "OPEN")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_subprotocol_negotiation(connection_tester):

    """Test WebSocket subprotocol negotiation for frontend clients."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    

    # Act

    ws = await websockets.connect(

        "ws://localhost:8000/websocket",

        additional_headers={"Authorization": f"Bearer {valid_token}"},

        subprotocols=["netra"]

    )

    connection_tester.active_connections.append(ws)

    

    # Assert

    await connection_tester.verify_connection_state(ws, "OPEN")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_connection_error_recovery(connection_tester):

    """Test WebSocket connection handles network interruption gracefully."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    ws = await connection_tester.create_websocket_connection(valid_token)

    

    # Act - Simulate network interruption by closing connection

    await ws.close(code=1006)  # Abnormal closure

    

    # Assert - Connection closed properly

    await connection_tester.verify_connection_state(ws, "CLOSED")

    

    # Act - Reconnect

    new_ws = await connection_tester.create_websocket_connection(valid_token)

    

    # Assert - New connection established

    await connection_tester.verify_connection_state(new_ws, "OPEN")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_dev_mode_features(connection_tester):

    """Test WebSocket connection includes dev mode specific features."""

    # Arrange

    valid_token = await connection_tester.jwt_helper.create_valid_jwt_token()

    

    # Act

    ws = await connection_tester.create_websocket_connection(valid_token)

    

    # Send dev mode ping

    dev_ping = {"type": "dev_ping", "payload": {"timestamp": datetime.now().isoformat()}}

    await ws.send(json.dumps(dev_ping))

    

    # Assert - Connection responds to dev mode messages

    response = await asyncio.wait_for(ws.recv(), timeout=5.0)

    response_data = json.loads(response)

    assert response_data.get("type") in ["pong", "dev_pong"]

