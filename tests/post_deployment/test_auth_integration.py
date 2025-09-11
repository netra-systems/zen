#!/usr/bin/env python3
"""
Post-deployment authentication integration test.
Verifies that authentication is working correctly between auth service and backend.

This test should be run after every deployment to staging/production to ensure:
1. JWT secrets are properly configured and match between services
2. Token generation and validation work end-to-end
3. API authentication middleware is functioning correctly
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Optional
from urllib.parse import urlparse

# Add project root to path BEFORE imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.isolated_environment import get_env

import httpx
import jwt
import pytest

# Initialize environment instance
env = get_env()

from test_framework.environment_markers import staging_only, prod_safe

logger = logging.getLogger(__name__)


class PostDeploymentAuthTest:
    """Post-deployment authentication verification tests."""
    
    def __init__(self, environment: str = "staging"):
        """Initialize test with target environment."""
        self.environment = environment
        self.auth_url = self._get_auth_url()
        self.backend_url = self._get_backend_url()
        self.test_email = f"test-{int(time.time())}@example.com"
        self.test_password = "TestPassword123!"
        
    def _get_auth_url(self) -> str:
        """Get auth service URL for environment."""
        env_urls = {
            "development": "http://localhost:8081",
            "staging": "https://auth.staging.netrasystems.ai",
            "production": "https://auth.netrasystems.ai"
        }
        return env.get("AUTH_SERVICE_URL", env_urls.get(self.environment, env_urls["staging"]))
    
    def _get_backend_url(self) -> str:
        """Get backend service URL for environment."""
        env_urls = {
            "development": "http://localhost:8000",
            "staging": "https://api.staging.netrasystems.ai",
            "production": "https://api.netrasystems.ai"
        }
        return env.get("BACKEND_URL", env_urls.get(self.environment, env_urls["staging"]))
    
    async def test_auth_service_health(self) -> bool:
        """Test that auth service is healthy."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.auth_url}/health")
                assert response.status_code == 200, f"Auth service unhealthy: {response.status_code}"
                logger.info(f"✓ Auth service is healthy at {self.auth_url}")
                return True
            except Exception as e:
                logger.error(f"✗ Auth service health check failed: {e}")
                return False
    
    async def test_backend_health(self) -> bool:
        """Test that backend service is healthy."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.backend_url}/health")
                assert response.status_code == 200, f"Backend unhealthy: {response.status_code}"
                logger.info(f"✓ Backend service is healthy at {self.backend_url}")
                return True
            except Exception as e:
                logger.error(f"✗ Backend health check failed: {e}")
                return False
    
    async def test_token_generation(self) -> Optional[str]:
        """Test that auth service can generate valid tokens."""
        async with httpx.AsyncClient() as client:
            try:
                # Use dev login for testing (if available)
                if self.environment == "development":
                    response = await client.post(
                        f"{self.auth_url}/auth/dev/login",
                        json={"email": self.test_email}
                    )
                else:
                    # For staging/production, use service token generation
                    response = await client.post(
                        f"{self.auth_url}/auth/service-token",
                        json={
                            "service_id": "test-service",
                            "service_secret": env.get("SERVICE_SECRET", "test-secret")
                        }
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    access_token = data.get("access_token")
                    
                    # Decode token without verification to check structure
                    payload = jwt.decode(access_token, options={'verify_signature': False})
                    
                    # Check for common issues
                    issues = []
                    if payload.get("type") != payload.get("token_type"):
                        issues.append(f"Token type mismatch: type={payload.get('type')}, token_type={payload.get('token_type')}")
                    
                    if payload.get("type") == "acess":  # Check for typo
                        issues.append("Token has typo: 'acess' instead of 'access'")
                    
                    if not payload.get("iss") == "netra-auth-service":
                        issues.append(f"Invalid issuer: {payload.get('iss')}")
                    
                    if issues:
                        logger.warning(f"Token generated with issues: {', '.join(issues)}")
                    else:
                        logger.info(f"✓ Token generated successfully")
                    
                    return access_token
                else:
                    logger.error(f"✗ Token generation failed: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"✗ Token generation error: {e}")
                return None
    
    async def test_token_validation(self, token: str) -> bool:
        """Test that backend can validate tokens from auth service."""
        async with httpx.AsyncClient() as client:
            try:
                # Test a protected endpoint
                response = await client.get(
                    f"{self.backend_url}/api/threads",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    logger.info(f"✓ Token validation successful - backend accepted auth token")
                    return True
                elif response.status_code == 401:
                    logger.error(f"✗ Token validation failed - backend rejected valid auth token")
                    logger.error(f"  Response: {response.text}")
                    
                    # Try to decode the token to understand why
                    try:
                        payload = jwt.decode(token, options={'verify_signature': False})
                        logger.error(f"  Token payload: {json.dumps(payload, indent=2)}")
                    except:
                        pass
                    
                    return False
                else:
                    logger.warning(f"  Unexpected status: {response.status_code}")
                    return False
                    
            except Exception as e:
                logger.error(f"✗ Token validation error: {e}")
                return False
    
    async def test_token_generation_wrapper(self) -> bool:
        """Wrapper for token generation test to return bool."""
        token = await self.test_token_generation()
        return token is not None
    
    async def test_cross_service_auth(self) -> bool:
        """Test complete auth flow between services."""
        async with httpx.AsyncClient() as client:
            try:
                # Step 1: Get auth config
                config_response = await client.get(f"{self.auth_url}/auth/config")
                if config_response.status_code != 200:
                    logger.error(f"✗ Failed to get auth config: {config_response.status_code}")
                    return False
                
                config = config_response.json()
                logger.info(f"✓ Auth config retrieved: environment={config.get('environment')}")
                
                # Step 2: Generate token
                token = await self.test_token_generation()
                if not token:
                    return False
                
                # Step 3: Validate token with backend
                if not await self.test_token_validation(token):
                    return False
                
                # Step 4: Test token refresh if available
                if config.get("endpoints", {}).get("refresh"):
                    # This would test refresh token flow
                    pass
                
                logger.info(f"✓ Cross-service authentication working correctly")
                return True
                
            except Exception as e:
                logger.error(f"✗ Cross-service auth test failed: {e}")
                return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all post-deployment tests."""
        results = {}
        
        logger.info(f"\n{'='*60}")
        logger.info(f"POST-DEPLOYMENT AUTH TESTS - {self.environment.upper()}")
        logger.info(f"{'='*60}")
        logger.info(f"Auth URL: {self.auth_url}")
        logger.info(f"Backend URL: {self.backend_url}")
        logger.info(f"{'='*60}\n")
        
        # Run tests in sequence
        tests = [
            ("Auth Service Health", self.test_auth_service_health),
            ("Backend Service Health", self.test_backend_health),
            ("Token Generation", self.test_token_generation_wrapper),
            ("Cross-Service Auth", self.test_cross_service_auth),
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\nRunning: {test_name}")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    results[test_name] = await test_func()
                else:
                    results[test_name] = await test_func()
            except Exception as e:
                logger.error(f"✗ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("TEST RESULTS SUMMARY")
        logger.info(f"{'='*60}")
        
        passed = sum(1 for v in results.values() if v)
        failed = len(results) - passed
        
        for test_name, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            logger.info(f"{status}: {test_name}")
        
        logger.info(f"\nTotal: {passed} passed, {failed} failed")
        
        if failed > 0:
            logger.error("\n⚠️  DEPLOYMENT VERIFICATION FAILED")
            logger.error("JWT secrets may be misconfigured between services")
            logger.error("Check that JWT_SECRET_KEY is set to the same value in both services")
        else:
            logger.info("\n✅ DEPLOYMENT VERIFICATION SUCCESSFUL")
        
        return results


@pytest.mark.asyncio
@pytest.mark.post_deployment
@staging_only
async def test_staging_auth_integration():
    """Test auth integration in staging environment."""
    tester = PostDeploymentAuthTest("staging")
    results = await tester.run_all_tests()
    
    # Assert all tests passed
    assert all(results.values()), f"Some tests failed: {results}"


@pytest.mark.asyncio
@pytest.mark.post_deployment
@prod_safe
async def test_production_auth_integration():
    """Test auth integration in production environment."""
    tester = PostDeploymentAuthTest("production")
    results = await tester.run_all_tests()
    
    # Assert all tests passed
    assert all(results.values()), f"Some tests failed: {results}"


async def main():
    """Run post-deployment tests from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Post-deployment authentication tests")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="staging",
        help="Target environment to test"
    )
    parser.add_argument(
        "--auth-url",
        help="Override auth service URL"
    )
    parser.add_argument(
        "--backend-url",
        help="Override backend service URL"
    )
    args = parser.parse_args()
    
    # Set environment variables if provided
    if args.auth_url:
        env.set("AUTH_SERVICE_URL", args.auth_url, "test")
    if args.backend_url:
        env.set("BACKEND_URL", args.backend_url, "test")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Run tests
    tester = PostDeploymentAuthTest(args.environment)
    results = await tester.run_all_tests()
    
    # Exit with error code if any test failed
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    asyncio.run(main())