#!/usr/bin/env python3
"""
Test Issue #642: GCP Authentication Module Dev_launcher Import Warnings in Production

ISSUE DESCRIPTION:
- In production GCP environments, test modules with direct dev_launcher imports fail
- dev_launcher is not available in production builds/deployments
- This results in inappropriate import failures and potential WARNING logs
- Production code should gracefully handle missing dev_launcher dependencies

REPRODUCTION STRATEGY:
- Simulate production environment where dev_launcher is unavailable
- Test that direct imports of dev_launcher modules fail appropriately
- Test that authentication modules handle missing dev_launcher gracefully
- Demonstrate the need for conditional imports or proper fallbacks

EXPECTED TEST BEHAVIOR:
- Tests should FAIL initially (demonstrating the issue exists)
- After remediation, tests should PASS (proving the issue is fixed)

Business Value: Platform/Stability - Clean production logs, proper fallback behavior
"""

import pytest
import sys
import os
import logging
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the modules that potentially have dev_launcher import issues
from netra_backend.app.auth import UnifiedAuthenticationService
from shared.isolated_environment import IsolatedEnvironment

# Module logger for test output
logger = logging.getLogger(__name__)


class TestIssue642DevLauncherImportWarnings(SSotBaseTestCase):
    """
    Test suite to reproduce and validate Issue #642 dev_launcher import warnings.
    
    These tests simulate production environment conditions where dev_launcher
    modules are unavailable and should demonstrate inappropriate WARNING logs.
    """
    
    def setUp(self):
        """Set up test environment with production-like conditions."""
        super().setUp()
        
        # Set up test environment to simulate production
        self._env = IsolatedEnvironment()
        self._env.set("ENVIRONMENT", "production", "test")
        self._env.set("GCP_PROJECT", "netra-production", "test") 
        
        # Create a temporary log file to capture warnings
        self.log_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log')
        
        # Set up logging capture
        self.log_handler = logging.FileHandler(self.log_file.name)
        self.log_handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        self.log_handler.setFormatter(formatter)
        
        # Add handler to relevant loggers
        self.auth_logger = logging.getLogger('netra_backend.app.auth')
        self.auth_logger.addHandler(self.log_handler)
        self.auth_logger.setLevel(logging.WARNING)
        
    def tearDown(self):
        """Clean up test resources."""
        # Clean up logging
        if hasattr(self, 'auth_logger'):
            self.auth_logger.removeHandler(self.log_handler)
        if hasattr(self, 'log_handler'):
            self.log_handler.close()
        
        # Clean up temp file
        if hasattr(self, 'log_file'):
            self.log_file.close()
            try:
                os.unlink(self.log_file.name)
            except OSError:
                pass
                
        super().tearDown()
        
    def _simulate_dev_launcher_unavailable(self):
        """
        Simulate production environment where dev_launcher is unavailable.
        
        This patches sys.modules to make dev_launcher imports fail,
        mimicking what happens in production GCP deployments.
        """
        # Remove any existing dev_launcher modules from sys.modules
        modules_to_remove = [mod for mod in sys.modules.keys() if mod.startswith('dev_launcher')]
        for module in modules_to_remove:
            del sys.modules[module]
        
        # Get the correct __import__ function
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name.startswith('dev_launcher'):
                raise ImportError(f"No module named '{name}' (simulating production environment)")
            return original_import(name, *args, **kwargs)
        
        return patch('builtins.__import__', side_effect=mock_import)
        
    def _get_log_content(self) -> str:
        """Get content from the log file."""
        self.log_handler.flush()
        self.log_file.flush()
        with open(self.log_file.name, 'r') as f:
            return f.read()

    def test_auth_module_dev_launcher_import_warnings(self):
        """
        Test that auth module handles missing dev_launcher gracefully without warnings.
        
        EXPECTED TO FAIL INITIALLY: This test should fail, demonstrating the issue.
        The auth module should work without generating dev_launcher import warnings.
        """
        with self._simulate_dev_launcher_unavailable():
            # Attempt to use auth module functionality that might trigger dev_launcher imports
            try:
                auth_service = UnifiedAuthenticationService()
                
                # Test basic functionality without dev_launcher
                stats = auth_service.get_authentication_stats()
                self.assertIsInstance(stats, dict)
                logger.info("Auth service basic functionality works without dev_launcher")
                
            except Exception as e:
                # We expect some functionality to work even without dev_launcher
                logger.info(f"Auth service exception (expected): {e}")
        
        # Check for inappropriate WARNING logs
        log_content = self._get_log_content()
        logger.info(f"Captured log content: {log_content}")
        
        # THIS ASSERTION SHOULD FAIL INITIALLY, proving the issue exists
        # In the broken state, we expect to see dev_launcher import warnings
        dev_launcher_warnings = [line for line in log_content.split('\n') 
                                if 'WARNING' in line and 'dev_launcher' in line]
        
        # ISSUE #642: These warnings should NOT appear in production
        # Test fails if warnings are found (proving the issue exists)
        self.assertEqual(len(dev_launcher_warnings), 0, 
                        f"Found inappropriate dev_launcher WARNING logs in production: {dev_launcher_warnings}")

    def test_database_test_modules_dev_launcher_imports(self):
        """
        Test database test modules that directly import dev_launcher.
        
        EXPECTED TO FAIL INITIALLY: Demonstrates that test modules inappropriately
        depend on dev_launcher, causing import failures in production-like environments.
        """
        with self._simulate_dev_launcher_unavailable():
            # Test that importing a module with direct dev_launcher dependency fails
            import_failed = False
            error_message = ""
            
            try:
                # This should fail because the module has: from dev_launcher.database_connector import DatabaseConnector
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "test_redis_connection_python312", 
                    "netra_backend/tests/database/test_redis_connection_python312.py"
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            except ImportError as e:
                import_failed = True
                error_message = str(e)
                logger.info(f"Import failed as expected: {e}")
            
            # This test demonstrates the issue - the import fails
            self.assertTrue(import_failed, "Import should fail when dev_launcher is unavailable")
            self.assertIn("dev_launcher", error_message, "Error should mention dev_launcher")
            
        log_content = self._get_log_content()
        
        # Check if any WARNING logs were generated during the failed import
        warning_logs = [line for line in log_content.split('\n') if 'WARNING' in line]
        
        # Issue #642: We shouldn't get WARNING logs for missing dev_launcher in production
        dev_launcher_warnings = [log for log in warning_logs if 'dev_launcher' in log]
        self.assertEqual(len(dev_launcher_warnings), 0,
                        f"Production should not generate dev_launcher warnings: {dev_launcher_warnings}")

    def test_production_environment_fallback_behavior(self):
        """
        Test that production environments handle missing dev_launcher gracefully.
        
        EXPECTED TO FAIL INITIALLY: Production code should gracefully handle missing
        dev_launcher without generating WARNING logs.
        """
        with self._simulate_dev_launcher_unavailable():
            # Test that core authentication functionality works without dev_launcher
            auth_service = UnifiedAuthenticationService()
            
            # Basic functionality should work even without dev_launcher
            self.assertIsNotNone(auth_service)
            
            # Test some basic method that shouldn't depend on dev_launcher
            try:
                # This should work in production without dev_launcher
                result = auth_service.is_initialized
                self.assertIsInstance(result, bool)
            except Exception as e:
                self.fail(f"Basic auth functionality failed without dev_launcher: {e}")
        
        log_content = self._get_log_content()
        
        # Issue #642: No WARNING logs should be generated for missing dev_launcher
        warning_lines = [line for line in log_content.split('\n') if 'WARNING' in line]
        dev_launcher_warnings = [line for line in warning_lines if 'dev_launcher' in line]
        
        self.assertEqual(len(dev_launcher_warnings), 0,
                        f"Production fallback generated inappropriate warnings: {dev_launcher_warnings}")

    def test_gcp_cloud_run_environment_simulation(self):
        """
        Test that simulates GCP Cloud Run environment where dev_launcher is unavailable.
        
        EXPECTED TO FAIL INITIALLY: In Cloud Run, dev_launcher won't be available,
        but the system should handle this gracefully without WARNING logs.
        """
        # Set up Cloud Run-like environment variables
        self._env.set("GAE_ENV", "standard", "test")
        self._env.set("GOOGLE_CLOUD_PROJECT", "netra-production", "test")
        self._env.set("K_SERVICE", "netra-backend", "test")
        
        with self._simulate_dev_launcher_unavailable():
            try:
                # Test authentication module initialization in Cloud Run environment
                auth_service = UnifiedAuthenticationService()
                
                # Core functionality should work
                self.assertIsNotNone(auth_service)
                
            except ImportError as e:
                if 'dev_launcher' in str(e):
                    self.fail(f"Cloud Run environment shouldn't depend on dev_launcher: {e}")
                else:
                    raise  # Re-raise if it's a different import error
        
        log_content = self._get_log_content()
        
        # Critical: Cloud Run environments should not generate dev_launcher warnings
        all_logs = log_content.split('\n')
        dev_launcher_logs = [line for line in all_logs if 'dev_launcher' in line and 'WARNING' in line]
        
        self.assertEqual(len(dev_launcher_logs), 0,
                        f"Cloud Run environment generated dev_launcher warnings: {dev_launcher_logs}")

    def test_log_level_verification_production(self):
        """
        Test that production environment has appropriate log levels.
        
        EXPECTED TO FAIL INITIALLY: Verifies that dev_launcher related logs
        are not appearing at WARNING level in production.
        """
        with self._simulate_dev_launcher_unavailable():
            # Trigger various authentication operations that might cause imports
            try:
                from netra_backend.app.auth import AuthMethodType, SecurityAuditEvent
                
                # Use authentication types (should work without dev_launcher)
                auth_type = AuthMethodType.JWT_BEARER
                self.assertEqual(auth_type.value, "jwt_bearer")
                
                # Create security audit event (should work without dev_launcher)  
                event = SecurityAuditEvent(event_type="test", success=True)
                self.assertEqual(event.event_type, "test")
                
            except ImportError as e:
                if 'dev_launcher' in str(e):
                    self.fail(f"Basic auth types shouldn't depend on dev_launcher: {e}")
        
        log_content = self._get_log_content()
        
        # Parse all log levels
        log_lines = [line.strip() for line in log_content.split('\n') if line.strip()]
        
        # Find any WARNING or ERROR logs related to dev_launcher
        problematic_logs = [line for line in log_lines 
                           if any(level in line for level in ['WARNING', 'ERROR']) 
                           and 'dev_launcher' in line]
        
        # Issue #642: Production should not have dev_launcher related WARNING/ERROR logs
        self.assertEqual(len(problematic_logs), 0,
                        f"Production generated inappropriate dev_launcher logs: {problematic_logs}")


if __name__ == '__main__':
    # Run the tests to demonstrate Issue #642
    pytest.main([__file__, '-v', '-s'])