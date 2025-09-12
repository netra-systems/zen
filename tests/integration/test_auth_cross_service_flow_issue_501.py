"""
Cross-Service Authentication Integration Test for Issue #501
==========================================================

This test suite identifies authentication flow breakdown between services:
- Auth Service: Issues JWT tokens
- Backend Service: Validates JWT tokens  
- Frontend Service: Uses JWT tokens

The issue manifests as auth service successfully issuing tokens that
the backend service then rejects with 403 Forbidden responses.

Test Strategy:
1. Test auth service JWT issuance in isolation
2. Test backend service JWT validation in isolation
3. Test cross-service JWT token flow
4. Identify the specific validation mismatch

Business Impact: Cross-service auth failures affect core user workflows
Technical Focus: Real service integration without Docker dependency
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import patch, MagicMock

import pytest
import httpx
import jwt

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import SSOT components per registry
from shared.isolated_environment import get_env
from netra_backend.app.auth_integration.auth import BackendAuthIntegration, AuthValidationResult, TokenRefreshResult
from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)

class CrossServiceAuthFlowTest(SSotAsyncTestCase):
    """
    Integration test suite for cross-service authentication flow analysis.
    
    This suite creates failing tests to identify where authentication breaks down
    between auth service token issuance and backend service token validation.
    """
    
    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = get_env()
        
        # Service endpoints (use env vars or staging defaults)
        self.auth_service_url = os.environ.get("AUTH_SERVICE_URL", "https://staging-auth.netra.ai")
        self.backend_service_url = os.environ.get("BACKEND_SERVICE_URL", "https://staging-backend.netra.ai")
        
        # Test configuration
        self.timeout = 30
        self.test_user = {
            "email": "test-cross-service@netra.ai",
            "password": "CrossServiceTest123!"
        }
        
        # Results tracking
        self.test_results = {}
        
    async def test_auth_service_token_issuance_isolated(self):
        """
        Test: Auth service can issue JWT tokens successfully (in isolation)
        Priority: HIGH - Must work for cross-service flow to be possible
        Expected: SHOULD PASS - Auth service token issuance should work
        """
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test auth service health first
                health_response = await client.get(f"{self.auth_service_url}/health")
                
                if health_response.status_code != 200:
                    pytest.skip(f"Auth service not healthy: {health_response.status_code}")
                
                # Test token issuance
                login_payload = {
                    "email": self.test_user["email"],
                    "password": self.test_user["password"]
                }
                
                login_response = await client.post(
                    f"{self.auth_service_url}/login",
                    json=login_payload
                )
                
                # Auth service should successfully issue tokens
                assert login_response.status_code == 200, f"Auth service login failed: {login_response.status_code}"
                
                login_data = login_response.json()
                access_token = login_data.get("access_token")
                
                assert access_token is not None, "Auth service did not provide access token"
                assert len(access_token) > 50, "Access token appears invalid (too short)"
                
                # Validate JWT format
                token_parts = access_token.split(".")
                assert len(token_parts) == 3, f"JWT format invalid: expected 3 parts, got {len(token_parts)}"
                
                self.test_results["auth_service_token_issuance"] = {
                    "status": "PASS",
                    "token_length": len(access_token),
                    "token_parts": len(token_parts),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                logger.info(f"✅ Auth service token issuance working: token length {len(access_token)}")
                
        except httpx.ConnectError:
            pytest.skip("Cannot connect to auth service")
        except Exception as e:
            pytest.fail(f"Auth service token issuance test failed: {e}")
    
    async def test_backend_service_token_validation_isolated(self):
        """
        Test: Backend service can validate JWT tokens (in isolation) 
        Priority: HIGH - Core of Issue #501
        Expected: SHOULD FAIL - Backend may not properly validate auth service tokens
        """
        
        try:
            # First get a valid token from auth service
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                login_response = await client.post(
                    f"{self.auth_service_url}/login",
                    json=self.test_user
                )
                
                if login_response.status_code != 200:
                    pytest.skip("Cannot get test token for backend validation test")
                
                access_token = login_response.json().get("access_token")
                
                # Test backend service token validation
                validation_headers = {"Authorization": f"Bearer {access_token}"}
                
                # Test various backend endpoints that require authentication
                test_endpoints = [
                    "/api/auth/verify",
                    "/api/user/profile", 
                    "/api/threads",
                    "/api/chat/history"
                ]
                
                validation_results = {}
                
                for endpoint in test_endpoints:
                    try:
                        backend_response = await client.get(
                            f"{self.backend_service_url}{endpoint}",
                            headers=validation_headers
                        )
                        
                        validation_results[endpoint] = {
                            "status_code": backend_response.status_code,
                            "response_length": len(backend_response.content),
                            "headers": dict(backend_response.headers)
                        }
                        
                        # Log the specific failure pattern for Issue #501
                        if backend_response.status_code == 403:
                            logger.error(f"🚨 Issue #501 pattern detected: {endpoint} returned 403 with valid token")
                            validation_results[endpoint]["issue_501_pattern"] = True
                            
                    except Exception as e:
                        validation_results[endpoint] = {"error": str(e)}
                
                self.test_results["backend_token_validation"] = validation_results
                
                # Check for Issue #501 pattern
                failed_validations = [
                    endpoint for endpoint, result in validation_results.items()
                    if isinstance(result, dict) and result.get("status_code") == 403
                ]
                
                if failed_validations:
                    failure_details = {
                        "failed_endpoints": failed_validations,
                        "total_endpoints_tested": len(test_endpoints),
                        "failure_rate": len(failed_validations) / len(test_endpoints),
                        "issue": "Backend service rejecting valid auth service tokens"
                    }
                    
                    logger.error(f"Backend validation failures: {json.dumps(failure_details, indent=2)}")
                    
                    # This test should fail because Issue #501 exists
                    pytest.fail(f"Backend service token validation failed for {len(failed_validations)} endpoints: {failed_validations}. This indicates Issue #501 cross-service auth breakdown.")
                
                logger.info("✅ Backend service token validation working correctly")
                
        except httpx.ConnectError:
            pytest.skip("Cannot connect to backend service")
        except Exception as e:
            pytest.fail(f"Backend service token validation test failed: {e}")
    
    async def test_jwt_secret_synchronization_issue_501(self):
        """
        Test: JWT secret synchronization between auth and backend services
        Priority: CRITICAL - Primary suspect for Issue #501 root cause
        Expected: SHOULD FAIL - JWT secret mismatch likely causing 403 errors
        """
        
        try:
            # Get a token from auth service
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                login_response = await client.post(
                    f"{self.auth_service_url}/login",
                    json=self.test_user
                )
                
                if login_response.status_code != 200:
                    pytest.skip("Cannot get test token for JWT secret synchronization test")
                
                access_token = login_response.json().get("access_token")
                
                # Try to decode token without verification to check structure
                try:
                    unverified_payload = jwt.decode(access_token, options={"verify_signature": False})
                    token_analysis = {
                        "iss": unverified_payload.get("iss"),
                        "aud": unverified_payload.get("aud"),
                        "exp": unverified_payload.get("exp"),
                        "iat": unverified_payload.get("iat"),
                        "sub": unverified_payload.get("sub")
                    }
                except Exception as e:
                    token_analysis = {"decode_error": str(e)}
                
                # Test if backend can decode the same token
                backend_decode_test = await client.post(
                    f"{self.backend_service_url}/api/auth/debug/decode",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                backend_decode_result = {
                    "status_code": backend_decode_test.status_code,
                    "can_decode": backend_decode_test.status_code == 200
                }
                
                if backend_decode_test.status_code == 200:
                    try:
                        backend_decode_result["decoded_payload"] = backend_decode_test.json()
                    except:
                        backend_decode_result["response_text"] = backend_decode_test.text
                
                jwt_sync_analysis = {
                    "auth_service_token_structure": token_analysis,
                    "backend_service_decode": backend_decode_result,
                    "synchronization_issue": backend_decode_result["status_code"] != 200
                }
                
                self.test_results["jwt_secret_sync"] = jwt_sync_analysis
                
                if jwt_sync_analysis["synchronization_issue"]:
                    logger.error(f"JWT secret synchronization issue detected: {json.dumps(jwt_sync_analysis, indent=2)}")
                    
                    # This indicates the root cause of Issue #501
                    pytest.fail(f"JWT secret synchronization failure detected: Auth service issues tokens that backend cannot decode. Status: {backend_decode_result['status_code']}")
                
                logger.info("✅ JWT secret synchronization appears correct")
                
        except Exception as e:
            pytest.fail(f"JWT secret synchronization test failed: {e}")
    
    async def test_auth_header_format_validation_issue_501(self):
        """
        Test: Authentication header format validation between services
        Priority: MEDIUM - Could be causing auth failures
        Expected: SHOULD PASS unless header format issues exist
        """
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get valid token
                login_response = await client.post(
                    f"{self.auth_service_url}/login",
                    json=self.test_user
                )
                
                if login_response.status_code != 200:
                    pytest.skip("Cannot get test token for header format validation")
                
                access_token = login_response.json().get("access_token")
                
                # Test different header formats
                header_formats = [
                    {"Authorization": f"Bearer {access_token}"},  # Standard format
                    {"Authorization": f"bearer {access_token}"},  # lowercase bearer
                    {"Authorization": access_token},             # No Bearer prefix
                    {"X-Auth-Token": access_token},              # Alternative header
                    {"jwt": access_token},                       # JWT header
                ]
                
                format_results = {}
                
                test_endpoint = "/api/user/profile"
                
                for i, headers in enumerate(header_formats):
                    header_name = list(headers.keys())[0]
                    header_value = list(headers.values())[0]
                    
                    response = await client.get(
                        f"{self.backend_service_url}{test_endpoint}",
                        headers=headers
                    )
                    
                    format_results[f"format_{i}_{header_name}"] = {
                        "header_format": f"{header_name}: {header_value[:20]}...",
                        "status_code": response.status_code,
                        "works": response.status_code not in [401, 403]
                    }
                
                self.test_results["auth_header_formats"] = format_results
                
                # Check if any format works
                working_formats = [
                    fmt for fmt, result in format_results.items()
                    if result.get("works", False)
                ]
                
                if not working_formats:
                    logger.error(f"No authentication header formats work: {json.dumps(format_results, indent=2)}")
                    pytest.fail(f"No authentication header formats accepted by backend service. This may be contributing to Issue #501.")
                
                logger.info(f"✅ Working auth header formats found: {len(working_formats)}")
                
        except Exception as e:
            pytest.fail(f"Auth header format validation test failed: {e}")
    
    async def test_token_expiration_timing_issue_501(self):
        """
        Test: Token expiration timing issues between services
        Priority: LOW - Edge case but could cause intermittent failures
        Expected: SHOULD PASS unless timing issues exist
        """
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get token and check expiration immediately
                login_start = time.time()
                login_response = await client.post(
                    f"{self.auth_service_url}/login",
                    json=self.test_user
                )
                login_end = time.time()
                
                if login_response.status_code != 200:
                    pytest.skip("Cannot get test token for timing validation")
                
                access_token = login_response.json().get("access_token")
                
                # Decode to check expiration
                try:
                    payload = jwt.decode(access_token, options={"verify_signature": False})
                    token_exp = payload.get("exp", 0)
                    token_iat = payload.get("iat", 0)
                    
                    current_time = time.time()
                    
                    timing_analysis = {
                        "login_duration_ms": round((login_end - login_start) * 1000, 2),
                        "token_issued_at": token_iat,
                        "token_expires_at": token_exp,
                        "token_lifetime_seconds": token_exp - token_iat if token_exp and token_iat else 0,
                        "current_time": current_time,
                        "time_until_expiry": token_exp - current_time if token_exp else 0,
                        "token_valid": token_exp > current_time if token_exp else False
                    }
                    
                    # Test token immediately after issuance
                    immediate_test_response = await client.get(
                        f"{self.backend_service_url}/api/user/profile",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    timing_analysis["immediate_validation"] = {
                        "status_code": immediate_test_response.status_code,
                        "works": immediate_test_response.status_code == 200
                    }
                    
                    self.test_results["token_timing"] = timing_analysis
                    
                    # Check for timing issues
                    if timing_analysis["token_valid"] and not timing_analysis["immediate_validation"]["works"]:
                        logger.error(f"Token timing issue detected: {json.dumps(timing_analysis, indent=2)}")
                        pytest.fail(f"Token timing issue: Valid token (expires in {timing_analysis['time_until_expiry']}s) rejected immediately by backend")
                    
                    if timing_analysis["token_lifetime_seconds"] < 60:  # Less than 1 minute
                        logger.warning(f"Very short token lifetime: {timing_analysis['token_lifetime_seconds']}s")
                    
                    logger.info(f"✅ Token timing analysis completed: {timing_analysis['token_lifetime_seconds']}s lifetime")
                    
                except Exception as decode_error:
                    pytest.fail(f"Could not decode token for timing analysis: {decode_error}")
                
        except Exception as e:
            pytest.fail(f"Token timing validation test failed: {e}")
    
    def teardown_method(self, method):
        """Cleanup and results logging after each test"""
        super().teardown_method(method)
        
        if self.test_results:
            logger.info(f"Cross-service auth test results: {json.dumps(self.test_results, indent=2)}")
            
            # Save results for analysis
            results_file = Path(__file__).parent.parent / "test_reports" / "cross_service_auth_results.json"
            results_file.parent.mkdir(exist_ok=True)
            
            with open(results_file, "w") as f:
                json.dump({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_method": method.__name__,
                    "results": self.test_results
                }, f, indent=2)

# Standalone execution for debugging
if __name__ == "__main__":
    async def run_cross_service_debug():
        test_instance = CrossServiceAuthFlowTest()
        
        print("🚀 Starting Cross-Service Authentication Flow Analysis")
        print("=" * 60)
        
        # Run each test method individually for detailed analysis
        test_methods = [
            "test_auth_service_token_issuance_isolated",
            "test_backend_service_token_validation_isolated", 
            "test_jwt_secret_synchronization_issue_501",
            "test_auth_header_format_validation_issue_501",
            "test_token_expiration_timing_issue_501"
        ]
        
        for method_name in test_methods:
            print(f"\n🔍 Running {method_name}")
            try:
                method = getattr(test_instance, method_name)
                await method()
                print(f"✅ {method_name} completed")
            except Exception as e:
                print(f"❌ {method_name} failed: {e}")
        
        print(f"\n📊 Final Results: {json.dumps(test_instance.test_results, indent=2)}")
    
    asyncio.run(run_cross_service_debug())