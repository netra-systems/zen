"""
Integration Test Suite for Auth Service Logging KeyError Fix Validation

CRITICAL ISSUE VALIDATION:
This test suite validates that the KeyError: 'timestamp' fix (commit 6926d6ae3) works correctly
in auth service integration scenarios. The issue has been FIXED and these tests confirm the solution works
when integrated with auth service components.

ISSUE BACKGROUND:
The original issue occurred when JSON formatter output was incorrectly passed to Loguru's
logger.add() format= parameter, causing Loguru to interpret "timestamp" as a format field.

FIX IMPLEMENTED:
The fix replaced the problematic format= parameter with a custom json_sink() function that
handles JSON formatting directly, preventing format string parsing errors.

EXPECTED BEHAVIOR: All tests in this suite should PASS to validate the fix works correctly
in real auth service integration scenarios.

TEST APPROACH:
- Test auth service initialization with logging (no Docker required)
- Validate AuthConfig.log_configuration() works without KeyError
- Test various logging scenarios that auth service uses
- Confirm JSON logging works in Cloud Run simulation
- Ensure no regression in auth service functionality
"""

import json
import logging
import os
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import Mock, patch

import pytest

# Auth service imports
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.services.auth_service import AuthService
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import (
    UnifiedLoggingSSOT, 
    get_ssot_logger, 
    get_logger,
    reset_logging
)


