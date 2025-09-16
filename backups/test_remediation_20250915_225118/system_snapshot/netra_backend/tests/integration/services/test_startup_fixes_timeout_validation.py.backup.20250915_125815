"""Integration tests for startup_fixes_integration background task timeout validation.

**Issue #573**: Background task timeout configuration missing
**Purpose**: Test the complete startup validation flow for background task timeout configuration
**Expected**: These tests should FAIL initially to prove the issue exists

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure  
- Business Goal: System Reliability & Startup Validation
- Value Impact: Ensures proper background task timeout configuration during system startup
- Revenue Impact: Prevents configuration gaps that could affect background processing reliability
"""

import unittest
import asyncio
import time
import logging
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import system under test
from netra_backend.app.services.startup_fixes_integration import StartupFixesIntegration
from netra_backend.app.services.background_task_manager import BackgroundTaskManager
from netra_backend.app.services.secure_background_task_manager import SecureBackgroundTaskManager

# Test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestStartupFixesTimeoutValidation(SSotBaseTestCase):
    """Test startup validation of background task timeout configuration.
    
    **CRITICAL TESTS**: These tests MUST FAIL initially to prove Issue #573 exists.
    The expected failures demonstrate the timeout configuration validation gap.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.startup_fixes = StartupFixesIntegration()
        
    def test_background_task_timeout_validation_finds_missing_config(self):
        """Test that startup validation detects missing DEFAULT_TIMEOUT configuration.
        
        **EXPECTED TO FAIL**: startup_fixes_integration should detect missing DEFAULT_TIMEOUT
        and log warnings, but the current test should fail because the validation
        doesn't properly handle the missing configuration.
        """
        # This test simulates the exact validation logic from startup_fixes_integration.py
        status = {
            "background_task_manager_available": False,
            "default_timeout_configured": False,
            "timeout_acceptable": False,
            "timeout_seconds": None
        }
        
        # Test the actual validation logic
        try:
            from netra_backend.app.services.background_task_manager import BackgroundTaskManager as manager_class
            status["background_task_manager_available"] = True
            
            # This is the exact logic from startup_fixes_integration.py lines 330-339
            if hasattr(manager_class, 'DEFAULT_TIMEOUT'):
                default_timeout = getattr(manager_class, 'DEFAULT_TIMEOUT')
                status["timeout_seconds"] = default_timeout
                status["default_timeout_configured"] = True
                status["timeout_acceptable"] = default_timeout <= 120
            else:
                # This is where the warning is logged in the actual code
                status["timeout_validation_warning"] = "Background task manager has no timeout configuration"
                
        except ImportError:
            status["import_error"] = "Background task manager not available for import"
            
        # EXPECTED FAILURE: DEFAULT_TIMEOUT should be configured but isn't
        self.assertTrue(
            status["background_task_manager_available"],
            "BackgroundTaskManager should be available for import"
        )
        
        # This should FAIL - no DEFAULT_TIMEOUT configuration exists
        self.assertTrue(
            status["default_timeout_configured"],
            f"BackgroundTaskManager should have DEFAULT_TIMEOUT configured - Issue #573. Status: {status}"
        )
        
    def test_startup_fixes_integration_background_task_validation_complete(self):
        """Test complete background task validation flow in StartupFixesIntegration.
        
        **EXPECTED TO FAIL**: The validation should detect missing timeout configuration
        and the test should fail because the issue exists.
        """
        # Run the actual background task validation
        with patch('logging.Logger.warning') as mock_warning:
            # This should trigger the validation logic
            # We need to call the specific method that validates background tasks
            validation_result = self._simulate_background_task_validation()
            
            # EXPECTED FAILURE: Validation should fail due to missing DEFAULT_TIMEOUT
            self.assertTrue(
                validation_result.get("default_timeout_configured", False),
                f"Background task timeout should be configured - Issue #573. Result: {validation_result}"
            )
            
            # Verify that no warnings were logged (should fail initially)
            self.assertEqual(
                mock_warning.call_count, 0,
                "No timeout configuration warnings should be logged if properly configured"
            )
            
    def _simulate_background_task_validation(self) -> Dict[str, Any]:
        """Simulate the background task validation logic from startup_fixes_integration.py.
        
        This replicates the exact validation logic to test the current behavior.
        """
        status = {
            "background_task_manager_available": False,
            "default_timeout_configured": False,
            "timeout_acceptable": False,
            "timeout_seconds": None
        }
        
        start_time = time.time()
        
        try:
            # Import both manager classes to test both
            from netra_backend.app.services.background_task_manager import BackgroundTaskManager
            from netra_backend.app.services.secure_background_task_manager import SecureBackgroundTaskManager
            
            status["background_task_manager_available"] = True
            
            for manager_name, manager_class in [
                ("BackgroundTaskManager", BackgroundTaskManager),
                ("SecureBackgroundTaskManager", SecureBackgroundTaskManager)
            ]:
                # This replicates the exact logic from startup_fixes_integration.py
                if hasattr(manager_class, 'DEFAULT_TIMEOUT'):
                    default_timeout = getattr(manager_class, 'DEFAULT_TIMEOUT')
                    status[f"{manager_name}_timeout_seconds"] = default_timeout
                    status["default_timeout_configured"] = True
                    status["timeout_acceptable"] = default_timeout <= 120
                    logging.info(f"{manager_name} using class default timeout: {default_timeout}s")
                else:
                    logging.warning(f"{manager_name} has no timeout configuration")
                    status[f"{manager_name}_missing_timeout"] = True
                    
        except ImportError as e:
            logging.warning(f"Background task manager not available for import: {e}")
            status["import_error"] = str(e)
            
        status["validation_duration"] = time.time() - start_time
        status["validation_success"] = (
            status["background_task_manager_available"] and (
                status["default_timeout_configured"] and status["timeout_acceptable"]
                or not status["default_timeout_configured"]  # Accept if no timeout is explicitly set
            )
        )
        
        return status
        
    def test_secure_background_task_manager_timeout_validation(self):
        """Test timeout validation for SecureBackgroundTaskManager specifically.
        
        **EXPECTED TO FAIL**: SecureBackgroundTaskManager also lacks DEFAULT_TIMEOUT.
        """
        from netra_backend.app.services.secure_background_task_manager import SecureBackgroundTaskManager
        
        # Test the same validation logic for SecureBackgroundTaskManager
        has_default_timeout = hasattr(SecureBackgroundTaskManager, 'DEFAULT_TIMEOUT')
        
        # This should FAIL - SecureBackgroundTaskManager has no DEFAULT_TIMEOUT
        self.assertTrue(
            has_default_timeout,
            "SecureBackgroundTaskManager should have DEFAULT_TIMEOUT for startup validation - Issue #573"
        )
        
        if has_default_timeout:
            default_timeout = getattr(SecureBackgroundTaskManager, 'DEFAULT_TIMEOUT')
            timeout_acceptable = default_timeout <= 120
            
            self.assertTrue(
                timeout_acceptable,
                f"SecureBackgroundTaskManager DEFAULT_TIMEOUT {default_timeout}s exceeds 120s limit"
            )
            
    def test_timeout_configuration_consistency_between_managers(self):
        """Test that both manager classes have consistent timeout configuration.
        
        **EXPECTED TO FAIL**: Neither manager has DEFAULT_TIMEOUT, so consistency cannot be verified.
        """
        from netra_backend.app.services.background_task_manager import BackgroundTaskManager
        from netra_backend.app.services.secure_background_task_manager import SecureBackgroundTaskManager
        
        bg_has_timeout = hasattr(BackgroundTaskManager, 'DEFAULT_TIMEOUT')
        secure_has_timeout = hasattr(SecureBackgroundTaskManager, 'DEFAULT_TIMEOUT')
        
        # Both should have timeout configuration for consistency
        self.assertTrue(bg_has_timeout, "BackgroundTaskManager missing DEFAULT_TIMEOUT - Issue #573")
        self.assertTrue(secure_has_timeout, "SecureBackgroundTaskManager missing DEFAULT_TIMEOUT - Issue #573")
        
        # If both have timeouts, they should be consistent
        if bg_has_timeout and secure_has_timeout:
            bg_timeout = getattr(BackgroundTaskManager, 'DEFAULT_TIMEOUT')
            secure_timeout = getattr(SecureBackgroundTaskManager, 'DEFAULT_TIMEOUT')
            
            self.assertEqual(
                bg_timeout, secure_timeout,
                f"Manager timeout values should be consistent: {bg_timeout}s vs {secure_timeout}s"
            )
            
    def test_startup_fixes_integration_logs_expected_warnings(self):
        """Test that StartupFixesIntegration logs appropriate warnings for missing config.
        
        **EXPECTED BEHAVIOR**: This test should pass initially, confirming that warnings
        are logged when DEFAULT_TIMEOUT is missing, which proves the issue exists.
        """
        with patch('logging.Logger.warning') as mock_warning:
            # Run the validation
            validation_result = self._simulate_background_task_validation()
            
            # We expect warnings to be logged for missing timeout configuration
            warning_calls = [str(call) for call in mock_warning.call_args_list]
            
            # This should PASS - warnings should be logged for missing config
            timeout_warning_logged = any(
                "has no timeout configuration" in str(call) 
                for call in warning_calls
            )
            
            self.assertTrue(
                timeout_warning_logged,
                f"Expected timeout configuration warning to be logged. Warning calls: {warning_calls}"
            )


if __name__ == '__main__':
    unittest.main()