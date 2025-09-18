"""
Comprehensive import health test for Issue #1318 resolution validation.

Tests all critical import paths to ensure SSOT compliance and verify that
the import issues reported in Issue #1308 are resolved.

Created: 2025-09-17
Issue: #1318 - SSOT violations validation
Related: #1308 - SessionManager import conflicts (now resolved)
"""

import unittest
import importlib
import sys
from typing import List, Tuple


class TestIssue1318ComprehensiveImportHealth(unittest.TestCase):
    """Comprehensive validation that all import issues are resolved."""

    def test_auth_integration_import_chain(self):
        """Test that complete auth integration import chain works."""
        try:
            from netra_backend.app.auth_integration.auth import auth_client
            self.assertIsNotNone(auth_client, "auth_client should be properly initialized")
        except ImportError as e:
            self.fail(f"Auth integration import failed: {e}")

    def test_middleware_import_chain(self):
        """Test that complete middleware import chain works (was failing in Issue #1308)."""
        try:
            from netra_backend.app.middleware import GCPAuthContextMiddleware
            self.assertIsNotNone(GCPAuthContextMiddleware, "GCPAuthContextMiddleware should be importable")
        except ImportError as e:
            self.fail(f"Middleware import chain failed: {e}")

    def test_uvicorn_protocol_enhancement_import(self):
        """Test the specific import that was failing in middleware setup."""
        try:
            from netra_backend.app.middleware.uvicorn_protocol_enhancement import UvicornWebSocketExclusionMiddleware
            self.assertIsNotNone(UvicornWebSocketExclusionMiddleware, "UvicornWebSocketExclusionMiddleware should be importable")
        except ImportError as e:
            self.fail(f"uvicorn_protocol_enhancement import failed: {e}")

    def test_session_manager_ssot_imports(self):
        """Test that all SessionManager imports use SSOT patterns."""
        ssot_sessionmanager_imports = [
            "netra_backend.app.database.session_manager.SessionManager",
            "netra_backend.app.database.session_manager.DatabaseSessionManager",
            "netra_backend.app.core.database.session_manager.SessionManager",
            "netra_backend.app.core.session_manager.SessionManager",
        ]

        for import_path in ssot_sessionmanager_imports:
            with self.subTest(import_path=import_path):
                try:
                    module_path, class_name = import_path.rsplit('.', 1)
                    module = importlib.import_module(module_path)
                    session_class = getattr(module, class_name)
                    self.assertIsNotNone(session_class, f"{class_name} should be available in {module_path}")
                except (ImportError, AttributeError) as e:
                    self.fail(f"SSOT SessionManager import failed for {import_path}: {e}")

    def test_critical_service_imports(self):
        """Test imports for critical services that were mentioned in Issue #1308 errors."""
        critical_imports = [
            "netra_backend.app.clients.auth_client_core.AuthServiceClient",
            "netra_backend.app.models.user_session.UserSessionManager",
            "netra_backend.app.websocket_core.user_session_manager.UserSessionManager",
        ]

        for import_path in critical_imports:
            with self.subTest(import_path=import_path):
                try:
                    module_path, class_name = import_path.rsplit('.', 1)
                    module = importlib.import_module(module_path)
                    service_class = getattr(module, class_name)
                    self.assertIsNotNone(service_class, f"{class_name} should be available in {module_path}")
                except (ImportError, AttributeError) as e:
                    self.fail(f"Critical service import failed for {import_path}: {e}")

    def test_no_circular_import_issues(self):
        """Test that there are no circular import issues in critical modules."""
        # Test critical module combinations that might cause circular imports
        critical_module_combinations = [
            ["netra_backend.app.auth_integration.auth", "netra_backend.app.middleware.gcp_auth_context_middleware"],
            ["netra_backend.app.database.session_manager", "netra_backend.app.models.user_session"],
            ["netra_backend.app.clients.auth_client_core", "netra_backend.app.auth_integration.auth"],
        ]

        for modules in critical_module_combinations:
            with self.subTest(modules=modules):
                try:
                    # Clear modules from cache to test fresh imports
                    for module_name in modules:
                        if module_name in sys.modules:
                            del sys.modules[module_name]

                    # Try importing in both orders
                    importlib.import_module(modules[0])
                    importlib.import_module(modules[1])

                    # And reverse order
                    for module_name in modules:
                        if module_name in sys.modules:
                            del sys.modules[module_name]

                    importlib.import_module(modules[1])
                    importlib.import_module(modules[0])

                except ImportError as e:
                    self.fail(f"Circular import detected between {modules}: {e}")

    def test_startup_import_sequence(self):
        """Test the import sequence that happens during app startup."""
        startup_sequence = [
            "netra_backend.app.core.middleware_setup",
            "netra_backend.app.middleware",
            "netra_backend.app.auth_integration.auth",
            "netra_backend.app.database.session_manager",
        ]

        for module_name in startup_sequence:
            with self.subTest(module=module_name):
                try:
                    importlib.import_module(module_name)
                except ImportError as e:
                    self.fail(f"Startup sequence import failed for {module_name}: {e}")

    def test_environment_independence(self):
        """Test that imports work regardless of environment variables."""
        # Store original environment
        import os
        original_env = dict(os.environ)

        try:
            # Test with minimal environment
            essential_vars = {
                'PYTHONPATH': original_env.get('PYTHONPATH', ''),
            }
            os.environ.clear()
            os.environ.update(essential_vars)

            # Try critical imports with minimal environment
            from netra_backend.app.auth_integration.auth import auth_client
            from netra_backend.app.middleware import GCPAuthContextMiddleware

            self.assertIsNotNone(auth_client)
            self.assertIsNotNone(GCPAuthContextMiddleware)

        except ImportError as e:
            self.fail(f"Import failed with minimal environment: {e}")
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)


if __name__ == '__main__':
    unittest.main()