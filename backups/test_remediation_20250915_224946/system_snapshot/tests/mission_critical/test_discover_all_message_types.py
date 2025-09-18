class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        """Comprehensive test to discover and validate all message types in the system."""

        import asyncio
        import json
        import os
        import re
        from pathlib import Path
        from typing import Set, Dict, List, Any
        import pytest
        from fastapi import WebSocket
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.websocket_core.handlers import MessageRouter
        from netra_backend.app.websocket_core.types import MessageType, LEGACY_MESSAGE_TYPE_MAP
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class MessageTypeDiscovery:
        """Discover all message types used in the codebase."""

        @staticmethod
    def find_message_types_in_code() -> Set[str]:
        """Search codebase for all message types being used."""
        message_types = set()

    # Patterns to search for message types
        patterns = [ )
        r'["\'](type)["\']:\s*["\']([\w_]+)["\']',  # {"type": "message_type"}
        r'MessageType\.([\w_]+)',  # MessageType.USER_MESSAGE
        r'message_type\s*==?\s*["\']([\w_]+)["\']',  # message_type == "user"
        r'\.type\s*==?\s*["\']([\w_]+)["\']',  # msg.type == "agent"
    

    # Common message types found in typical WebSocket systems
        common_types = { )
    # Connection lifecycle
        "connect", "disconnect", "reconnect", "close",
    # Authentication
        "auth", "login", "logout", "register", "token_refresh",
    # Heartbeat
        "ping", "pong", "heartbeat", "heartbeat_ack", "keep_alive",
    # User messages
        "user", "user_message", "user_input", "user_typing",
    # Agent/AI messages
        "agent", "agent_request", "agent_response", "agent_task",
        "agent_status", "agent_update", "agent_error", "agent_started",
        "agent_thinking", "agent_completed", "tool_executing", "tool_completed",
    # Chat
        "chat", "message", "text", "typing", "typing_started", "typing_stopped",
    # System
        "system", "system_message", "error", "error_message", "warning", "info",
    # Broadcasting
        "broadcast", "broadcast_test", "room_join", "room_leave",
    # Threads
        "thread", "thread_update", "thread_created", "thread_closed",
    # Status
        "status", "status_request", "status_update", "presence",
    # Notifications
        "notification", "alert", "announcement",
    # Subscriptions
        "subscribe", "unsubscribe", "subscription_update",
    # Testing
        "test", "echo", "debug", "resilience_test", "recovery_test",
    # Data operations
        "request", "response", "query", "mutation", "subscription",
    # Acknowledgments
        "ack", "nack", "receipt", "delivery", "read",
    # Session
        "session", "session_start", "session_end", "session_update",
    # File operations
        "upload", "download", "file_transfer",
    # Real-time updates
        "update", "patch", "sync", "delta",
    # Commands
        "command", "action", "execute",
    Frontend specific types from test files
        "connected", "connection_established", "rate_test", "timeout_test",
        "ttl_test", "recovery", "user_created", "user_action", "page_view",
    # Agent event types (critical for business value)
        "agent_fallback", "agent_failed", "start_agent",
        "agent_response_chunk", "agent_response_complete",
        "agent_status_request", "agent_status_update", "agent_progress",
        "agent_task_ack", "direct_message"
    

        return common_types

        @staticmethod
    def get_defined_message_types() -> Dict[str, Set[str]]:
        """Get all message types defined in the system."""
        result = { )
        "enum_values": set(),
        "legacy_map_keys": set(),
        "all_supported": set()
    

    # Get MessageType enum values
        for attr in dir(MessageType):
        if not attr.startswith('_') and attr.isupper():
        value = getattr(MessageType, attr)
        if isinstance(value, str):
        result["enum_values"].add(value)

                # Get legacy map keys
        result["legacy_map_keys"] = set(LEGACY_MESSAGE_TYPE_MAP.keys())

                # Combine all supported types
        result["all_supported"] = result["enum_values"] | result["legacy_map_keys"]

        return result


