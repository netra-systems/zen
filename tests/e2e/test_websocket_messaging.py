"""Frontend WebSocket Messaging E2E Tests for DEV MODE



CRITICAL CONTEXT: WebSocket Message Send/Receive Testing

Tests real message routing, state synchronization, reconnection scenarios,

and error handling for frontend WebSocket communication flows.



Business Value Justification (BVJ):

1. Segment: All segments - Core real-time communication

2. Business Goal: Ensure reliable message delivery and state sync

3. Value Impact: Prevents message loss and improves user experience

4. Revenue Impact: Critical for agent communication and real-time features



Module Architecture Compliance: Under 300 lines, functions under 8 lines

"""



import asyncio

import json

import uuid

from datetime import datetime

from typing import Any, Dict, List, Optional

from shared.isolated_environment import IsolatedEnvironment



import pytest

import websockets



from tests.e2e.harness_utils import (

    UnifiedTestHarnessComplete as TestHarness,

)

from tests.e2e.jwt_token_helpers import JWTTestHelper

from tests.e2e.harness_utils import UnifiedTestHarnessComplete





class TestWebSocketMessaginger:

    """Test utilities for WebSocket messaging scenarios."""

    

    def __init__(self):

        self.harness = TestHarness()

        self.jwt_helper = JWTTestHelper()

        self.connections: Dict[str, websockets.ClientConnection] = {}

        self.message_log: Dict[str, List[Dict]] = {}

        self.state_tracker: Dict[str, Any] = {}

    

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

        for ws in self.connections.values():

            if not ws.closed:

                await ws.close()

        self.connections.clear()

    

    async def create_authenticated_connection(self, connection_id: str):

        """Create authenticated WebSocket connection."""

        token = await self.jwt_helper.create_valid_jwt_token()

        ws = await websockets.connect(

            "ws://localhost:8000/websocket",

            additional_headers={"Authorization": f"Bearer {token}"}

        )

        self.connections[connection_id] = ws

        self.message_log[connection_id] = []

        return ws, token

    

    async def send_message(self, connection_id: str, message_type: str, payload: Dict):

        """Send typed message through WebSocket connection."""

        ws = self.connections[connection_id]

        message = {"type": message_type, "payload": payload}

        await ws.send(json.dumps(message))

        self.message_log[connection_id].append({"sent": message})

        return message

    

    async def receive_message(self, connection_id: str, timeout: float = 5.0):

        """Receive and log message from WebSocket connection."""

        ws = self.connections[connection_id]

        response = await asyncio.wait_for(ws.recv(), timeout=timeout)

        message_data = json.loads(response)

        self.message_log[connection_id].append({"received": message_data})

        return message_data

    

    async def verify_message_structure(self, message: Dict, expected_type: str):

        """Verify message follows expected structure."""

        assert message.get("type") == expected_type

        assert "payload" in message

        return message["payload"]





@pytest.fixture

