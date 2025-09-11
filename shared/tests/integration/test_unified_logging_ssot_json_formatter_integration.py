"""
Integration Test for SSOT Logging JSON Formatter KeyError Issue

CRITICAL INTEGRATION REPRODUCTION:
This test reproduces the `KeyError: '"timestamp"'` issue in a full SSOT logging
configuration scenario, simulating the exact conditions in Cloud Run GCP environments.

ROOT CAUSE INTEGRATION FOCUS:
When UnifiedLoggingSSOT detects Cloud Run environment (K_SERVICE present),
it enables JSON logging via _configure_handlers() method which calls
_get_json_formatter(). The returned JSON formatter function produces JSON strings
that are passed to Loguru's logger.add() as format strings, causing the KeyError.

BUSINESS IMPACT:
- Blocks GCP staging/production logging functionality
- Prevents Cloud Run deployment success
- Breaks $500K+ ARR Golden Path monitoring and error reporting
- Affects all services in staging/production environments

INTEGRATION TEST SCOPE:
- Full SSOT logging initialization sequence
- Real Cloud Run environment simulation (without Docker)
- Complete handler configuration process
- Real logging message attempts
- WebSocket event logging integration
"""

import json
import logging
import sys
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from loguru import logger

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Import SSOT logging components
from shared.logging.unified_logging_ssot import (
    UnifiedLoggingSSOT, 
    get_ssot_logger, 
    get_logger,
    reset_logging
)


