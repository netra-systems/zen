# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Test to verify MessageRouter SSOT compliance

    # REMOVED_SYNTAX_ERROR: This test ensures that there is only ONE MessageRouter implementation in the codebase
    # REMOVED_SYNTAX_ERROR: and that it has the correct interface for all components.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment
    # REMOVED_SYNTAX_ERROR: import asyncio

# REMOVED_SYNTAX_ERROR: def test_single_message_router_exists():
    # REMOVED_SYNTAX_ERROR: """Verify only one MessageRouter implementation exists."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import MessageRouter as CoreMessageRouter
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import get_message_router

    # Get the singleton instance
    # REMOVED_SYNTAX_ERROR: router_instance = get_message_router()

    # Verify it's the correct type
    # REMOVED_SYNTAX_ERROR: assert isinstance(router_instance, CoreMessageRouter), "Router instance is from websocket_core.handlers"

    # Verify it has the correct interface
    # REMOVED_SYNTAX_ERROR: assert hasattr(router_instance, 'add_handler'), "MessageRouter has add_handler method"
    # REMOVED_SYNTAX_ERROR: assert hasattr(router_instance, 'remove_handler'), "MessageRouter has remove_handler method"
    # REMOVED_SYNTAX_ERROR: assert hasattr(router_instance, 'route_message'), "MessageRouter has route_message method"

    # Verify it does NOT have the old interface
    # REMOVED_SYNTAX_ERROR: assert not hasattr(router_instance, 'register_handler'), "MessageRouter does NOT have register_handler method"


# REMOVED_SYNTAX_ERROR: def test_agent_compatibility_import():
    # REMOVED_SYNTAX_ERROR: """Verify the compatibility import works correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.message_router import MessageRouter
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import MessageRouter as CoreMessageRouter

    # Verify they are the same class
    # REMOVED_SYNTAX_ERROR: assert MessageRouter is CoreMessageRouter, "Compatibility import returns the correct MessageRouter"


# REMOVED_SYNTAX_ERROR: def test_message_router_interface_works():
    # REMOVED_SYNTAX_ERROR: """Test that the MessageRouter interface works as expected."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import get_message_router
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import BaseMessageHandler

    # REMOVED_SYNTAX_ERROR: router = get_message_router()

    # Create a mock handler
    # REMOVED_SYNTAX_ERROR: mock_handler = MagicMock(spec=BaseMessageHandler)
    # REMOVED_SYNTAX_ERROR: mock_handler.supported_types = ['test_message']
    # REMOVED_SYNTAX_ERROR: mock_handler.can_handle.return_value = True

    # Test add_handler works
    # REMOVED_SYNTAX_ERROR: initial_count = len(router.handlers)
    # REMOVED_SYNTAX_ERROR: router.add_handler(mock_handler)
    # REMOVED_SYNTAX_ERROR: assert len(router.handlers) == initial_count + 1, "Handler was added successfully"

    # Test remove_handler works
    # REMOVED_SYNTAX_ERROR: router.remove_handler(mock_handler)
    # REMOVED_SYNTAX_ERROR: assert len(router.handlers) == initial_count, "Handler was removed successfully"


# REMOVED_SYNTAX_ERROR: def test_no_duplicate_message_router_imports():
    # REMOVED_SYNTAX_ERROR: """Verify no imports try to use the old services/websocket MessageRouter."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import re

    # REMOVED_SYNTAX_ERROR: codebase_root = os.path.join(os.path.dirname(__file__), '..', '..')
    # REMOVED_SYNTAX_ERROR: old_import_pattern = r'from netra_backend\.app\.services\.websocket\.message_router import MessageRouter'

    # Search through Python files
    # REMOVED_SYNTAX_ERROR: duplicate_imports = []

    # REMOVED_SYNTAX_ERROR: for root, dirs, files in os.walk(codebase_root):
        # Skip certain directories
        # REMOVED_SYNTAX_ERROR: if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: for file in files:
                # REMOVED_SYNTAX_ERROR: if file.endswith('.py'):
                    # REMOVED_SYNTAX_ERROR: file_path = os.path.join(root, file)

                    # Skip test files that are intentionally checking for the failure
                    # REMOVED_SYNTAX_ERROR: if 'test_message_router_failure.py' in file_path:
                        # REMOVED_SYNTAX_ERROR: continue

                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: with open(file_path, 'r', encoding='utf-8') as f:
                                # REMOVED_SYNTAX_ERROR: content = f.read()
                                # REMOVED_SYNTAX_ERROR: if re.search(old_import_pattern, content):
                                    # REMOVED_SYNTAX_ERROR: duplicate_imports.append(file_path)
                                    # REMOVED_SYNTAX_ERROR: except (UnicodeDecodeError, IOError):
                                        # Skip files that can't be read
                                        # REMOVED_SYNTAX_ERROR: continue

                                        # REMOVED_SYNTAX_ERROR: assert not duplicate_imports, "formatted_string"


# REMOVED_SYNTAX_ERROR: def test_websocket_integration_uses_correct_router():
    # REMOVED_SYNTAX_ERROR: """Test that WebSocket integration uses the correct MessageRouter."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.handlers import get_message_router

    # REMOVED_SYNTAX_ERROR: router = get_message_router()

    # Verify the router has the expected handlers for production
    # REMOVED_SYNTAX_ERROR: handler_names = [handler.__class__.__name__ for handler in router.handlers]

    # Should have basic handlers
    # REMOVED_SYNTAX_ERROR: assert 'HeartbeatHandler' in handler_names, "HeartbeatHandler is registered"
    # REMOVED_SYNTAX_ERROR: assert 'UserMessageHandler' in handler_names, "UserMessageHandler is registered"
    # REMOVED_SYNTAX_ERROR: assert 'JsonRpcHandler' in handler_names, "JsonRpcHandler is registered"
    # REMOVED_SYNTAX_ERROR: assert 'ErrorHandler' in handler_names, "ErrorHandler is registered"

    # Should NOT have test-only handlers in production
    # REMOVED_SYNTAX_ERROR: test_handlers = ['AgentRequestHandler', 'TestAgentHandler']
    # REMOVED_SYNTAX_ERROR: for test_handler in test_handlers:
        # REMOVED_SYNTAX_ERROR: assert test_handler not in handler_names, "formatted_string"


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # REMOVED_SYNTAX_ERROR: print("Running MessageRouter SSOT compliance tests...")
            # REMOVED_SYNTAX_ERROR: test_single_message_router_exists()
            # REMOVED_SYNTAX_ERROR: test_agent_compatibility_import()
            # REMOVED_SYNTAX_ERROR: test_message_router_interface_works()
            # REMOVED_SYNTAX_ERROR: test_no_duplicate_message_router_imports()
            # REMOVED_SYNTAX_ERROR: test_websocket_integration_uses_correct_router()
            # REMOVED_SYNTAX_ERROR: print(" )
            # REMOVED_SYNTAX_ERROR: All SSOT compliance tests passed!")
            # REMOVED_SYNTAX_ERROR: pass