async def messaging_tester():

    """Fixture providing WebSocket messaging test utilities."""

    tester = WebSocketMessagingTester()

    await tester.setup()

    yield tester

    await tester.cleanup()





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_basic_message_sending(messaging_tester):

    """Test basic message sending and receiving."""

    # Arrange

    ws, token = await messaging_tester.create_authenticated_connection("client1")

    

    # Act

    test_payload = {"content": "Hello WebSocket", "timestamp": datetime.now().isoformat()}

    await messaging_tester.send_message("client1", "chat_message", test_payload)

    

    # Assert

    response = await messaging_tester.receive_message("client1")

    payload = await messaging_tester.verify_message_structure(response, "message_received")

    assert payload["content"] == test_payload["content"]





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_message_routing(messaging_tester):

    """Test message routing between multiple connections."""

    # Arrange

    ws1, token1 = await messaging_tester.create_authenticated_connection("client1")

    ws2, token2 = await messaging_tester.create_authenticated_connection("client2")

    

    # Act - Client1 sends message

    message_payload = {"content": "Hello from client1", "target": "broadcast"}

    await messaging_tester.send_message("client1", "broadcast_message", message_payload)

    

    # Assert - Both clients receive message

    response1 = await messaging_tester.receive_message("client1")

    response2 = await messaging_tester.receive_message("client2")

    

    for response in [response1, response2]:

        payload = await messaging_tester.verify_message_structure(response, "broadcast_received")

        assert payload["content"] == message_payload["content"]





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_state_synchronization(messaging_tester):

    """Test state synchronization across WebSocket connections."""

    # Arrange

    ws, token = await messaging_tester.create_authenticated_connection("client1")

    initial_state = {"user_status": "active", "current_thread": "thread_123"}

    

    # Act - Update state

    await messaging_tester.send_message("client1", "state_update", initial_state)

    response = await messaging_tester.receive_message("client1")

    

    # Assert - State updated

    payload = await messaging_tester.verify_message_structure(response, "state_synced")

    assert payload["user_status"] == initial_state["user_status"]

    

    # Act - Request state

    await messaging_tester.send_message("client1", "state_request", {})

    state_response = await messaging_tester.receive_message("client1")

    

    # Assert - State persisted

    state_payload = await messaging_tester.verify_message_structure(state_response, "state_response")

    assert state_payload["current_thread"] == initial_state["current_thread"]





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_reconnection_message_recovery(messaging_tester):

    """Test message recovery after reconnection."""

    # Arrange

    ws1, token = await messaging_tester.create_authenticated_connection("client1")

    

    # Act - Send message and close connection

    message_id = str(uuid.uuid4())

    await messaging_tester.send_message("client1", "important_message", {

        "id": message_id, "content": "Critical data"

    })

    await ws1.close()

    

    # Reconnect

    ws2, _ = await messaging_tester.create_authenticated_connection("client2")

    

    # Request message recovery

    await messaging_tester.send_message("client2", "recover_messages", {"token": token})

    

    # Assert - Messages recovered

    recovery_response = await messaging_tester.receive_message("client2")

    payload = await messaging_tester.verify_message_structure(recovery_response, "messages_recovered")

    

    recovered_messages = payload.get("messages", [])

    assert any(msg.get("id") == message_id for msg in recovered_messages)





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_error_handling(messaging_tester):

    """Test WebSocket error handling and recovery."""

    # Arrange

    ws, token = await messaging_tester.create_authenticated_connection("client1")

    

    # Act - Send malformed message

    malformed_message = {"invalid": "structure"}

    await ws.send(json.dumps(malformed_message))

    

    # Assert - Error response received

    error_response = await messaging_tester.receive_message("client1")

    await messaging_tester.verify_message_structure(error_response, "error")

    

    # Act - Send valid message after error

    valid_payload = {"content": "Recovery test"}

    await messaging_tester.send_message("client1", "test_message", valid_payload)

    

    # Assert - Connection still functional

    response = await messaging_tester.receive_message("client1")

    payload = await messaging_tester.verify_message_structure(response, "message_received")

    assert payload["content"] == valid_payload["content"]





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_concurrent_messaging(messaging_tester):

    """Test concurrent message sending and ordering."""

    # Arrange

    ws, token = await messaging_tester.create_authenticated_connection("client1")

    

    # Act - Send multiple messages concurrently

    message_tasks = []

    for i in range(10):

        payload = {"sequence": i, "content": f"Message {i}"}

        task = messaging_tester.send_message("client1", "sequence_message", payload)

        message_tasks.append(task)

    

    await asyncio.gather(*message_tasks)

    

    # Assert - All messages processed

    responses = []

    for _ in range(10):

        response = await messaging_tester.receive_message("client1")

        responses.append(response)

    

    assert len(responses) == 10

    sequences = [resp["payload"]["sequence"] for resp in responses]

    assert set(sequences) == set(range(10))





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_message_validation(messaging_tester):

    """Test message validation and type checking."""

    # Arrange

    ws, token = await messaging_tester.create_authenticated_connection("client1")

    

    # Act - Send message with missing required fields

    invalid_payload = {"incomplete": "data"}

    await messaging_tester.send_message("client1", "validated_message", invalid_payload)

    

    # Assert - Validation error received

    validation_response = await messaging_tester.receive_message("client1")

    await messaging_tester.verify_message_structure(validation_response, "validation_error")

    

    # Act - Send valid message

    valid_payload = {"required_field": "value", "optional_field": "optional"}

    await messaging_tester.send_message("client1", "validated_message", valid_payload)

    

    # Assert - Message accepted

    success_response = await messaging_tester.receive_message("client1")

    await messaging_tester.verify_message_structure(success_response, "message_validated")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_heartbeat_mechanism(messaging_tester):

    """Test WebSocket heartbeat and keepalive functionality."""

    # Arrange

    ws, token = await messaging_tester.create_authenticated_connection("client1")

    

    # Act - Send ping

    ping_payload = {"timestamp": datetime.now().isoformat()}

    await messaging_tester.send_message("client1", "ping", ping_payload)

    

    # Assert - Pong received

    pong_response = await messaging_tester.receive_message("client1")

    pong_payload = await messaging_tester.verify_message_structure(pong_response, "pong")

    assert pong_payload["timestamp"] == ping_payload["timestamp"]





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_websocket_agent_communication(messaging_tester):

    """Test frontend-agent communication through WebSocket."""

    # Arrange

    ws, token = await messaging_tester.create_authenticated_connection("client1")

    

    # Act - Send agent request

    agent_request = {

        "agent_type": "test_agent",

        "query": "Analyze this data",

        "request_id": str(uuid.uuid4())

    }

    await messaging_tester.send_message("client1", "agent_request", agent_request)

    

    # Assert - Agent response received

    agent_response = await messaging_tester.receive_message("client1")

    payload = await messaging_tester.verify_message_structure(agent_response, "agent_response")

    assert payload["request_id"] == agent_request["request_id"]

    assert "result" in payload or "status" in payload

