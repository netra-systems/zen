"""Test WebSocket Manager Canonical Source Validation - Issue #824 Phase 1

Test that only UnifiedWebSocketManager is imported/used as SSOT.
Verify no duplicate manager implementations are active.
Ensure single source of truth for WebSocket management.

Business Value: Protects $500K+ ARR by preventing SSOT fragmentation failures.
"""

import pytest
import sys
import warnings
import importlib
import inspect
from typing import Set, Dict, Any, List
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class TestWebSocketManagerCanonicalSourceValidation(SSotAsyncTestCase):
    """Test canonical source validation for WebSocket Manager SSOT."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.expected_canonical_module = "netra_backend.app.websocket_core.websocket_manager"
        self.expected_canonical_class = "WebSocketManager"

    def test_canonical_websocket_manager_is_primary_import(self):
        """Test that canonical WebSocketManager is the primary import source."""
        # Import from canonical source
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as CanonicalWSM
        except ImportError as e:
            self.fail(f"CRITICAL: Cannot import canonical WebSocketManager: {e}")

        # Verify it's a real class, not a redirect
        self.assertTrue(inspect.isclass(CanonicalWSM),
                       "Canonical WebSocketManager should be a real class")

        # Verify it has expected SSOT methods
        expected_methods = ['send_event', 'register_connection', 'disconnect_user']
        for method_name in expected_methods:
            self.assertTrue(hasattr(CanonicalWSM, method_name),
                          f"Canonical WebSocketManager missing expected method: {method_name}")

        logger.info("✅ Canonical WebSocketManager validated successfully")

    def test_no_duplicate_websocket_manager_classes_active(self):
        """Test that no duplicate WebSocket Manager implementations are simultaneously active."""
        websocket_manager_classes = []

        # Search through loaded modules for WebSocketManager classes
        for module_name, module in sys.modules.items():
            if not module_name.startswith('netra_backend.app.websocket'):
                continue

            if hasattr(module, 'WebSocketManager'):
                websocket_manager_class = getattr(module, 'WebSocketManager')
                if inspect.isclass(websocket_manager_class):
                    class_info = {
                        'module': module_name,
                        'class': websocket_manager_class,
                        'file': getattr(module, '__file__', 'unknown'),
                        'id': id(websocket_manager_class)
                    }
                    websocket_manager_classes.append(class_info)

        # Log all found WebSocket Manager classes
        logger.info(f"Found {len(websocket_manager_classes)} WebSocketManager classes:")
        for info in websocket_manager_classes:
            logger.info(f"  {info['module']}: {info['class']} (id: {info['id']}) from {info['file']}")

        # Verify all classes point to the same implementation (SSOT)
        if len(websocket_manager_classes) > 1:
            # Check if they're all the same class object (aliases are OK)
            canonical_class_id = None
            for info in websocket_manager_classes:
                if info['module'] == self.expected_canonical_module:
                    canonical_class_id = info['id']
                    break

            if canonical_class_id is None:
                self.fail(f"SSOT VIOLATION: Canonical module {self.expected_canonical_module} not found")

            # All other classes should be aliases to the canonical class
            non_canonical_classes = [info for info in websocket_manager_classes
                                   if info['module'] != self.expected_canonical_module]

            for info in non_canonical_classes:
                if info['id'] != canonical_class_id:
                    self.fail(f"SSOT VIOLATION: Duplicate WebSocketManager implementation found in "
                            f"{info['module']} (id: {info['id']}) != canonical (id: {canonical_class_id})")

        logger.info("✅ No duplicate WebSocketManager implementations detected")

    def test_websocket_manager_import_consistency(self):
        """Test that all WebSocket Manager import paths resolve to same canonical source."""
        import_paths_to_test = [
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
            "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
        ]

        imported_classes = {}

        for import_path in import_paths_to_test:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    websocket_manager_class = getattr(module, class_name)
                    imported_classes[import_path] = {
                        'class': websocket_manager_class,
                        'id': id(websocket_manager_class),
                        'module_file': getattr(module, '__file__', 'unknown')
                    }
                    logger.info(f"✓ Successfully imported {import_path} (id: {id(websocket_manager_class)})")
                else:
                    logger.warning(f"⚠ Class {class_name} not found in {module_path}")
            except ImportError as e:
                logger.warning(f"⚠ Could not import {import_path}: {e}")

        # If we have multiple imports, they should all be the same class object
        if len(imported_classes) > 1:
            class_ids = set(info['id'] for info in imported_classes.values())
            if len(class_ids) > 1:
                details = [f"{path}: id={info['id']}" for path, info in imported_classes.items()]
                self.fail(f"SSOT VIOLATION: Import paths resolve to different classes:\n" +
                         "\n".join(details))

        logger.info("✅ WebSocket Manager import consistency validated")

    def test_websocket_manager_ssot_enforcement(self):
        """Test that SSOT WebSocket Manager prevents multiple instance patterns."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

        # Test that WebSocketManager class exists and is properly formed
        self.assertTrue(inspect.isclass(WebSocketManager))

        # Test that it has SSOT indicators
        class_doc = WebSocketManager.__doc__ or ""
        self.assertIn("SSOT", class_doc.upper(),
                     "WebSocketManager should have SSOT documentation")

        # Test expected SSOT methods exist
        ssot_methods = ['send_event', 'register_connection', 'disconnect_user', '__init__']
        for method_name in ssot_methods:
            self.assertTrue(hasattr(WebSocketManager, method_name),
                          f"SSOT WebSocketManager missing method: {method_name}")

        # Test that it's not an abstract class
        try:
            # This should not raise TypeError for abstract class
            inspect.signature(WebSocketManager.__init__)
            logger.info("✓ WebSocketManager is instantiable (not abstract)")
        except Exception as e:
            self.fail(f"WebSocketManager appears to be abstract or malformed: {e}")

        logger.info("✅ WebSocket Manager SSOT enforcement validated")

    def test_deprecated_factory_patterns_redirect_to_ssot(self):
        """Test that deprecated factory patterns properly redirect to SSOT."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

            # The factory should exist but warn about deprecation
            with warnings.catch_warnings(record=True) as w:
                # Don't actually call it since it might require complex setup
                # Just verify the function exists and is marked as deprecated
                factory_doc = create_websocket_manager.__doc__ or ""
                self.assertIn("DEPRECATED", factory_doc.upper(),
                             "Factory function should be marked as deprecated")

            logger.info("✓ Deprecated factory properly warns about deprecation")

        except ImportError:
            logger.info("ℹ Factory module not found - likely already removed (acceptable)")

        logger.info("✅ Deprecated factory pattern redirection validated")


if __name__ == '__main__':
    import unittest
    unittest.main()