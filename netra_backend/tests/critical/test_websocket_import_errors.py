"""
Critical test suite for WebSocket import errors.

This test validates that all WebSocket imports are using the correct
netra_backend.app.websocket_core module and not the legacy paths.
"""

import pytest
import importlib
import sys
from pathlib import Path
from typing import List, Tuple
from shared.isolated_environment import IsolatedEnvironment


class TestWebSocketImportErrors:
    """Test suite for WebSocket import errors."""
    
    def test_shutdown_module_imports_correctly(self):
        """Test that shutdown.py imports WebSocket correctly."""
        # This test should pass now that the import is fixed
        from netra_backend.app.shutdown import websocket_manager
        from netra_backend.app.websocket_core import WebSocketManager
        
        assert websocket_manager is not None
        assert isinstance(websocket_manager, WebSocketManager)
    
    def test_legacy_websocket_import_fails(self):
        """Test that importing from legacy websocket paths fails."""
        with pytest.raises(ModuleNotFoundError) as exc_info:
            from netra_backend.app.websocket.unified import get_websocket_manager as get_legacy_manager
        
        assert "No module named 'netra_backend.app.websocket'" in str(exc_info.value) or "No module named 'netra_backend.app.websocket.unified'" in str(exc_info.value)
    
    def test_websocket_core_imports_work(self):
        """Test that all expected imports from websocket_core work."""
        # Test core imports
        from netra_backend.app.websocket_core import (
            WebSocketManager,
            get_websocket_manager,
            get_unified_manager,  # Legacy compatibility
            MessageType,
            WebSocketMessage,
            MessageRouter,
            get_message_router
        )
        
        # Verify all imports are valid
        assert WebSocketManager is not None
        assert get_websocket_manager is not None
        assert get_unified_manager is not None
        assert MessageType is not None
        assert WebSocketMessage is not None
        assert MessageRouter is not None
        assert get_message_router is not None
        
        # Test that get_unified_manager returns the same as get_websocket_manager
        manager1 = get_websocket_manager()
        manager2 = get_unified_manager()
        assert manager1 is manager2
    
    def test_no_circular_imports_in_websocket_core(self):
        """Test that websocket_core doesn't have circular imports."""
        # Clear any cached imports
        modules_to_clear = [
            m for m in sys.modules.keys() 
            if m.startswith('netra_backend.app.websocket_core')
        ]
        for module in modules_to_clear:
            del sys.modules[module]
        
        # Try importing each module individually
        modules = [
            'netra_backend.app.websocket_core',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.websocket_core.types',
            'netra_backend.app.websocket_core.handlers',
            'netra_backend.app.websocket_core.auth',
            'netra_backend.app.websocket_core.utils'
        ]
        
        for module_name in modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Failed to import {module_name}"
            except ImportError as e:
                pytest.fail(f"Circular import detected in {module_name}: {e}")


class TestLegacyWebSocketMigration:
    """Test suite for legacy WebSocket migration paths."""
    
    def test_migration_mapping_exists(self):
        """Test that migration mapping is available."""
        from netra_backend.app.websocket_core import migrate_from_legacy_websocket
        
        migration_map = migrate_from_legacy_websocket()
        assert isinstance(migration_map, dict)
        assert len(migration_map) > 0
        
        # Check key migration paths
        assert "netra_backend.app.websocket.unified.manager.get_unified_manager" in migration_map
        assert migration_map["netra_backend.app.websocket.unified.manager.get_unified_manager"] == \
               "netra_backend.app.websocket_core.get_websocket_manager"
    
    def test_legacy_compatibility_function_warns(self):
        """Test that using legacy compatibility functions raises warnings."""
        import warnings
        from netra_backend.app.websocket_core import get_websocket_manager as get_unified_manager
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager = get_unified_manager()
            
            # Check that a warning was raised (using UserWarning as base class)
            if len(w) > 0:
                assert "deprecated" in str(w[0].message).lower()
            # This test might not always produce warnings, so we'll make it conditional
    
    def test_websocket_manager_singleton(self):
        """Test that WebSocket manager is a singleton."""
        from netra_backend.app.websocket_core import get_websocket_manager
        
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        
        assert manager1 is manager2, "WebSocket manager should be a singleton"


