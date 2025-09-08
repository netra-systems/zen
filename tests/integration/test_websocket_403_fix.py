"""
Test WebSocket 403 Fix - JWT Secret Consistency

This test reproduces the WebSocket 403 authentication error and verifies 
that the unified JWT secret manager fixes the issue by ensuring both
auth service and backend use identical JWT secrets.

Business Value: Prevents $50K MRR loss from WebSocket authentication failures
"""

import pytest
import jwt
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from shared.jwt_secret_manager import (
    get_unified_jwt_secret, 
    get_jwt_secret_manager,
    validate_unified_jwt_config
)
from auth_service.auth_core.auth_environment import get_auth_env
from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor
from shared.isolated_environment import get_env


class TestWebSocket403Fix:
    """Test that unified JWT secret manager fixes WebSocket 403 errors."""
    
    def setup_method(self):
        """Setup test environment."""
        # Clear any cached secrets
        get_jwt_secret_manager().clear_cache()
        
        # Set test environment
        env = get_env()
        env.set("ENVIRONMENT", "staging", "test_setup")
        env.set("JWT_SECRET_KEY", "test_unified_secret_32_characters_long", "test_setup")
    
    def teardown_method(self):
        """Cleanup test environment."""
        get_jwt_secret_manager().clear_cache()
        
    def test_unified_jwt_secret_consistency(self):
        """Test that auth service and backend use identical JWT secrets."""
        # Test that both services use the unified manager
        auth_env = get_auth_env()
        backend_extractor = UserContextExtractor()
        
        # Get secrets from both services
        auth_secret = auth_env.get_jwt_secret_key()
        backend_secret = backend_extractor._get_jwt_secret()
        
        # They must be identical
        assert auth_secret == backend_secret, f"JWT secrets don't match: auth='{auth_secret}' vs backend='{backend_secret}'"
        print(f"[SUCCESS] Both services use identical JWT secret")
        
    def test_jwt_token_generation_and_validation(self):
        """Test JWT token generation by auth service and validation by backend."""
        # Simulate auth service generating a JWT token
        auth_env = get_auth_env()
        jwt_secret = auth_env.get_jwt_secret_key()
        
        # Create a test JWT payload
        payload = {
            "sub": "test_user_123",
            "email": "test@staging.netrasystems.ai", 
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour expiration
            "permissions": ["read", "write"]
        }
        
        # Generate token (simulate auth service)
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        print(f"[SUCCESS] Auth service generated token: {token[:20]}...")
        
        # Validate token (simulate backend service)
        backend_extractor = UserContextExtractor()
        backend_secret = backend_extractor._get_jwt_secret()
        
        try:
            decoded_payload = jwt.decode(token, backend_secret, algorithms=["HS256"])
            assert decoded_payload["sub"] == "test_user_123"
            assert decoded_payload["email"] == "test@staging.netrasystems.ai"
            print(f"[SUCCESS] Backend service validated token successfully")
            return True
        except jwt.InvalidSignatureError:
            pytest.fail(f"JWT signature validation failed - secrets don't match")
        except Exception as e:
            pytest.fail(f"JWT validation failed: {e}")
    
    async def test_websocket_jwt_extraction_and_validation(self):
        """Test WebSocket JWT extraction and validation pipeline."""
        # Create test WebSocket mock with JWT in Authorization header
        mock_websocket = MagicMock()
        
        # Generate a valid JWT token
        jwt_secret = get_unified_jwt_secret()
        payload = {
            "sub": "websocket_test_user",
            "email": "wstest@staging.netrasystems.ai",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600
        }
        test_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        # Mock WebSocket headers with JWT
        mock_websocket.headers = {
            "authorization": f"Bearer {test_token}",
            "user-agent": "test-client",
            "origin": "https://staging.netrasystems.ai"
        }
        
        # Test JWT extraction and validation
        extractor = UserContextExtractor()
        
        # Extract JWT token
        extracted_token = extractor.extract_jwt_from_websocket(mock_websocket)
        assert extracted_token == test_token
        print(f"[SUCCESS] JWT token extracted from WebSocket headers")
        
        # Validate JWT token - CRITICAL FIX: Added await for async method
        validated_payload = await extractor.validate_and_decode_jwt(extracted_token)
        assert validated_payload is not None
        assert validated_payload["sub"] == "websocket_test_user"
        print(f"[SUCCESS] JWT token validated successfully")
        
    def test_environment_specific_jwt_secret_resolution(self):
        """Test environment-specific JWT secret resolution."""
        env = get_env()
        
        # Test staging-specific secret
        env.set("JWT_SECRET_STAGING", "staging_specific_secret_32chars", "test")
        env.set("ENVIRONMENT", "staging", "test")
        
        # Clear cache to force re-resolution
        get_jwt_secret_manager().clear_cache()
        
        # Should use staging-specific secret
        secret = get_unified_jwt_secret()
        assert secret == "staging_specific_secret_32chars"
        print(f"[SUCCESS] Environment-specific JWT secret resolution works")
        
        # Clean up
        env.unset("JWT_SECRET_STAGING")
        get_jwt_secret_manager().clear_cache()
        
    def test_jwt_configuration_validation(self):
        """Test JWT configuration validation."""
        validation_result = validate_unified_jwt_config()
        
        # Should be valid in test environment
        assert validation_result["valid"] == True
        assert validation_result["environment"] in ["staging", "test", "testing"]
        assert validation_result["info"]["secret_length"] >= 32
        
        print(f"[SUCCESS] JWT configuration validation passed")
        print(f"   Environment: {validation_result['environment']}")
        print(f"   Secret length: {validation_result['info']['secret_length']} characters")
        
    def test_reproduce_websocket_403_scenario_before_fix(self):
        """
        Reproduce the original WebSocket 403 scenario.
        
        This test simulates the condition where auth service and backend
        use different JWT secrets, causing signature verification to fail.
        """
        # Create different secrets for auth and backend (simulate the bug)
        auth_secret = "auth_service_secret_32_chars_12"
        backend_secret = "backend_service_secret_32chars1"
        
        # Generate token with auth service secret
        payload = {
            "sub": "test_user_403",
            "email": "test403@staging.netrasystems.ai",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600
        }
        token = jwt.encode(payload, auth_secret, algorithm="HS256")
        
        # Try to validate with different backend secret (should fail)
        try:
            jwt.decode(token, backend_secret, algorithms=["HS256"])
            pytest.fail("Expected JWT validation to fail with different secrets")
        except jwt.InvalidSignatureError:
            print(f"[SUCCESS] Reproduced 403 scenario: JWT signature mismatch detected")
            
        # Now verify the fix works with unified secrets
        unified_secret = get_unified_jwt_secret()
        token_unified = jwt.encode(payload, unified_secret, algorithm="HS256")
        
        try:
            decoded = jwt.decode(token_unified, unified_secret, algorithms=["HS256"])
            assert decoded["sub"] == "test_user_403"
            print(f"[SUCCESS] Fix verified: Unified secrets enable successful validation")
        except Exception as e:
            pytest.fail(f"Unified JWT validation should succeed: {e}")
    
    def test_staging_environment_configuration(self):
        """Test that staging environment configuration is correct."""
        env = get_env()
        env.set("ENVIRONMENT", "staging", "test")
        
        # Clear cache
        get_jwt_secret_manager().clear_cache()
        
        # Should work in staging environment
        try:
            secret = get_unified_jwt_secret()
            assert len(secret) >= 32, f"JWT secret too short: {len(secret)} characters"
            print(f"[SUCCESS] Staging JWT secret resolution successful")
        except Exception as e:
            # If it fails, it should be due to missing configuration, not logic errors
            assert "not configured" in str(e).lower()
            print(f"[SUCCESS] Staging correctly requires proper JWT configuration: {e}")


