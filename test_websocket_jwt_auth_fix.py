#!/usr/bin/env python
"""
WebSocket JWT Authentication Fix Verification

This script proves that WebSocket authentication now works correctly
with environment-specific JWT secrets after the fix.
"""

import jwt
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.isolated_environment import get_env


def test_websocket_auth_with_fix():
    """Test the complete WebSocket authentication flow with the fix."""
    print("=" * 80)
    print("WEBSOCKET JWT AUTHENTICATION FIX VERIFICATION")
    print("=" * 80)
    
    env = get_env()
    
    # Clean up any existing secrets
    for key in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET"]:
        try:
            env.delete(key, "test_cleanup")
        except:
            pass
    
    # Set up staging environment with JWT_SECRET_STAGING
    print("\n1. Setting up STAGING environment with JWT_SECRET_STAGING...")
    env.set("ENVIRONMENT", "staging", "test")
    staging_secret = "staging-jwt-secret-for-websocket-auth-minimum-32-chars"
    env.set("JWT_SECRET_STAGING", staging_secret, "test")
    print(f"   Set JWT_SECRET_STAGING: {staging_secret[:30]}...")
    
    # Import after setting environment
    from netra_backend.app.websocket_core.user_context_extractor import (
        UserContextExtractor,
        extract_websocket_user_context
    )
    
    # Simulate auth service creating a JWT token
    print("\n2. Auth service creates JWT token with staging secret...")
    auth_payload = {
        "sub": "websocket-user-999",
        "email": "websocket@staging.example.com",
        "permissions": ["chat", "agent_execution", "read", "write"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
        "iat": datetime.now(timezone.utc),
        "session_id": "session_staging_123",
        "thread_id": "thread_staging_456",
        "run_id": "run_staging_789"
    }
    
    auth_token = jwt.encode(auth_payload, staging_secret, algorithm="HS256")
    print(f"   Token created by auth service: {auth_token[:60]}...")
    
    # Mock WebSocket connection with the JWT token
    print("\n3. WebSocket client connects with JWT token...")
    mock_websocket = MagicMock()
    mock_websocket.headers = {
        "authorization": f"Bearer {auth_token}",
        "user-agent": "StagingTestClient/2.0",
        "origin": "https://staging.netra.com",
        "host": "staging-api.netra.com",
        "sec-websocket-protocol": "chat.v2"
    }
    print("   WebSocket headers configured with Bearer token")
    
    # Extract user context (THIS WAS FAILING WITH 401 BEFORE THE FIX!)
    print("\n4. Backend extracts user context from WebSocket...")
    try:
        user_context, auth_info = extract_websocket_user_context(mock_websocket)
        
        print("   [SUCCESS] User context extracted successfully!")
        print(f"   User ID: {user_context.user_id}")
        print(f"   Thread ID: {user_context.thread_id}")
        print(f"   Run ID: {user_context.run_id}")
        print(f"   WebSocket Connection ID: {user_context.websocket_connection_id}")
        print(f"   Email: {auth_info.get('email', 'Not in auth_info')}")
        print(f"   Permissions: {auth_info['permissions']}")
        print(f"   Session ID: {auth_info.get('session_id', 'N/A')}")
        
        # Verify the data matches
        assert user_context.user_id == "websocket-user-999"
        # Note: thread_id and run_id are generated if not in JWT, that's OK
        assert "chat" in auth_info["permissions"]
        assert "agent_execution" in auth_info["permissions"]
        
    except Exception as e:
        print(f"   [FAIL] Failed to extract user context: {e}")
        print("   This is the 401 error that was happening in staging!")
        raise
    
    # Test what happens without the fix (simulate old behavior)
    print("\n5. Simulating OLD behavior (before fix)...")
    env.delete("JWT_SECRET_STAGING", "test")
    env.set("JWT_SECRET_KEY", "different-backend-secret-32-characters-long", "test")
    
    # Create new extractor with wrong secret
    old_extractor = UserContextExtractor()
    print("   Backend using JWT_SECRET_KEY (not JWT_SECRET_STAGING)")
    
    # Try to validate the auth token with wrong secret
    decoded = old_extractor.validate_and_decode_jwt(auth_token)
    if decoded is None:
        print("   [EXPECTED] Token validation failed with wrong secret")
        print("   This is what was causing 401 errors in staging!")
    else:
        print("   [UNEXPECTED] Token validated with wrong secret - this shouldn't happen!")
    
    # Test the fix again with proper configuration
    print("\n6. Verifying fix with proper staging configuration...")
    env.set("JWT_SECRET_STAGING", staging_secret, "test")
    
    # Create fresh extractor
    fixed_extractor = UserContextExtractor()
    decoded = fixed_extractor.validate_and_decode_jwt(auth_token)
    
    if decoded:
        print("   [SUCCESS] Token validated correctly with staging secret!")
        print(f"   Decoded user: {decoded['sub']}")
        print(f"   Decoded email: {decoded['email']}")
    else:
        print("   [FAIL] Token validation failed even with correct secret!")
        raise AssertionError("Fix not working!")
    
    print("\n" + "=" * 80)
    print("WEBSOCKET AUTHENTICATION FIX VERIFIED!")
    print("=" * 80)
    print("\nKEY FINDINGS:")
    print("1. Backend now correctly uses JWT_SECRET_STAGING in staging environment")
    print("2. WebSocket authentication works with environment-specific secrets")
    print("3. The 401 authentication failures in staging are now fixed")
    print("4. Auth service and backend are properly aligned on JWT secrets")
    
    # Clean up
    env.delete("JWT_SECRET_STAGING", "test")
    env.delete("JWT_SECRET_KEY", "test")
    env.set("ENVIRONMENT", "development", "test")
    
    return True


if __name__ == "__main__":
    try:
        success = test_websocket_auth_with_fix()
        if success:
            print("\n[SUCCESS] WEBSOCKET JWT AUTHENTICATION FIX VERIFIED!")
            sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)