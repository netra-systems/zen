"""
Agent Reconnection State Manager - E2E Testing Helper

Handles WebSocket reconnection scenarios while preserving agent execution state.
Tests business-critical functionality: session continuity during network interruptions.

Business Value: Protects $500K+ ARR by ensuring chat sessions survive connection drops.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from shared.isolated_environment import IsolatedEnvironment


@dataclass
class AgentConnectionState:
    """Represents the state of an agent connection during reconnection testing."""
    user_id: str
    session_id: str
    conversation_id: Optional[str] = None
    active_agent_state: Optional[Dict[str, Any]] = None
    websocket_client: Optional[Any] = None
    last_message_timestamp: Optional[float] = None


class AgentStateReconnectionManager:
    """
    Manages agent state preservation during WebSocket reconnections.

    Simulates real-world network interruptions and validates that:
    1. Agent execution state persists across reconnections
    2. Chat sessions can be resumed seamlessly
    3. No data loss occurs during connection drops
    """

    def __init__(self, client_factory):
        """Initialize with a real client factory for creating WebSocket connections."""
        self.client_factory = client_factory
        self.connection_states: Dict[str, AgentConnectionState] = {}
        self.env = IsolatedEnvironment()

    async def establish_initial_connection(self, user_id: str) -> AgentConnectionState:
        """
        Establish initial WebSocket connection and capture baseline state.

        Args:
            user_id: Unique identifier for the test user

        Returns:
            AgentConnectionState: Initial connection state for comparison
        """
        session_id = f"session_{user_id}_{int(time.time())}"

        # Create real WebSocket client
        websocket_client = await self.client_factory.create_websocket_client(
            user_id=user_id,
            session_id=session_id
        )

        # Establish connection and capture initial state
        await websocket_client.connect()

        connection_state = AgentConnectionState(
            user_id=user_id,
            session_id=session_id,
            websocket_client=websocket_client,
            last_message_timestamp=time.time()
        )

        self.connection_states[user_id] = connection_state
        return connection_state

    async def simulate_connection_loss(self, user_id: Optional[str] = None) -> None:
        """
        Simulate network connection loss by closing WebSocket connections.

        Args:
            user_id: Specific user to disconnect, or None for all connections
        """
        if user_id:
            if user_id in self.connection_states:
                state = self.connection_states[user_id]
                if state.websocket_client:
                    await state.websocket_client.disconnect()
                    state.websocket_client = None
        else:
            # Disconnect all connections
            for state in self.connection_states.values():
                if state.websocket_client:
                    await state.websocket_client.disconnect()
                    state.websocket_client = None

    async def attempt_reconnection(self, user_id: str) -> AgentConnectionState:
        """
        Attempt to reconnect and restore agent state.

        Args:
            user_id: User to reconnect

        Returns:
            AgentConnectionState: Updated connection state after reconnection
        """
        if user_id not in self.connection_states:
            raise ValueError(f"No previous connection state found for user {user_id}")

        state = self.connection_states[user_id]

        # Create new WebSocket client with same session info
        new_client = await self.client_factory.create_websocket_client(
            user_id=user_id,
            session_id=state.session_id
        )

        # Attempt reconnection
        await new_client.connect()

        # Update state with new client
        state.websocket_client = new_client
        state.last_message_timestamp = time.time()

        return state

    async def capture_agent_state(self, user_id: str) -> Dict[str, Any]:
        """
        Capture current agent execution state for comparison.

        Args:
            user_id: User whose agent state to capture

        Returns:
            Dict containing agent state snapshot
        """
        if user_id not in self.connection_states:
            return {}

        state = self.connection_states[user_id]
        if not state.websocket_client:
            return {}

        try:
            # Request current agent state via WebSocket
            await state.websocket_client.send_message({
                "type": "get_agent_state",
                "session_id": state.session_id
            })

            # Wait for state response
            response = await state.websocket_client.wait_for_message(
                message_type="agent_state_response",
                timeout=5.0
            )

            return response.get("agent_state", {})

        except Exception as e:
            # Return empty state if capture fails
            return {"capture_error": str(e)}

    async def validate_state_preservation(
        self,
        user_id: str,
        pre_disconnect_state: Dict[str, Any],
        post_reconnect_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that agent state was preserved across reconnection.

        Args:
            user_id: User whose state to validate
            pre_disconnect_state: State before disconnection
            post_reconnect_state: State after reconnection

        Returns:
            Dict containing validation results
        """
        validation_results = {
            "user_id": user_id,
            "state_preserved": False,
            "differences": [],
            "critical_fields_intact": True
        }

        # Critical fields that must be preserved
        critical_fields = [
            "conversation_id",
            "agent_type",
            "execution_context",
            "user_data"
        ]

        # Check critical fields
        for field in critical_fields:
            pre_value = pre_disconnect_state.get(field)
            post_value = post_reconnect_state.get(field)

            if pre_value != post_value:
                validation_results["differences"].append({
                    "field": field,
                    "pre_disconnect": pre_value,
                    "post_reconnect": post_value
                })
                validation_results["critical_fields_intact"] = False

        # Overall state preservation check
        validation_results["state_preserved"] = (
            validation_results["critical_fields_intact"] and
            len(validation_results["differences"]) == 0
        )

        return validation_results

    async def cleanup(self) -> None:
        """Clean up all connection states and resources."""
        for state in self.connection_states.values():
            if state.websocket_client:
                try:
                    await state.websocket_client.disconnect()
                except Exception:
                    pass  # Ignore cleanup errors

        self.connection_states.clear()