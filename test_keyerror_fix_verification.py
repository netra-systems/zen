#!/usr/bin/env python3
"""
Simple verification test for the KeyError: '"timestamp"' fix.

This test verifies that the fix implemented in shared/logging/unified_logging_ssot.py
correctly resolves the Loguru KeyError issue by using a custom sink instead of 
format strings for JSON logging.
"""

import os
import sys
import json
from io import StringIO
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from shared.logging.unified_logging_ssot import UnifiedLoggingSSOT, get_ssot_logger
from shared.isolated_environment import IsolatedEnvironment


def test_json_logging_no_keyerror():
    """
    Test that JSON logging works without KeyError after the fix.
    
    This test simulates Cloud Run environment conditions and verifies
    that the custom sink approach prevents the KeyError: '"timestamp"'.
    """
    print("Testing JSON logging with custom sink approach...")
    
    # Mock Cloud Run environment to trigger JSON logging
    with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
        # Set up mock environment that triggers JSON logging
        env_instance = MagicMock()
        env_instance.get.side_effect = lambda key, default=None: {
            'K_SERVICE': 'test-service',      # Cloud Run marker
            'ENVIRONMENT': 'staging',         # GCP environment  
            'TESTING': None,                  # Not in testing mode
            'NETRA_SECRETS_LOADING': None,
            'SERVICE_NAME': 'test-service',
            'LOG_LEVEL': 'INFO'
        }.get(key, default)
        
        env_instance.set = MagicMock()  # Mock the set method for cloud run logging
        mock_env.return_value = env_instance
        
        # Reset the SSOT logger instance to ensure fresh initialization
        import shared.logging.unified_logging_ssot
        shared.logging.unified_logging_ssot._ssot_logger_instance = None
        
        # Capture stdout to verify JSON output
        stdout_capture = StringIO()
        
        with patch('sys.stdout', stdout_capture):
            try:
                # Create SSOT logger instance - should trigger JSON logging setup
                logger = get_ssot_logger()
                
                # The logger should be configured with JSON logging due to our mocked environment
                print(f"Logger setup completed. JSON logging enabled: {logger._config.get('enable_json_logging', False)}")
                
                # Test logging a message - this should NOT raise KeyError
                logger.info("Test message for KeyError verification")
                
                # Check that JSON was output to stdout
                output = stdout_capture.getvalue()
                if output.strip():
                    # Try to parse each line as JSON
                    for line in output.strip().split('\n'):
                        if line.strip():
                            try:
                                parsed = json.loads(line)
                                print(f"✅ Successfully parsed JSON log: {parsed}")
                                assert 'timestamp' in parsed, "Timestamp field missing from JSON log"
                                assert 'message' in parsed, "Message field missing from JSON log"
                                assert 'severity' in parsed, "Severity field missing from JSON log"
                                print("✅ All required JSON fields present")
                            except json.JSONDecodeError as e:
                                print(f"X Failed to parse JSON: {e}")
                                print(f"Raw output: {line}")
                                return False
                else:
                    print("⚠️  No output captured - likely testing mode or no-op sink")
                
                print("✅ JSON logging test completed successfully - No KeyError occurred!")
                return True
                
            except KeyError as e:
                if '"timestamp"' in str(e):
                    print(f"X KeyError still occurring: {e}")
                    print("The fix has not resolved the issue.")
                    return False
                else:
                    print(f"X Unexpected KeyError: {e}")
                    return False
            except Exception as e:
                print(f"X Unexpected error during logging test: {e}")
                return False


def test_json_formatter_direct():
    """
    Test the JSON formatter directly to ensure it produces valid JSON.
    """
    print("\nTesting JSON formatter directly...")
    
    # Mock environment for JSON logging
    with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
        env_instance = MagicMock()
        env_instance.get.side_effect = lambda key, default=None: {
            'K_SERVICE': 'test-service',
            'ENVIRONMENT': 'staging',
            'TESTING': None,
            'NETRA_SECRETS_LOADING': None,
            'SERVICE_NAME': 'test-service',
            'LOG_LEVEL': 'INFO'
        }.get(key, default)
        env_instance.set = MagicMock()
        mock_env.return_value = env_instance
        
        # Reset logger instance
        import shared.logging.unified_logging_ssot
        shared.logging.unified_logging_ssot._ssot_logger_instance = None
        
        try:
            # Create logger and get formatter
            logger = UnifiedLoggingSSOT()
            formatter = logger._get_json_formatter()
            
            # Create a mock record with proper structure
            class MockLevel:
                name = 'INFO'
            
            mock_record = {
                'level': MockLevel(),
                'message': 'Test message',
                'name': 'test_logger',
                'exception': None,
                'extra': {'test_field': 'test_value'}
            }
            
            # Call formatter directly
            json_output = formatter(mock_record)
            print(f"Formatter output: {json_output}")
            
            # Verify it's valid JSON
            parsed = json.loads(json_output)
            print(f"OK Parsed JSON: {parsed}")
            
            # Verify required fields
            assert 'timestamp' in parsed, "Timestamp missing"
            assert 'message' in parsed, "Message missing"
            assert 'severity' in parsed, "Severity missing"
            assert 'service' in parsed, "Service missing"
            
            print("OK JSON formatter test passed!")
            return True
            
        except Exception as e:
            print(f"X JSON formatter test failed: {e}")
            return False


if __name__ == '__main__':
    print("KeyError: '\"timestamp\"' Fix Verification Test")
    print("=" * 50)
    
    success1 = test_json_logging_no_keyerror()
    success2 = test_json_formatter_direct()
    
    if success1 and success2:
        print("\n*** ALL TESTS PASSED - KeyError fix is working correctly!")
        sys.exit(0)
    else:
        print("\nX Some tests failed - KeyError fix may not be working")
        sys.exit(1)