class TestUnifiedLoggingSSOTJsonFormatterIntegration(SSotBaseTestCase):
    """
    Integration test for the complete SSOT logging system KeyError reproduction.
    
    This test should FAIL with KeyError to prove the integration-level bug reproduction.
    """
    
    def setUp(self):
        """Set up integration test environment with Cloud Run simulation."""
        super().setUp()
        
        # Reset logging state
        reset_logging()
        
        # Remove any existing loguru handlers
        try:
            logger.remove()
        except ValueError:
            pass
        
        # Patch the isolated environment for Cloud Run simulation
        self.env_patcher = patch.object(IsolatedEnvironment, 'get_instance')
        self.mock_env = self.env_patcher.start()
        
        # Create mock environment instance that simulates Cloud Run
        self.env_instance = MagicMock()
        self.env_instance.get.side_effect = self._mock_env_get
        self.env_instance.set = MagicMock()
        self.mock_env.return_value = self.env_instance
        
        # Track calls for debugging
        self.env_calls = []
    
    def _mock_env_get(self, key, default=None):
        """Mock environment getter that simulates Cloud Run conditions."""
        self.env_calls.append(key)
        
        # Cloud Run environment variables that trigger JSON logging
        cloud_run_env = {
            'K_SERVICE': 'netra-backend-staging',  # Cloud Run service marker
            'K_REVISION': 'netra-backend-staging-001',
            'ENVIRONMENT': 'staging',              # GCP staging environment
            'TESTING': None,                       # Not in testing mode
            'NETRA_SECRETS_LOADING': None,         # Not loading secrets
            'SERVICE_NAME': 'netra-backend',
            'LOG_LEVEL': 'INFO',
            'ENABLE_GCP_ERROR_REPORTING': 'true',
            'GCP_PROJECT_ID': 'netra-staging',
            
            # Disable colored output (Cloud Run simulation)
            'NO_COLOR': None,
            'FORCE_COLOR': None,
            'PY_COLORS': None,
        }
        
        return cloud_run_env.get(key, default)
    
    def tearDown(self):
        """Clean up integration test environment."""
        super().tearDown()
        self.env_patcher.stop()
        
        # Reset logging state
        reset_logging()
        
        # Clean up loguru handlers
        try:
            logger.remove()
        except ValueError:
            pass
    
    def test_full_ssot_logging_initialization_keyerror(self):
        """
        CRITICAL INTEGRATION TEST: Full SSOT logging setup with KeyError reproduction.
        
        This test should FAIL with KeyError during the complete logging initialization,
        proving the issue occurs in real integration scenarios.
        """
        print("\n=== STARTING FULL SSOT LOGGING INTEGRATION TEST ===")
        
        # Capture all output for analysis
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Create SSOT logger instance - this should trigger the bug
                ssot_logger = get_ssot_logger()
                
                # Force initialization by calling get_logger
                # This triggers _setup_logging() -> _configure_handlers() -> _get_json_formatter()
                logger_instance = ssot_logger.get_logger('test_integration')
                
                # Try to log a message - this should trigger the KeyError
                ssot_logger.info("Integration test message - this should fail with KeyError")
                
                # If we reach here, the bug wasn't reproduced
                self.fail(
                    "Expected KeyError: '\"timestamp\"' during SSOT logging initialization. "
                    "The integration bug reproduction failed."
                )
                
        except KeyError as e:
            # This is the expected error that proves the integration bug
            error_message = str(e)
            captured_stderr = stderr_capture.getvalue()
            captured_stdout = stdout_capture.getvalue()
            
            print(f"\n=== KEYERROR INTEGRATION REPRODUCTION SUCCESSFUL ===")
            print(f"KeyError: {e}")
            print(f"Environment calls made: {self.env_calls}")
            print(f"Stderr output: {captured_stderr[:500]}...")
            print(f"Stdout output: {captured_stdout[:200]}...")
            print(f"This proves the SSOT logging system fails during Cloud Run initialization.")
            print(f"=== END INTEGRATION REPRODUCTION ===\n")
            
            # Verify it's the timestamp-related KeyError
            self.assertIn('timestamp', error_message.lower())
            
            # Re-raise to show test "failure" (which proves the bug)
            raise
            
        except Exception as e:
            # Any other exception indicates a different integration issue
            captured_stderr = stderr_capture.getvalue()
            captured_stdout = stdout_capture.getvalue()
            
            print(f"\n=== UNEXPECTED INTEGRATION ERROR ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {e}")
            print(f"Stderr: {captured_stderr}")
            print(f"Stdout: {captured_stdout}")
            print(f"Environment calls: {self.env_calls}")
            print(f"=== END UNEXPECTED ERROR ===\n")
            
            self.fail(
                f"Expected KeyError: '\"timestamp\"' but got {type(e).__name__}: {e}"
            )
    
    def test_cloud_run_environment_triggers_json_logging(self):
        """
        Test that Cloud Run environment properly triggers the problematic JSON logging path.
        
        This verifies the conditions that lead to the integration bug.
        """
        # Create SSOT logger without triggering setup
        ssot_logger = UnifiedLoggingSSOT()
        
        # Test environment detection
        should_use_json = ssot_logger._should_use_json_logging()
        self.assertTrue(should_use_json, "Cloud Run environment should trigger JSON logging")
        
        # Test configuration loading
        config = ssot_logger._load_config()
        self.assertTrue(config['enable_json_logging'], "Config should enable JSON logging")
        self.assertEqual(config['log_level'], 'INFO')
        
        # Test service name inference
        service_name = ssot_logger._infer_service_name()
        self.assertEqual(service_name, 'netra-backend')
        
        print(f"\n=== ENVIRONMENT ANALYSIS ===")
        print(f"Should use JSON logging: {should_use_json}")
        print(f"Config: {config}")
        print(f"Service name: {service_name}")
        print(f"Environment calls: {self.env_calls}")
        print(f"=== END ANALYSIS ===\n")
    
    def test_json_formatter_in_handler_configuration(self):
        """
        Test the specific handler configuration that causes the KeyError.
        
        This isolates the exact point where JSON string is incorrectly used as format.
        """
        ssot_logger = UnifiedLoggingSSOT()
        
        # Set up the configuration that leads to JSON formatting
        ssot_logger._config = {
            'log_level': 'INFO',
            'enable_file_logging': False,
            'enable_json_logging': True,  # This triggers the problematic path
            'log_file_path': 'logs/test.log'
        }
        
        # Get the JSON formatter that causes the issue
        json_formatter = ssot_logger._get_json_formatter()
        
        # Test the formatter with a sample record
        mock_record = {
            'level': MagicMock(name='INFO'),
            'message': 'Integration test message',
            'name': 'integration.test',
            'exception': None,
            'extra': {}
        }
        mock_record['level'].name = 'INFO'
        
        # Get the format string that will cause the KeyError
        format_string = json_formatter(mock_record)
        
        # Verify it's JSON (this works fine)
        parsed_json = json.loads(format_string)
        self.assertIn('timestamp', parsed_json)
        
        print(f"\n=== HANDLER CONFIGURATION ANALYSIS ===")
        print(f"JSON formatter result: {format_string[:100]}...")
        print(f"Parsed JSON keys: {list(parsed_json.keys())}")
        print(f"This JSON string will be passed to logger.add() as format parameter")
        print(f"causing Loguru to interpret '\"timestamp\"' as a format field.")
        print(f"=== END HANDLER ANALYSIS ===\n")
        
        # The actual KeyError happens when this format_string is passed to logger.add()
        # We can't test that here without triggering the full error