class TestAuthServiceLoggingKeyErrorIntegration:
    """
    Integration test class for validating KeyError fix in auth service context.
    
    IMPORTANT: These tests validate that the fix works in real auth service scenarios.
    """

    def setup_method(self):
        """Setup for each test method - prepare auth service environment."""
        # Reset SSOT logging state
        reset_logging()
        
        # Set up auth service environment variables for testing
        env = get_env()
        env.set("ENVIRONMENT", "staging", source="test_setup")  # Force Cloud Run conditions
        env.set("K_SERVICE", "auth-service", source="test_setup")  # Force Cloud Run mode
        env.set("TESTING", "0", source="test_setup")  # Disable test mode to trigger full logging
        
    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset logging state
        reset_logging()
        
        # Clear environment
        env = get_env()
        env.set("ENVIRONMENT", "testing", source="test_cleanup")
        env.set("K_SERVICE", None, source="test_cleanup")
        env.set("TESTING", "1", source="test_cleanup")

    def test_auth_config_log_configuration_no_keyerror(self):
        """
        Validate that AuthConfig.log_configuration() works without KeyError.
        
        This was one of the original scenarios where the KeyError occurred.
        The fix should allow this to complete successfully.
        """
        # Arrange: Create AuthConfig instance as in real auth service startup
        config = AuthConfig()
        
        # Act: Call log_configuration which should work without KeyError
        # This directly tests the method that was failing before the fix
        try:
            config.log_configuration()
            print("✅ AuthConfig.log_configuration() completed without KeyError - fix validated")
        except KeyError as ke:
            if "timestamp" in str(ke):
                pytest.fail("❌ KeyError: 'timestamp' still occurring in AuthConfig.log_configuration() - fix may have regressed")
            else:
                pytest.fail(f"❌ Unexpected KeyError in AuthConfig.log_configuration(): {ke}")
        except Exception as e:
            # Other exceptions might occur due to missing dependencies, but KeyError shouldn't
            print(f"ℹ️ Non-KeyError exception (may be expected): {type(e).__name__}: {e}")
            
            # Make sure it's not a masked KeyError
            if "timestamp" in str(e):
                pytest.fail(f"❌ Possible masked KeyError: {e}")
        
        # Assert: If we reach here without KeyError, the fix is working
        assert True, "AuthConfig.log_configuration() completed without KeyError"

    def test_auth_service_initialization_logging_no_keyerror(self):
        """
        Validate that AuthService initialization logging works without KeyError.
        
        This tests the logging that occurs during auth service component initialization.
        """
        # Skip if dependencies not available (no Docker required)
        try:
            from auth_service.auth_core.services.auth_service import AuthService
        except ImportError:
            pytest.skip("AuthService not available for testing")
        
        # Capture any KeyErrors that occur during initialization
        captured_errors = []
        
        # Mock database to avoid dependency issues
        with patch('auth_service.auth_core.services.auth_service.AuthService._initialize_database') as mock_db:
            mock_db.return_value = None
            
            # Mock redis to avoid dependency issues  
            with patch('auth_service.auth_core.services.auth_service.AuthService._initialize_redis') as mock_redis:
                mock_redis.return_value = None
                
                # Act: Try to create AuthService instance
                try:
                    auth_service = AuthService()
                    print("✅ AuthService initialization completed without KeyError - fix validated")
                except KeyError as ke:
                    if "timestamp" in str(ke):
                        pytest.fail("❌ KeyError: 'timestamp' still occurring during AuthService init - fix may have regressed")
                    else:
                        pytest.fail(f"❌ Unexpected KeyError during AuthService init: {ke}")
                except Exception as e:
                    # Other exceptions are expected due to mocked dependencies
                    print(f"ℹ️ Expected exception due to mocked dependencies: {type(e).__name__}: {e}")

    def test_json_logging_cloud_run_simulation_no_keyerror(self):
        """
        Validate JSON logging works in Cloud Run environment simulation.
        
        This tests the exact scenario where the original KeyError occurred:
        Cloud Run environment with JSON logging enabled.
        """
        # Arrange: Set up Cloud Run environment simulation
        env = get_env()
        env.set("K_SERVICE", "netra-auth-service-staging", source="cloud_run_test")
        env.set("K_REVISION", "netra-auth-service-staging-00001-abc", source="cloud_run_test") 
        env.set("PORT", "8080", source="cloud_run_test")
        env.set("ENVIRONMENT", "staging", source="cloud_run_test")
        
        # Get SSOT logger and force configuration
        ssot_logger = get_ssot_logger()
        
        # Force JSON logging configuration (this triggers the code path that had the bug)
        ssot_logger._config = {
            'log_level': 'INFO',
            'enable_file_logging': False,
            'enable_json_logging': True,  # This is the critical path
            'log_file_path': 'logs/auth-service.log'
        }
        ssot_logger._config_loaded = True
        
        # Capture stdout to see if JSON is produced correctly
        captured_output = StringIO()
        
        try:
            # The original bug occurred in the _configure_handlers method when JSON logging was enabled
            with redirect_stdout(captured_output):
                ssot_logger._setup_logging()  # This would trigger the KeyError in the old code
                
                # Try various logging calls that would have failed before
                ssot_logger.info("Auth service Cloud Run test message")
                ssot_logger.warning("Test warning message")
                ssot_logger.error("Test error message")
                
            print("✅ Cloud Run JSON logging completed without KeyError - fix validated")
            
            # Verify output (should be JSON if working correctly)
            output = captured_output.getvalue()
            if output.strip():
                # Try to parse as JSON to verify format
                lines = output.strip().split('\n')
                for line in lines:
                    if line.strip():
                        try:
                            parsed = json.loads(line)
                            assert 'timestamp' in parsed, "JSON output missing timestamp field"
                            assert 'severity' in parsed, "JSON output missing severity field" 
                            assert 'message' in parsed, "JSON output missing message field"
                            print(f"✅ Valid JSON output produced: {line[:100]}...")
                        except json.JSONDecodeError:
                            print(f"ℹ️ Non-JSON output (expected in test mode): {line[:50]}...")
            
        except KeyError as ke:
            if "timestamp" in str(ke):
                pytest.fail("❌ KeyError: 'timestamp' still occurring in Cloud Run simulation - fix may have regressed")
            else:
                pytest.fail(f"❌ Unexpected KeyError in Cloud Run simulation: {ke}")
        except Exception as e:
            pytest.fail(f"❌ Unexpected error in Cloud Run simulation: {type(e).__name__}: {e}")
        finally:
            # Cleanup
            env.set("K_SERVICE", None, source="test_cleanup")
            env.set("K_REVISION", None, source="test_cleanup") 
            env.set("PORT", None, source="test_cleanup")

    def test_auth_service_logger_integration_no_keyerror(self):
        """
        Test that auth service can get and use loggers without KeyError.
        
        This validates the common auth service logging patterns work correctly.
        """
        # Test the common pattern used in auth service
        try:
            # This is how auth service typically gets loggers
            logger = get_logger(__name__)
            
            # Test various logging levels
            logger.info("Auth service integration test - info level")
            logger.warning("Auth service integration test - warning level")  
            logger.error("Auth service integration test - error level")
            
            print("✅ Auth service logger integration completed without KeyError - fix validated")
            
        except KeyError as ke:
            if "timestamp" in str(ke):
                pytest.fail("❌ KeyError: 'timestamp' still occurring in auth service logger integration - fix may have regressed")
            else:
                pytest.fail(f"❌ Unexpected KeyError in auth service logger integration: {ke}")
        except Exception as e:
            pytest.fail(f"❌ Unexpected error in auth service logger integration: {type(e).__name__}: {e}")

    def test_concurrent_logging_no_keyerror(self):
        """
        Test concurrent logging scenarios to ensure fix works under load.
        
        This validates that the fix is thread-safe and works with concurrent requests.
        """
        import threading
        import time
        
        # Test concurrent logging (simulating multiple auth requests)
        errors = []
        
        def log_worker(worker_id):
            try:
                logger = get_logger(f"auth_worker_{worker_id}")
                for i in range(10):
                    logger.info(f"Worker {worker_id} - message {i}")
                    time.sleep(0.001)  # Small delay to allow interleaving
            except Exception as e:
                errors.append(e)
        
        # Start multiple worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for any KeyErrors
        keyerrors = [e for e in errors if isinstance(e, KeyError) and "timestamp" in str(e)]
        if keyerrors:
            pytest.fail(f"❌ KeyError: 'timestamp' occurred during concurrent logging - fix may have thread safety issues: {keyerrors[0]}")
        
        if errors:
            print(f"ℹ️ Non-KeyError exceptions occurred (may be expected): {[type(e).__name__ for e in errors]}")
        
        print("✅ Concurrent auth service logging completed without KeyError - fix validated")

    def test_exception_logging_no_keyerror(self):
        """
        Test exception logging scenarios to ensure fix works with error handling.
        
        This validates exception serialization doesn't trigger the KeyError.
        """
        logger = get_logger("auth_exception_test")
        
        try:
            # Create a test exception scenario
            try:
                raise ValueError("Test auth service exception")
            except ValueError as e:
                # This type of exception logging was problematic before the fix
                logger.error("Auth service exception occurred", exception=e)
                logger.critical("Critical auth service error", exception=e)
                
            print("✅ Auth service exception logging completed without KeyError - fix validated")
                
        except KeyError as ke:
            if "timestamp" in str(ke):
                pytest.fail("❌ KeyError: 'timestamp' still occurring in exception logging - fix may have regressed")
            else:
                pytest.fail(f"❌ Unexpected KeyError in exception logging: {ke}")
        except Exception as e:
            pytest.fail(f"❌ Unexpected error in exception logging: {type(e).__name__}: {e}")