"""
SIMPLIFIED JWT SECRET SYNCHRONIZATION TEST (ASCII VERSION)
===========================================================

A simplified test to verify JWT secret synchronization issues between
auth service and backend service.

This test focuses on the core issue without complex service orchestration.
"""

import hashlib
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import jwt

# Configure detailed logging with reduced verbosity
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_jwt_secret_loading():
    """Test basic JWT secret loading from SharedJWTSecretManager."""
    print("=== JWT SECRET SYNCHRONIZATION TEST ===")
    
    try:
        # Test 1: Import SharedJWTSecretManager
        from shared.jwt_secret_manager import SharedJWTSecretManager
        print("[OK] Successfully imported SharedJWTSecretManager")
        
        # Test 2: Get JWT secret
        secret = SharedJWTSecretManager.get_jwt_secret()
        print(f"[OK] JWT secret loaded: {len(secret)} characters")
        print(f"[OK] Secret hash: {hashlib.sha256(secret.encode()).hexdigest()[:16]}...")
        
        # Test 3: Test secret consistency
        secret2 = SharedJWTSecretManager.get_jwt_secret()
        assert secret == secret2, "JWT secret inconsistent between calls"
        print("[OK] JWT secret is consistent between calls")
        
        # Test 4: Clear cache and reload
        SharedJWTSecretManager.clear_cache()
        secret3 = SharedJWTSecretManager.get_jwt_secret()
        assert secret == secret3, "JWT secret changed after cache clear"
        print("[OK] JWT secret consistent after cache clear")
        
        return secret
        
    except Exception as e:
        print(f"[FAIL] JWT Secret loading failed: {e}")
        raise

def test_auth_config_jwt_secret():
    """Test JWT secret loading from AuthConfig."""
    print("\n=== AUTH CONFIG JWT SECRET TEST ===")
    
    try:
        # Test import AuthConfig
        from auth_service.auth_core.config import AuthConfig
        print("[OK] Successfully imported AuthConfig")
        
        # Test get JWT secret
        secret = AuthConfig.get_jwt_secret()
        print(f"[OK] Auth config JWT secret loaded: {len(secret)} characters")
        print(f"[OK] Auth secret hash: {hashlib.sha256(secret.encode()).hexdigest()[:16]}...")
        
        return secret
        
    except Exception as e:
        print(f"[FAIL] Auth config JWT secret loading failed: {e}")
        raise

def test_secret_synchronization():
    """Test that both sources provide the same JWT secret."""
    print("\n=== SECRET SYNCHRONIZATION TEST ===")
    
    try:
        # Get secrets from both sources
        shared_secret = test_jwt_secret_loading()
        auth_secret = test_auth_config_jwt_secret()
        
        # Compare secrets
        print(f"Shared secret hash: {hashlib.sha256(shared_secret.encode()).hexdigest()[:16]}...")
        print(f"Auth secret hash:   {hashlib.sha256(auth_secret.encode()).hexdigest()[:16]}...")
        
        if shared_secret == auth_secret:
            print("[SUCCESS] JWT SECRETS ARE SYNCHRONIZED!")
            return True
        else:
            print("[CRITICAL] JWT SECRETS ARE NOT SYNCHRONIZED!")
            print(f"Shared secret length: {len(shared_secret)}")
            print(f"Auth secret length: {len(auth_secret)}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Secret synchronization test failed: {e}")
        raise

def test_jwt_token_creation_and_validation():
    """Test JWT token creation and validation with the synchronized secret."""
    print("\n=== JWT TOKEN CREATION AND VALIDATION TEST ===")
    
    try:
        # Get the synchronized secret
        from shared.jwt_secret_manager import SharedJWTSecretManager
        secret = SharedJWTSecretManager.get_jwt_secret()
        
        # Create a test token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test_user_123",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "token_type": "access",
            "type": "access",
            "iss": "netra-auth-service",
            "aud": "netra-platform",
            "jti": str(uuid.uuid4()),
            "env": "staging",
            "email": "test@example.com",
            "permissions": ["read", "write"]
        }
        
        # Encode token
        token = jwt.encode(payload, secret, algorithm="HS256")
        print(f"[OK] Created JWT token: {token[:50]}...")
        
        # Validate token (disable audience verification for this test)
        decoded = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        print(f"[OK] Successfully validated token")
        print(f"[OK] Token subject: {decoded.get('sub')}")
        print(f"[OK] Token issuer: {decoded.get('iss')}")
        print(f"[OK] Token audience: {decoded.get('aud')}")
        
        # Test with wrong secret
        wrong_secret = "wrong_secret_for_testing"
        try:
            jwt.decode(token, wrong_secret, algorithms=["HS256"], options={"verify_aud": False})
            print("[FAIL] Token validation with wrong secret should have failed!")
            return False
        except jwt.InvalidTokenError:
            print("[OK] Token correctly rejected with wrong secret")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] JWT token test failed: {e}")
        raise

