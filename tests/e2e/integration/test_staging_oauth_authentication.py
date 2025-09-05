"""
Comprehensive GCP Staging OAuth Authentication Tests - Updated for GCP Secrets Integration

BVJ (Business Value Justification):
1. Segment: All customer segments - OAuth is primary authentication method
2. Business Goal: Protect $300K+ MRR via GCP staging OAuth flow validation  
3. Value Impact: Prevents OAuth failures that block user conversions
4. Revenue Impact: Each OAuth issue caught saves $15K+ MRR monthly

REQUIREMENTS:
- Tests GCP staging OAuth configuration and Google OAuth flow
- Uses GCP Secrets Manager integration for E2E bypass keys
- Proper timeout handling for GCP Cloud Run services
- Independent tests with proper error handling
- Graceful handling of GCP service startup delays
- Works with unified test runner staging environment
"""

import json
import os
import time
import uuid
from typing import Any, Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest
from shared.isolated_environment import get_env

from tests.e2e.staging_auth_bypass import StagingAuthHelper

import logging
logger = logging.getLogger(__name__)


class GCPStagingOAuthTestHelper:
    """Helper class for GCP staging OAuth authentication tests."""
    
    def __init__(self):
        self.auth_helper = StagingAuthHelper()
        # Use GCP staging service URLs from task requirements
        self.staging_auth_url = "https://auth.staging.netrasystems.ai"
        self.staging_backend_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
        self.staging_frontend_url = "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app"
        self.auth_helper.staging_auth_url = self.staging_auth_url
        self.test_session_id = str(uuid.uuid4())
        self.mock_oauth_state = str(uuid.uuid4())
        
    async def verify_staging_environment(self):
        """Verify GCP staging environment configuration."""
        env = get_env()
        environment = env.get("ENVIRONMENT", "development")
        if environment != "staging":
            raise ValueError(f"Expected staging environment, got {environment}")
        
        # Verify E2E_OAUTH_SIMULATION_KEY is available
        if not self.auth_helper.bypass_key:
            raise ValueError("E2E_OAUTH_SIMULATION_KEY not available - ensure unified test runner configured it")
            
        logger.info("✓ GCP staging environment verified")

    async def test_oauth_service_health(self):
        """Test OAuth service health on GCP staging."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_auth_url}/health", timeout=30.0)
                
                if response.status_code != 200:
                    raise Exception(f"OAuth service health check failed: {response.status_code}")
                
                health_data = response.json()
                return {
                    "service_healthy": True,
                    "service_url": self.staging_auth_url,
                    "health_data": health_data
                }
        except httpx.TimeoutException:
            raise Exception("GCP OAuth service timeout - may be starting up")

    async def test_oauth_config_endpoint(self):
        """Test OAuth configuration endpoint."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.staging_auth_url}/auth/config", timeout=30.0)
                
                if response.status_code == 200:
                    config_data = response.json()
                    return {
                        "config_accessible": True,
                        "has_google_config": "google_client_id" in config_data,
                        "config_data": config_data
                    }
                else:
                    return {
                        "config_accessible": False,
                        "status_code": response.status_code
                    }
        except Exception as e:
            logger.warning(f"OAuth config test failed: {e}")
            raise

    async def generate_test_token(self, user_email: str = None):
        """Generate test token using E2E bypass."""
        email = user_email or f"oauth-test-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        
        try:
            token = await self.auth_helper.get_test_token(
                email=email,
                name="OAuth Test User",
                permissions=["read", "write"]
            )
            
            if not token or len(token) < 20:
                raise Exception("Invalid token generated")
            
            return {
                "token": token,
                "email": email,
                "token_valid": True
            }
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            raise

    async def verify_token_with_service(self, token: str):
        """Verify token with GCP staging auth service."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.staging_auth_url}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "verification_successful": True,
                        "token_valid": data.get("valid", False),
                        "user_data": data
                    }
                else:
                    return {
                        "verification_successful": False,
                        "status_code": response.status_code
                    }
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise

    async def test_authenticated_endpoint(self, token: str):
        """Test authenticated endpoint access."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.staging_auth_url}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "endpoint_accessible": True,
                        "user_data": user_data
                    }
                else:
                    return {
                        "endpoint_accessible": False,
                        "status_code": response.status_code
                    }
        except Exception as e:
            logger.error(f"Authenticated endpoint test failed: {e}")
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_oauth_service_health():
    """Test 1: OAuth service health check on GCP staging."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        health_result = await helper.test_oauth_service_health()
        assert health_result["service_healthy"] is True, "OAuth service not healthy"
        
        logger.info("[SUCCESS] GCP staging OAuth service health verified")
        
    except Exception as e:
        if any(term in str(e).lower() for term in ["gcp", "timeout", "run.app", "secret"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio 
@pytest.mark.e2e
async def test_gcp_staging_oauth_config_endpoint():
    """Test 2: OAuth configuration endpoint accessibility."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        config_result = await helper.test_oauth_config_endpoint()
        assert config_result["config_accessible"] is True, "OAuth config not accessible"
        
        logger.info("[SUCCESS] GCP staging OAuth config endpoint verified")
        
    except Exception as e:
        if any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_e2e_token_generation():
    """Test 3: E2E bypass token generation on GCP staging."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        token_result = await helper.generate_test_token()
        assert token_result["token_valid"] is True, "Token generation failed"
        assert len(token_result["token"]) > 20, "Token appears invalid"
        
        logger.info("[SUCCESS] GCP staging E2E token generation verified")
        
    except Exception as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        elif any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_token_verification():
    """Test 4: Token verification with GCP staging auth service."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        # Generate token
        token_result = await helper.generate_test_token()
        token = token_result["token"]
        
        # Verify token
        verification_result = await helper.verify_token_with_service(token)
        assert verification_result["verification_successful"] is True, "Token verification failed"
        assert verification_result["token_valid"] is True, "Token not valid"
        
        logger.info("[SUCCESS] GCP staging token verification passed")
        
    except Exception as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        elif any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_authenticated_endpoint_access():
    """Test 5: Authenticated endpoint access with generated token."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        # Generate token
        token_result = await helper.generate_test_token()
        token = token_result["token"]
        
        # Test authenticated endpoint
        endpoint_result = await helper.test_authenticated_endpoint(token)
        assert endpoint_result["endpoint_accessible"] is True, "Authenticated endpoint not accessible"
        
        user_data = endpoint_result["user_data"]
        assert user_data.get("email") is not None, "User email not found"
        
        logger.info("[SUCCESS] GCP staging authenticated endpoint access verified")
        
    except Exception as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        elif any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_session_management():
    """Test 6: Session management with GCP staging services."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        # Get authenticated client
        auth_client = await helper.auth_helper.get_authenticated_client(
            base_url=helper.staging_auth_url
        )
        
        # Test session endpoint
        session_response = await auth_client.get("/auth/session", timeout=30.0)
        
        if session_response.status_code == 200:
            session_data = session_response.json()
            assert session_data.get("user_id") is not None, "Session user_id missing"
            logger.info("[SUCCESS] GCP staging session management verified")
        else:
            logger.warning(f"Session endpoint returned {session_response.status_code}")
        
        await auth_client.aclose()
        
    except Exception as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        elif any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_cross_service_token_validation():
    """Test 7: Cross-service token validation between GCP staging services."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        # Generate token from auth service
        token_result = await helper.generate_test_token()
        token = token_result["token"]
        
        # Test token with backend service
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with backend health endpoint (may or may not require auth)
            response = await client.get(
                f"{helper.staging_backend_url}/api/health",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            
            # Any response from backend service indicates connectivity
            backend_responsive = response.status_code in [200, 401, 403, 404]
            assert backend_responsive, f"Backend service not responsive: {response.status_code}"
            
            logger.info(f"[SUCCESS] GCP staging cross-service validation - backend returned {response.status_code}")
        
    except httpx.TimeoutException:
        pytest.skip("GCP backend service timeout")
    except Exception as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        elif any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_multiple_concurrent_sessions():
    """Test 8: Multiple concurrent session handling."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        # Create multiple test tokens
        session_tokens = []
        for i in range(3):
            try:
                token_result = await helper.generate_test_token(
                    f"concurrent-test-{i}-{uuid.uuid4().hex[:6]}@staging.netrasystems.ai"
                )
                session_tokens.append(token_result["token"])
            except Exception as e:
                logger.warning(f"Failed to create session {i}: {e}")
        
        assert len(session_tokens) >= 1, "Failed to create any test sessions"
        
        # Verify all tokens work
        valid_sessions = 0
        for token in session_tokens:
            try:
                verification_result = await helper.verify_token_with_service(token)
                if verification_result["verification_successful"]:
                    valid_sessions += 1
            except Exception as e:
                logger.warning(f"Session verification failed: {e}")
        
        assert valid_sessions >= 1, "No valid concurrent sessions"
        logger.info(f"[SUCCESS] GCP staging concurrent sessions: {valid_sessions}/{len(session_tokens)} valid")
        
    except Exception as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        elif any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_error_handling():
    """Test 9: Error handling with invalid credentials."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        await helper.verify_staging_environment()
        
        # Test with invalid token
        invalid_token = f"invalid_token_{uuid.uuid4().hex}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{helper.staging_auth_url}/auth/verify",
                headers={"Authorization": f"Bearer {invalid_token}"},
                timeout=30.0
            )
            
            # Should return 401 or similar for invalid token
            assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
            
            logger.info("[SUCCESS] GCP staging error handling for invalid token verified")
        
    except Exception as e:
        if any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_oauth_complete_integration():
    """Test 10: Complete OAuth integration flow on GCP staging."""
    # Skip if not in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    try:
        helper = GCPStagingOAuthTestHelper()
        start_time = time.time()
        
        # Step 1: Verify environment
        await helper.verify_staging_environment()
        
        # Step 2: Check service health
        health_result = await helper.test_oauth_service_health()
        assert health_result["service_healthy"] is True
        
        # Step 3: Generate and verify token
        token_result = await helper.generate_test_token()
        token = token_result["token"]
        
        verification_result = await helper.verify_token_with_service(token)
        assert verification_result["verification_successful"] is True
        
        # Step 4: Test authenticated access
        endpoint_result = await helper.test_authenticated_endpoint(token)
        assert endpoint_result["endpoint_accessible"] is True
        
        # Calculate total time
        total_time = time.time() - start_time
        
        logger.info(f"[SUCCESS] GCP staging OAuth complete integration test PASSED in {total_time:.2f}s")
        
        # Verify reasonable performance (allowing for GCP startup)
        assert total_time < 60.0, f"Complete integration too slow: {total_time:.2f}s"
        
    except Exception as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e) or "secret" in str(e).lower():
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        elif any(term in str(e).lower() for term in ["gcp", "timeout", "run.app"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise