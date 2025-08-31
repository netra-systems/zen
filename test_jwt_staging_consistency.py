#!/usr/bin/env python3
"""
Test JWT staging consistency between auth and backend services.
Verifies that both services use the same JWT secret in staging environment.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_jwt_staging_consistency():
    """Test that auth and backend services use same JWT secret in staging."""
    
    # Create a clean test environment
    test_env = {}
    test_env['ENVIRONMENT'] = 'staging'
    test_env['JWT_SECRET_STAGING'] = '7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A'
    
    # Clear existing JWT env vars
    for key in list(os.environ.keys()):
        if 'JWT' in key:
            del os.environ[key]
    
    # Set test environment
    for key, value in test_env.items():
        os.environ[key] = value
    
    print("🔍 Testing JWT Staging Consistency")
    print("=" * 50)
    
    print(f"Environment: {os.environ.get('ENVIRONMENT')}")
    print(f"JWT_SECRET_STAGING length: {len(os.environ.get('JWT_SECRET_STAGING', ''))} chars")
    
    # Test 1: Backend JWT secret loading
    try:
        sys.path.insert(0, str(project_root / 'netra_backend'))
        from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
        
        backend_secret_manager = UnifiedSecretManager()
        backend_jwt_secret = backend_secret_manager.get_jwt_secret()
        backend_length = len(backend_jwt_secret)
        
        print(f"✅ Backend JWT secret: {backend_length} chars")
        
    except Exception as e:
        print(f"❌ Backend JWT secret error: {e}")
        backend_jwt_secret = None
        backend_length = 0
    
    # Test 2: Auth service JWT secret loading  
    try:
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        auth_jwt_secret = AuthSecretLoader.get_jwt_secret()
        auth_length = len(auth_jwt_secret)
        
        print(f"✅ Auth service JWT secret: {auth_length} chars")
        
    except Exception as e:
        print(f"❌ Auth service JWT secret error: {e}")
        auth_jwt_secret = None
        auth_length = 0
    
    # Test 3: Consistency check
    print("\n🔍 Consistency Analysis:")
    print("-" * 30)
    
    if backend_jwt_secret and auth_jwt_secret:
        if backend_jwt_secret == auth_jwt_secret:
            print("✅ JWT secrets match between services")
            print(f"   Both services use {len(backend_jwt_secret)}-char secret")
        else:
            print("❌ JWT secret mismatch detected!")
            print(f"   Backend: {backend_length} chars")
            print(f"   Auth: {auth_length} chars")
            print("   This will cause cross-service authentication failures")
            return False
    else:
        print("❌ Could not load JWT secrets from one or both services")
        return False
    
    return True

if __name__ == "__main__":
    success = test_jwt_staging_consistency()
    if success:
        print("\n✅ JWT staging consistency test PASSED")
        sys.exit(0)
    else:
        print("\n❌ JWT staging consistency test FAILED") 
        sys.exit(1)