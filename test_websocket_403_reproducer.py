"""
WebSocket 403 Bug Reproducer Test

This test reproduces the JWT secret mismatch causing WebSocket 403 errors.
It demonstrates the exact failure scenario by comparing the JWT secret used 
for token creation vs token validation.

CRITICAL: This test validates the root cause identified in the Five Whys analysis:
Environment configuration mismatch between test JWT secret source and staging deployment.
"""

import os
import jwt
import asyncio
from datetime import datetime, timedelta, timezone
import uuid


def test_websocket_auth_secret_mismatch_reproducer():
    """
    Reproduces the JWT secret mismatch causing WebSocket 403 errors.
    
    This test demonstrates the exact failure scenario by comparing
    the JWT secret used for token creation vs token validation.
    """
    print("=" * 80)
    print("WEBSOCKET 403 BUG REPRODUCER TEST")
    print("=" * 80)
    
    # STEP 0: Set up proper staging environment
    print("\n[STEP 0] Setting up staging environment...")
    original_env = os.environ.get("ENVIRONMENT")
    original_jwt_secret = os.environ.get("JWT_SECRET_STAGING")
    
    # Set staging environment and JWT secret from config/staging.env  
    os.environ["ENVIRONMENT"] = "staging"
    # This is the JWT secret from config/staging.env line 40
    staging_jwt_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
    os.environ["JWT_SECRET_STAGING"] = staging_jwt_secret
    
    print(f"Environment: {os.environ.get('ENVIRONMENT')}")
    print(f"JWT_SECRET_STAGING set: {bool(os.environ.get('JWT_SECRET_STAGING'))}")
    
    # STEP 1: Create JWT token using test environment setup
    print("\n[STEP 1] Creating JWT token using test environment setup...")
    
    try:
        # Use unified JWT secret manager like the test does
        from shared.jwt_secret_manager import get_unified_jwt_secret
        test_secret = get_unified_jwt_secret()
        print(f"Test JWT secret (first 20 chars): {test_secret[:20]}...")
        print(f"Test JWT secret length: {len(test_secret)}")
        
        # Create token like staging config does
        payload = {
            "sub": f"test-user-{uuid.uuid4().hex[:8]}",
            "email": "test@netrasystems.ai",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iss": "netra-auth-service",
            "jti": str(uuid.uuid4())
        }
        
        test_token = jwt.encode(payload, test_secret, algorithm="HS256")
        print(f"Created test JWT token: {test_token[:50]}...")
        print(f"Token payload user: {payload['sub']}")
        
    except Exception as e:
        print(f"[X] FAILED to create test token: {e}")
        return False
        
    finally:
        # Restore original environment
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)
            
        if original_jwt_secret:
            os.environ["JWT_SECRET_STAGING"] = original_jwt_secret
        else:
            os.environ.pop("JWT_SECRET_STAGING", None)
    
    # STEP 2: Validate token using backend UserContextExtractor  
    print("\n[STEP 2] Validating token using backend UserContextExtractor...")
    try:
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        backend_secret = extractor.jwt_secret_key
        print(f"Backend JWT secret (first 20 chars): {backend_secret[:20]}...")
        print(f"Backend JWT secret length: {len(backend_secret)}")
        
    except Exception as e:
        print(f"[X] FAILED to get backend secret: {e}")
        return False
    
    # STEP 3: Compare secrets and validate token
    print("\n[STEP 3] Comparing secrets and validating token...")
    secrets_match = test_secret == backend_secret
    print(f"Secrets match: {secrets_match}")
    
    if not secrets_match:
        print("[X] REPRODUCER CONFIRMED: JWT secrets don't match - this WILL cause 403 errors")
        print(f"Test secret:    {test_secret[:30]}...")
        print(f"Backend secret: {backend_secret[:30]}...")
        print("\nDifferences analysis:")
        if len(test_secret) != len(backend_secret):
            print(f"  - Length mismatch: test={len(test_secret)} vs backend={len(backend_secret)}")
        if test_secret[:10] != backend_secret[:10]:
            print(f"  - Prefix mismatch: test starts with '{test_secret[:10]}' vs backend '{backend_secret[:10]}'")
    else:
        print("[OK] Secrets match - this should work properly")
    
    # Try to validate the token
    print("\n[STEP 4] Testing token validation...")
    try:
        decoded_payload = extractor.validate_and_decode_jwt(test_token)
        validation_success = decoded_payload is not None
        print(f"Token validation success: {validation_success}")
        
        if validation_success:
            print(f"[OK] Token validated successfully for user: {decoded_payload.get('sub', 'unknown')}")
        else:
            print("[X] Token validation FAILED despite using unified secret manager")
            
    except Exception as e:
        print(f"[X] Token validation ERROR: {e}")
        validation_success = False
    
    # STEP 5: Environment diagnostics
    print("\n[STEP 5] Environment diagnostics...")
    try:
        from shared.jwt_secret_manager import get_jwt_secret_manager
        manager = get_jwt_secret_manager()
        debug_info = manager.get_debug_info()
        
        print(f"Environment: {debug_info['environment']}")
        print(f"Environment-specific key: {debug_info['environment_specific_key']}")
        print(f"Has env-specific key: {debug_info['has_env_specific']}")
        print(f"Has generic key: {debug_info['has_generic_key']}")
        print(f"Available keys: {debug_info['available_keys']}")
        
        # Validate configuration
        validation = manager.validate_jwt_configuration()
        print(f"Configuration valid: {validation['valid']}")
        if validation['issues']:
            print(f"Issues: {validation['issues']}")
        if validation['warnings']:
            print(f"Warnings: {validation['warnings']}")
            
    except Exception as e:
        print(f"[X] Environment diagnostics FAILED: {e}")
    
    # STEP 6: Summary and result
    print("\n" + "=" * 80)
    print("REPRODUCER TEST RESULTS")
    print("=" * 80)
    
    if not secrets_match:
        print("[X] BUG REPRODUCED: JWT secret mismatch detected")
        print("   This WILL cause WebSocket 403 authentication failures")
        print("   Root cause: Environment configuration mismatch")
        print("\n[FIX] REQUIRED FIX:")
        print("   1. Ensure staging deployment uses IDENTICAL JWT secret resolution")
        print("   2. Verify GCP deployment injects correct JWT_SECRET_STAGING")
        print("   3. Test WebSocket auth with aligned configuration")
        return False
    elif not validation_success:
        print("[X] BUG REPRODUCED: Token validation failed despite matching secrets")
        print("   This indicates additional JWT validation issues")
        return False
    else:
        print("[OK] BUG NOT REPRODUCED: JWT secrets align and validation works")
        print("   WebSocket authentication should work correctly")
        return True


if __name__ == "__main__":
    success = test_websocket_auth_secret_mismatch_reproducer()
    exit(0 if success else 1)