class TestUnifiedLoggingSSOTAsyncIntegration(SSotAsyncTestCase):
    """
    Async integration test for SSOT logging with WebSocket event context.
    
    Tests the async logging paths that are used in WebSocket event delivery,
    which is critical for the Golden Path user flow.
    """
    
    def setUp(self):
        """Set up async integration test environment."""
        super().setUp()
        
        # Reset logging state
        reset_logging()
        
        # Mock Cloud Run environment
        self.env_patcher = patch.object(IsolatedEnvironment, 'get_instance')
        self.mock_env = self.env_patcher.start()
        
        env_instance = MagicMock()
        env_instance.get.side_effect = lambda key, default=None: {
            'K_SERVICE': 'netra-backend-staging',
            'ENVIRONMENT': 'staging',
            'TESTING': None,
            'SERVICE_NAME': 'netra-backend',
            'LOG_LEVEL': 'INFO'
        }.get(key, default)
        env_instance.set = MagicMock()
        self.mock_env.return_value = env_instance
    
    def tearDown(self):
        """Clean up async test environment."""
        super().tearDown()
        self.env_patcher.stop()
        reset_logging()
    
    async def test_async_logging_with_websocket_context(self):
        """
        Test async logging with WebSocket context that triggers KeyError.
        
        This simulates the real-world scenario where WebSocket events
        are logged during agent execution, which is when the KeyError occurs.
        """
        # Create SSOT logger for async context
        ssot_logger = get_ssot_logger()
        
        # Set WebSocket event context (typical in Golden Path flow)
        ssot_logger.set_context(
            request_id='test-request-123',
            user_id='user-456',
            trace_id='trace-789',
            event_type='agent_started'
        )
        
        try:
            # This should trigger the KeyError in async context
            async with ssot_logger.request_context(
                request_id='async-request-456',
                event_type='agent_thinking'
            ):
                # Attempt WebSocket event logging
                ssot_logger.info(
                    "WebSocket event: agent_thinking", 
                    agent_type="supervisor",
                    step="planning"
                )
                
                # Performance logging that would occur during agent execution
                ssot_logger.log_performance("agent_execution", 0.5, status="in_progress")
                
            # If we reach here, the async bug wasn't reproduced
            pytest.fail(
                "Expected KeyError during async WebSocket logging. "
                "Async integration bug reproduction failed."
            )
            
        except KeyError as e:
            # Expected error in async context
            print(f"\n=== ASYNC WEBSOCKET LOGGING KEYERROR ===")
            print(f"Async KeyError: {e}")
            print(f"Context: WebSocket event logging during agent execution")
            print(f"This blocks the Golden Path user flow in staging/production")
            print(f"=== END ASYNC REPRODUCTION ===\n")
            
            # Verify timestamp-related KeyError
            assert 'timestamp' in str(e).lower()
            raise


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])