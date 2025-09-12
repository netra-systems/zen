"""
Debug test to reproduce and validate the WebSocket JWT secret mismatch issue.

This test demonstrates the root cause of the WebSocket 403 authentication failures
by comparing JWT secrets between test environment and backend validation.

CRITICAL: This test validates the Five Whys analysis from WEBSOCKET_AUTH_BUG_FIX_REPORT_20250907.md
"""

import pytest
import os
import jwt
from datetime import datetime, timedelta, timezone
import uuid


def test_jwt_secret_alignment_diagnosis():
    """
    Diagnose JWT secret alignment between test creation and backend validation.
    
    This test proves the root cause identified in the Five Whys analysis:
    Environment configuration mismatch between test JWT secret source 
    and staging deployment JWT secret configuration.
    """
    print("\n" + "="*70)
    print("JWT SECRET ALIGNMENT DIAGNOSIS")
    print("="*70)
    
    # STEP 1: Get test environment JWT secret (how tests create tokens)
    original_env = os.environ.get("ENVIRONMENT")
    
    try:
        # Simulate test environment setup
        os.environ["ENVIRONMENT"] = "staging"
        
        from shared.jwt_secret_manager import get_unified_jwt_secret
        test_secret = get_unified_jwt_secret()
        print(f"[OK] Test JWT secret (first 20 chars): {test_secret[:20]}...")
        print(f"[OK] Test JWT secret length: {len(test_secret)} chars")
        
    except Exception as e:
        print(f"[FAIL] Failed to get test JWT secret: {e}")
        test_secret = None
        
    finally:
        # Restore original environment
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)
    
    # STEP 2: Get backend JWT secret (how backend validates tokens)
    try:
        from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
        extractor = UserContextExtractor()
        backend_secret = extractor.jwt_secret_key
        print(f"[OK] Backend JWT secret (first 20 chars): {backend_secret[:20]}...")
        print(f"[OK] Backend JWT secret length: {len(backend_secret)} chars")
        
    except Exception as e:
        print(f"[FAIL] Failed to get backend JWT secret: {e}")
        backend_secret = None
    
    # STEP 3: Compare secrets
    if test_secret and backend_secret:
        secrets_match = test_secret == backend_secret
        print(f"\n[{'PASS' if secrets_match else 'FAIL'}] Secrets match: {secrets_match}")
        
        if not secrets_match:
            print("\nSECRET MISMATCH ANALYSIS:")
            print(f"   Test secret:    {test_secret}")
            print(f"   Backend secret: {backend_secret}")
            print("\nROOT CAUSE CONFIRMED: JWT secret mismatch will cause 403 WebSocket errors")
            
        return secrets_match
    else:
        print("[FAIL] Could not retrieve one or both JWT secrets for comparison")
        return False


def test_jwt_token_creation_and_validation_flow():
    """
    Test the complete JWT token creation and validation flow to reproduce 403 errors.
    
    This simulates exactly what happens in the failing WebSocket tests.
    """
    print("\n" + "="*70)
    print("JWT TOKEN CREATION & VALIDATION FLOW TEST")
    print("="*70)
    
    # STEP 1: Create JWT token using test environment (staging config approach)
    original_env = os.environ.get("ENVIRONMENT")
    test_token = None
    
    try:
        os.environ["ENVIRONMENT"] = "staging"
        
        from shared.jwt_secret_manager import get_unified_jwt_secret
        test_secret = get_unified_jwt_secret()
        
        # Create payload identical to staging test config
        payload = {
            "sub": f"test-user-{uuid.uuid4().hex[:8]}",
            "email": "test@netrasystems.ai", 
            "permissions": ["read", "write"],
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iss": "netra-auth-service",
            "jti": str(uuid.uuid4())
        }
        
        test_token = jwt.encode(payload, test_secret, algorithm="HS256")
        print(f"[U+2713] Created JWT token using test environment secret")
        print(f"  Token (first 50 chars): {test_token[:50]}...")
        print(f"  User ID: {payload['sub']}")
        
    except Exception as e:
        print(f" FAIL:  Failed to create JWT token: {e}")
        
    finally:
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)
    
    # STEP 2: Validate token using backend UserContextExtractor
    if test_token:
        try:
            from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
            extractor = UserContextExtractor()
            
            print(f"\n SEARCH:  Validating token with backend extractor...")
            decoded_payload = extractor.validate_and_decode_jwt(test_token)
            
            if decoded_payload:
                print(f" PASS:  JWT validation SUCCESS")
                print(f"  Decoded user: {decoded_payload.get('sub', 'unknown')}")
                print(f"  Permissions: {decoded_payload.get('permissions', [])}")
                return True
            else:
                print(f" FAIL:  JWT validation FAILED")
                print(f" ALERT:  This explains the WebSocket 403 errors!")
                print(f"   Backend rejected the token due to signature mismatch")
                return False
                
        except Exception as e:
            print(f" FAIL:  Exception during JWT validation: {e}")
            return False
    else:
        print(f" FAIL:  No token to validate")
        return False


def test_environment_configuration_diagnosis():
    """
    Diagnose environment configuration issues that could cause JWT secret misalignment.
    """
    print("\n" + "="*70)
    print("ENVIRONMENT CONFIGURATION DIAGNOSIS")
    print("="*70)
    
    # Check current environment setup
    current_env = os.environ.get("ENVIRONMENT", "not_set")
    print(f"Current ENVIRONMENT: {current_env}")
    
    # Check for staging JWT secret environment variables
    staging_secrets = {
        "JWT_SECRET_STAGING": os.environ.get("JWT_SECRET_STAGING"),
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"), 
        "JWT_SECRET": os.environ.get("JWT_SECRET"),
    }
    
    print(f"\nJWT Environment Variables:")
    for key, value in staging_secrets.items():
        if value:
            print(f"[U+2713] {key}: {value[:20]}... (length: {len(value)})")
        else:
            print(f" FAIL:  {key}: NOT SET")
    
    # Check unified JWT secret manager behavior
    try:
        from shared.jwt_secret_manager import get_jwt_secret_manager
        manager = get_jwt_secret_manager()
        debug_info = manager.get_debug_info()
        
        print(f"\nUnified JWT Secret Manager Debug Info:")
        for key, value in debug_info.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f" FAIL:  Failed to get JWT manager debug info: {e}")


if __name__ == "__main__":
    """Run diagnosis tests directly for debugging."""
    print("WEBSOCKET JWT SECRET MISMATCH DIAGNOSIS")
    print("=" * 80)
    
    # Run all diagnostic tests
    test_environment_configuration_diagnosis()
    secrets_aligned = test_jwt_secret_alignment_diagnosis()  
    token_validation_works = test_jwt_token_creation_and_validation_flow()
    
    print("\n" + "="*80)
    print("DIAGNOSIS SUMMARY")
    print("="*80)
    print(f"JWT Secrets Aligned: {'YES' if secrets_aligned else 'NO'}")
    print(f"Token Validation Works: {'YES' if token_validation_works else 'NO'}")
    
    if not secrets_aligned:
        print("\nROOT CAUSE CONFIRMED:")
        print("   JWT secret mismatch between test environment and backend")
        print("   This will cause WebSocket 403 authentication failures")
        print("   Solution: Fix staging deployment JWT secret configuration")
    elif not token_validation_works:
        print("\nVALIDATION ISSUE:")
        print("   JWT secrets match but validation still fails")
        print("   May indicate algorithm mismatch or payload format issue")
    else:
        print("\nJWT AUTHENTICATION WORKING CORRECTLY")
        print("   If WebSocket tests are still failing, investigate other causes")