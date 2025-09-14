"""
Direct test of auth service without database dependency
"""
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import IsolatedEnvironment before auth modules
from shared.isolated_environment import get_env

# Get environment instance and set required variables using IsolatedEnvironment
env = get_env()
env.set("JWT_SECRET_KEY", "test-secret-key-for-audit-testing-only-not-for-production", "test_auth_direct")
env.set("SERVICE_SECRET", "test-service-secret-for-audit-only", "test_auth_direct")
env.set("SERVICE_ID", "test-service", "test_auth_direct")
env.set("ENVIRONMENT", "test", "test_auth_direct")

import time
import uuid
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.services.auth_service import AuthService


def test_token_refresh_uniqueness():
    """Test that refresh tokens are always unique"""
    print("\n=== Testing Token Refresh Uniqueness ===")
    
    jwt_handler = JWTHandler()
    
    # Create initial tokens with real user data
    user_id = "test-user-" + str(uuid.uuid4())[:8]
    email = "test@example.com"
    permissions = ["read", "write"]
    
    # Create initial refresh token
    initial_refresh = jwt_handler.create_refresh_token(user_id, email, permissions)
    print(f"Initial refresh token: {initial_refresh[:50]}...")
    
    # Perform multiple refreshes and check uniqueness
    tokens_seen = set()
    tokens_seen.add(initial_refresh)
    
    current_refresh = initial_refresh
    for i in range(5):
        # Use JWT handler refresh method
        result = jwt_handler.refresh_access_token(current_refresh)
        
        if result is None:
            print(f"FAIL: Refresh {i+1} failed!")
            return False
            
        access_token, new_refresh = result
        
        # Check uniqueness
        if access_token in tokens_seen:
            print(f"FAIL: Duplicate access token found at refresh {i+1}!")
            return False
        if new_refresh in tokens_seen:
            print(f"FAIL: Duplicate refresh token found at refresh {i+1}!")
            return False
            
        tokens_seen.add(access_token)
        tokens_seen.add(new_refresh)
        
        # Verify payload contains real user data
        access_payload = jwt_handler.validate_token(access_token, "access")
        if access_payload["email"] != email:
            print(f"FAIL: Email mismatch: expected {email}, got {access_payload['email']}")
            return False
        if access_payload["sub"] != user_id:
            print(f"FAIL: User ID mismatch: expected {user_id}, got {access_payload['sub']}")
            return False
            
        print(f"OK: Refresh {i+1}: Generated unique tokens with correct user data")
        
        # Use new refresh for next iteration
        current_refresh = new_refresh
        
        # Small delay to ensure different timestamps
        time.sleep(0.001)
    
    print(f"OK: All {len(tokens_seen)} tokens are unique!")
    return True


def test_token_validation():
    """Test token validation logic"""
    print("\n=== Testing Token Validation ===")
    
    jwt_handler = JWTHandler()
    
    # Test valid token
    user_id = "validation-test"
    email = "validate@example.com"
    access_token = jwt_handler.create_access_token(user_id, email)
    
    payload = jwt_handler.validate_token(access_token, "access")
    if payload is None:
        print("FAIL: Valid token was rejected!")
        return False
    print("OK: Valid token accepted")
    
    # Test invalid token formats
    invalid_tokens = [
        "",
        "invalid",
        "a.b.c",
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",  # Header only
        None
    ]
    
    for token in invalid_tokens:
        payload = jwt_handler.validate_token(token, "access") if token else None
        if payload is not None:
            print(f"FAIL: Invalid token was accepted: {token}")
            return False
    print("OK: All invalid tokens rejected")
    
    # Test token blacklisting
    blacklist_token = jwt_handler.create_access_token("blacklist-user", "blacklist@example.com")
    jwt_handler.blacklist_token(blacklist_token)
    
    payload = jwt_handler.validate_token(blacklist_token, "access")
    if payload is not None:
        print("FAIL: Blacklisted token was accepted!")
        return False
    print("OK: Blacklisted token rejected")
    
    return True


def test_jti_uniqueness():
    """Test that JWT ID (jti) is unique for each token"""
    print("\n=== Testing JWT ID Uniqueness ===")
    
    jwt_handler = JWTHandler()
    jtis = set()
    
    for i in range(20):
        token = jwt_handler.create_access_token(f"user-{i}", f"user{i}@example.com")
        payload = jwt_handler.validate_token(token, "access")
        
        if payload is None:
            print(f"FAIL: Token {i} validation failed")
            return False
            
        jti = payload.get("jti")
        if jti is None:
            print(f"FAIL: Token {i} missing jti claim")
            return False
            
        if jti in jtis:
            print(f"FAIL: Duplicate jti found: {jti}")
            return False
            
        jtis.add(jti)
    
    print(f"OK: All {len(jtis)} JTIs are unique")
    return True


def test_auth_service_refresh():
    """Test auth service refresh method"""
    print("\n=== Testing Auth Service Refresh ===")
    
    import asyncio
    
    async def run_test():
        auth_service = AuthService()
        
        # Create initial token
        user_id = "service-test"
        email = "service@example.com"
        permissions = ["admin"]
        
        initial_refresh = auth_service.jwt_handler.create_refresh_token(
            user_id, email, permissions
        )
        
        # Test refresh
        result = await auth_service.refresh_tokens(initial_refresh)
        
        if result is None:
            print("FAIL: Auth service refresh failed!")
            return False
            
        access_token, new_refresh = result
        
        # Verify tokens are different
        if new_refresh == initial_refresh:
            print("FAIL: Refresh token not regenerated!")
            return False
            
        # Verify user data preserved
        access_payload = auth_service.jwt_handler.validate_token(access_token, "access")
        if access_payload["email"] != email:
            print(f"FAIL: Email not preserved: {access_payload['email']}")
            return False
            
        print("OK: Auth service refresh working correctly")
        
        # Test that old refresh token cannot be reused
        result2 = await auth_service.refresh_tokens(initial_refresh)
        if result2 is not None:
            print("FAIL: Old refresh token was accepted (should be rejected)!")
            return False
            
        print("OK: Old refresh token correctly rejected")
        return True
    
    return asyncio.run(run_test())


def main():
    """Run all tests"""
    print("=" * 60)
    print("AUTHENTICATION SYSTEM AUDIT")
    print("=" * 60)
    
    tests = [
        ("Token Refresh Uniqueness", test_token_refresh_uniqueness),
        ("Token Validation", test_token_validation),
        ("JWT ID Uniqueness", test_jti_uniqueness),
        ("Auth Service Refresh", test_auth_service_refresh),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"FAIL: Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\nSUCCESS: ALL TESTS PASSED! The auth system is working correctly.")
    else:
        print("\nWARNING: Some tests failed. Please review the issues above.")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)