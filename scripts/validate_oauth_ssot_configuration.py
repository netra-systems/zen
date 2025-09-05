#!/usr/bin/env python3
"""
OAuth SSOT Configuration Validation Script

This script validates that the new SSOT OAuth configuration system works correctly
for all environments (development, test, staging, production).

Usage:
    python scripts/validate_oauth_ssot_configuration.py
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.configuration.central_config_validator import (
    get_central_validator,
    get_oauth_client_id,
    get_oauth_client_secret,
    get_oauth_credentials,
    Environment
)
from shared.isolated_environment import get_env

def test_environment_oauth(env_name: str, test_configs: dict):
    """Test OAuth configuration for a specific environment."""
    print(f"\n[TEST] Testing OAuth configuration for {env_name.upper()} environment")
    
    # Set up environment for testing
    original_env = os.environ.get('ENVIRONMENT')
    
    try:
        # Mock environment variables for this test
        for key, value in test_configs.items():
            os.environ[key] = value
        
        # Clear cached environment in central validator and reset global validator
        from shared.configuration.central_config_validator import clear_central_validator_cache
        import shared.configuration.central_config_validator as cv_module
        clear_central_validator_cache()
        cv_module._global_validator = None
        
        # Test SSOT OAuth configuration
        try:
            # Test individual methods
            client_id = get_oauth_client_id()
            client_secret = get_oauth_client_secret()
            
            # Test combined method
            credentials = get_oauth_credentials()
            
            print(f"[PASS] OAuth Client ID: {client_id[:20]}... (length: {len(client_id)})")
            print(f"[PASS] OAuth Client Secret: {client_secret[:5]}... (length: {len(client_secret)})")
            print(f"[PASS] Combined credentials: client_id={len(credentials['client_id'])}, client_secret={len(credentials['client_secret'])}")
            
            # Validate consistency
            assert client_id == credentials['client_id'], f"Client ID mismatch: {client_id} != {credentials['client_id']}"
            assert client_secret == credentials['client_secret'], f"Client Secret mismatch"
            
            print(f"[PASS] {env_name.upper()} OAuth configuration: PASSED")
            return True
            
        except Exception as e:
            print(f"[FAIL] {env_name.upper()} OAuth configuration: FAILED - {e}")
            return False
            
    finally:
        # Clean up environment
        for key in test_configs.keys():
            if key in os.environ:
                del os.environ[key]
        
        # Restore original environment
        if original_env:
            os.environ['ENVIRONMENT'] = original_env
        elif 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']

def main():
    """Validate OAuth SSOT configuration for all environments."""
    print("OAuth SSOT Configuration Validation")
    print("=" * 50)
    
    test_cases = {
        'development': {
            'ENVIRONMENT': 'development',
            'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT': 'dev-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT': 'dev-client-secret-abcdef'
        },
        'test': {
            'ENVIRONMENT': 'test',
            'GOOGLE_OAUTH_CLIENT_ID_TEST': 'test-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_TEST': 'test-client-secret-abcdef'
        },
        'staging': {
            'ENVIRONMENT': 'staging',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'staging-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'staging-client-secret-abcdef'
        },
        'production': {
            'ENVIRONMENT': 'production',
            'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION': 'prod-client-id-12345',
            'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION': 'prod-client-secret-abcdef'
        }
    }
    
    results = {}
    
    for env_name, test_config in test_cases.items():
        results[env_name] = test_environment_oauth(env_name, test_config)
    
    # Summary
    print("\nVALIDATION SUMMARY")
    print("=" * 50)
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    for env_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{env_name.upper()}: {status}")
    
    print(f"\nOverall: {passed_count}/{total_count} environments passed")
    
    if passed_count == total_count:
        print("All OAuth SSOT configurations are working correctly!")
        return 0
    else:
        print("Some OAuth SSOT configurations failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())