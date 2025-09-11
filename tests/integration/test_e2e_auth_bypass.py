"""
Integration tests for E2E authentication bypass mechanism (issue #254).

Tests the complete E2E authentication flow to ensure:
1. E2E bypass endpoint accepts valid bypass keys
2. Authentication bypass works end-to-end in staging
3. Proper HTTP status codes and responses
4. Security restrictions are enforced
5. Integration between auth routes and secret loader

These tests validate the complete fix for the E2E_OAUTH_SIMULATION_KEY issue
that was preventing staging E2E tests from authenticating properly.

Business Value: Platform/Internal - E2E Testing Infrastructure  
Enables automated testing of $500K+ ARR functionality in staging environment.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional
import json

# SSOT: Import SSOT base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import FastAPI components for testing
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import auth service components
from auth_service.auth_core.routes.auth_routes import router
from auth_service.auth_core.secret_loader import AuthSecretLoader


class TestE2EAuthBypass(SSotAsyncTestCase):
    """
    Integration tests for E2E authentication bypass mechanism.
    
    CRITICAL: These tests validate the complete E2E authentication flow
    that enables automated testing of business-critical functionality.
    """
    
    def setup_method(self, method=None):
        """Set up test client and environment for each test."""
        super().setup_method(method)
        
        # Create FastAPI test app with auth routes
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)
        
        # Default staging environment
        self.set_env_var("ENVIRONMENT", "staging")
        
        # Record test setup
        self.record_metric("test_setup", "auth_bypass_integration")

    def test_e2e_auth_bypass_staging_success(self):
        """
        Test successful E2E authentication bypass in staging environment.
        
        EXPECTED TO PASS: This validates the complete fix for issue #254.
        """
        # Set up staging environment with valid E2E key
        bypass_key = "staging-e2e-test-bypass-key-2025"
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            E2E_OAUTH_SIMULATION_KEY=bypass_key
        ):
            # Make request to E2E auth endpoint with valid bypass key
            response = self.client.post(
                "/api/auth/e2e/test-auth",
                headers={
                    "X-E2E-Bypass-Key": bypass_key,
                    "Content-Type": "application/json"
                }
            )
            
            # Assertions
            self.assertEqual(response.status_code, 200, "E2E auth bypass should succeed in staging")
            
            # Validate response structure
            response_data = response.json()
            self.assertIn("access_token", response_data, "Response should include access token")
            self.assertIn("user", response_data, "Response should include user data")
            
            # Validate token structure (should be JWT-like)
            access_token = response_data["access_token"]
            self.assertIsInstance(access_token, str, "Access token should be a string")
            self.assertGreater(len(access_token), 10, "Access token should be substantial")
            
            # Record success metrics
            self.record_metric("e2e_bypass_success", True)
            self.record_metric("response_structure_valid", True)
            self.record_metric("token_length", len(access_token))

    def test_e2e_auth_bypass_invalid_key_rejected(self):
        """
        Test E2E authentication bypass rejects invalid bypass keys.
        
        EXPECTED TO PASS: Security validation should reject invalid keys.
        """
        # Set up staging environment with valid E2E key
        valid_key = "staging-e2e-test-bypass-key-2025"
        invalid_key = "invalid-wrong-bypass-key"
        
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            E2E_OAUTH_SIMULATION_KEY=valid_key
        ):
            # Make request with invalid bypass key
            response = self.client.post(
                "/api/auth/e2e/test-auth",
                headers={
                    "X-E2E-Bypass-Key": invalid_key,
                    "Content-Type": "application/json"
                }
            )
            
            # Assertions
            self.assertEqual(response.status_code, 401, "Invalid bypass key should be rejected")
            
            # Validate error response
            response_data = response.json()
            self.assertIn("detail", response_data, "Error response should include detail")
            
            # Record security validation
            self.record_metric("invalid_key_rejected", True)
            self.record_metric("security_validation", "key_mismatch_blocked")

    def test_e2e_auth_bypass_missing_key_header_rejected(self):
        """
        Test E2E authentication bypass rejects requests without bypass key header.
        
        EXPECTED TO PASS: Missing header should be rejected for security.
        """
        # Set up staging environment with valid E2E key
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            E2E_OAUTH_SIMULATION_KEY="staging-e2e-test-bypass-key-2025"
        ):
            # Make request WITHOUT X-E2E-Bypass-Key header
            response = self.client.post(
                "/api/auth/e2e/test-auth",
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            # Assertions
            self.assertEqual(response.status_code, 401, "Missing bypass key header should be rejected")
            
            # Validate error response
            response_data = response.json()
            self.assertIn("detail", response_data, "Error response should include detail")
            detail_message = response_data["detail"].lower()
            self.assertIn("bypass key", detail_message, "Error should mention bypass key requirement")
            
            # Record security validation
            self.record_metric("missing_header_rejected", True)
            self.record_metric("security_validation", "missing_header_blocked")

    def test_e2e_auth_bypass_production_environment_blocked(self):
        """
        Test E2E authentication bypass is completely blocked in production.
        
        EXPECTED TO PASS: Production environment should reject all E2E bypass attempts.
        """
        # Set up production environment with E2E key (should be ignored)
        with self.temp_env_vars(
            ENVIRONMENT="production",
            E2E_OAUTH_SIMULATION_KEY="should-never-work-in-production"
        ):
            # Make request with bypass key in production
            response = self.client.post(
                "/api/auth/e2e/test-auth",
                headers={
                    "X-E2E-Bypass-Key": "should-never-work-in-production",
                    "Content-Type": "application/json"
                }
            )
            
            # Assertions
            self.assertEqual(response.status_code, 403, "Production should block all E2E bypass attempts")
            
            # Validate security response
            response_data = response.json()
            self.assertIn("detail", response_data)
            detail_message = response_data["detail"].lower()
            self.assertIn("production", detail_message, "Error should mention production restriction")
            
            # Record production security
            self.record_metric("production_blocked", True)
            self.record_metric("security_compliance", "production_bypass_completely_blocked")

    @patch('auth_service.auth_core.secret_loader.AuthSecretLoader._load_from_secret_manager')
    def test_e2e_auth_bypass_secret_manager_integration(self, mock_secret_manager):
        """
        Test E2E authentication bypass with Secret Manager integration.
        
        EXPECTED TO PASS: Should work when key is loaded from Secret Manager.
        """
        # Mock Secret Manager to return bypass key
        bypass_key = "secret-manager-e2e-bypass-key-staging"
        mock_secret_manager.return_value = bypass_key
        
        # Set up staging environment WITHOUT environment variable
        with self.temp_env_vars(
            ENVIRONMENT="staging"
        ):
            # Ensure no environment variable is set
            self.delete_env_var("E2E_OAUTH_SIMULATION_KEY")
            
            # Make request with Secret Manager bypass key
            response = self.client.post(
                "/api/auth/e2e/test-auth",
                headers={
                    "X-E2E-Bypass-Key": bypass_key,
                    "Content-Type": "application/json"
                }
            )
            
            # Assertions
            self.assertEqual(response.status_code, 200, "Secret Manager key should work for E2E bypass")
            
            # Verify Secret Manager was called
            mock_secret_manager.assert_called_with("e2e-bypass-key")
            
            # Validate response
            response_data = response.json()
            self.assertIn("access_token", response_data)
            
            # Record Secret Manager integration
            self.record_metric("secret_manager_integration", True)
            self.record_metric("e2e_key_source", "secret_manager")

    @patch('auth_service.auth_core.secret_loader.AuthSecretLoader._load_from_secret_manager')
    def test_e2e_auth_bypass_key_not_configured_error(self, mock_secret_manager):
        """
        Test E2E authentication bypass when key is not configured anywhere.
        
        ORIGINAL ISSUE REPRODUCTION: This should demonstrate the configuration
        issue that was preventing E2E tests from working in staging.
        """
        # Mock Secret Manager to return None (not configured)
        mock_secret_manager.return_value = None
        
        # Set up staging environment WITHOUT E2E key anywhere
        with self.temp_env_vars(
            ENVIRONMENT="staging"
        ):
            # Ensure no environment variable is set
            self.delete_env_var("E2E_OAUTH_SIMULATION_KEY")
            
            # Make request with any bypass key (should fail - key not configured)
            response = self.client.post(
                "/api/auth/e2e/test-auth",
                headers={
                    "X-E2E-Bypass-Key": "any-key-should-fail",
                    "Content-Type": "application/json"
                }
            )
            
            # Assertions - this demonstrates the original issue
            self.assertIn(response.status_code, [401, 500], "Should fail when E2E key not configured")
            
            # Record configuration issue
            self.record_metric("configuration_error", "key_not_configured_anywhere")
            self.record_metric("original_issue_reproduced", True)

    def test_e2e_auth_bypass_comprehensive_flow_validation(self):
        """
        Comprehensive test validating the complete E2E authentication flow.
        
        This test validates all aspects of the fix for issue #254:
        1. Environment detection
        2. Key loading (env var and Secret Manager)  
        3. HTTP request handling
        4. Response generation
        5. Security validation
        """
        # Test comprehensive flow with multiple scenarios
        test_scenarios = [
            {
                "name": "staging_env_var_success",
                "environment": "staging",
                "env_key": "staging-comprehensive-test-key",
                "request_key": "staging-comprehensive-test-key",
                "expected_status": 200,
                "should_succeed": True
            },
            {
                "name": "staging_key_mismatch_failure", 
                "environment": "staging",
                "env_key": "correct-staging-key",
                "request_key": "wrong-request-key",
                "expected_status": 401,
                "should_succeed": False
            },
            {
                "name": "development_blocked",
                "environment": "development",
                "env_key": "dev-key-should-be-ignored",
                "request_key": "dev-key-should-be-ignored", 
                "expected_status": 401,  # Should be rejected due to environment
                "should_succeed": False
            }
        ]
        
        for scenario in test_scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Set up environment for scenario
                with self.temp_env_vars(
                    ENVIRONMENT=scenario["environment"],
                    E2E_OAUTH_SIMULATION_KEY=scenario["env_key"]
                ):
                    # Make request
                    response = self.client.post(
                        "/api/auth/e2e/test-auth",
                        headers={
                            "X-E2E-Bypass-Key": scenario["request_key"],
                            "Content-Type": "application/json"
                        }
                    )
                    
                    # Validate status code
                    self.assertEqual(
                        response.status_code,
                        scenario["expected_status"],
                        f"Status code mismatch for scenario {scenario['name']}"
                    )
                    
                    # Validate response structure based on expected outcome
                    response_data = response.json()
                    if scenario["should_succeed"]:
                        self.assertIn("access_token", response_data, f"Success response missing token for {scenario['name']}")
                    else:
                        self.assertIn("detail", response_data, f"Error response missing detail for {scenario['name']}")
                    
                    # Record scenario result
                    self.record_metric(f"scenario_{scenario['name']}", {
                        "status_code": response.status_code,
                        "expected_status": scenario["expected_status"],
                        "success": scenario["should_succeed"],
                        "response_valid": True
                    })
        
        # Record comprehensive test completion
        self.record_metric("comprehensive_flow_validation", "all_scenarios_tested")

    def test_e2e_auth_bypass_response_format_validation(self):
        """
        Test that E2E authentication bypass returns properly formatted responses.
        
        EXPECTED TO PASS: Response format should match OAuth standards for compatibility.
        """
        # Set up staging environment with valid bypass
        bypass_key = "format-validation-test-key-2025"
        with self.temp_env_vars(
            ENVIRONMENT="staging",
            E2E_OAUTH_SIMULATION_KEY=bypass_key
        ):
            # Make successful request
            response = self.client.post(
                "/api/auth/e2e/test-auth",
                headers={
                    "X-E2E-Bypass-Key": bypass_key,
                    "Content-Type": "application/json"
                }
            )
            
            # Assertions for successful response
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            
            # Validate required fields
            required_fields = ["access_token", "token_type", "user"]
            for field in required_fields:
                self.assertIn(field, response_data, f"Response should include {field}")
            
            # Validate field types and formats
            self.assertIsInstance(response_data["access_token"], str, "access_token should be string")
            self.assertGreater(len(response_data["access_token"]), 20, "access_token should be substantial")
            
            # Validate user structure
            user_data = response_data["user"]
            self.assertIsInstance(user_data, dict, "user should be object")
            self.assertIn("id", user_data, "user should have id")
            self.assertIn("email", user_data, "user should have email")
            
            # Record response format validation
            self.record_metric("response_format_valid", True)
            self.record_metric("required_fields_present", len(required_fields))
            self.record_metric("access_token_length", len(response_data["access_token"]))

    def teardown_method(self, method=None):
        """Clean up test client and record metrics."""
        # Record final test metrics
        if hasattr(self, '_metrics'):
            execution_time = self._metrics.execution_time
            if execution_time > 0:
                self.record_metric("integration_test_performance", execution_time)
        
        # Clean up client
        if hasattr(self, 'client'):
            del self.client
        if hasattr(self, 'app'):
            del self.app
        
        # Call parent teardown
        super().teardown_method(method)