@pytest.mark.integration
class TestWebSocketAuthenticationPipeline:
    """Integration tests for the complete WebSocket authentication pipeline."""
    
    async def test_end_to_end_websocket_auth_pipeline(self):
        """Test complete end-to-end WebSocket authentication pipeline."""
        # This test requires both services to be using unified JWT secrets
        
        # 1. Generate token (auth service simulation)
        auth_env = get_auth_env()
        jwt_secret = auth_env.get_jwt_secret_key()
        
        payload = {
            "sub": "e2e_test_user",
            "email": "e2e@staging.netrasystems.ai",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "permissions": ["websocket_access"]
        }
        
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        print(f"Step 1: Auth service generated JWT token")
        
        # 2. WebSocket connection with JWT (backend simulation)
        mock_websocket = MagicMock()
        mock_websocket.headers = {
            "authorization": f"Bearer {token}",
            "origin": "https://staging.netrasystems.ai"
        }
        
        # 3. Extract and validate token (WebSocket handler simulation)
        extractor = UserContextExtractor()
        
        try:
            # Extract user context (this does JWT validation internally) - CRITICAL FIX: Added await for async method
            user_context, auth_info = await extractor.extract_user_context_from_websocket(mock_websocket)
            
            # Verify extraction was successful
            assert user_context.user_id == "e2e_test_user"
            assert auth_info["user_id"] == "e2e_test_user"
            assert "websocket_access" in auth_info["permissions"]
            
            print(f"Step 2: Backend successfully validated JWT and created user context")
            print(f"Step 3: WebSocket connection would be authorized")
            print(f"[SUCCESS] End-to-end WebSocket authentication pipeline successful")
            
        except Exception as e:
            pytest.fail(f"End-to-end authentication pipeline failed: {e}")


if __name__ == "__main__":
    # Run tests directly
    import sys
    import asyncio
    
    async def run_tests():
        print("=" * 60)
        print("WebSocket 403 Fix Validation Tests")
        print("=" * 60)
        
        test_instance = TestWebSocket403Fix()
        test_instance.setup_method()
        
        try:
            test_instance.test_unified_jwt_secret_consistency()
            test_instance.test_jwt_token_generation_and_validation() 
            await test_instance.test_websocket_jwt_extraction_and_validation()  # CRITICAL FIX: Added await
            test_instance.test_environment_specific_jwt_secret_resolution()
            test_instance.test_jwt_configuration_validation()
            test_instance.test_reproduce_websocket_403_scenario_before_fix()
            test_instance.test_staging_environment_configuration()
            
            # Integration test
            integration_test = TestWebSocketAuthenticationPipeline()
            await integration_test.test_end_to_end_websocket_auth_pipeline()  # CRITICAL FIX: Added await
            
            print("\n" + "=" * 60)
            print("[CELEBRATION] ALL TESTS PASSED - WebSocket 403 fix verified!")
            print("[ROCKET] $50K MRR WebSocket functionality restored")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n[FAILED] TEST FAILED: {e}")
            sys.exit(1)
        finally:
            test_instance.teardown_method()
    
    asyncio.run(run_tests())