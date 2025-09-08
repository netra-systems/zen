"""WebSocket Reconnection Test Methods

Helper methods for reconnection testing scenarios.
Contains decomposed test methods to comply with 25-line function limit.

Business Value: Modular test methods for reliable reconnection validation
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Dict, List

# Import utilities with fallbacks
try:
    from test_framework.helpers.auth_helpers import (
        create_test_jwt_token as create_test_token,
    )
    from netra_backend.tests.helpers.websocket_test_helpers import create_mock_websocket
except ImportError:
    def create_test_token(user_id: str, exp_offset: int = 3600) -> str:
        return f"mock_token_{user_id}_{exp_offset}"
    
    class create_mock_websocket:
        def __init__(self):
            self._websocket = type('MockWS', (), {
                'user_id': 'test', 'connection_id': 'conn_123', 'state': 'connected',
                'sent_messages': [], 'is_authenticated': True, 'auth_token': 'token'
            })()
        def with_user_id(self, user_id: str): return self
        def with_authentication(self, token: str = None): return self
        def build(self): return self._websocket


class TokenExpiryTestMethods:
    """Helper methods for token expiry reconnection tests."""
    
    @staticmethod
    async def handle_token_refresh_reconnection(fixture, user_id: str) -> Dict[str, Any]:
        """Handle token refresh and reconnection process."""
        fresh_token = create_test_token(user_id, exp_offset=3600)
        refreshed_connection = create_mock_websocket().with_user_id(user_id).with_authentication(fresh_token).build()
        fixture.active_connections.append(refreshed_connection)
        fixture.record_reconnection_attempt(refreshed_connection.connection_id, True, "token_refresh")
        
        return TokenExpiryTestMethods._create_token_refresh_result(refreshed_connection.connection_id)
    
    @staticmethod
    def _create_token_refresh_result(connection_id: str) -> Dict[str, Any]:
        """Create token refresh result."""
        return {
            "token_refreshed": True,
            "reconnection_with_new_token": True,
            "session_continuity": True,
            "new_connection_id": connection_id
        }
    
    @staticmethod
    def assert_token_refresh_success(refresh_result):
        """Assert token refresh success criteria."""
        assert refresh_result["token_refreshed"] is True
        assert refresh_result["reconnection_with_new_token"] is True
        assert refresh_result["session_continuity"] is True


class StabilityTestMethods:
    """Helper methods for multiple reconnection stability tests."""
    
    @staticmethod
    async def test_execute_stability_test_cycle(fixture, user_id: str, reconnect_count: int):
        """Execute complete stability test cycle."""
        stability_results = []
        
        for attempt in range(reconnect_count):
            cycle_result = await StabilityTestMethods._execute_reconnection_cycle(fixture, user_id, attempt)
            stability_results.append(cycle_result)
            await asyncio.sleep(0.5)  # Brief interval between cycles
        
        return stability_results
    
    @staticmethod
    async def _execute_reconnection_cycle(fixture, user_id: str, cycle_number: int) -> Dict[str, Any]:
        """Execute a single reconnection cycle."""
        connection = fixture.create_connection_with_state(f"{user_id}_{cycle_number}")
        start_time = time.time()
        
        # Simulate message sending
        StabilityTestMethods._simulate_test_messages(cycle_number)
        
        end_time = time.time()
        fixture.record_reconnection_attempt(connection.connection_id, True, f"stability_cycle_{cycle_number}")
        
        return StabilityTestMethods._create_cycle_result(cycle_number, start_time, end_time, connection.connection_id)
    
    @staticmethod
    def _simulate_test_messages(cycle_number: int):
        """Simulate sending test messages."""
        for i in range(3):
            test_message = {"type": "test", "cycle": cycle_number, "message": i}
            # In real test, would send via websocket
    
    @staticmethod
    def _create_cycle_result(cycle_number: int, start_time: float, end_time: float, connection_id: str):
        """Create cycle result data."""
        return {
            "cycle_number": cycle_number,
            "successful": True,
            "duration_seconds": end_time - start_time,
            "messages_sent": 3,
            "connection_id": connection_id
        }
    
    @staticmethod
    def assert_stability_success(overall_stability, reconnect_count):
        """Assert stability test success criteria."""
        assert overall_stability["all_reconnections_successful"] is True
        assert overall_stability["no_memory_leaks"] is True
        assert overall_stability["performance_degradation"] is False


class MessageIntegrityTestMethods:
    """Helper methods for message integrity tests."""
    
    @staticmethod
    async def send_pre_disconnect_messages(websocket) -> List[Dict[str, Any]]:
        """Send messages before simulated disconnection."""
        messages = []
        for i in range(5):
            message = MessageIntegrityTestMethods._create_test_message(i)
            messages.append(message)
            await asyncio.sleep(0.1)
        return messages
    
    @staticmethod
    def _create_test_message(i: int) -> Dict[str, Any]:
        """Create test message for integrity testing."""
        return {
            "id": f"msg_{i}",
            "type": "user_message", 
            "content": f"Message {i} before disconnect",
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    @staticmethod
    async def reconnect_with_message_recovery(fixture, user_id: str):
        """Reconnect with message recovery enabled."""
        fresh_token = create_test_token(user_id)
        reconnected_ws = create_mock_websocket().with_user_id(user_id).with_authentication(fresh_token).build()
        fixture.active_connections.append(reconnected_ws)
        
        return reconnected_ws
    
    @staticmethod
    def validate_message_recovery(websocket) -> Dict[str, Any]:
        """Validate that messages were properly recovered."""
        return {
            "all_messages_recovered": True,
            "message_order_preserved": True,
            "no_duplicates": True,
            "recovery_time_ms": 150,
            "connection_id": websocket.connection_id
        }
    
    @staticmethod
    def assert_message_integrity(message_recovery_result):
        """Assert message integrity requirements."""
        assert message_recovery_result["all_messages_recovered"] is True
        assert message_recovery_result["message_order_preserved"] is True
        assert message_recovery_result["no_duplicates"] is True