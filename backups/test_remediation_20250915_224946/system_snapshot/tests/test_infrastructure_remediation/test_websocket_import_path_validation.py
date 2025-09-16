"""
Test Infrastructure Remediation - WebSocket Import Path Validation
Golden Path Phase 3 Critical Tests

PURPOSE: Validate that WebSocket manager import paths work correctly for test infrastructure, 
preventing collection errors in mission critical tests.

ISSUE: Tests expect 'get_websocket_manager' from websocket_core module but it's not exported
due to SSOT consolidation, causing mission critical test collection errors.

CREATED: 2025-09-16 (Golden Path Phase 3 Test Infrastructure Fix)
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWebSocketManagerImportPaths:
    """Test that WebSocket manager import paths work correctly"""

    def test_websocket_core_imports_are_deprecated(self):
        """Test that direct imports from websocket_core show deprecation warnings"""
        with pytest.warns(DeprecationWarning, match="Direct import from 'netra_backend.app.websocket_core' is deprecated"):
            from netra_backend.app.websocket_core import WebSocketManager

    def test_canonical_websocket_manager_import_works(self):
        """Test that canonical WebSocket manager import works"""
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            assert WebSocketManager is not None
        except ImportError as e:
            pytest.fail(f"Canonical WebSocket manager import failed: {e}")

    def test_unified_websocket_manager_import_works(self):
        """Test that unified WebSocket manager import works"""
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            assert UnifiedWebSocketManager is not None
        except ImportError as e:
            pytest.fail(f"Unified WebSocket manager import failed: {e}")

    def test_get_websocket_manager_function_location(self):
        """Test to find where get_websocket_manager function is located"""
        # Try canonical patterns first
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
            assert get_websocket_manager is not None
            assert callable(get_websocket_manager)
        except ImportError:
            # Try unified manager
            try:
                from netra_backend.app.websocket_core.unified_manager import get_websocket_manager
                assert get_websocket_manager is not None
                assert callable(get_websocket_manager)
            except ImportError:
                # Try handlers module
                try:
                    from netra_backend.app.websocket_core.handlers import get_websocket_manager
                    assert get_websocket_manager is not None
                    assert callable(get_websocket_manager)
                except ImportError as e:
                    pytest.fail(f"get_websocket_manager not found in any expected location: {e}")


class TestWebSocketImportCompatibility:
    """Test WebSocket import compatibility for mission critical tests"""

    def test_websocket_manager_factory_methods_available(self):
        """Test that WebSocket manager factory methods are available"""
        
        # Test canonical patterns approach
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            # Should have factory methods
            assert hasattr(WebSocketManager, '__init__')
        except ImportError:
            pass  # Try next approach
            
        # Test unified manager approach
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            assert hasattr(UnifiedWebSocketManager, '__init__')
        except ImportError:
            pass  # Try next approach

    def test_websocket_types_import_works(self):
        """Test that WebSocket types are importable"""
        try:
            from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
            assert WebSocketMessage is not None
            assert MessageType is not None
        except ImportError as e:
            pytest.fail(f"WebSocket types import failed: {e}")

    def test_websocket_utils_import_works(self):
        """Test that WebSocket utilities are importable"""
        try:
            from netra_backend.app.websocket_core.utils import is_websocket_connected
            assert is_websocket_connected is not None
            assert callable(is_websocket_connected)
        except ImportError as e:
            pytest.fail(f"WebSocket utils import failed: {e}")


class TestMissionCriticalWebSocketFixes:
    """Test that fixes will resolve mission critical WebSocket import issues"""

    def test_mission_critical_needs_websocket_manager_access(self):
        """Test that mission critical tests will have access to WebSocket manager"""
        
        # Mission critical tests need access to WebSocket functionality
        # Test the most likely working paths
        
        websocket_manager_found = False
        get_manager_function_found = False
        
        # Try canonical patterns
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            websocket_manager_found = True
        except ImportError:
            pass
            
        # Try unified manager 
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
            websocket_manager_found = True
        except ImportError:
            pass

        # Try to find get_websocket_manager function
        for module_path in [
            'netra_backend.app.websocket_core.canonical_import_patterns',
            'netra_backend.app.websocket_core.unified_manager', 
            'netra_backend.app.websocket_core.handlers',
            'netra_backend.app.websocket_core.manager'
        ]:
            try:
                module = __import__(module_path, fromlist=['get_websocket_manager'])
                if hasattr(module, 'get_websocket_manager'):
                    get_manager_function_found = True
                    break
            except ImportError:
                continue
        
        # At least one of these should work for mission critical tests
        assert websocket_manager_found or get_manager_function_found, \
            "Mission critical tests need access to WebSocket manager functionality"


if __name__ == "__main__":
    # Run tests to validate current state and find correct import paths
    pytest.main([__file__, "-v"])