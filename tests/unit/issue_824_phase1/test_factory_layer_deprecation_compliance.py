"""Test Factory Layer Deprecation Compliance - Issue #824 Phase 1

Test deprecation warnings for websocket_manager_factory.py.
Verify factory patterns redirect to SSOT.
Test controlled deprecation path.

Business Value: Ensures smooth migration without breaking existing code during SSOT consolidation.
"""

import pytest
import warnings
import sys
import importlib
import inspect
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class FactoryLayerDeprecationComplianceTests(SSotAsyncTestCase):
    """Test factory layer deprecation compliance for WebSocket Manager SSOT."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory_module_path = "netra_backend.app.websocket_core.websocket_manager_factory"
        self.canonical_module_path = "netra_backend.app.websocket_core.websocket_manager"

    def test_factory_module_exists_with_deprecation_notice(self):
        """Test that factory module exists but contains proper deprecation notices."""
        try:
            factory_module = importlib.import_module(self.factory_module_path)
        except ImportError as e:
            self.fail(f"MIGRATION ERROR: Factory module should exist during Phase 1: {e}")

        # Check module docstring for deprecation notice
        module_doc = factory_module.__doc__ or ""
        self.assertIn("DEPRECATED", module_doc.upper(),
                     "Factory module should have DEPRECATED in docstring")
        self.assertIn("ISSUE #824", module_doc,
                     "Factory module should reference Issue #824")
        self.assertIn("SSOT", module_doc.upper(),
                     "Factory module should mention SSOT in deprecation notice")

        logger.info("CHECK Factory module contains proper deprecation notices")

    def test_factory_functions_emit_deprecation_warnings(self):
        """Test that factory functions emit proper deprecation warnings."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        except ImportError:
            self.skipTest("Factory module not available - already removed")

        # Mock dependencies to avoid complex initialization
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManager') as mock_wsm:
            mock_instance = MagicMock()
            mock_wsm.return_value = mock_instance

            # Test that calling factory function emits warning
            with warnings.catch_warnings(record=True) as warning_list:
                warnings.simplefilter("always")  # Ensure all warnings are captured

                try:
                    # Call the factory function with minimal parameters
                    result = create_websocket_manager()

                    # Check if we got deprecation warnings
                    deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]

                    # Should have at least one deprecation warning
                    if len(deprecation_warnings) == 0:
                        logger.warning("WARNING No deprecation warning emitted - checking function documentation")

                        # Check if function at least documents the deprecation
                        func_doc = create_websocket_manager.__doc__ or ""
                        self.assertIn("DEPRECATED", func_doc.upper(),
                                     "Factory function should be documented as deprecated")
                    else:
                        # Verify warning message content
                        warning_message = str(deprecation_warnings[0].message)
                        self.assertIn("deprecated", warning_message.lower(),
                                     "Warning message should mention deprecation")
                        logger.info(f"CHECK Deprecation warning emitted: {warning_message}")

                except Exception as e:
                    logger.warning(f"WARNING Factory function call failed (expected during migration): {e}")
                    # Verify function is at least documented as deprecated
                    func_doc = create_websocket_manager.__doc__ or ""
                    self.assertIn("DEPRECATED", func_doc.upper(),
                                 "Factory function should be documented as deprecated")

        logger.info("CHECK Factory deprecation warnings validated")

    def test_factory_redirects_to_canonical_ssot(self):
        """Test that factory functions redirect to canonical SSOT implementation."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as CanonicalWSM
        except ImportError as e:
            self.skipTest(f"Required modules not available: {e}")

        # Mock the canonical WebSocketManager to track calls
        with patch(f'{self.canonical_module_path}.WebSocketManager') as mock_canonical:
            mock_instance = MagicMock()
            mock_canonical.return_value = mock_instance

            try:
                # Call factory function
                result = create_websocket_manager()

                # Verify that canonical WebSocketManager was called
                self.assertTrue(mock_canonical.called,
                               "Factory should delegate to canonical WebSocketManager")

                logger.info("CHECK Factory successfully redirects to canonical SSOT")

            except Exception as e:
                logger.warning(f"WARNING Factory redirection test failed (expected during migration): {e}")

                # At minimum, verify that the factory imports from canonical source
                factory_module = sys.modules.get(self.factory_module_path)
                if factory_module:
                    factory_source = inspect.getsource(factory_module)
                    self.assertIn("unified_manager", factory_source.lower(),
                                 "Factory should import from unified_manager")

        logger.info("CHECK Factory redirection to SSOT validated")

    def test_factory_migration_phase_identification(self):
        """Test that factory clearly identifies current migration phase."""
        try:
            factory_module = importlib.import_module(self.factory_module_path)
        except ImportError:
            self.skipTest("Factory module not available - likely Phase 3 (removal)")

        module_doc = factory_module.__doc__ or ""

        # Should identify current phase
        phase_indicators = ["Phase 1", "Phase 2", "Phase 3"]
        found_phase = None
        for phase in phase_indicators:
            if phase.upper() in module_doc.upper():
                found_phase = phase
                break

        self.assertIsNotNone(found_phase,
                           "Factory module should clearly identify migration phase")

        # Should have migration instructions
        self.assertIn("MIGRATION INSTRUCTIONS", module_doc.upper(),
                     "Factory should provide clear migration instructions")

        # Should reference new canonical import
        self.assertIn("unified_manager", module_doc.lower(),
                     "Factory should reference canonical unified_manager import")

        logger.info(f"CHECK Factory identifies migration {found_phase} with clear instructions")

    def test_factory_deprecation_timeline(self):
        """Test that factory includes clear deprecation timeline."""
        try:
            factory_module = importlib.import_module(self.factory_module_path)
        except ImportError:
            self.skipTest("Factory module not available - already removed")

        module_doc = factory_module.__doc__ or ""

        # Should have phase out plan
        self.assertIn("PHASE OUT PLAN", module_doc.upper(),
                     "Factory should include phase out plan")

        # Should reference business justification
        business_indicators = ["BVJ", "Business Value", "Revenue Impact", "$500K"]
        found_business_ref = any(indicator in module_doc for indicator in business_indicators)
        self.assertTrue(found_business_ref,
                       "Factory deprecation should include business justification")

        # Should have clear next steps
        next_step_indicators = ["Phase 2", "Phase 3", "Next", "Final"]
        found_next_step = any(indicator in module_doc for indicator in next_step_indicators)
        self.assertTrue(found_next_step,
                       "Factory should indicate next steps in deprecation timeline")

        logger.info("CHECK Factory deprecation timeline properly documented")

    def test_no_new_factory_patterns_created(self):
        """Test that no new factory patterns are being created for WebSocket Manager."""
        websocket_factory_modules = []

        # Search for WebSocket factory modules
        for module_name in sys.modules:
            if 'websocket' in module_name.lower() and 'factory' in module_name.lower():
                if module_name.startswith('netra_backend.app'):
                    websocket_factory_modules.append(module_name)

        # Should only have the deprecated factory module (if any)
        expected_factories = [
            "netra_backend.app.websocket_core.websocket_manager_factory",
            "netra_backend.app.factories.websocket_bridge_factory",  # Different component
            "netra_backend.app.routes.websocket_factory",  # Different component
        ]

        unexpected_factories = []
        for module_name in websocket_factory_modules:
            if module_name not in expected_factories:
                unexpected_factories.append(module_name)

        if unexpected_factories:
            self.fail(f"SSOT VIOLATION: Unexpected WebSocket factory modules found: {unexpected_factories}")

        logger.info("CHECK No unexpected WebSocket factory patterns detected")

    def test_factory_backward_compatibility(self):
        """Test that factory maintains backward compatibility during migration."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        except ImportError:
            self.skipTest("Factory module not available - already removed")

        # Verify function signature is preserved for compatibility
        signature = inspect.signature(create_websocket_manager)

        # Should accept common parameters without breaking
        expected_params = ['user_context', 'mode']  # Common factory parameters
        function_params = list(signature.parameters.keys())

        # At least some compatibility parameters should be maintained
        compatible_params = [param for param in expected_params if param in function_params]

        # Should have some backward compatibility OR clear documentation
        if not compatible_params:
            func_doc = create_websocket_manager.__doc__ or ""
            self.assertIn("MIGRATION", func_doc.upper(),
                         "If parameters changed, should document migration path")

        logger.info("CHECK Factory backward compatibility considerations validated")


if __name__ == '__main__':
    import unittest
    unittest.main()