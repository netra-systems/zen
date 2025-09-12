"""
E2E Staging Authentication Test Suite for Issue #501
===================================================

This test suite reproduces the exact 403 authentication error pattern identified in Issue #501:
- Users can login successfully
- But subsequent API calls receive 403 Forbidden responses
- Despite having valid authentication tokens

Test Strategy:
1. Test complete user authentication flow against staging environment
2. Reproduce the exact 403 error pattern with real API calls
3. Validate token presence vs API access mismatch
4. Identify the specific point where authentication breaks down

Business Impact: $500K+ ARR at risk from authentication failures
Technical Focus: Real staging environment testing with actual user flows
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import httpx
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import SSOT authentication components
from shared.isolated_environment import get_env
from netra_backend.app.auth_integration.auth import BackendAuthIntegration, AuthValidationResult

logger = logging.getLogger(__name__)

# Staging environment configuration
STAGING_BACKEND_URL = os.environ.get("STAGING_BACKEND_URL", "https://staging-backend.netra.ai")
STAGING_AUTH_URL = os.environ.get("STAGING_AUTH_URL", "https://staging-auth.netra.ai")
STAGING_FRONTEND_URL = os.environ.get("STAGING_FRONTEND_URL", "https://staging.netra.ai")

# Test configuration
REQUEST_TIMEOUT = 30  # seconds
TEST_USER_EMAIL = "test-issue-501@netra.ai"
TEST_USER_PASSWORD = "TestPassword123!"

class StagingAuth403ReproductionTest:
    """
    Comprehensive test suite to reproduce Issue #501 authentication failure pattern.
    
    This class creates failing tests that prove the authentication issue exists
    by testing the exact user flow that results in 403 errors.
    """
    
    def __init__(self):
        self.env = get_env()
        self.auth_tokens = {}
        self.session_cookies = {}
        self.test_results = []
        
    @pytest.fixture
    async def staging_client(self):
        """Create HTTP client configured for staging environment testing"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Netra-Test-Suite/1.0 (Issue-501-Reproduction)"
        }
        
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            follow_redirects=True
        ) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_staging_environment_connectivity(self, staging_client):
        """
        Test: Verify staging environment is accessible
        Priority: CRITICAL - Must pass for other tests to be meaningful
        Expected: Should pass (environment should be accessible)
        """
        try:
            # Test backend health
            backend_response = await staging_client.get(f"{STAGING_BACKEND_URL}/health")
            assert backend_response.status_code == 200, f"Backend health check failed: {backend_response.status_code}"
            
            # Test auth service health  
            auth_response = await staging_client.get(f"{STAGING_AUTH_URL}/health")
            assert auth_response.status_code == 200, f"Auth service health check failed: {auth_response.status_code}"
            
            # Test frontend accessibility
            frontend_response = await staging_client.get(f"{STAGING_FRONTEND_URL}")
            assert frontend_response.status_code in [200, 301, 302], f"Frontend not accessible: {frontend_response.status_code}"
            
            logger.info("✅ Staging environment connectivity verified")
            
        except httpx.ConnectError as e:
            pytest.skip(f"Cannot connect to staging environment: {e}")
        except Exception as e:
            pytest.fail(f"Staging environment connectivity test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_user_login_success_but_api_403_issue_501(self, staging_client):
        """
        Test: Reproduce Issue #501 - User login succeeds but API calls return 403
        Priority: P0 CRITICAL - This is the core issue reproduction test
        Expected: SHOULD FAIL - This test should demonstrate the 403 issue exists
        
        Test Flow:
        1. User attempts login (should succeed)
        2. User makes authenticated API call (should fail with 403)
        3. Validate token is present but not working
        """
        
        # Step 1: Attempt user login - this should succeed
        login_payload = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            login_response = await staging_client.post(
                f"{STAGING_AUTH_URL}/login",
                json=login_payload
            )
            
            # Login should succeed
            if login_response.status_code != 200:
                # If login fails, we can't test the 403 issue
                pytest.skip(f"Cannot test 403 issue - login failed: {login_response.status_code}")
            
            login_data = login_response.json()
            access_token = login_data.get("access_token")
            
            assert access_token is not None, "Login succeeded but no access token received"
            
            logger.info(f"✅ User login successful - token received: {access_token[:20]}...")
            
            # Step 2: Make authenticated API call - this is where Issue #501 manifests
            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Test various authenticated endpoints to find the 403 pattern
            test_endpoints = [
                "/api/user/profile",
                "/api/chat/history", 
                "/api/threads",
                "/api/agents/list",
                "/api/user/settings"
            ]
            
            failed_requests = []
            
            for endpoint in test_endpoints:
                try:
                    api_response = await staging_client.get(
                        f"{STAGING_BACKEND_URL}{endpoint}",
                        headers=auth_headers
                    )
                    
                    if api_response.status_code == 403:
                        failed_requests.append({
                            "endpoint": endpoint,
                            "status_code": 403,
                            "response": api_response.text,
                            "token_present": True
                        })
                        logger.warning(f"🚨 Issue #501 reproduced: {endpoint} returned 403 with valid token")
                    
                except httpx.RequestError as e:
                    logger.error(f"Request error for {endpoint}: {e}")
                    continue
            
            # Step 3: Assert that Issue #501 exists (this test should fail)
            if failed_requests:
                # Issue #501 is reproduced - this is what we expect
                failure_details = {
                    "issue": "Issue #501 Authentication Failure Reproduced",
                    "login_successful": True,
                    "token_present": True,
                    "failed_api_calls": len(failed_requests),
                    "failed_endpoints": [req["endpoint"] for req in failed_requests],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                logger.error(f"🚨 ISSUE #501 CONFIRMED: {json.dumps(failure_details, indent=2)}")
                
                # This test SHOULD FAIL because the issue exists
                pytest.fail(f"Issue #501 reproduced: {len(failed_requests)} API calls returned 403 despite valid authentication. "
                           f"Failed endpoints: {[req['endpoint'] for req in failed_requests]}")
            
            else:
                # If no 403 errors, the issue might be resolved (unexpected)
                logger.info("🎉 No 403 errors found - Issue #501 may be resolved")
                
        except Exception as e:
            logger.error(f"Test execution error: {e}")
            pytest.fail(f"Could not complete Issue #501 reproduction test: {e}")
    
    @pytest.mark.asyncio 
    async def test_token_validation_deep_analysis(self, staging_client):
        """
        Test: Deep analysis of token validation failure patterns
        Priority: HIGH - Understanding token validation breakdown
        Expected: SHOULD FAIL - Should identify specific token validation issues
        """
        
        # First get a token through successful login
        login_payload = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            login_response = await staging_client.post(
                f"{STAGING_AUTH_URL}/login",
                json=login_payload
            )
            
            if login_response.status_code != 200:
                pytest.skip("Cannot perform token analysis - login failed")
            
            login_data = login_response.json()
            access_token = login_data.get("access_token")
            
            # Analyze token properties
            token_analysis = {
                "token_length": len(access_token) if access_token else 0,
                "token_format": "JWT" if access_token and access_token.count(".") == 2 else "Unknown",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Test token validation endpoint
            validation_response = await staging_client.get(
                f"{STAGING_AUTH_URL}/validate",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            token_analysis["validation_status"] = validation_response.status_code
            token_analysis["validation_response"] = validation_response.text[:200]
            
            # Test backend token verification
            backend_validation_response = await staging_client.get(
                f"{STAGING_BACKEND_URL}/api/auth/verify",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            token_analysis["backend_validation_status"] = backend_validation_response.status_code
            token_analysis["backend_validation_response"] = backend_validation_response.text[:200]
            
            logger.info(f"Token Analysis Results: {json.dumps(token_analysis, indent=2)}")
            
            # If there's a mismatch between auth service validation and backend validation
            if (validation_response.status_code == 200 and 
                backend_validation_response.status_code != 200):
                
                pytest.fail(f"Token validation mismatch found: Auth service validates token (200) but backend rejects it ({backend_validation_response.status_code})")
            
        except Exception as e:
            pytest.fail(f"Token validation analysis failed: {e}")
    
    @pytest.mark.asyncio
    async def test_cross_service_authentication_flow(self, staging_client):
        """
        Test: Cross-service authentication flow analysis
        Priority: HIGH - Understanding auth flow between services
        Expected: SHOULD FAIL - Should identify cross-service auth breakdown
        """
        
        # Test the complete authentication flow across services
        flow_results = {}
        
        try:
            # Step 1: Frontend OAuth initiation
            oauth_init_response = await staging_client.get(
                f"{STAGING_AUTH_URL}/oauth/google"
            )
            flow_results["oauth_init"] = {
                "status": oauth_init_response.status_code,
                "headers": dict(oauth_init_response.headers)
            }
            
            # Step 2: Direct login for testing
            login_payload = {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
            login_response = await staging_client.post(
                f"{STAGING_AUTH_URL}/login",
                json=login_payload
            )
            
            if login_response.status_code != 200:
                pytest.skip("Cannot test cross-service flow - login failed")
            
            flow_results["login"] = {
                "status": login_response.status_code,
                "has_token": "access_token" in login_response.json()
            }
            
            access_token = login_response.json().get("access_token")
            
            # Step 3: Backend service communication
            backend_endpoints = [
                "/api/user/profile",
                "/api/threads",
                "/api/chat/history"
            ]
            
            backend_results = {}
            for endpoint in backend_endpoints:
                backend_response = await staging_client.get(
                    f"{STAGING_BACKEND_URL}{endpoint}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                backend_results[endpoint] = {
                    "status": backend_response.status_code,
                    "response_size": len(backend_response.content)
                }
            
            flow_results["backend_api_calls"] = backend_results
            
            # Analyze flow breakdown
            auth_failures = [
                endpoint for endpoint, result in backend_results.items() 
                if result["status"] == 403
            ]
            
            if auth_failures:
                flow_results["failure_analysis"] = {
                    "auth_service_working": True,
                    "backend_service_rejecting": True,
                    "failed_endpoints": auth_failures,
                    "likely_cause": "Cross-service JWT validation mismatch"
                }
                
                logger.error(f"Cross-service auth failure detected: {json.dumps(flow_results, indent=2)}")
                
                pytest.fail(f"Cross-service authentication breakdown: Auth service issues tokens but backend rejects them. Failed endpoints: {auth_failures}")
            
        except Exception as e:
            pytest.fail(f"Cross-service authentication flow test failed: {e}")

# Additional utility functions for test analysis
async def analyze_staging_auth_configuration():
    """Utility to analyze staging authentication configuration"""
    
    config_analysis = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": "staging",
        "endpoints": {
            "backend": STAGING_BACKEND_URL,
            "auth": STAGING_AUTH_URL,
            "frontend": STAGING_FRONTEND_URL
        }
    }
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Test auth service configuration endpoint
        try:
            config_response = await client.get(f"{STAGING_AUTH_URL}/config")
            config_analysis["auth_config"] = {
                "status": config_response.status_code,
                "config": config_response.json() if config_response.status_code == 200 else None
            }
        except Exception as e:
            config_analysis["auth_config"] = {"error": str(e)}
            
        # Test backend configuration
        try:
            backend_config_response = await client.get(f"{STAGING_BACKEND_URL}/config")
            config_analysis["backend_config"] = {
                "status": backend_config_response.status_code,
                "config": backend_config_response.json() if backend_config_response.status_code == 200 else None
            }
        except Exception as e:
            config_analysis["backend_config"] = {"error": str(e)}
    
    return config_analysis

if __name__ == "__main__":
    # Direct execution for debugging
    async def run_debug_analysis():
        test_instance = StagingAuth403ReproductionTest()
        
        print("🚀 Starting Issue #501 Authentication Failure Reproduction")
        print("=" * 60)
        
        config_analysis = await analyze_staging_auth_configuration()
        print(f"Configuration Analysis: {json.dumps(config_analysis, indent=2)}")
        
    asyncio.run(run_debug_analysis())