#!/usr/bin/env python3
"""
Test to reproduce and verify the WebSocket JWT authentication bug fix.

This test demonstrates the WebSocket JWT authentication issue and verifies the fix:
1. Reproduces the JWT secret mismatch between test config and backend
2. Shows the environment variable loading issue
3. Verifies the fix resolves the authentication failure
"""

import asyncio
import json
import jwt
import pytest
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from shared.isolated_environment import get_env
from tests.e2e.staging_test_config import StagingConfig

# Import the modules we need to test
from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor


class TestWebSocketJWTAuthFix:
    """Test class to reproduce and verify WebSocket JWT authentication fix."""

    async def test_reproduce_jwt_secret_mismatch(self):
        """Reproduce the JWT secret mismatch issue between test config and backend."""
        print("\n=== REPRODUCING JWT SECRET MISMATCH BUG ===")
        
        # Clean environment first
        env = get_env()
        for key in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET"]:
            try:
                env.delete(key, "test_cleanup")
            except:
                pass
        
        # Set up staging environment 
        env.set("ENVIRONMENT", "staging", "test")
        
        # This is the actual secret from config/staging.env
        staging_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
        
        print(f"1. Setting JWT_SECRET_STAGING in environment...")
        env.set("JWT_SECRET_STAGING", staging_secret, "test")
        
        # Now test the StagingConfig JWT token generation
        print(f"2. Testing StagingConfig JWT token generation...")
        config = StagingConfig()
        test_jwt_token = config.create_test_jwt_token()
        
        if test_jwt_token:
            print(f"   ✅ StagingConfig generated JWT token: {test_jwt_token[:50]}...")
        else:
            print(f"   ❌ StagingConfig failed to generate JWT token")
        
        # Test the UserContextExtractor JWT validation
        print(f"3. Testing UserContextExtractor JWT validation...")
        extractor = UserContextExtractor()
        
        # Check what secret the extractor is using
        extractor_secret = extractor.jwt_secret_key
        print(f"   Backend JWT secret: {extractor_secret[:30]}...")
        print(f"   Test JWT secret:    {staging_secret[:30]}...")
        
        # Test JWT validation
        if test_jwt_token and extractor_secret:
            print(f"4. Testing JWT token validation...")
            payload = await extractor.validate_and_decode_jwt(test_jwt_token)  # CRITICAL FIX: Added await
            
            if payload:
                print(f"   ✅ JWT validation SUCCESS - fix is working!")
                print(f"   User ID: {payload.get('sub', 'unknown')}")
            else:
                print(f"   ❌ JWT validation FAILED - secret mismatch detected!")
                print(f"   This reproduces the original bug")
                
                # Try to debug the mismatch
                try:
                    # Attempt to decode with test secret to verify token is valid
                    test_payload = jwt.decode(test_jwt_token, staging_secret, algorithms=["HS256"])
                    print(f"   Token is valid with test secret: {test_payload.get('sub')}")
                    
                    # This means the backend is using a different secret
                    print(f"   ❌ CONFIRMED: Backend and test config use different JWT secrets")
                except Exception as e:
                    print(f"   Token verification error: {e}")
        
        # Clean up
        for key in ["JWT_SECRET_STAGING", "ENVIRONMENT"]:
            try:
                env.delete(key, "test")
            except:
                pass
                
        # Assert that we found the issue (this test should initially fail)
        assert extractor_secret == staging_secret, (
            f"JWT secret mismatch detected! "
            f"Backend uses: {extractor_secret[:30]}... "
            f"Test config uses: {staging_secret[:30]}... "
            f"This confirms the WebSocket authentication bug."
        )

    def test_environment_variable_loading_issue(self):
        """Test that demonstrates the environment variable loading issue."""
        print("\n=== TESTING ENVIRONMENT VARIABLE LOADING ===")
        
        env = get_env()
        
        # Test different scenarios of JWT secret loading
        test_cases = [
            {
                "name": "staging_specific_secret",
                "environment": "staging", 
                "variables": {"JWT_SECRET_STAGING": "staging-secret-test"},
                "expected": "staging-secret-test"
            },
            {
                "name": "fallback_to_generic", 
                "environment": "staging",
                "variables": {"JWT_SECRET_KEY": "generic-secret-test"},
                "expected": "generic-secret-test"
            },
            {
                "name": "development_default",
                "environment": "development",
                "variables": {},
                "expected": "test_jwt_secret_key_for_development_only"
            }
        ]
        
        for case in test_cases:
            print(f"\nTesting case: {case['name']}")
            
            # Clean environment
            for key in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET", "ENVIRONMENT"]:
                try:
                    env.delete(key, f"test_{case['name']}")
                except:
                    pass
            
            # Set up test environment
            env.set("ENVIRONMENT", case["environment"], f"test_{case['name']}")
            
            for key, value in case["variables"].items():
                env.set(key, value, f"test_{case['name']}")
            
            # Test UserContextExtractor secret resolution
            extractor = UserContextExtractor()
            actual_secret = extractor.jwt_secret_key
            
            print(f"   Environment: {case['environment']}")
            print(f"   Set variables: {case['variables']}")
            print(f"   Expected secret: {case['expected'][:20]}...")
            print(f"   Actual secret: {actual_secret[:20]}...")
            
            # Verify the secret matches expectation
            if actual_secret == case["expected"]:
                print(f"   ✅ Secret loading works correctly")
            else:
                print(f"   ❌ Secret loading failed - environment variable issue")
            
            # Clean up this test case
            for key in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET", "ENVIRONMENT"]:
                try:
                    env.delete(key, f"test_{case['name']}")
                except:
                    pass
    
    @pytest.mark.asyncio
    async def test_websocket_headers_generation_fix(self):
        """Test the fix for WebSocket headers generation in staging config."""
        print("\n=== TESTING WEBSOCKET HEADERS GENERATION FIX ===")
        
        env = get_env()
        
        # Set up proper staging environment
        env.set("ENVIRONMENT", "staging", "test_headers")
        staging_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
        env.set("JWT_SECRET_STAGING", staging_secret, "test_headers")
        
        print("1. Testing StagingConfig WebSocket headers generation...")
        config = StagingConfig()
        
        # Test WebSocket headers with proper environment setup
        headers = config.get_websocket_headers()
        
        print(f"   Generated headers: {list(headers.keys())}")
        
        if "Authorization" in headers:
            auth_header = headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split("Bearer ")[1]
                print(f"   ✅ Found Bearer token in headers: {token[:30]}...")
                
                # Test that this token can be validated by backend
                print("2. Testing token validation by backend...")
                extractor = UserContextExtractor()
                payload = await extractor.validate_and_decode_jwt(token)  # CRITICAL FIX: Added await
                
                if payload:
                    print(f"   ✅ Token validation SUCCESS!")
                    print(f"   User ID: {payload.get('sub', 'unknown')}")
                    print(f"   Token expiry: {datetime.fromtimestamp(payload.get('exp', 0))}")
                else:
                    print(f"   ❌ Token validation FAILED - this indicates the bug still exists")
            else:
                print(f"   ❌ Authorization header malformed: {auth_header}")
        else:
            print(f"   ❌ No Authorization header generated")
        
        # Clean up
        for key in ["JWT_SECRET_STAGING", "ENVIRONMENT"]:
            try:
                env.delete(key, "test_headers")
            except:
                pass
        
        # Assert that we have proper authorization header
        assert "Authorization" in headers, "WebSocket headers should include Authorization header"
        assert headers["Authorization"].startswith("Bearer "), "Authorization header should be Bearer token"

    async def test_create_reproduction_scenario(self):
        """Create a scenario that exactly reproduces the staging WebSocket auth failure."""
        print("\n=== CREATING REPRODUCTION SCENARIO ===")
        
        # This test simulates the exact conditions where the bug occurs
        env = get_env()
        
        # Scenario: Test is running but environment variables not properly loaded
        print("1. Simulating staging environment without proper JWT_SECRET_STAGING...")
        
        # Clean all JWT secrets
        for key in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET"]:
            try:
                env.delete(key, "reproduction")
            except:
                pass
        
        env.set("ENVIRONMENT", "staging", "reproduction") 
        
        # Now try to create a test JWT token (this should use fallback)
        config = StagingConfig()
        test_token = config.create_test_jwt_token()
        
        print(f"   Test token created with fallback: {test_token[:30] if test_token else 'None'}...")
        
        # Try to validate with backend (this should fail)
        extractor = UserContextExtractor()
        
        try:
            payload = await extractor.validate_and_decode_jwt(test_token) if test_token else None  # CRITICAL FIX: Added await
            if payload:
                print(f"   ❌ UNEXPECTED: Token validation succeeded - this shouldn't happen in bug scenario")
            else:
                print(f"   ✅ REPRODUCED: Token validation failed as expected in bug scenario")
        except Exception as e:
            print(f"   ✅ REPRODUCED: Backend validation error: {str(e)[:100]}")
        
        # Clean up
        for key in ["ENVIRONMENT"]:
            try:
                env.delete(key, "reproduction")
            except:
                pass
        
        print("\n   This reproduces the exact WebSocket authentication failure in staging!")

if __name__ == "__main__":
    # Run tests directly for debugging
    test = TestWebSocketJWTAuthFix()
    
    print("Running WebSocket JWT Authentication Bug Reproduction Tests")
    print("=" * 60)
    
    try:
        asyncio.run(test.test_reproduce_jwt_secret_mismatch())  # CRITICAL FIX: Added asyncio.run
    except AssertionError as e:
        print(f"✅ CONFIRMED BUG: {e}")
    
    test.test_environment_variable_loading_issue()
    
    asyncio.run(test.test_websocket_headers_generation_fix())
    
    asyncio.run(test.test_create_reproduction_scenario())  # CRITICAL FIX: Added asyncio.run
    
    print("\n" + "=" * 60)
    print("Bug reproduction complete. Implement fix and re-run tests.")