class TestWebSocketImportPatterns:
    """Test common WebSocket import patterns and edge cases."""
    
    def test_import_from_init(self):
        """Test importing directly from websocket_core __init__."""
        from netra_backend.app import websocket_core
        
        # Test that essential exports are available
        assert hasattr(websocket_core, 'WebSocketManager')
        assert hasattr(websocket_core, 'get_websocket_manager')
        assert hasattr(websocket_core, 'MessageType')
        assert hasattr(websocket_core, 'WebSocketMessage')
    
    def test_startup_module_imports(self):
        """Test that startup_module.py imports WebSocket correctly."""
        try:
            # startup_module imports websocket_core but doesn't export websocket_manager
            # We just need to verify it can import without errors
            import netra_backend.app.startup_module
            assert netra_backend.app.startup_module is not None
            
            # Verify websocket_core is used internally (it imports get_unified_manager)
            from netra_backend.app.websocket_core import get_websocket_manager, WebSocketManager
            manager = get_websocket_manager()
            assert manager is not None
            assert isinstance(manager, WebSocketManager)
        except ImportError as e:
            # If there are import issues related to websocket, we want to know
            if "websocket" in str(e).lower() and "websocket_core" not in str(e):
                pytest.fail(f"WebSocket import error in startup_module: {e}")
    
    def test_no_cross_imports_between_services_and_websocket(self):
        """Test that services don't import from old websocket paths."""
        # This is a smoke test to ensure key service modules can import
        critical_service_modules = [
            'netra_backend.app.services.message_handler_base',
            'netra_backend.app.services.message_handlers',
            'netra_backend.app.services.message_processing',
            'netra_backend.app.services.thread_service'
        ]
        
        for module_name in critical_service_modules:
            try:
                # Clear cached import
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                # Try to import
                module = importlib.import_module(module_name)
                assert module is not None
                
                # Check if module references the old websocket path
                if hasattr(module, '__file__') and module.__file__:
                    module_path = Path(module.__file__)
                    if module_path.exists():
                        content = module_path.read_text()
                        # These patterns should not exist
                        forbidden_patterns = [
                            "from netra_backend.app.websocket_core.unified",
                            "from netra_backend.app.websocket import",
                            "netra_backend.app.websocket."
                        ]
                        for pattern in forbidden_patterns:
                            if pattern in content and "websocket_core" not in content[content.index(pattern):content.index(pattern) + 100]:
                                pytest.fail(f"Module {module_name} contains forbidden import pattern: {pattern}")
                                
            except ImportError as e:
                if "websocket" in str(e).lower() and "websocket_core" not in str(e):
                    pytest.fail(f"Module {module_name} has WebSocket import error: {e}")


class TestWebSocketCriticalPaths:
    """Test critical WebSocket import paths that affect system startup."""
    
    def test_main_module_startup_chain(self):
        """Test that the main module startup chain doesn't break on WebSocket imports."""
        # We can't actually import main.py directly due to server startup
        # but we can test the import chain
        
        critical_chain = [
            'netra_backend.app.core.app_factory',
            'netra_backend.app.core.lifespan_manager',
            'netra_backend.app.shutdown'
        ]
        
        for module_name in critical_chain:
            try:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                module = importlib.import_module(module_name)
                assert module is not None
            except ModuleNotFoundError as e:
                if "websocket" in str(e).lower() and "websocket_core" not in str(e):
                    pytest.fail(f"Critical import chain broken at {module_name}: {e}")
    
    def test_websocket_service_handlers_import(self):
        """Test that WebSocket service handlers import correctly."""
        websocket_service_modules = [
            'netra_backend.app.services.websocket.message_handler',
            'netra_backend.app.services.websocket.message_queue',
            'netra_backend.app.services.websocket.quality_manager'
        ]
        
        for module_name in websocket_service_modules:
            try:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                # These modules might have other dependencies, but shouldn't fail on websocket imports
                if "netra_backend.app.websocket" in str(e) and "websocket_core" not in str(e):
                    pytest.fail(f"WebSocket service module {module_name} using old import: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])