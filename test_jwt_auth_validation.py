"""
Test script to validate JWT authentication configuration across services.
This tests the root cause of the 403 errors in the staging environment.
"""

import os
import sys
import asyncio
import base64
import json
from datetime import datetime, timedelta

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_jwt_secret_consistency():
    """Test that JWT secrets are consistent across services."""
    print("\n" + "="*70)
    print("JWT SECRET CONSISTENCY TEST")
    print("="*70)
    
    results = []
    
    # Test 1: Auth service JWT secret resolution
    print("\n[TEST 1] Auth Service JWT Secret Resolution")
    try:
        from auth_service.auth_core.auth_environment import get_auth_env
        auth_env = get_auth_env()
        auth_jwt_secret = auth_env.get_jwt_secret_key()
        print(f"[PASS] Auth service JWT secret: {len(auth_jwt_secret)} chars")
        print(f"  First 8 chars: {auth_jwt_secret[:8]}...")
        results.append(("Auth Service", auth_jwt_secret))
    except Exception as e:
        print(f"[FAIL] Auth service JWT secret failed: {e}")
        results.append(("Auth Service", None))
    
    # Test 2: Backend unified JWT manager (the one that SHOULD be used)
    print("\n[TEST 2] Shared JWT Secret Manager (CORRECT)")
    try:
        from shared.jwt_secret_manager import get_unified_jwt_secret
        shared_jwt_secret = get_unified_jwt_secret()
        print(f"[PASS] Shared JWT manager secret: {len(shared_jwt_secret)} chars")
        print(f"  First 8 chars: {shared_jwt_secret[:8]}...")
        results.append(("Shared Manager", shared_jwt_secret))
    except Exception as e:
        print(f"[FAIL] Shared JWT manager failed: {e}")
        results.append(("Shared Manager", None))
    
    # Test 3: Backend unified secrets (the one that IS being used - WRONG!)
    print("\n[TEST 3] Backend Unified Secrets (INCORRECT)")
    try:
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        backend_jwt_secret = get_jwt_secret()
        print(f"[PASS] Backend unified secrets JWT: {len(backend_jwt_secret)} chars")
        print(f"  First 8 chars: {backend_jwt_secret[:8]}...")
        results.append(("Backend Unified", backend_jwt_secret))
    except Exception as e:
        print(f"[FAIL] Backend unified secrets failed: {e}")
        results.append(("Backend Unified", None))
    
    # Test 4: WebSocket user context extractor
    print("\n[TEST 4] WebSocket User Context Extractor")
    try:
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        ws_jwt_secret = extractor.jwt_secret_key
        print(f"[PASS] WebSocket extractor JWT secret: {len(ws_jwt_secret)} chars")
        print(f"  First 8 chars: {ws_jwt_secret[:8]}...")
        results.append(("WebSocket Extractor", ws_jwt_secret))
    except Exception as e:
        print(f"[FAIL] WebSocket extractor failed: {e}")
        results.append(("WebSocket Extractor", None))
    
    # Compare all secrets
    print("\n" + "="*70)
    print("JWT SECRET COMPARISON")
    print("="*70)
    
    secrets = {name: secret for name, secret in results if secret}
    unique_secrets = set(secrets.values())
    
    if len(unique_secrets) == 0:
        print("[FAIL] CRITICAL: No JWT secrets could be loaded!")
        return False
    elif len(unique_secrets) == 1:
        print("[PASS] SUCCESS: All services use the SAME JWT secret")
        return True
    else:
        print(f"[FAIL] FAILURE: Found {len(unique_secrets)} DIFFERENT JWT secrets!")
        print("\nMismatched secrets by service:")
        for name, secret in secrets.items():
            if secret:
                print(f"  - {name}: {secret[:8]}... (len={len(secret)})")
        return False

def test_jwt_token_validation():
    """Test JWT token creation and validation across services."""
    print("\n" + "="*70)
    print("JWT TOKEN VALIDATION TEST")
    print("="*70)
    
    # Create a test token using auth service secret
    try:
        import jwt
        from auth_service.auth_core.auth_environment import get_auth_env
        
        auth_env = get_auth_env()
        auth_jwt_secret = auth_env.get_jwt_secret_key()
        
        # Create test payload
        payload = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        # Create token with auth service secret
        token = jwt.encode(payload, auth_jwt_secret, algorithm="HS256")
        print(f"[PASS] Created test token with auth service secret")
        print(f"  Token (first 50 chars): {token[:50]}...")
        
        # Try to validate with backend secret
        print("\n[VALIDATION TEST]")
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        backend_secret = get_jwt_secret()
        
        try:
            decoded = jwt.decode(token, backend_secret, algorithms=["HS256"])
            print("[PASS] Backend successfully validated auth token!")
            print(f"  Decoded user_id: {decoded.get('user_id')}")
            return True
        except jwt.InvalidSignatureError:
            print("[FAIL] Backend FAILED to validate auth token - SIGNATURE MISMATCH!")
            print("  This is the root cause of 403 errors!")
            return False
        except Exception as e:
            print(f"[FAIL] Backend validation error: {e}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Token test failed: {e}")
        return False

def test_environment_variables():
    """Test environment variable configuration."""
    print("\n" + "="*70)
    print("ENVIRONMENT VARIABLE TEST")
    print("="*70)
    
    env_vars = [
        "ENVIRONMENT",
        "JWT_SECRET_KEY",
        "JWT_SECRET",
        "JWT_SECRET_STAGING",
        "JWT_SECRET_PRODUCTION",
        "JWT_SECRET_DEVELOPMENT",
        "JWT_SECRET_TEST"
    ]
    
    print("Current JWT-related environment variables:")
    found_any = False
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            found_any = True
            if "SECRET" in var:
                print(f"  {var}: {'*' * 8} (len={len(value)})")
            else:
                print(f"  {var}: {value}")
    
    if not found_any:
        print("  No JWT environment variables set")
    
    return True

def main():
    """Run all JWT authentication tests."""
    print("\n" + "="*70)
    print("JWT AUTHENTICATION DIAGNOSTIC TESTS")
    print("="*70)
    print("Testing root cause of 403 errors in staging environment")
    
    # Run tests
    env_test = test_environment_variables()
    consistency_test = test_jwt_secret_consistency()
    validation_test = test_jwt_token_validation()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    if consistency_test and validation_test:
        print("[PASS] ALL TESTS PASSED - JWT configuration is correct")
        return 0
    else:
        print("[FAIL] TESTS FAILED - JWT configuration mismatch detected!")
        print("\nROOT CAUSE:")
        print("The backend is using its own JWT secret resolution")
        print("instead of the unified JWT secret manager.")
        print("\nSOLUTION:")
        print("Update backend's unified_secrets.py to use")
        print("shared.jwt_secret_manager.get_unified_jwt_secret()")
        return 1

if __name__ == "__main__":
    sys.exit(main())