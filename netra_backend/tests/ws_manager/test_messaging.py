"""
Tests for WebSocketManager messaging functionality
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, call, patch

import pytest
from starlette.websockets import WebSocketState

from netra_backend.app.websocket.unified import UnifiedWebSocketManager as WebSocketManager
from netra_backend.tests.test_base import MockWebSocket, WebSocketTestBase

class TestMessageSending(WebSocketTestBase):

    """Test message sending functionality"""

    async def test_send_message_to_connected(self, fresh_manager, connected_websocket):

        """Test sending message to connected WebSocket"""

        connection_id = "test-send-123"

        await fresh_manager.connect(connected_websocket, connection_id)
        
        message = {"type": "test", "data": "hello"}

        await fresh_manager.send_message(connection_id, message)
        
        connected_websocket.send_json.assert_called_once_with(message)

    async def test_send_message_to_disconnected(self, fresh_manager, disconnected_websocket):

        """Test sending message to disconnected WebSocket"""

        connection_id = "test-disconnected-send"

        await fresh_manager.connect(disconnected_websocket, connection_id)
        
        message = {"type": "test", "data": "hello"}

        await fresh_manager.send_message(connection_id, message)
        
        # Should not send to disconnected websocket

        disconnected_websocket.send_json.assert_not_called()
        # Connection should be cleaned up

        assert connection_id not in fresh_manager.connections

    async def test_send_message_to_nonexistent(self, fresh_manager):

        """Test sending message to non-existent connection"""
        # Should not raise an error

        await fresh_manager.send_message("nonexistent-123", {"type": "test"})

    async def test_send_message_with_error(self, fresh_manager, connected_websocket):

        """Test send_message handles send errors gracefully"""

        connection_id = "test-error-send"

        connected_websocket.send_json.side_effect = Exception("Send failed")
        
        await fresh_manager.connect(connected_websocket, connection_id)
        
        # Should not raise

        await fresh_manager.send_message(connection_id, {"type": "test"})
        
        # Connection should be removed on error

        assert connection_id not in fresh_manager.connections

    async def test_send_message_complex_data(self, fresh_manager, connected_websocket):

        """Test sending complex message data"""

        connection_id = "test-complex"

        await fresh_manager.connect(connected_websocket, connection_id)
        
        complex_message = {

            "type": "complex",

            "data": {

                "nested": {"level": 2},

                "list": [1, 2, 3],

                "timestamp": datetime.now().isoformat()

            }

        }
        
        await fresh_manager.send_message(connection_id, complex_message)

        connected_websocket.send_json.assert_called_once_with(complex_message)

class TestConnectionSending(WebSocketTestBase):

    """Test connection-based sending methods"""

    async def test_send_to_connection_success(self, fresh_manager, connected_websocket):

        """Test send_to_connection with valid connection"""

        connection_id = "test-send-conn"

        await fresh_manager.connect(connected_websocket, connection_id)
        
        await fresh_manager.send_to_connection(connection_id, "test", {"key": "value"})
        
        expected_message = {

            "type": "test",

            "data": {"key": "value"},

            "timestamp": connected_websocket.send_json.call_args[0][0]["timestamp"]

        }
        
        actual_call = connected_websocket.send_json.call_args[0][0]

        assert actual_call["type"] == expected_message["type"]

        assert actual_call["data"] == expected_message["data"]

        assert "timestamp" in actual_call

    async def test_send_to_user_single_connection(self, fresh_manager, connected_websocket):

        """Test send_to_user with single connection"""

        user_id = "user-789"

        connection_id = "user-conn-1"
        
        await fresh_manager.connect(connected_websocket, connection_id, user_id=user_id)

        await fresh_manager.send_to_user(user_id, "user_message", {"msg": "hello"})
        
        assert connected_websocket.send_json.called

        message = connected_websocket.send_json.call_args[0][0]

        assert message["type"] == "user_message"

        assert message["data"] == {"msg": "hello"}

    async def test_send_to_user_multiple_connections(self, fresh_manager):

        """Test send_to_user with multiple connections from same user"""

        user_id = "multi-user"
        
        ws1 = MockWebSocket()

        ws2 = MockWebSocket()

        ws3 = MockWebSocket()  # Different user
        
        await fresh_manager.connect(ws1, "conn-1", user_id=user_id)

        await fresh_manager.connect(ws2, "conn-2", user_id=user_id)

        await fresh_manager.connect(ws3, "conn-3", user_id="other-user")
        
        await fresh_manager.send_to_user(user_id, "broadcast", {"data": "test"})
        
        # Should send to both connections of the user

        assert ws1.send_json.called

        assert ws2.send_json.called
        # Should not send to other user

        assert not ws3.send_json.called

    async def test_send_to_user_no_connections(self, fresh_manager):

        """Test send_to_user with no connections for user"""
        # Should not raise an error

        await fresh_manager.send_to_user("nonexistent-user", "test", {})

    async def test_send_to_role_single_role(self, fresh_manager):

        """Test send_to_role with single role"""

        ws_admin = MockWebSocket()

        ws_user = MockWebSocket()
        
        await fresh_manager.connect(ws_admin, "admin-1", role="admin")

        await fresh_manager.connect(ws_user, "user-1", role="user")
        
        await fresh_manager.send_to_role("admin", "admin_only", {"restricted": True})
        
        assert ws_admin.send_json.called

        assert not ws_user.send_json.called

    async def test_send_to_role_multiple_same_role(self, fresh_manager):

        """Test send_to_role with multiple connections of same role"""

        ws1 = MockWebSocket()

        ws2 = MockWebSocket()

        ws3 = MockWebSocket()
        
        await fresh_manager.connect(ws1, "mod-1", role="moderator")

        await fresh_manager.connect(ws2, "mod-2", role="moderator")

        await fresh_manager.connect(ws3, "user-1", role="user")
        
        await fresh_manager.send_to_role("moderator", "mod_message", {"info": "test"})
        
        assert ws1.send_json.called

        assert ws2.send_json.called

        assert not ws3.send_json.called

    async def test_send_to_role_no_connections(self, fresh_manager):

        """Test send_to_role with no connections for role"""
        # Should not raise an error

        await fresh_manager.send_to_role("nonexistent-role", "test", {})

class TestSpecializedMessages(WebSocketTestBase):

    """Test specialized message types"""

    async def test_send_error(self, fresh_manager, connected_websocket):

        """Test sending error message"""

        connection_id = "test-error"

        await fresh_manager.connect(connected_websocket, connection_id)
        
        await fresh_manager.send_error(connection_id, "Something went wrong", "ERROR_CODE")
        
        message = self.assert_message_sent(connected_websocket, "error")

        assert message["error"] == "Something went wrong"

        assert message["code"] == "ERROR_CODE"

    async def test_send_success(self, fresh_manager, connected_websocket):

        """Test sending success message"""

        connection_id = "test-success"

        await fresh_manager.connect(connected_websocket, connection_id)
        
        await fresh_manager.send_success(connection_id, "Operation completed", {"result": "data"})
        
        message = self.assert_message_sent(connected_websocket, "success")

        assert message["message"] == "Operation completed"

        assert message["data"] == {"result": "data"}

    async def test_send_notification(self, fresh_manager, connected_websocket):

        """Test sending notification message"""

        connection_id = "test-notification"

        await fresh_manager.connect(connected_websocket, connection_id)
        
        await fresh_manager.send_notification(

            connection_id,

            "New message",

            "info",

            {"extra": "metadata"}

        )
        
        message = self.assert_message_sent(connected_websocket, "notification")

        assert message["title"] == "New message"

        assert message["level"] == "info"

        assert message["metadata"] == {"extra": "metadata"}

    async def test_send_status_update(self, fresh_manager, connected_websocket):

        """Test sending status update"""

        connection_id = "test-status"

        await fresh_manager.connect(connected_websocket, connection_id)
        
        await fresh_manager.send_status_update(

            connection_id,

            "processing",

            {"progress": 50}

        )
        
        message = self.assert_message_sent(connected_websocket, "status_update")

        assert message["status"] == "processing"

        assert message["details"] == {"progress": 50}

class TestBroadcasting(WebSocketTestBase):

    """Test broadcasting functionality"""

    async def test_broadcast_to_all(self, fresh_manager):

        """Test broadcasting to all connections"""

        ws1 = MockWebSocket()

        ws2 = MockWebSocket()

        ws3 = MockWebSocket()
        
        await fresh_manager.connect(ws1, "conn-1")

        await fresh_manager.connect(ws2, "conn-2")

        await fresh_manager.connect(ws3, "conn-3")
        
        await fresh_manager.broadcast({"type": "announcement", "data": "Hello all"})
        
        # All should receive the message

        for ws in [ws1, ws2, ws3]:

            assert ws.send_json.called

            message = ws.send_json.call_args[0][0]

            assert message["type"] == "announcement"

            assert message["data"] == "Hello all"

    async def test_broadcast_with_exclusion(self, fresh_manager):

        """Test broadcasting with connection exclusion"""

        ws1 = MockWebSocket()

        ws2 = MockWebSocket()

        ws3 = MockWebSocket()
        
        await fresh_manager.connect(ws1, "conn-1")

        await fresh_manager.connect(ws2, "conn-2")

        await fresh_manager.connect(ws3, "conn-3")
        
        await fresh_manager.broadcast(

            {"type": "update", "data": "test"},

            exclude=["conn-2"]

        )
        
        assert ws1.send_json.called

        assert not ws2.send_json.called  # Excluded

        assert ws3.send_json.called

    async def test_broadcast_to_empty(self, fresh_manager):

        """Test broadcasting when no connections exist"""
        # Should not raise an error

        await fresh_manager.broadcast({"type": "test", "data": "empty"})

    async def test_broadcast_handles_errors(self, fresh_manager):

        """Test broadcast continues despite individual send errors"""

        ws1 = MockWebSocket()

        ws2 = MockWebSocket()

        ws3 = MockWebSocket()
        
        # Make ws2 fail on send

        ws2.send_json.side_effect = Exception("Send failed")
        
        await fresh_manager.connect(ws1, "conn-1")

        await fresh_manager.connect(ws2, "conn-2")

        await fresh_manager.connect(ws3, "conn-3")
        
        await fresh_manager.broadcast({"type": "test", "data": "broadcast"})
        
        # ws1 and ws3 should still receive the message

        assert ws1.send_json.called

        assert ws3.send_json.called
        # ws2 should be removed due to error

        assert "conn-2" not in fresh_manager.connections