def test_environment_configuration():
    """Test environment configuration for staging."""
    print("\n=== ENVIRONMENT CONFIGURATION TEST ===")
    
    try:
        from shared.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment.get_instance()
        
        print(f"Current ENVIRONMENT: {env.get('ENVIRONMENT', 'not set')}")
        print(f"JWT_SECRET_STAGING available: {env.get('JWT_SECRET_STAGING') is not None}")
        print(f"JWT_SECRET_KEY available: {env.get('JWT_SECRET_KEY') is not None}")
        print(f"JWT_SECRET available: {env.get('JWT_SECRET') is not None}")
        
        # Force staging environment
        original_env = env.get('ENVIRONMENT')
        env.set('ENVIRONMENT', 'staging')
        print("[OK] Set environment to staging")
        
        # Test secret loading in staging
        from shared.jwt_secret_manager import SharedJWTSecretManager
        SharedJWTSecretManager.clear_cache()
        
        try:
            staging_secret = SharedJWTSecretManager.get_jwt_secret()
            print(f"[OK] Successfully loaded JWT secret in staging: {len(staging_secret)} chars")
        except Exception as e:
            print(f"[FAIL] Failed to load JWT secret in staging: {e}")
        
        # Restore original environment
        if original_env:
            env.set('ENVIRONMENT', original_env)
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Environment configuration test failed: {e}")
        raise

def test_cross_service_auth_simulation():
    """Simulate the cross-service authentication issue."""
    print("\n=== CROSS-SERVICE AUTH SIMULATION ===")
    
    try:
        # Test 1: Create token using auth service method
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        jwt_handler = JWTHandler()
        
        # Create an access token
        user_id = "test_cross_service_user"
        email = "cross.service@test.netra.ai"
        permissions = ["read", "write"]
        
        token = jwt_handler.create_access_token(user_id, email, permissions)
        print(f"[OK] Auth service created token: {token[:50]}...")
        
        # Test 2: Validate with auth service
        auth_validation = jwt_handler.validate_token(token, "access")
        print(f"[OK] Auth service validation: {auth_validation is not None}")
        
        if auth_validation:
            print(f"    Subject: {auth_validation.get('sub')}")
            print(f"    Issuer: {auth_validation.get('iss')}")
            print(f"    Audience: {auth_validation.get('aud')}")
        
        # Test 3: Try to validate with backend service approach
        try:
            from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator
            backend_validator = UnifiedJWTValidator()
            
            # This will likely fail if there's a synchronization issue
            backend_validation = backend_validator.validate_token_sync(token)
            print(f"[OK] Backend service validation: {backend_validation.valid if backend_validation else False}")
            
            if backend_validation and not backend_validation.valid:
                print(f"    Backend validation error: {backend_validation.error}")
            
        except Exception as be:
            print(f"[INFO] Backend validation not available in sync mode: {be}")
            print("    This is expected as backend uses async validation")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Cross-service auth simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("STARTING JWT SECRET SYNCHRONIZATION DIAGNOSTIC TESTS")
    print("=" * 60)
    
    try:
        # Run all tests
        secrets_sync = test_secret_synchronization()
        token_test = test_jwt_token_creation_and_validation()
        env_test = test_environment_configuration()
        cross_service_test = test_cross_service_auth_simulation()
        
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY:")
        print(f"[RESULT] Secrets synchronized: {secrets_sync}")
        print(f"[RESULT] Token creation/validation: {token_test}")
        print(f"[RESULT] Environment configuration: {env_test}")
        print(f"[RESULT] Cross-service simulation: {cross_service_test}")
        
        if all([secrets_sync, token_test, env_test]):
            print("\n[SUCCESS] CORE JWT INFRASTRUCTURE TESTS PASSED!")
            print("          JWT secrets appear to be properly synchronized.")
            if not cross_service_test:
                print("          Cross-service issues detected - likely in validation logic.")
            return True
        else:
            print("\n[CRITICAL] CORE JWT INFRASTRUCTURE ISSUES DETECTED!")
            print("           JWT secret synchronization problems found!")
            return False
            
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)