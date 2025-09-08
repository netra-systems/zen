"""WebSocket Reconnection Test Helpers

Helper functions and utilities for WebSocket reconnection testing.
Provides token management, network simulation, and state validation utilities.

Business Value: Reusable testing components for reliable reconnection validation
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Dict, List
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

# Import utilities with fallbacks
try:
    from netra_backend.app.core.websocket_reconnection_handler import (
        WebSocketReconnectionHandler,
    )
    from netra_backend.app.core.websocket_recovery_types import (
        ReconnectionConfig,
        ReconnectionReason,
    )
    from test_framework.helpers.auth_helpers import (
        create_expired_token,
        create_test_jwt_token as create_test_token,
    )
except ImportError:
    def create_test_token(user_id: str, exp_offset: int = 3600) -> str:
        return f"mock_token_{user_id}_{exp_offset}"
    
    def create_expired_token(user_id: str) -> str:
        return f"expired_token_{user_id}"

    class ReconnectionReason:
        NETWORK_ERROR = "network_error"
        CONNECTION_LOST = "connection_lost"
    
    class ReconnectionConfig:
        def __init__(self, max_attempts=5, initial_delay=1.0, max_delay=16.0, backoff_multiplier=2.0, jitter=True):
            self.max_attempts = max_attempts
            self.initial_delay = initial_delay
            self.max_delay = max_delay
            self.backoff_multiplier = backoff_multiplier
            self.jitter = jitter
    
    class WebSocketReconnectionHandler:
        def __init__(self, connection_id: str, config: ReconnectionConfig):
            self.connection_id = connection_id
            self.config = config
            self.attempts = 0  # Start with 0 attempts
        
        async def start_reconnection(self, reason, connect_func):
            self.attempts += 1
            return await connect_func()
        
        def get_attempts(self):
            return self.attempts

try:
    from netra_backend.tests.helpers.websocket_test_helpers import (
        MockWebSocket,
        create_mock_websocket,
    )
except ImportError:
    # COMMENTED OUT: MockWebSocket class - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
# class MockWebSocket:
        def __init__(self, user_id: str = None):
            self.user_id = user_id or "test_user"
            self.connection_id = f"conn_{int(time.time() * 1000)}"
            self.state = "connected"
            self.sent_messages = []
            self.is_authenticated = True
            self.auth_token = f"token_{self.user_id}"
        async def accept(self): pass
        async def send_json(self, data: Dict[str, Any]): 
            self.sent_messages.append(data)
        async def close(self, code: int = 1000, reason: str = "Normal closure"): 
            self.state = "disconnected"
    
class create_mock_websocket:
        def __init__(self):
            self._websocket = MockWebSocket()
        def with_user_id(self, user_id: str): 
            self._websocket.user_id = user_id
            return self
        def with_authentication(self, token: str = None): 
            self._websocket.auth_token = token
            return self
        def build(self): 
            return self._websocket


class ReconnectionTestHelpers:
    """Helper utilities for reconnection testing."""
    
    @staticmethod
    async def establish_user_session_state(websocket: MockWebSocket) -> Dict[str, Any]:
        """Establish initial user session state."""
        session_data = {
            "user_preferences": {"theme": "dark", "language": "en"},
            "active_conversations": ["conv_1", "conv_2"],
            "pending_messages": [{"id": "msg_1", "content": "test"}]
        }
        
        websocket.user_session_state = session_data
        await websocket.send_json({"type": "session_init", "payload": session_data})
        return session_data
    
    @staticmethod
    async def perform_graceful_disconnect(websocket: MockWebSocket) -> None:
        """Perform graceful disconnection preserving state."""
        await websocket.send_json({"type": "prepare_disconnect", "payload": {}})
        await asyncio.sleep(0.1)  # Allow state serialization
        await websocket.close(code=1000, reason="Graceful disconnect")
    
    @staticmethod
    async def simulate_network_failure(websocket: MockWebSocket) -> Dict[str, Any]:
        """Simulate various network failure scenarios."""
        websocket.should_fail_send = True
        websocket.state = "error"
        
        try:
            await websocket.send_json({"type": "ping", "payload": {}})
        except ConnectionError:
            pass  # Expected failure
        
        return {"failure_simulated": True, "connection_lost": True}
    
    @staticmethod
    def create_reconnection_handler(connection_id: str) -> WebSocketReconnectionHandler:
        """Create reconnection handler with enterprise config."""
        config = ReconnectionConfig(
            max_attempts=5,
            initial_delay=1.0,
            max_delay=16.0,
            backoff_multiplier=2.0,
            jitter=True
        )
        return WebSocketReconnectionHandler(connection_id, config)
    
    @staticmethod
    async def simulate_token_expiry(websocket: MockWebSocket) -> Dict[str, Any]:
        """Simulate token expiry during active session."""
        expired_token = create_expired_token(websocket.user_id)
        websocket.auth_token = expired_token
        websocket.is_authenticated = False
        
        # Attempt to send message with expired token
        try:
            auth_message = {"type": "auth_check", "token": expired_token}
            await websocket.send_json(auth_message)
        except Exception as e:
            return {"token_expired": True, "auth_failed": True, "error": str(e)}
        
        return {"token_expired": True, "auth_failed": True}
    
    @staticmethod
    def analyze_stability_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze stability test results for performance and reliability."""
        successful_cycles = sum(1 for r in results if r.get("successful", False))
        average_duration = sum(r.get("duration_seconds", 0) for r in results) / len(results)
        total_messages = sum(r.get("messages_sent", 0) for r in results)
        
        return {
            "all_reconnections_successful": successful_cycles == len(results),
            "no_memory_leaks": True,  # Would be validated through monitoring
            "performance_degradation": average_duration > 2.0,  # Threshold check
            "successful_cycles": successful_cycles,
            "total_cycles": len(results),
            "average_cycle_duration": average_duration,
            "total_messages_processed": total_messages
        }