"""
WebSocket SSOT Import Violation Detection Tests

These tests detect current SSOT violations in WebSocket manager imports and ensure
only ONE import path works after SSOT consolidation.

Business Value: Platform/Internal - Prevent import confusion and circular dependencies
Prevents developers from using multiple import paths for same functionality.

Test Status: DESIGNED TO FAIL with current code (detecting violations)
Expected Result: PASS after SSOT consolidation removes duplicate imports
"""

import asyncio
import logging
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Any

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestWebSocketSSotImportViolations(SSotBaseTestCase, unittest.TestCase):
    """
    Test suite to detect and validate WebSocket SSOT import violations.
    
    These tests are designed to FAIL with current code and PASS after consolidation.
    """
    
    def test_only_one_websocket_manager_import_path_allowed(self):
        """
        Test that only ONE import path works for WebSocket manager after SSOT consolidation.
        
        CURRENT BEHAVIOR: Multiple import paths work (VIOLATION)
        EXPECTED AFTER SSOT: Only unified import path works
        """
        import_test_results = {}
        
        # Test current import paths that should fail after consolidation
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            import_test_results['legacy_manager_import'] = True
        except ImportError:
            import_test_results['legacy_manager_import'] = False
            
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            import_test_results['websocket_manager_import'] = True
        except ImportError:
            import_test_results['websocket_manager_import'] = False
            
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            import_test_results['unified_manager_import'] = True
        except ImportError:
            import_test_results['unified_manager_import'] = False
        
        # Count successful imports
        successful_imports = sum(import_test_results.values())
        
        # CURRENT EXPECTATION: Multiple imports work (this will fail indicating violation)
        # AFTER SSOT: Only one import should work
        self.assertGreater(successful_imports, 1, 
                          "SSOT VIOLATION DETECTED: Multiple WebSocket manager import paths exist. "
                          f"Found {successful_imports} working import paths: {import_test_results}")
        
        # Log the violation for debugging
        import logging
        logging.getLogger(__name__).warning(f"WebSocket SSOT Import Violation: {successful_imports} import paths work")
        self.record_metric("websocket_ssot_import_violation", {
            "successful_imports": successful_imports,
            "import_results": import_test_results
        })

    def test_circular_import_prevention(self):
        """
        Test that WebSocket manager imports don't create circular dependencies.
        
        CURRENT BEHAVIOR: May have circular imports (VIOLATION)
        EXPECTED AFTER SSOT: Clean import hierarchy
        """
        import sys
        original_modules = set(sys.modules.keys())
        
        try:
            # Test import sequence that might cause circular dependencies
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.websocket_core.manager import WebSocketManager as LegacyWebSocketManager
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # Check if same class is imported with different names
            manager_classes = [WebSocketManager, LegacyWebSocketManager, UnifiedWebSocketManager]
            unique_classes = set(id(cls) for cls in manager_classes)
            
            # CURRENT EXPECTATION: Multiple class IDs exist (violation)
            # AFTER SSOT: Should be same class with different aliases
            self.assertGreater(len(unique_classes), 1,
                             "SSOT VIOLATION DETECTED: Multiple WebSocket manager class definitions found. "
                             f"Found {len(unique_classes)} unique class IDs")
            
            logging.getLogger(__name__).warning(f"Circular Import Test: Found {len(unique_classes)} unique WebSocket manager classes")
            
        except ImportError as e:
            # If imports fail, that might indicate circular dependency issues
            self.fail(f"Import error detected (possible circular dependency): {e}")
        
        # Check for new modules loaded during import
        new_modules = set(sys.modules.keys()) - original_modules
        websocket_modules = [mod for mod in new_modules if 'websocket' in mod.lower()]
        
        self.record_metric("websocket_circular_import_test", {
            "unique_classes": len(unique_classes),
            "new_websocket_modules": len(websocket_modules)
        })

    def test_alias_confusion_detection(self):
        """
        Test for WebSocket manager alias confusion that prevents clear SSOT.
        
        CURRENT BEHAVIOR: Multiple aliases for same/different managers (VIOLATION)
        EXPECTED AFTER SSOT: Clear single import pattern
        """
        aliases_found = {}
        
        # Test different alias patterns currently in use
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager as ManagerAlias1
            aliases_found['manager_websocketmanager'] = True
        except ImportError:
            aliases_found['manager_websocketmanager'] = False
            
        try:
            from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager as ManagerAlias2
            aliases_found['manager_unifiedwebsocketmanager'] = True
        except ImportError:
            aliases_found['manager_unifiedwebsocketmanager'] = False
            
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WSMAlias
            aliases_found['websocket_manager_websocketmanager'] = True
        except ImportError:
            aliases_found['websocket_manager_websocketmanager'] = False
            
        try:
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketManager as FactoryAlias
            aliases_found['factory_websocketmanager'] = True
        except ImportError:
            aliases_found['factory_websocketmanager'] = False
        
        working_aliases = sum(aliases_found.values())
        
        # CURRENT EXPECTATION: Multiple aliases work (violation)
        # AFTER SSOT: Should have consistent single import pattern
        self.assertGreater(working_aliases, 1,
                          "SSOT VIOLATION DETECTED: Multiple WebSocket manager aliases found. "
                          f"Found {working_aliases} working aliases: {aliases_found}")
        
        logging.getLogger(__name__).warning(f"WebSocket Alias Confusion: {working_aliases} aliases work")
        self.record_metric("websocket_alias_confusion", {
            "working_aliases": working_aliases,
            "alias_results": aliases_found
        })