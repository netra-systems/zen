#!/usr/bin/env python3
"""
Test Auth Service OAuth Integration with SSOT Configuration

Tests that the auth service can load OAuth credentials using the new SSOT system.
"""

import os
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_auth_oauth_with_test_config():
    """Test auth service OAuth loading with test configuration."""
    print("Testing Auth Service OAuth Integration")
    print("=" * 45)
    
    # Set up test environment
    os.environ.update({
        'ENVIRONMENT': 'test',
        'GOOGLE_OAUTH_CLIENT_ID_TEST': 'test-client-id-123456',
        'GOOGLE_OAUTH_CLIENT_SECRET_TEST': 'test-client-secret-abcdef'
    })
    
    try:
        # Import auth service secret loader
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        # Test OAuth client ID loading
        client_id = AuthSecretLoader.get_google_client_id()
        print(f"OAuth Client ID: {client_id}")
        
        # Test OAuth client secret loading
        client_secret = AuthSecretLoader.get_google_client_secret()
        print(f"OAuth Client Secret: {client_secret[:10]}...")
        
        # Validate results
        assert client_id == 'test-client-id-123456', f"Expected test client ID, got: {client_id}"
        assert client_secret == 'test-client-secret-abcdef', f"Expected test client secret, got: {client_secret[:10]}..."
        
        print("\nAuth Service OAuth Integration: PASSED")
        return True
        
    except Exception as e:
        print(f"\nAuth Service OAuth Integration: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up environment
        for key in ['ENVIRONMENT', 'GOOGLE_OAUTH_CLIENT_ID_TEST', 'GOOGLE_OAUTH_CLIENT_SECRET_TEST']:
            if key in os.environ:
                del os.environ[key]

def test_auth_oauth_with_development_config():
    """Test auth service OAuth loading with development configuration."""
    print("\nTesting Auth Service OAuth Integration (Development)")
    print("=" * 55)
    
    # Set up development environment
    os.environ.update({
        'ENVIRONMENT': 'development',
        'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT': 'dev-client-id-789012',
        'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT': 'dev-client-secret-ghijkl'
    })
    
    try:
        # Clear any cached validator
        from shared.configuration.central_config_validator import clear_central_validator_cache
        import shared.configuration.central_config_validator as cv_module
        clear_central_validator_cache()
        cv_module._global_validator = None
        
        # Clear isolated environment cache to ensure new values are picked up
        from shared.isolated_environment import get_env
        env = get_env()
        env.clear_cache()  # Clear environment cache
        
        # Import auth service secret loader
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        # Test OAuth client ID loading
        client_id = AuthSecretLoader.get_google_client_id()
        print(f"OAuth Client ID: {client_id}")
        
        # Test OAuth client secret loading
        client_secret = AuthSecretLoader.get_google_client_secret()
        print(f"OAuth Client Secret: {client_secret[:10]}...")
        
        # Validate results
        assert client_id == 'dev-client-id-789012', f"Expected dev client ID, got: {client_id}"
        assert client_secret == 'dev-client-secret-ghijkl', f"Expected dev client secret, got: {client_secret[:10]}..."
        
        print("\nAuth Service OAuth Integration (Development): PASSED")
        return True
        
    except Exception as e:
        print(f"\nAuth Service OAuth Integration (Development): FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up environment
        for key in ['ENVIRONMENT', 'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT', 'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT']:
            if key in os.environ:
                del os.environ[key]

def main():
    """Run auth service OAuth integration tests."""
    print("Auth Service OAuth SSOT Integration Test")
    print("=" * 50)
    
    tests = [
        test_auth_oauth_with_test_config,
        test_auth_oauth_with_development_config,
    ]
    
    results = []
    for test_func in tests:
        result = test_func()
        results.append(result)
    
    # Summary
    print("\nSUMMARY")
    print("=" * 20)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("All auth service OAuth SSOT integrations working!")
        return 0
    else:
        print("Some auth service OAuth SSOT integrations failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())