"""Test to verify MessageRouter SSOT compliance

This test ensures that there is only ONE MessageRouter implementation in the codebase
and that it has the correct interface for all components.
"""

import pytest
from unittest.mock import MagicMock

def test_single_message_router_exists():
    """Verify only one MessageRouter implementation exists."""
    from netra_backend.app.websocket_core.handlers import MessageRouter as CoreMessageRouter
    from netra_backend.app.websocket_core.handlers import get_message_router
    
    # Get the singleton instance
    router_instance = get_message_router()
    
    # Verify it's the correct type
    assert isinstance(router_instance, CoreMessageRouter), "Router instance is from websocket_core.handlers"
    
    # Verify it has the correct interface
    assert hasattr(router_instance, 'add_handler'), "MessageRouter has add_handler method"
    assert hasattr(router_instance, 'remove_handler'), "MessageRouter has remove_handler method"
    assert hasattr(router_instance, 'route_message'), "MessageRouter has route_message method"
    
    # Verify it does NOT have the old interface
    assert not hasattr(router_instance, 'register_handler'), "MessageRouter does NOT have register_handler method"


def test_agent_compatibility_import():
    """Verify the compatibility import works correctly."""
    from netra_backend.app.agents.message_router import MessageRouter
    from netra_backend.app.websocket_core.handlers import MessageRouter as CoreMessageRouter
    
    # Verify they are the same class
    assert MessageRouter is CoreMessageRouter, "Compatibility import returns the correct MessageRouter"


def test_message_router_interface_works():
    """Test that the MessageRouter interface works as expected."""
    from netra_backend.app.websocket_core.handlers import get_message_router
    from netra_backend.app.websocket_core.handlers import BaseMessageHandler
    
    router = get_message_router()
    
    # Create a mock handler
    mock_handler = MagicMock(spec=BaseMessageHandler)
    mock_handler.supported_types = ['test_message']
    mock_handler.can_handle.return_value = True
    
    # Test add_handler works
    initial_count = len(router.handlers)
    router.add_handler(mock_handler)
    assert len(router.handlers) == initial_count + 1, "Handler was added successfully"
    
    # Test remove_handler works  
    router.remove_handler(mock_handler)
    assert len(router.handlers) == initial_count, "Handler was removed successfully"


def test_no_duplicate_message_router_imports():
    """Verify no imports try to use the old services/websocket MessageRouter."""
    import os
    import re
    
    codebase_root = os.path.join(os.path.dirname(__file__), '..', '..')
    old_import_pattern = r'from netra_backend\.app\.services\.websocket\.message_router import MessageRouter'
    
    # Search through Python files
    duplicate_imports = []
    
    for root, dirs, files in os.walk(codebase_root):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if re.search(old_import_pattern, content):
                            duplicate_imports.append(file_path)
                except (UnicodeDecodeError, IOError):
                    # Skip files that can't be read
                    continue
    
    assert not duplicate_imports, f"Found old MessageRouter imports in: {duplicate_imports}"


def test_websocket_integration_uses_correct_router():
    """Test that WebSocket integration uses the correct MessageRouter."""
    from netra_backend.app.websocket_core.handlers import get_message_router
    
    router = get_message_router()
    
    # Verify the router has the expected handlers for production
    handler_names = [handler.__class__.__name__ for handler in router.handlers]
    
    # Should have basic handlers
    assert 'HeartbeatHandler' in handler_names, "HeartbeatHandler is registered"
    assert 'UserMessageHandler' in handler_names, "UserMessageHandler is registered" 
    assert 'JsonRpcHandler' in handler_names, "JsonRpcHandler is registered"
    assert 'ErrorHandler' in handler_names, "ErrorHandler is registered"
    
    # Should NOT have test-only handlers in production
    test_handlers = ['AgentRequestHandler', 'TestAgentHandler']
    for test_handler in test_handlers:
        assert test_handler not in handler_names, f"{test_handler} should not be in production router"


if __name__ == "__main__":
    print("Running MessageRouter SSOT compliance tests...")
    test_single_message_router_exists()
    test_agent_compatibility_import()
    test_message_router_interface_works()
    test_no_duplicate_message_router_imports()
    test_websocket_integration_uses_correct_router()
    print("\nAll SSOT compliance tests passed!")