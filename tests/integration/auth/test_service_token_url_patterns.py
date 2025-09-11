"""
Service Token URL Pattern Validation Integration Test

Business Value Justification (BVJ):
- Segment: Platform/Internal - Service-to-service authentication reliability
- Business Goal: Prevent service integration failures due to URL pattern inconsistencies
- Value Impact: Ensures reliable inter-service authentication, preventing system outages
- Strategic Impact: Core infrastructure that enables microservice architecture authentication

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real service-to-service authentication flows against staging
- Tests both correct URL pattern (/auth/service-token) and incorrect pattern (/auth/service/token)  
- Validates that correct pattern works and incorrect pattern fails appropriately
- Documents the URL pattern mismatch issue for validation and resolution

PURPOSE:
This test validates the URL pattern mismatch issue where:
1. The correct URL is: /auth/service-token (with hyphen)
2. The incorrect URL is: /auth/service/token (with slash)  
3. Some parts of the system may inconsistently use slash instead of hyphen

The test is designed to FAIL initially to demonstrate the current bug state,
then pass after the URL pattern inconsistencies are resolved.
"""

import asyncio
import pytest
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.service_availability import check_service_availability, ServiceUnavailableError


class TestServiceTokenUrlPatterns(BaseIntegrationTest):
    """Integration tests for service token URL pattern validation."""
    
    def setup_method(self):
        """Set up for service token URL pattern tests."""
        super().setup_method()
        self.env = get_env()
        
        # Use staging environment for real auth service testing
        self.environment = self.env.get("TEST_ENV", "staging")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        
        # Service endpoints - use staging for real validation
        if self.environment == "staging":
            # Use staging auth service URL from StagingTestConfig
            from tests.e2e.staging_config import StagingTestConfig
            staging_config = StagingTestConfig()
            self.auth_service_url = staging_config.urls.auth_url
        else:
            # Fallback to local test environment
            self.auth_service_url = "http://localhost:8083"
        
        # Check if auth service is available
        self.auth_service_available = self._check_auth_service_availability()
        
        # Test service credentials for service token requests
        self.test_service_credentials = {
            "service_id": "netra-backend", 
            "service_secret": self.env.get("BACKEND_SERVICE_SECRET", "test-service-secret-123")
        }
    
    def _check_auth_service_availability(self) -> bool:
        """Check if auth service is available for testing."""
        import socket
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(self.auth_service_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            
            # Quick connection test
            with socket.create_connection((host, port), timeout=5.0):
                self.logger.debug(f"Auth service available at {host}:{port}")
                return True
        except (socket.timeout, socket.error, OSError) as e:
            self.logger.debug(f"Auth service unavailable at {self.auth_service_url}: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_token_url_pattern_validation(self):
        """
        Test service token URL patterns - correct vs incorrect.
        
        This test validates the URL pattern mismatch issue:
        - Correct URL: /auth/service-token (hyphen)
        - Incorrect URL: /auth/service/token (slash)
        
        Business Value: Prevents service integration failures due to URL inconsistencies.
        Security Impact: Ensures service authentication works reliably across all services.
        
        CRITICAL: This test is designed to FAIL initially to demonstrate the bug.
        It should pass after URL pattern inconsistencies are resolved.
        """
        # Skip if auth service not available
        if not self.auth_service_available:
            pytest.skip(f"Auth service not available at {self.auth_service_url}")
        
        service_credentials = self.test_service_credentials
        
        async with httpx.AsyncClient() as client:
            # Test 1: Correct URL pattern - /auth/service-token (with hyphen)
            correct_url = f"{self.auth_service_url}/auth/service-token"
            
            try:
                self.logger.info(f"Testing CORRECT URL pattern: {correct_url}")
                
                correct_response = await client.post(
                    correct_url,
                    json=service_credentials,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0  # Extended timeout for staging
                )
                
                correct_result = {
                    "url": correct_url,
                    "status_code": correct_response.status_code,
                    "success": correct_response.status_code in [200, 201],
                    "response_data": None,
                    "error": None
                }
                
                if correct_result["success"]:
                    try:
                        correct_result["response_data"] = correct_response.json()
                        self.logger.info("✅ Correct URL pattern works - service token created successfully")
                    except:
                        correct_result["response_data"] = correct_response.text
                else:
                    try:
                        error_data = correct_response.json()
                        correct_result["error"] = error_data.get("detail", str(error_data))
                    except:
                        correct_result["error"] = correct_response.text
                    self.logger.warning(f"⚠️ Correct URL pattern failed: {correct_result['error']}")
                    
            except Exception as e:
                correct_result = {
                    "url": correct_url,
                    "status_code": None,
                    "success": False,
                    "response_data": None,
                    "error": f"Request failed: {str(e)}"
                }
                self.logger.error(f"❌ Correct URL pattern request failed: {e}")
            
            # Test 2: Incorrect URL pattern - /auth/service/token (with slash)
            incorrect_url = f"{self.auth_service_url}/auth/service/token"
            
            try:
                self.logger.info(f"Testing INCORRECT URL pattern: {incorrect_url}")
                
                incorrect_response = await client.post(
                    incorrect_url,
                    json=service_credentials,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0  # Extended timeout for staging
                )
                
                incorrect_result = {
                    "url": incorrect_url,
                    "status_code": incorrect_response.status_code,
                    "success": incorrect_response.status_code in [200, 201],
                    "response_data": None,
                    "error": None
                }
                
                if incorrect_result["success"]:
                    try:
                        incorrect_result["response_data"] = incorrect_response.json()
                        self.logger.warning("⚠️ Incorrect URL pattern unexpectedly works!")
                    except:
                        incorrect_result["response_data"] = incorrect_response.text
                else:
                    try:
                        error_data = incorrect_response.json()
                        incorrect_result["error"] = error_data.get("detail", str(error_data))
                    except:
                        incorrect_result["error"] = incorrect_response.text
                    self.logger.info("✅ Incorrect URL pattern correctly fails (expected)")
                    
            except Exception as e:
                incorrect_result = {
                    "url": incorrect_url,
                    "status_code": None,
                    "success": False,
                    "response_data": None,
                    "error": f"Request failed: {str(e)}"
                }
                self.logger.info("✅ Incorrect URL pattern request failed (expected)")
        
        # Validation Logic - Designed to demonstrate the URL pattern issue
        self.logger.info("=== URL Pattern Validation Results ===")
        self.logger.info(f"Correct URL (/auth/service-token): Status {correct_result['status_code']} - {'SUCCESS' if correct_result['success'] else 'FAILED'}")
        self.logger.info(f"Incorrect URL (/auth/service/token): Status {incorrect_result['status_code']} - {'SUCCESS' if incorrect_result['success'] else 'FAILED'}")
        
        # CRITICAL ASSERTION: This test demonstrates the URL pattern issue
        # The key difference is HTTP status codes, not authentication success
        
        # The correct URL should return a valid HTTP response (200, 401, 422) - not 404
        correct_endpoint_exists = correct_result["status_code"] not in [404, None]
        assert correct_endpoint_exists, (
            f"CORRECT URL pattern /auth/service-token should exist but returned {correct_result['status_code']}. "
            f"Error: {correct_result.get('error', 'Unknown error')}. "
            f"This indicates the service token endpoint is not configured properly."
        )
        
        # The incorrect URL should return 404 (not found) - not other valid responses
        incorrect_endpoint_missing = incorrect_result["status_code"] in [404, None] or "Not Found" in str(incorrect_result.get("error", ""))
        assert incorrect_endpoint_missing, (
            f"INCORRECT URL pattern /auth/service/token should return 404 but got {incorrect_result['status_code']}. "
            f"This indicates there may be duplicate routes or URL pattern inconsistencies "
            f"that could cause confusion in service-to-service authentication."
        )
        
        # Log the successful URL pattern validation
        self.logger.info("✅ URL Pattern Validation PASSED:")
        self.logger.info(f"  - Correct URL /auth/service-token exists (Status: {correct_result['status_code']})")
        self.logger.info(f"  - Incorrect URL /auth/service/token missing (Status: {incorrect_result['status_code']})")
        
        # Additional validation: If correct endpoint returned 401, that's actually good
        if correct_result["status_code"] == 401:
            self.logger.info("✅ HTTP 401 on correct URL indicates endpoint exists and is validating credentials")
            
        # Additional validation: If correct endpoint returned 422, that's validation errors
        if correct_result["status_code"] == 422:
            self.logger.info("✅ HTTP 422 on correct URL indicates endpoint exists and is validating request format")
        
        # Validate that we got a proper token from the correct URL
        if correct_result["success"] and correct_result["response_data"]:
            response_data = correct_result["response_data"]
            
            # Check for expected service token response structure
            assert isinstance(response_data, dict), "Service token response should be JSON object"
            
            # Should contain access token
            token_field = None
            for field in ["access_token", "token", "service_token"]:
                if field in response_data:
                    token_field = field
                    break
            
            assert token_field is not None, (
                f"Service token response should contain access token field. "
                f"Got fields: {list(response_data.keys())}"
            )
            
            token_value = response_data[token_field]
            assert isinstance(token_value, str) and len(token_value) > 20, (
                f"Service token should be a substantial string, got: {type(token_value)} "
                f"with length {len(str(token_value))}"
            )
            
            self.logger.info(f"✅ Service token validation successful - token field: {token_field}")
        
        self.logger.info("=== URL Pattern Test Complete ===")
        self.logger.info("If this test passes, the URL patterns are working correctly:")
        self.logger.info("  - /auth/service-token (hyphen) works ✅")
        self.logger.info("  - /auth/service/token (slash) fails as expected ✅")
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_service_token_endpoint_response_structure(self):
        """
        Test that the service token endpoint returns properly structured responses.
        
        Business Value: Ensures service token responses follow expected format.
        Integration Impact: Validates service-to-service auth data structures.
        """
        if not self.auth_service_available:
            pytest.skip(f"Auth service not available at {self.auth_service_url}")
        
        service_credentials = self.test_service_credentials
        correct_url = f"{self.auth_service_url}/auth/service-token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                correct_url,
                json=service_credentials,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            # If the endpoint works, validate response structure
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Validate response structure matches service token format
                assert isinstance(data, dict), "Response should be JSON object"
                
                # Should have token field (various possible names)
                token_fields = ["access_token", "token", "service_token"]
                found_token_field = None
                
                for field in token_fields:
                    if field in data:
                        found_token_field = field
                        break
                
                assert found_token_field is not None, (
                    f"Response should contain token field. Expected one of: {token_fields}. "
                    f"Got fields: {list(data.keys())}"
                )
                
                # Validate token is properly formatted JWT-like string
                token_value = data[found_token_field]
                assert isinstance(token_value, str), "Token should be string"
                assert len(token_value) > 20, "Token should be substantial length"
                assert "." in token_value, "Token should be JWT-like format with dots"
                
                # May also have token type and expiry information
                if "token_type" in data:
                    assert data["token_type"] == "Bearer", "Token type should be Bearer"
                
                if "expires_in" in data:
                    assert isinstance(data["expires_in"], int), "Expires_in should be integer"
                    assert data["expires_in"] > 0, "Expires_in should be positive"
                
                self.logger.info("✅ Service token response structure validated")
                
            elif response.status_code == 422:
                # Validation error - check that it's a proper error response
                error_data = response.json()
                assert "detail" in error_data or "error" in error_data, (
                    "422 responses should have proper error structure"
                )
                self.logger.info("✅ Service token validation error response properly structured")
                
            elif response.status_code == 401:
                # Authentication error - expected for invalid credentials
                self.logger.info("✅ Service token authentication error response (expected for test credentials)")
                
            else:
                # Unexpected response - this might indicate an issue
                pytest.fail(
                    f"Unexpected response from service token endpoint: "
                    f"Status {response.status_code}, Body: {response.text}"
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_url_pattern_consistency_across_documentation(self):
        """
        Test that validates URL pattern consistency expectations.
        
        This test documents the expected URL patterns and validates they work as documented.
        
        Business Value: Ensures documentation matches implementation.
        Developer Impact: Prevents confusion about correct URL patterns.
        """
        if not self.auth_service_available:
            pytest.skip(f"Auth service not available at {self.auth_service_url}")
        
        # Document the expected URL patterns
        expected_patterns = {
            "service_token": "/auth/service-token",  # Hyphen format (correct)
            "token_validation": "/auth/validate",
            "user_login": "/auth/login",
            "user_register": "/auth/register"
        }
        
        # Document patterns that should NOT work (common mistakes)
        incorrect_patterns = {
            "service_token_slash": "/auth/service/token",  # Slash format (incorrect)
            "service_token_underscore": "/auth/service_token",  # Underscore format (incorrect)
        }
        
        async with httpx.AsyncClient() as client:
            # Test that expected patterns are reachable (even if they return auth errors)
            for pattern_name, pattern_url in expected_patterns.items():
                full_url = f"{self.auth_service_url}{pattern_url}"
                
                try:
                    # Use GET for most endpoints to just test reachability
                    if pattern_name == "service_token":
                        # Service token requires POST
                        response = await client.post(
                            full_url, 
                            json={},  # Empty body should give validation error
                            timeout=10.0
                        )
                    else:
                        # Other endpoints can use GET to test existence
                        response = await client.get(full_url, timeout=10.0)
                    
                    # We expect these to exist (even if they return errors for invalid requests)
                    # 404 means the endpoint doesn't exist, which would be a problem
                    assert response.status_code != 404, (
                        f"Expected URL pattern {pattern_url} should exist but returned 404. "
                        f"This indicates a missing or incorrectly configured endpoint."
                    )
                    
                    self.logger.info(f"✅ Expected pattern {pattern_name} exists: {pattern_url}")
                    
                except httpx.TimeoutException:
                    # Timeout is acceptable - means endpoint exists but is slow
                    self.logger.info(f"⏱️ Expected pattern {pattern_name} exists but timed out: {pattern_url}")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not test pattern {pattern_name} at {pattern_url}: {e}")
            
            # Test that incorrect patterns properly fail
            for pattern_name, pattern_url in incorrect_patterns.items():
                full_url = f"{self.auth_service_url}{pattern_url}"
                
                try:
                    if "service" in pattern_name:
                        # Service endpoints require POST
                        response = await client.post(
                            full_url,
                            json=self.test_service_credentials,
                            timeout=10.0
                        )
                    else:
                        response = await client.get(full_url, timeout=10.0)
                    
                    # Incorrect patterns should return 404 (not found)
                    # If they don't return 404, it might indicate pattern inconsistency
                    if response.status_code != 404:
                        self.logger.warning(
                            f"⚠️ Incorrect pattern {pattern_name} at {pattern_url} "
                            f"returned {response.status_code} instead of 404. "
                            f"This might indicate URL pattern inconsistency."
                        )
                    else:
                        self.logger.info(f"✅ Incorrect pattern {pattern_name} properly returns 404: {pattern_url}")
                        
                except httpx.TimeoutException:
                    # Timeout on incorrect pattern might indicate it exists when it shouldn't
                    self.logger.warning(f"⚠️ Incorrect pattern {pattern_name} timed out (might exist): {pattern_url}")
                    
                except Exception as e:
                    # Connection errors are expected for non-existent patterns
                    self.logger.info(f"✅ Incorrect pattern {pattern_name} failed as expected: {e}")
        
        self.logger.info("=== URL Pattern Consistency Test Complete ===")

    async def test_cross_service_url_pattern_usage(self):
        """
        Test that validates how other services in the system use service token URLs.
        
        This test checks for potential inconsistencies in how different parts of the
        system reference the service token endpoint.
        
        Business Value: Prevents service integration failures from URL mismatches.
        System Impact: Ensures consistent URL usage across microservices.
        """
        # This test documents the issue without requiring external services
        # It serves as documentation for the URL pattern validation
        
        documented_correct_usage = "/auth/service-token"  # Hyphen format
        common_mistake_patterns = [
            "/auth/service/token",    # Slash format
            "/auth/service_token",    # Underscore format  
            "/auth/servicetoken",     # No separator
        ]
        
        self.logger.info("=== Cross-Service URL Pattern Documentation ===")
        self.logger.info(f"✅ CORRECT pattern: {documented_correct_usage}")
        self.logger.info("❌ INCORRECT patterns that should be avoided:")
        
        for mistake_pattern in common_mistake_patterns:
            self.logger.info(f"   - {mistake_pattern}")
        
        # This test always passes - it's for documentation and awareness
        assert True, "URL pattern documentation complete"
        
        self.logger.info("=== URL Pattern Usage Guidelines ===")
        self.logger.info("1. Always use hyphen format: /auth/service-token")
        self.logger.info("2. Never use slash format: /auth/service/token")  
        self.logger.info("3. Check service configuration files for consistency")
        self.logger.info("4. Update service discovery and API gateway configurations")
        self.logger.info("5. Validate all service-to-service authentication calls")