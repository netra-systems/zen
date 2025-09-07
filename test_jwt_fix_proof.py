#!/usr/bin/env python
"""
Proof of Fix: JWT Environment-Specific Secret Support

This script demonstrates that the fix for JWT_AUTH_STAGING_FAILURE_20250907 works correctly.
It proves that both auth service and backend now use the same environment-specific JWT secrets.
"""

import jwt
import os
import sys
from datetime import datetime, timedelta, timezone

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.isolated_environment import get_env


def test_jwt_secret_fix():
    """Demonstrate the JWT secret fix works correctly."""
    print("=" * 80)
    print("JWT ENVIRONMENT-SPECIFIC SECRET FIX VERIFICATION")
    print("=" * 80)
    
    env = get_env()
    
    # Test staging environment
    print("\n1. Testing STAGING environment...")
    env.set("ENVIRONMENT", "staging", "test")
    staging_secret = "staging-jwt-secret-minimum-32-characters"
    env.set("JWT_SECRET_STAGING", staging_secret, "test")
    env.set("JWT_SECRET_KEY", "generic-secret-different", "test")
    
    # Import after setting environment
    from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
    
    # Backend extractor
    print("   Creating backend UserContextExtractor...")
    backend_extractor = UserContextExtractor()
    backend_secret = backend_extractor._get_jwt_secret()
    
    print(f"   Backend JWT secret: {backend_secret[:20]}...")
    print(f"   Expected staging secret: {staging_secret[:20]}...")
    
    assert backend_secret == staging_secret, "Backend should use JWT_SECRET_STAGING!"
    print("   [PASS] Backend correctly uses JWT_SECRET_STAGING")
    
    # Create a JWT token with staging secret (simulating auth service)
    print("\n2. Creating JWT token with staging secret (simulating auth service)...")
    payload = {
        "sub": "staging-user-123",
        "email": "test@staging.example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "permissions": ["read", "write"]
    }
    
    token = jwt.encode(payload, staging_secret, algorithm="HS256")
    print(f"   Token created: {token[:50]}...")
    
    # Validate token with backend (this was failing before the fix!)
    print("\n3. Validating token with backend UserContextExtractor...")
    decoded = backend_extractor.validate_and_decode_jwt(token)
    
    if decoded:
        print("   [PASS] Token validation SUCCESSFUL!")
        print(f"   User ID: {decoded['sub']}")
        print(f"   Email: {decoded['email']}")
        print(f"   Permissions: {decoded.get('permissions', [])}")
    else:
        print("   [FAIL] Token validation FAILED (this was the bug!)")
        raise AssertionError("Token validation failed - bug not fixed!")
    
    # Test fallback to JWT_SECRET_KEY when environment-specific not available
    print("\n4. Testing fallback to JWT_SECRET_KEY...")
    env.delete("JWT_SECRET_STAGING", "test")
    
    # Create new extractor
    backend_extractor2 = UserContextExtractor()
    backend_secret2 = backend_extractor2._get_jwt_secret()
    
    print(f"   Backend now uses: {backend_secret2[:20]}...")
    assert backend_secret2 == "generic-secret-different", "Should fall back to JWT_SECRET_KEY"
    print("   [PASS] Correctly falls back to JWT_SECRET_KEY when staging secret not available")
    
    # Demonstrate the original bug scenario
    print("\n5. Demonstrating the ORIGINAL BUG scenario...")
    print("   Auth service uses: JWT_SECRET_STAGING")
    print("   Backend uses: JWT_SECRET_KEY (before fix)")
    
    # Token created with staging secret
    auth_token = jwt.encode(payload, staging_secret, algorithm="HS256")
    
    # Try to validate with different secret (simulating bug)
    try:
        jwt.decode(auth_token, "generic-secret-different", algorithms=["HS256"])
        print("   [FAIL] Should have failed with different secrets!")
    except jwt.InvalidSignatureError:
        print("   [PASS] Correctly fails with mismatched secrets (this was causing 401 errors)")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE: Fix is working correctly!")
    print("=" * 80)
    print("\nSUMMARY:")
    print("- Backend now checks JWT_SECRET_STAGING first in staging environment")
    print("- Falls back to JWT_SECRET_KEY if environment-specific not available")
    print("- JWT tokens from auth service can now be validated by backend")
    print("- This fixes the 401 authentication failures in staging")
    
    # Clean up
    env.delete("JWT_SECRET_KEY", "test")
    env.set("ENVIRONMENT", "development", "test")
    
    return True


if __name__ == "__main__":
    try:
        success = test_jwt_secret_fix()
        if success:
            print("\n[SUCCESS] ALL TESTS PASSED - JWT FIX VERIFIED!")
            sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)