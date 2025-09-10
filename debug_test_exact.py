#!/usr/bin/env python3
"""Debug script that exactly mimics the failing test setup."""

import sys
import os
sys.path.insert(0, '.')

from shared.isolated_environment import get_env
from netra_backend.app.core.backend_environment import BackendEnvironment

class TestDebug:
    def setup_isolated_environment(self):
        """Setup isolated environment for each test - EXACT COPY from test."""
        # Get singleton instance
        self.env = get_env()
        
        # Enable isolation for test consistency  
        self.env.enable_isolation(backup_original=True)
        
        # Store original state for cleanup
        self.original_vars = self.env.get_all().copy()
    
    def test_configuration_validation_integration(self):
        """Test integrated configuration validation catches Redis issues - EXACT COPY."""
        # Test with invalid configuration
        invalid_config = {
            "ENVIRONMENT": "staging",
            "REDIS_HOST": "",  # Invalid empty host
            "REDIS_PORT": "invalid_port",
            "POSTGRES_HOST": "localhost",  # Invalid for staging
            "JWT_SECRET_KEY": "short",     # Too short
            "SECRET_KEY": ""               # Missing
        }
        
        for key, value in invalid_config.items():
            self.env.set(key, value, "validation_test")
        
        backend_env = BackendEnvironment()
        
        # Validate configuration and check for issues
        validation_result = backend_env.validate()
        
        print(f"=== VALIDATION RESULT ===")
        print(f"Valid: {validation_result['valid']}")
        print(f"Issues: {validation_result['issues']}")
        print(f"Warnings: {validation_result['warnings']}")
        
        # Check individual values that might affect validation
        print(f"\n=== INDIVIDUAL CHECKS ===")
        try:
            jwt_secret = backend_env.get_jwt_secret_key()
            print(f"JWT_SECRET_KEY: '{jwt_secret}' (length: {len(jwt_secret) if jwt_secret else 0})")
        except Exception as e:
            print(f"JWT_SECRET_KEY error: {e}")
        
        try:
            secret_key = backend_env.get_secret_key()
            print(f"SECRET_KEY: '{secret_key}' (length: {len(secret_key) if secret_key else 0})")
        except Exception as e:
            print(f"SECRET_KEY error: {e}")
        
        # Check that the environment variables are actually set
        print(f"\n=== ENV VAR CHECKS ===")
        for key, expected_value in invalid_config.items():
            actual_value = self.env.get(key)
            print(f"{key}: expected='{expected_value}', actual='{actual_value}', match={actual_value == expected_value}")
        
        # Should detect issues
        print(f"\n=== ASSERTION ANALYSIS ===")
        print(f"validation_result['valid']: {validation_result['valid']} (type: {type(validation_result['valid'])})")
        print(f"validation_result['valid'] is False: {validation_result['valid'] is False}")
        print(f"validation_result['valid'] == False: {validation_result['valid'] == False}")
        
        assert validation_result["valid"] is False, f"Expected validation to be False, got {validation_result['valid']}"
        assert len(validation_result["issues"]) > 0
    
    def cleanup(self):
        """Cleanup - restore original state."""
        self.env.reset_to_original()

def main():
    test = TestDebug()
    try:
        test.setup_isolated_environment()
        test.test_configuration_validation_integration()
        print("TEST PASSED!")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test.cleanup()

if __name__ == "__main__":
    main()