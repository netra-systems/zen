"""Agent State Reconnection Manager

Manages WebSocket reconnection with agent state preservation for E2E testing.
Split from main test file to maintain 450-line architectural compliance.

Business Value: Reliable agent state management across network interruptions
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from tests.unified.real_websocket_client import RealWebSocketClient
from tests.unified.reconnection_test_helpers import create_test_token


class AgentStateReconnectionManager:
    """Manages WebSocket reconnection with agent state preservation."""
    
    def __init__(self, client_factory):
        """Initialize reconnection manager."""
        self.factory = client_factory
        self.ws_client: Optional[RealWebSocketClient] = None
        self.agent_state: Dict[str, Any] = {}
        self.session_id: Optional[str] = None
        self.auth_token: Optional[str] = None
    
    async def establish_initial_connection(self, user_id: str) -> Dict[str, Any]:
        """Establish initial connection with agent state."""
        self.auth_token = create_test_token(user_id)
        ws_url = f"ws://localhost:8000/ws"
        self.ws_client = self.factory.create_websocket_client(ws_url)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        connected = await self.ws_client.connect(headers)
        assert connected, "Failed to establish initial connection"
        
        return await self._initialize_agent_state(user_id)
    
    async def _initialize_agent_state(self, user_id: str) -> Dict[str, Any]:
        """Initialize agent state through conversation."""
        self.session_id = f"session_{user_id}_{int(time.time() * 1000)}"
        init_message = self._create_init_message(user_id)
        
        await self.ws_client.send(init_message)
        response = await self.ws_client.receive()
        
        self.agent_state = self._extract_agent_state(response)
        return self.agent_state
    
    def _create_init_message(self, user_id: str) -> Dict[str, Any]:
        """Create initialization message."""
        return {
            "type": "chat_message",
            "content": f"Start AI cost optimization for user {user_id}",
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _extract_agent_state(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract agent state from response."""
        return {
            "conversation_context": response.get("context", {}),
            "user_preferences": response.get("preferences", {}),
            "analysis_state": response.get("analysis_data", {}),
            "session_id": self.session_id,
            "initialized_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def simulate_connection_loss(self) -> None:
        """Simulate network connection loss."""
        if self.ws_client:
            await self.ws_client.close()
            self.ws_client = None
    
    async def reconnect_and_verify_state(self) -> Dict[str, Any]:
        """Reconnect and verify agent state preservation."""
        ws_url = f"ws://localhost:8000/ws"
        self.ws_client = self.factory.create_websocket_client(ws_url)
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        reconnected = await self.ws_client.connect(headers)
        assert reconnected, "Failed to reconnect"
        
        return await self._verify_state_preservation()
    
    async def _verify_state_preservation(self) -> Dict[str, Any]:
        """Verify agent state was preserved after reconnection."""
        state_query = self._create_state_query()
        
        await self.ws_client.send(state_query)
        response = await self.ws_client.receive()
        
        return self._validate_preserved_state(response)
    
    def _create_state_query(self) -> Dict[str, Any]:
        """Create state verification query."""
        return {
            "type": "state_verification",
            "session_id": self.session_id,
            "expected_context": self.agent_state["conversation_context"]
        }
    
    def _validate_preserved_state(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that state was properly preserved."""
        preserved_context = response.get("context", {})
        original_context = self.agent_state["conversation_context"]
        
        return {
            "state_preserved": preserved_context == original_context,
            "session_continuity": response.get("session_id") == self.session_id,
            "reconnection_successful": True,
            "preserved_context": preserved_context,
            "original_context": original_context
        }
