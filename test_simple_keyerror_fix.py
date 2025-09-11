#!/usr/bin/env python3
"""
Simple test to verify the KeyError fix is working.
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from shared.logging.unified_logging_ssot import UnifiedLoggingSSOT
from shared.isolated_environment import IsolatedEnvironment

def test_keyerror_fix():
    """Test that the KeyError issue has been fixed."""
    print("Testing KeyError fix...")
    
    # Mock Cloud Run environment to trigger JSON logging
    with patch.object(IsolatedEnvironment, 'get_instance') as mock_env:
        # Set up mock environment that triggers JSON logging
        env_instance = MagicMock()
        env_instance.get.side_effect = lambda key, default=None: {
            'K_SERVICE': 'test-service',      # Cloud Run marker
            'ENVIRONMENT': 'staging',         # GCP environment  
            'TESTING': 'false',               # Not in testing mode - force real logging
            'NETRA_SECRETS_LOADING': None,
            'SERVICE_NAME': 'test-service',
            'LOG_LEVEL': 'INFO'
        }.get(key, default)
        
        env_instance.set = MagicMock()  # Mock the set method
        mock_env.return_value = env_instance
        
        # Reset the SSOT logger instance
        import shared.logging.unified_logging_ssot
        shared.logging.unified_logging_ssot._ssot_logger_instance = None
        
        try:
            # Create SSOT logger instance - this should trigger JSON logging setup
            logger = UnifiedLoggingSSOT()
            
            # Force config load
            config = logger._load_config()
            print(f"JSON logging enabled: {config.get('enable_json_logging', False)}")
            
            # Test the JSON formatter directly
            formatter = logger._get_json_formatter()
            
            # Create a proper mock record
            class MockLevel:
                name = 'INFO'
            
            mock_record = {
                'level': MockLevel(),
                'message': 'Test message with "timestamp" in it',
                'name': 'test_logger',
                'exception': None,
                'extra': {'test_field': 'test_value'}
            }
            
            # This should NOT raise KeyError: '"timestamp"'
            json_output = formatter(mock_record)
            print(f"JSON output: {json_output}")
            
            # Verify it's valid JSON
            parsed = json.loads(json_output)
            print(f"Parsed successfully: {parsed}")
            
            # Test the configuration method
            logger._setup_logging()
            print("Logger setup completed without KeyError")
            
            return True
            
        except KeyError as e:
            if '"timestamp"' in str(e):
                print(f"FAILED: KeyError still occurring: {e}")
                return False
            else:
                print(f"FAILED: Unexpected KeyError: {e}")
                return False
        except Exception as e:
            print(f"FAILED: Unexpected error: {e}")
            return False

if __name__ == '__main__':
    print("KeyError Fix Verification")
    print("=" * 30)
    
    success = test_keyerror_fix()
    
    if success:
        print("\n✓ SUCCESS: KeyError fix is working correctly!")
        print("The custom sink approach prevents the Loguru format string issue.")
    else:
        print("\n✗ FAILED: KeyError fix is not working")