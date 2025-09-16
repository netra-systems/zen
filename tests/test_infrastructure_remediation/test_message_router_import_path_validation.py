"""
Test Infrastructure Remediation - MessageRouter Import Path Validation
Golden Path Phase 3 Critical Tests

PURPOSE: Validate that all expected MessageRouter import paths work correctly
for test infrastructure, preventing collection errors that block mission-critical tests.

ISSUE: Tests expect 'netra_backend.app.routes.message_router' but this path doesn't exist,
causing 10 collection errors in mission critical test suite.

CREATED: 2025-09-16 (Golden Path Phase 3 Test Infrastructure Fix)
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestMessageRouterImportPaths:
    """Test that all expected MessageRouter import paths work correctly"""

    def test_canonical_import_path_works(self):
        """Test that the canonical SSOT import path works"""
        try:
            from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
            assert CanonicalMessageRouter is not None
            assert hasattr(CanonicalMessageRouter, 'route_message')
        except ImportError as e:
            pytest.fail(f"Canonical import path failed: {e}")

    def test_compatibility_import_path_works(self):
        """Test that the compatibility import path works"""
        try:
            from netra_backend.app.websocket_core.message_router import MessageRouter
            assert MessageRouter is not None
            assert hasattr(MessageRouter, 'route_message')
        except ImportError as e:
            pytest.fail(f"Compatibility import path failed: {e}")

    def test_routes_import_path_missing(self):
        """Test that proves the routes import path is missing (causing test failures)"""
        with pytest.raises(ImportError, match="No module named 'netra_backend.app.routes.message_router'"):
            from netra_backend.app.routes.message_router import MessageRouter

    def test_handlers_import_path_works(self):
        """Test that handlers import path works (used by some tests)"""
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            assert MessageRouter is not None
            assert hasattr(MessageRouter, 'route_message')
        except ImportError as e:
            pytest.fail(f"Handlers import path failed: {e}")


class TestMessageRouterInterfaceCompliance:
    """Test that all import paths provide the same interface"""

    def test_all_imports_provide_same_class(self):
        """Test that all working import paths provide the same underlying class"""
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.message_router import MessageRouter
        from netra_backend.app.websocket_core.handlers import MessageRouter as HandlersMessageRouter

        # All should be the same class
        assert MessageRouter is CanonicalMessageRouter
        assert HandlersMessageRouter is CanonicalMessageRouter

    def test_factory_functions_work(self):
        """Test that factory functions work correctly"""
        from netra_backend.app.websocket_core.canonical_message_router import create_message_router
        from netra_backend.app.websocket_core.message_router import create_router
        from netra_backend.app.websocket_core.handlers import get_message_router

        # Test canonical factory
        canonical_router = create_message_router()
        assert canonical_router is not None
        assert hasattr(canonical_router, 'route_message')

        # Test compatibility factory
        compat_router = create_router()
        assert compat_router is not None
        assert hasattr(compat_router, 'route_message')

        # Test handlers factory
        handlers_router = get_message_router()
        assert handlers_router is not None
        assert hasattr(handlers_router, 'route_message')


class TestMissionCriticalTestCollectionFix:
    """Test that the import fix resolves mission critical test collection errors"""

    def test_mission_critical_imports_will_work_after_fix(self):
        """Test that proves the fix will resolve mission critical test imports"""
        
        # This test simulates what mission critical tests need:
        # They import from routes.message_router which doesn't exist
        
        # After the fix, this import should work
        # For now, we test the working alternatives exist
        from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
        from netra_backend.app.websocket_core.message_router import MessageRouter
        
        # Both should be usable for tests
        assert CanonicalMessageRouter is not None
        assert MessageRouter is not None
        
        # Both should have the interface tests expect
        required_methods = ['route_message', 'register_connection', 'unregister_connection']
        for method in required_methods:
            assert hasattr(CanonicalMessageRouter, method), f"Missing method: {method}"
            assert hasattr(MessageRouter, method), f"Missing method: {method}"

    def test_websocket_event_types_available(self):
        """Test that WebSocket event types are available for tests"""
        from netra_backend.app.websocket_core.canonical_message_router import WebSocketEventType
        
        # Tests need these event types
        assert hasattr(WebSocketEventType, 'agent_started')
        assert hasattr(WebSocketEventType, 'agent_thinking')
        assert hasattr(WebSocketEventType, 'tool_executing')
        assert hasattr(WebSocketEventType, 'tool_completed')
        assert hasattr(WebSocketEventType, 'agent_completed')


if __name__ == "__main__":
    # Run tests to validate current state and planned fixes
    pytest.main([__file__, "-v"])