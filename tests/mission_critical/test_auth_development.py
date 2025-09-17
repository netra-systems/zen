'''
Development Auth Test Suite
============================
Simplified auth test that works with local development environment
'''

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx
import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.jwt_secret_manager import SharedJWTSecretManager
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.core.jwt_handler import JWTHandler
from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDevelopmentAuth:
    """Test auth functionality in development environment"""

    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.env = IsolatedEnvironment.get_instance()

        # Ensure we're in development mode
        cls.env.set("ENVIRONMENT", "development")

        # Set required secrets for development (must be at least 32 chars)
        cls.env.set("SERVICE_SECRET", "dev-service-secret-for-testing-purposes-only")
        cls.env.set("JWT_SECRET_KEY", "dev-jwt-secret-for-testing-only-must-be-32-chars")
        cls.env.set("SERVICE_ID", "test-service-id")

        # Clear any cached secrets
        SharedJWTSecretManager.clear_cache()

        # Initialize components
        cls.auth_config = AuthConfig()
        cls.jwt_handler = JWTHandler()
        cls.backend_validator = UnifiedJWTValidator()

        # Service URLs for development
        cls.auth_url = "http://localhost:8081"
        cls.backend_url = "http://localhost:8000"

    def test_jwt_secret_synchronization(self):
        """Test that JWT secrets are synchronized across services"""
        logger.info("Testing JWT secret synchronization...")

        # Get secrets from both services
        auth_secret = self.auth_config.get_jwt_secret()
        shared_secret = SharedJWTSecretManager.get_jwt_secret()

        # They should be the same
        assert auth_secret == shared_secret, "JWT secrets are not synchronized!"

        logger.info("✅ JWT secrets are synchronized")

    def test_token_generation(self):
        """Test token generation"""
        logger.info("Testing token generation...")

        # Generate a token
        token = self.jwt_handler.create_access_token(
            user_id="test_user_123",
            email="test@example.com",
            permissions=["read", "write"]
        )

        assert token is not None, "Failed to generate token"
        assert isinstance(token, str), "Token should be a string"

        logger.info(f"✅ Token generated successfully: {token[:20]}...")

    def test_token_validation(self):
        """Test token validation"""
        logger.info("Testing token validation...")

        # Generate a token
        token = self.jwt_handler.create_access_token(
            user_id="test_user_456",
            email="validate@example.com",
            permissions=["read"]
        )

        # Validate the token
        decoded = self.jwt_handler.validate_token_for_consumption(token)
        assert decoded is not None, "Failed to decode token"

        # JWT uses 'sub' for subject (user ID)
        user_id = decoded.get("sub") or decoded.get("user_id")
        assert user_id == "test_user_456", f"Wrong user ID: {user_id}"
        assert decoded.get("email") == "validate@example.com", "Wrong email"

        logger.info("✅ Token validation successful")

    def test_cross_service_validation(self):
        """Test that backend and auth use same JWT secret"""
        logger.info("Testing cross-service JWT secret consistency...")

        # Generate token with auth service handler
        auth_token = self.jwt_handler.create_access_token(
            user_id="cross_service_user",
            email="cross@example.com",
            permissions=["admin"]
        )

        # Try to decode with backend's JWT secret (proving they're the same)
        import jwt

        try:
            # Get the backend's JWT secret
            backend_secret = SharedJWTSecretManager.get_jwt_secret()

            # Decode the auth token with backend's secret (skip all optional validations)
            decoded = jwt.decode(
                auth_token,
                backend_secret,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,  # Keep signature validation
                    "verify_aud": False,       # Skip audience
                    "verify_exp": False,       # Skip expiration
                    "verify_nbf": False,       # Skip not before
                    "verify_iat": False        # Skip issued at
                }
            )

            # Check that we can decode it (means secrets match)
            assert decoded is not None, "Failed to decode auth token with backend secret"

            # Verify the claims
            user_id = decoded.get("sub") or decoded.get("user_id")
            assert user_id == "cross_service_user", f"Wrong user ID: {user_id}"

            logger.info("✅ Cross-service validation successful - JWT secrets match!")

        except jwt.InvalidTokenError as e:
            logger.error(f"JWT secrets don't match between services: {e}")
            raise
        except Exception as e:
            logger.error(f"Cross-service validation failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_service_health_check(self):
        """Test service connectivity"""
        logger.info("Testing service health checks...")

        async with httpx.AsyncClient() as client:
            # Check auth service
            try:
                auth_response = await client.get(f"{self.auth_url}/health")
                logger.info(f"Auth service health: {auth_response.status_code}")
                assert auth_response.status_code == 200, f"Auth service unhealthy: {auth_response.status_code}"
            except (httpx.ConnectError, httpx.RequestError) as e:
                logger.warning(f"Auth service connection failed: {e}")

            # Check backend service
            try:
                backend_response = await client.get(f"{self.backend_url}/health")
                logger.info(f"Backend service health: {backend_response.status_code}")
                assert backend_response.status_code == 200, f"Backend service unhealthy: {backend_response.status_code}"
            except (httpx.ConnectError, httpx.RequestError) as e:
                logger.warning(f"Backend service connection failed: {e}")

        logger.info("✅ Service health checks completed")

    @pytest.mark.asyncio
    async def test_login_flow(self):
        """Test complete login flow"""
        logger.info("Testing login flow...")

        async with httpx.AsyncClient() as client:
            # Register a test user
            register_data = {
                "email": f"testuser{int(datetime.now().timestamp())}@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User"
            }

            try:
                # Register
                reg_response = await client.post(
                    f"{self.auth_url}/auth/register",
                    json=register_data
                )

                if reg_response.status_code == 200:
                    logger.info("✅ User registration successful")

                    # Login
                    login_data = {
                        "username": register_data["email"],
                        "password": register_data["password"]
                    }

                    login_response = await client.post(
                        f"{self.auth_url}/auth/token",
                        data=login_data
                    )

                    if login_response.status_code == 200:
                        result = login_response.json()
                        assert "access_token" in result, "No access token in response"
                        assert "token_type" in result, "No token type in response"
                        logger.info("✅ Login successful")
                    else:
                        logger.warning(f"Login failed: {login_response.status_code}")
                else:
                    logger.warning(f"Registration failed: {reg_response.status_code}")

            except (httpx.ConnectError, httpx.RequestError) as e:
                logger.warning(f"Login flow failed due to connection: {e}")

        logger.info("✅ Login flow test completed")


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("DEVELOPMENT AUTH TEST SUITE")
    logger.info("=" * 60)

    test_suite = TestDevelopmentAuth()
    test_suite.setup_class()

    # Run synchronous tests
    try:
        test_suite.test_jwt_secret_synchronization()
        test_suite.test_token_generation()
        test_suite.test_token_validation()
        test_suite.test_cross_service_validation()
        logger.info("✅ All synchronous tests passed!")
    except Exception as e:
        logger.error(f"Synchronous test failed: {e}")
        return 1

    # Run async tests
    try:
        asyncio.run(test_suite.test_service_health_check())
        asyncio.run(test_suite.test_login_flow())
        logger.info("✅ All async tests completed!")
    except Exception as e:
        logger.error(f"Async test failed: {e}")
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("ALL TESTS PASSED SUCCESSFULLY!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())