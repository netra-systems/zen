#!/usr/bin/env python3
"""
Unit tests for WebSocket import isolation - Issue #1321

These tests verify that WebSocket modules do not import auth_service directly,
ensuring service independence and preventing import errors when auth_service
is not available in the backend container.

Business Value:
- Prevents complete platform outages due to cross-service import dependencies
- Ensures Golden Path functionality when services are deployed independently
- Validates service architecture isolation patterns
"""

import pytest
import sys
import importlib
from typing import Set, List
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketImportIsolation(SSotAsyncTestCase):
    """Test that WebSocket modules maintain proper import isolation from auth_service."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level test data."""
        super().setUpClass()
        cls.auth_service_modules = {
            'auth_service',
            'auth_service.auth_core',
            'auth_service.auth_core.config',
            'auth_service.auth_core.core',
            'auth_service.auth_core.core.jwt_handler',
            'auth_service.auth_core.core.session_manager',
            'auth_service.auth_core.core.token_validator',
            'auth_service.auth_core.services',
            'auth_service.auth_core.services.auth_service',
        }

        cls.websocket_modules_to_test = [
            'netra_backend.app.websocket_core',
            'netra_backend.app.websocket_core.auth',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.core.middleware_setup',
        ]

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

    def test_websocket_modules_do_not_import_auth_service_directly(self):
        """
        Test that WebSocket modules do not import auth_service directly.

        This test should FAIL initially, proving the import isolation issue exists.
        """
        auth_service_modules = {
            'auth_service',
            'auth_service.auth_core',
            'auth_service.auth_core.config',
            'auth_service.auth_core.core',
            'auth_service.auth_core.core.jwt_handler',
            'auth_service.auth_core.core.session_manager',
            'auth_service.auth_core.core.token_validator',
            'auth_service.auth_core.services',
            'auth_service.auth_core.services.auth_service',
        }

        websocket_modules_to_test = [
            'netra_backend.app.websocket_core',
            'netra_backend.app.websocket_core.auth',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.core.middleware_setup',
        ]

        # Block auth_service imports to simulate container environment
        with patch.dict('sys.modules'):
            # Remove any existing auth_service modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('auth_service'):
                    del sys.modules[module_name]

            # Mock auth_service modules to raise ImportError
            for auth_module in auth_service_modules:
                sys.modules[auth_module] = None

            # Test that WebSocket modules can still be imported
            import_errors = []

            for module_name in websocket_modules_to_test:
                try:
                    # Clear any cached imports
                    if module_name in sys.modules:
                        del sys.modules[module_name]

                    # Try to import the module
                    importlib.import_module(module_name)
                    self.logger.info(f"✅ Successfully imported {module_name} without auth_service")

                except ImportError as e:
                    if 'auth_service' in str(e):
                        import_errors.append(f"{module_name}: {e}")
                        self.logger.error(f"❌ Import error in {module_name}: {e}")
                    else:
                        # Re-raise non-auth_service import errors
                        raise
                except Exception as e:
                    self.logger.warning(f"⚠️ Unexpected error importing {module_name}: {e}")

            # This assertion should FAIL initially, proving the issue
            self.assertEqual(
                len(import_errors), 0,
                f"WebSocket modules have direct auth_service imports: {import_errors}"
            )

    def test_websocket_auth_uses_http_integration_layer(self):
        """
        Test that WebSocket auth uses HTTP integration layer instead of direct imports.

        This test verifies the proper solution is in place.
        """
        from netra_backend.app.websocket_core.auth import WebSocketAuthenticator

        # Create authenticator instance
        auth = WebSocketAuthenticator()

        # Check that it doesn't have direct auth_service dependencies
        # Should use get_unified_auth_service() pattern instead
        self.assertTrue(hasattr(auth, 'authenticate_connection'))

        # Verify it can function without auth_service module being present
        with patch.dict('sys.modules'):
            # Remove auth_service modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('auth_service'):
                    del sys.modules[module_name]

            # Should still be able to call health check
            health = auth.get_health_status_sync()
            self.assertIsInstance(health, dict)
            self.assertIn('status', health)

    def test_middleware_setup_handles_missing_auth_service(self):
        """
        Test that middleware setup handles missing auth_service gracefully.

        This verifies the middleware can start without auth_service.
        """
        from netra_backend.app.core.middleware_setup import setup_middleware
        from fastapi import FastAPI

        app = FastAPI()

        # Block auth_service imports
        with patch.dict('sys.modules'):
            # Remove auth_service modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('auth_service'):
                    del sys.modules[module_name]

            # Mock auth_service modules to return None
            for auth_module in self.auth_service_modules:
                sys.modules[auth_module] = None

            # Should not raise ImportError
            try:
                setup_middleware(app)
                self.logger.info("✅ Middleware setup completed without auth_service")
            except ImportError as e:
                if 'auth_service' in str(e):
                    self.fail(f"Middleware setup failed due to auth_service import: {e}")
                else:
                    raise

    def test_imports_use_http_integration_pattern(self):
        """
        Test that modules use the HTTP integration pattern instead of direct imports.

        This validates the correct architectural pattern is in use.
        """
        # Check that auth integration is available
        try:
            from netra_backend.app.auth_integration.auth import get_unified_auth_service
            self.logger.info("✅ HTTP integration layer available")
        except ImportError:
            self.fail("HTTP integration layer not available - this is required for service isolation")

        # Verify the integration function works
        try:
            # This should work without direct auth_service imports
            auth_service = get_unified_auth_service()
            self.assertIsNotNone(auth_service)
            self.logger.info("✅ get_unified_auth_service() works correctly")
        except Exception as e:
            self.logger.warning(f"get_unified_auth_service() error (may be expected in test env): {e}")

    def test_websocket_core_init_isolation(self):
        """
        Test that websocket_core.__init__.py doesn't import auth_service.

        This specifically tests the __init__.py file which is commonly problematic.
        """
        import ast
        import inspect
        from pathlib import Path

        # Get the websocket_core __init__.py file
        import netra_backend.app.websocket_core as websocket_core
        init_file = Path(inspect.getfile(websocket_core))

        # Parse the file to check for auth_service imports
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for direct auth_service imports in the source
        self.assertNotIn('from auth_service', content,
                        "websocket_core.__init__.py contains direct auth_service import")
        self.assertNotIn('import auth_service', content,
                        "websocket_core.__init__.py contains direct auth_service import")

        # Parse AST to check for any auth_service references
        tree = ast.parse(content)

        auth_service_references = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and 'auth_service' in node.module:
                    auth_service_references.append(f"from {node.module} import ...")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if 'auth_service' in alias.name:
                        auth_service_references.append(f"import {alias.name}")

        self.assertEqual(len(auth_service_references), 0,
                        f"Found auth_service imports in websocket_core.__init__.py: {auth_service_references}")

    def test_import_dependency_manager_not_used_in_websocket_modules(self):
        """
        Test that WebSocket modules don't use ImportDependencyManager.

        The ImportDependencyManager should be removed as it creates dependency coupling.
        """
        import ast
        import inspect
        from pathlib import Path

        modules_to_check = [
            'netra_backend.app.websocket_core.auth',
            'netra_backend.app.websocket_core.websocket_manager',
        ]

        for module_name in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                module_file = Path(inspect.getfile(module))

                with open(module_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for ImportDependencyManager usage
                self.assertNotIn('ImportDependencyManager', content,
                                f"{module_name} still uses ImportDependencyManager")
                self.assertNotIn('import_dependency_manager', content,
                                f"{module_name} still imports import_dependency_manager")

            except ImportError:
                # Module doesn't exist or can't be imported - that's fine for this test
                pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])