class TestMessageTypeCompleteness:
        """Test suite to ensure all message types are properly handled."""

    def test_discover_missing_mappings(self):
        """Discover message types that might be missing from LEGACY_MESSAGE_TYPE_MAP."""
        discovery = MessageTypeDiscovery()

    # Get all types used in code
        used_types = discovery.find_message_types_in_code()

    # Get defined types
        defined = discovery.get_defined_message_types()

    # Find potentially missing types
        potentially_missing = used_types - defined["all_supported"]

    # Filter out types that are likely test-only or internal
        test_only_patterns = ["test", "debug", "mock", "example", "demo"]
        missing = { )
        t for t in potentially_missing
        if not any(pattern in t.lower() for pattern in test_only_patterns)
    

        print(" )
        === Message Type Discovery Report ===
        ")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

        if missing:
        print("formatted_string")
        for msg_type in sorted(missing):
        print("formatted_string")

            # Generate suggested mappings
        print(" )
        Suggested additions to LEGACY_MESSAGE_TYPE_MAP:")
        for msg_type in sorted(missing):
        suggested_enum = self._suggest_enum_mapping(msg_type, defined["enum_values"])
        if suggested_enum:
        print('formatted_string')
        else:
        print(" )
        SUCCESS: All common message types appear to be supported!")

                        # List current mappings for reference
        print("formatted_string")

    def _suggest_enum_mapping(self, msg_type: str, enum_values: Set[str]) -> str:
        """Suggest an appropriate MessageType enum value for a message type."""
        pass
    # Direct mappings
        suggestions = { )
        "auth": "AUTH",
        "login": "LOGIN",
        "logout": "LOGOUT",
        "register": "REGISTER",
        "subscribe": "SUBSCRIBE",
        "unsubscribe": "UNSUBSCRIBE",
        "notification": "NOTIFICATION",
        "thread": "THREAD_UPDATE",
        "typing": "USER_TYPING",
        "status": "STATUS_UPDATE",
        "update": "UPDATE",
        "request": "REQUEST",
        "response": "RESPONSE",
        "command": "COMMAND",
        "action": "ACTION",
        "session": "SESSION",
        "connect": "CONNECT",
        "disconnect": "DISCONNECT",
        "reconnect": "RECONNECT"
    

    # Try to find if the suggested enum exists
        for key, suggested in suggestions.items():
        if key in msg_type.lower():
            # Check if this enum value exists
        for enum_val in enum_values:
        if suggested in enum_val.upper():
        return suggested
                    # Try related values
        if key in enum_val.lower():
        return enum_val.upper().replace('-', '_')

                        # Default suggestions based on patterns
        if "agent" in msg_type:
        return "AGENT_REQUEST"
        elif "user" in msg_type:
        return "USER_MESSAGE"
        elif "error" in msg_type:
        return "ERROR_MESSAGE"
        elif "system" in msg_type:
        return "SYSTEM_MESSAGE"

        return None

@pytest.mark.asyncio
    async def test_all_common_types_route_successfully(self):
"""Test that all commonly used message types route without errors."""
router = MessageRouter()
mock_websocket = AsyncMock(spec=WebSocket)
mock_# websocket setup complete
mock_# websocket setup complete

                                            # Test common message types that should work
test_types = [ )
"ping", "pong", "heartbeat",
"user", "user_message", "user_input",
"agent", "agent_request", "agent_response",
"chat", "system", "error",
"broadcast", "thread_update"
                                            

failed_types = []

for msg_type in test_types:
message = { )
"type": msg_type,
"payload": {"test": "data"},
"id": "formatted_string"
                                                

try:
result = await router.route_message("test_user", mock_websocket, message)
if not result:
failed_types.append((msg_type, "Returned False"))
except Exception as e:
failed_types.append((msg_type, str(e)))

if failed_types:
print(" )
FAILED message types:")
for msg_type, error in failed_types:
print("formatted_string")
assert False, "formatted_string"
else:
print("formatted_string")

def test_frontend_critical_message_types(self):
"""Ensure frontend-critical message types are properly mapped."""
pass
    # These are critical for the chat UI business value
critical_types = { )
"agent_started": "Agent begins processing",
"agent_thinking": "Agent reasoning visibility",
"agent_completed": "Agent finished processing",
"tool_executing": "Tool usage transparency",
"tool_completed": "Tool results display",
"agent_fallback": "Fallback handling",
"agent_failed": "Error handling",
"agent_error": "Error details",
"user": "User messages",
"agent": "Agent requests"
    

unmapped = []
for msg_type, description in critical_types.items():
        # Check if it's in the legacy map or is a valid enum
if msg_type not in LEGACY_MESSAGE_TYPE_MAP:
try:
MessageType(msg_type)
except ValueError:
unmapped.append((msg_type, description))

if unmapped:
print(" )
WARNING: Critical frontend message types not mapped:")
for msg_type, desc in unmapped:
print("formatted_string")

                            # These are critical for business value, so fail the test
assert False, "formatted_string"
else:
print(" )
SUCCESS: All critical frontend message types are properly mapped")

def test_generate_comprehensive_mapping_report(self):
"""Generate a comprehensive report of all message type mappings."""
print(" )
" + "="*60)
print("COMPREHENSIVE MESSAGE TYPE MAPPING REPORT")
print("="*60)

    # Current MessageType enum values
print(" )
[MessageType Enum Values]")
enum_values = []
for attr in dir(MessageType):
if not attr.startswith('_') and attr.isupper():
value = getattr(MessageType, attr)
if isinstance(value, str):
enum_values.append((attr, value))

for attr, value in sorted(enum_values):
print("formatted_string")

                    # Current LEGACY_MESSAGE_TYPE_MAP
print("formatted_string")
for key in sorted(LEGACY_MESSAGE_TYPE_MAP.keys()):
mapped_to = LEGACY_MESSAGE_TYPE_MAP[key]
print("formatted_string")

                        # Check for duplicates
print(" )
[Checking for duplicate mappings]")
reverse_map = {}
for key, value in LEGACY_MESSAGE_TYPE_MAP.items():
if value not in reverse_map:
reverse_map[value] = []
reverse_map[value].append(key)

duplicates = {}
if duplicates:
print("  Found types mapping to same enum:")
for enum_val, keys in duplicates.items():
print("formatted_string")
else:
print("  SUCCESS: No duplicate mappings found")

print(" )
" + "="*60)


if __name__ == "__main__":
                                                # Run discovery
discovery = MessageTypeDiscovery()
test = TestMessageTypeCompleteness()

                                                # Run tests
print("Running message type discovery and validation...")
test.test_discover_missing_mappings()
test.test_frontend_critical_message_types()
test.test_generate_comprehensive_mapping_report()

                                                # Run async tests
import asyncio
asyncio.run(test.test_all_common_types_route_successfully())
pass
