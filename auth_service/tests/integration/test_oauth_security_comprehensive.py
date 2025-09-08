"""
OAuth Provider Integration and Security Validation Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Secure user onboarding and authentication via OAuth providers
- Value Impact: Enables users to sign up and login easily while maintaining security
- Strategic Impact: OAuth failures block user acquisition and cause security vulnerabilities

This test suite validates OAuth provider integration and security validation
from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml and critical auth flows:

1. OAuth provider configuration and credential validation
2. OAuth redirect URI validation and security
3. OAuth state parameter validation (CSRF protection)
4. OAuth token exchange and user data extraction
5. OAuth callback security and error handling
6. Multi-provider OAuth support and isolation

CRITICAL: OAuth vulnerabilities can lead to account takeover attacks,
CSRF attacks, and unauthorized access. These tests prevent security breaches
that could compromise user accounts and platform integrity.

Incident References:
- OAuth redirect mismatches cause authentication failures
- Missing OAuth state validation enables CSRF attacks
- OAuth configuration errors block new user signups
"""

import asyncio
import json
import logging
import secrets
import time
import urllib.parse
from typing import Dict, Any, Optional, List
from unittest.mock import patch, AsyncMock, MagicMock
from urllib.parse import urlparse, parse_qs

import aiohttp
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestUtility
from test_framework.ssot.integration_auth_manager import (
    IntegrationAuthServiceManager,
    IntegrationTestAuthHelper,
    create_integration_test_helper
)
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class TestOAuthSecurityComprehensive(SSotBaseTestCase):
    """
    OAuth Provider Integration and Security Validation Tests.
    
    Tests critical OAuth flows and security validations using real auth service
    and mocked OAuth providers (external APIs can be mocked for integration tests).
    
    CRITICAL: Tests both successful OAuth flows and security attack scenarios
    to ensure robust OAuth implementation.
    """
    
    @pytest.fixture(scope="class")
    async def auth_manager(self):
        """Start real auth service for OAuth integration testing."""
        manager = IntegrationAuthServiceManager()
        
        # Start auth service with OAuth configuration
        success = await manager.start_auth_service()
        if not success:
            pytest.fail("Failed to start auth service for OAuth integration tests")
        
        yield manager
        
        # Cleanup
        await manager.stop_auth_service()
    
    @pytest.fixture
    async def auth_helper(self, auth_manager):
        """Create auth helper for OAuth integration testing."""
        helper = IntegrationTestAuthHelper(auth_manager)
        yield helper
    
    @pytest.fixture
    async def test_database(self):
        """Provide isolated test database session."""
        async with DatabaseTestUtility("auth_service").transaction_scope() as db_session:
            yield db_session
    
    @pytest.fixture
    def oauth_test_config(self):
        """Provide OAuth test configuration."""
        return {
            "google": {
                "client_id": "test-google-client-id",
                "client_secret": "test-google-client-secret",
                "redirect_uri": "http://localhost:8081/auth/oauth/google/callback",
                "scopes": ["openid", "email", "profile"]
            },
            "github": {
                "client_id": "test-github-client-id",
                "client_secret": "test-github-client-secret",
                "redirect_uri": "http://localhost:8081/auth/oauth/github/callback",
                "scopes": ["user:email"]
            }
        }
    
    @pytest.fixture
    def mock_oauth_responses(self):
        """Provide mock OAuth provider responses."""
        return {
            "google_token_response": {
                "access_token": "mock-google-access-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "mock-google-refresh-token",
                "scope": "openid email profile",
                "id_token": "mock-google-id-token"
            },
            "google_user_info": {
                "id": "123456789",
                "email": "oauth.test@gmail.com",
                "verified_email": True,
                "name": "OAuth Test User",
                "given_name": "OAuth",
                "family_name": "User",
                "picture": "https://example.com/avatar.jpg"
            },
            "github_token_response": {
                "access_token": "mock-github-access-token",
                "scope": "user:email",
                "token_type": "bearer"
            },
            "github_user_info": {
                "id": 987654321,
                "login": "oauth-test-user",
                "email": "oauth.test@github.com",
                "name": "OAuth Test User",
                "avatar_url": "https://github.com/avatar.jpg"
            }
        }
    
    # === OAUTH CONFIGURATION AND SETUP TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_provider_configuration_validation(
        self, auth_manager, oauth_test_config
    ):
        """
        Integration test for OAuth provider configuration validation.
        
        Tests that OAuth providers are properly configured with valid
        client IDs, secrets, and redirect URIs.
        """
        # Record test metadata
        self.record_metric("test_category", "oauth_configuration")
        self.record_metric("test_focus", "provider_config_validation")
        
        # Test OAuth configuration for each provider
        for provider, config in oauth_test_config.items():
            logger.debug(f"Testing OAuth configuration for provider: {provider}")
            
            # Test OAuth authorization URL generation
            auth_url = await self._get_oauth_authorization_url(
                auth_manager, provider, config
            )
            
            assert auth_url is not None, f"Failed to get OAuth authorization URL for {provider}"
            
            # Validate authorization URL structure
            parsed_url = urlparse(auth_url)
            assert parsed_url.scheme in ["http", "https"], f"Invalid OAuth URL scheme for {provider}"
            assert parsed_url.netloc, f"Missing OAuth URL domain for {provider}"
            
            # Validate authorization URL parameters
            query_params = parse_qs(parsed_url.query)
            
            # Required OAuth parameters
            required_params = ["client_id", "redirect_uri", "response_type", "state"]
            for param in required_params:
                assert param in query_params, f"Missing required OAuth parameter '{param}' for {provider}"
            
            # Validate specific parameter values
            assert query_params["client_id"][0] == config["client_id"], (
                f"OAuth client_id mismatch for {provider}"
            )
            assert query_params["redirect_uri"][0] == config["redirect_uri"], (
                f"OAuth redirect_uri mismatch for {provider}"
            )
            assert query_params["response_type"][0] == "code", (
                f"OAuth response_type should be 'code' for {provider}"
            )
            
            # Validate state parameter (CSRF protection)
            state_param = query_params["state"][0]
            assert len(state_param) >= 16, f"OAuth state parameter too short for {provider} (CSRF vulnerability)"
            
            self.record_metric(f"oauth_config_{provider}", "valid")
            self.increment_db_query_count(1)  # Configuration lookup
        
        self.record_metric("oauth_configuration_validation", "working")
        logger.info(f"✅ OAuth provider configuration validation working ({len(oauth_test_config)} providers)")
    
    async def _get_oauth_authorization_url(
        self, 
        auth_manager: IntegrationAuthServiceManager, 
        provider: str, 
        config: Dict[str, Any]
    ) -> Optional[str]:
        """Get OAuth authorization URL from auth service."""
        try:
            async with aiohttp.ClientSession() as session:
                request_data = {
                    "provider": provider,
                    "redirect_uri": config["redirect_uri"],
                    "scopes": config["scopes"]
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/oauth/{provider}/authorize",
                    json=request_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("authorization_url")
                    else:
                        logger.warning(f"OAuth authorization URL request failed: {response.status}")
                        return None
        except Exception as e:
            logger.warning(f"OAuth authorization URL request error: {e}")
            return None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_redirect_uri_security_validation(
        self, auth_manager, oauth_test_config
    ):
        """
        Integration test for OAuth redirect URI security validation.
        
        Tests that OAuth redirect URIs are properly validated to prevent
        redirect attacks and unauthorized callback handling.
        
        CRITICAL: Invalid redirect URI validation can enable OAuth hijacking attacks.
        """
        # Record test metadata
        self.record_metric("test_category", "oauth_security")
        self.record_metric("test_focus", "redirect_uri_validation")
        
        provider = "google"  # Test with Google OAuth
        valid_config = oauth_test_config[provider]
        
        # Test valid redirect URI (should work)
        valid_auth_url = await self._get_oauth_authorization_url(
            auth_manager, provider, valid_config
        )
        assert valid_auth_url is not None, "Valid redirect URI should be accepted"
        self.record_metric("valid_redirect_uri_test", "passed")
        
        # Test invalid redirect URIs (should be rejected)
        invalid_redirect_scenarios = [
            {
                "name": "malicious_domain",
                "redirect_uri": "https://malicious-site.com/oauth/callback",
                "reason": "Different domain should be rejected"
            },
            {
                "name": "open_redirect", 
                "redirect_uri": "http://localhost:8081/auth/oauth/google/callback?redirect=https://evil.com",
                "reason": "Open redirect parameters should be rejected"
            },
            {
                "name": "javascript_scheme",
                "redirect_uri": "javascript:alert('xss')",
                "reason": "JavaScript scheme should be rejected"
            },
            {
                "name": "data_scheme",
                "redirect_uri": "data:text/html,<script>alert('xss')</script>",
                "reason": "Data scheme should be rejected"
            }
        ]
        
        for scenario in invalid_redirect_scenarios:
            scenario_name = scenario["name"]
            invalid_redirect = scenario["redirect_uri"]
            
            logger.debug(f"Testing invalid redirect URI scenario: {scenario_name}")
            
            # Create config with invalid redirect URI
            invalid_config = valid_config.copy()
            invalid_config["redirect_uri"] = invalid_redirect
            
            # This should fail or return None
            invalid_auth_url = await self._get_oauth_authorization_url(
                auth_manager, provider, invalid_config
            )
            
            # Should reject invalid redirect URIs
            assert invalid_auth_url is None, (
                f"Invalid redirect URI scenario '{scenario_name}' should be rejected. "
                f"{scenario['reason']}. This is a security vulnerability."
            )
            
            self.record_metric(f"invalid_redirect_{scenario_name}", "correctly_rejected")
            self.increment_db_query_count(1)
        
        self.record_metric("redirect_uri_security", "working")
        logger.info(f"✅ OAuth redirect URI security validation working ({len(invalid_redirect_scenarios)} attack scenarios blocked)")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_state_parameter_csrf_protection(
        self, auth_manager, oauth_test_config
    ):
        """
        Integration test for OAuth state parameter CSRF protection.
        
        Tests that OAuth state parameters are properly generated, validated,
        and protect against CSRF attacks.
        
        CRITICAL: Missing state validation enables CSRF attacks on OAuth flow.
        """
        # Record test metadata
        self.record_metric("test_category", "oauth_csrf_protection")
        self.record_metric("test_focus", "state_parameter_validation")
        
        provider = "google"
        config = oauth_test_config[provider]
        
        # Step 1: Generate multiple authorization URLs and collect state parameters
        state_parameters = []
        num_requests = 5
        
        for i in range(num_requests):
            auth_url = await self._get_oauth_authorization_url(
                auth_manager, provider, config
            )
            
            assert auth_url is not None, f"Failed to get OAuth authorization URL for request {i}"
            
            # Extract state parameter
            parsed_url = urlparse(auth_url)
            query_params = parse_qs(parsed_url.query)
            state_param = query_params.get("state", [None])[0]
            
            assert state_param is not None, f"Missing state parameter in request {i}"
            state_parameters.append(state_param)
            
            self.increment_db_query_count(1)
        
        # Step 2: Validate state parameters are unique (prevent replay attacks)
        unique_states = set(state_parameters)
        assert len(unique_states) == len(state_parameters), (
            "OAuth state parameters are not unique. This enables replay attacks."
        )
        
        # Step 3: Validate state parameter characteristics
        for i, state in enumerate(state_parameters):
            # Should be sufficiently long
            assert len(state) >= 16, (
                f"State parameter {i} is too short ({len(state)} chars). "
                f"Short state parameters are vulnerable to brute force attacks."
            )
            
            # Should be cryptographically random (basic entropy check)
            # Convert to bytes for entropy analysis
            state_bytes = state.encode('utf-8')
            unique_chars = len(set(state_bytes))
            assert unique_chars >= len(state) * 0.5, (
                f"State parameter {i} has low entropy. This reduces CSRF protection effectiveness."
            )
        
        self.record_metric("state_parameters_generated", len(state_parameters))
        self.record_metric("state_uniqueness", "confirmed")
        self.record_metric("csrf_protection", "working")
        
        logger.info(f"✅ OAuth state parameter CSRF protection working ({len(state_parameters)} unique states)")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_callback_security_validation(
        self, auth_manager, oauth_test_config, mock_oauth_responses
    ):
        """
        Integration test for OAuth callback security validation.
        
        Tests OAuth callback handling including state validation, 
        authorization code processing, and user data extraction.
        """
        # Record test metadata
        self.record_metric("test_category", "oauth_callback_security")
        self.record_metric("test_focus", "callback_validation")
        
        provider = "google"
        config = oauth_test_config[provider]
        
        # Step 1: Get authorization URL with valid state
        auth_url = await self._get_oauth_authorization_url(
            auth_manager, provider, config
        )
        
        assert auth_url is not None, "Failed to get OAuth authorization URL"
        
        # Extract state parameter for callback validation
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        original_state = query_params["state"][0]
        
        # Step 2: Test valid OAuth callback (should work)
        valid_callback_success = await self._test_oauth_callback(
            auth_manager, provider, config, 
            authorization_code="valid-test-code",
            state=original_state,
            mock_responses=mock_oauth_responses,
            should_succeed=True,
            scenario="valid_callback"
        )
        
        assert valid_callback_success, "Valid OAuth callback should succeed"
        
        # Step 3: Test invalid OAuth callback scenarios
        invalid_callback_scenarios = [
            {
                "name": "wrong_state",
                "authorization_code": "valid-test-code",
                "state": "wrong-state-parameter",
                "reason": "Wrong state parameter should be rejected (CSRF protection)"
            },
            {
                "name": "missing_state",
                "authorization_code": "valid-test-code", 
                "state": None,
                "reason": "Missing state parameter should be rejected"
            },
            {
                "name": "missing_code",
                "authorization_code": None,
                "state": original_state,
                "reason": "Missing authorization code should be rejected"
            },
            {
                "name": "empty_code",
                "authorization_code": "",
                "state": original_state, 
                "reason": "Empty authorization code should be rejected"
            }
        ]
        
        for scenario in invalid_callback_scenarios:
            scenario_name = scenario["name"]
            
            logger.debug(f"Testing invalid OAuth callback scenario: {scenario_name}")
            
            callback_success = await self._test_oauth_callback(
                auth_manager, provider, config,
                authorization_code=scenario["authorization_code"],
                state=scenario["state"],
                mock_responses=mock_oauth_responses,
                should_succeed=False,
                scenario=scenario_name
            )
            
            assert not callback_success, (
                f"Invalid OAuth callback scenario '{scenario_name}' should be rejected. "
                f"{scenario['reason']}. This is a security vulnerability."
            )
            
            self.record_metric(f"invalid_callback_{scenario_name}", "correctly_rejected")
        
        self.record_metric("oauth_callback_security", "working")
        logger.info(f"✅ OAuth callback security validation working ({len(invalid_callback_scenarios)} attack scenarios blocked)")
    
    async def _test_oauth_callback(
        self,
        auth_manager: IntegrationAuthServiceManager,
        provider: str,
        config: Dict[str, Any],
        authorization_code: Optional[str],
        state: Optional[str],
        mock_responses: Dict[str, Any],
        should_succeed: bool,
        scenario: str
    ) -> bool:
        """Test OAuth callback handling."""
        try:
            # Mock external OAuth provider responses
            with patch('aiohttp.ClientSession.post') as mock_post:
                # Setup mock response for token exchange
                mock_response = AsyncMock()
                mock_response.status = 200 if should_succeed else 400
                mock_response.json = AsyncMock(return_value=mock_responses.get(f"{provider}_token_response", {}))
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Prepare callback parameters
                callback_params = {}
                if authorization_code is not None:
                    callback_params["code"] = authorization_code
                if state is not None:
                    callback_params["state"] = state
                
                # Test OAuth callback
                async with aiohttp.ClientSession() as session:
                    callback_url = f"{auth_manager.get_auth_url()}/auth/oauth/{provider}/callback"
                    
                    async with session.get(
                        callback_url,
                        params=callback_params
                    ) as response:
                        if should_succeed:
                            # Valid callbacks should succeed (200 or redirect)
                            success = response.status in [200, 302]
                        else:
                            # Invalid callbacks should fail (400, 401, 403)
                            success = response.status not in [200, 302]
                        
                        self.record_metric(f"callback_test_{scenario}", "passed" if success else "failed")
                        self.increment_db_query_count(1)
                        
                        return success if should_succeed else not success
                        
        except Exception as e:
            logger.warning(f"OAuth callback test error for scenario {scenario}: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_token_exchange_security(
        self, auth_manager, oauth_test_config, mock_oauth_responses
    ):
        """
        Integration test for OAuth token exchange security.
        
        Tests the security of token exchange process including proper
        validation of authorization codes and secure token handling.
        """
        # Record test metadata
        self.record_metric("test_category", "oauth_token_exchange")
        self.record_metric("test_focus", "token_exchange_security")
        
        provider = "google"
        config = oauth_test_config[provider]
        
        # Test token exchange with various scenarios
        token_exchange_scenarios = [
            {
                "name": "valid_exchange",
                "authorization_code": "valid-authorization-code",
                "mock_status": 200,
                "mock_response": mock_oauth_responses["google_token_response"],
                "should_succeed": True
            },
            {
                "name": "invalid_code",
                "authorization_code": "invalid-authorization-code",
                "mock_status": 400,
                "mock_response": {"error": "invalid_grant"},
                "should_succeed": False
            },
            {
                "name": "expired_code",
                "authorization_code": "expired-authorization-code",
                "mock_status": 400,
                "mock_response": {"error": "invalid_grant", "error_description": "Code expired"},
                "should_succeed": False
            },
            {
                "name": "provider_error",
                "authorization_code": "valid-code-but-provider-error",
                "mock_status": 500,
                "mock_response": {"error": "server_error"},
                "should_succeed": False
            }
        ]
        
        for scenario in token_exchange_scenarios:
            scenario_name = scenario["name"]
            
            logger.debug(f"Testing token exchange scenario: {scenario_name}")
            
            # Mock OAuth provider token exchange response
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status = scenario["mock_status"]
                mock_response.json = AsyncMock(return_value=scenario["mock_response"])
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Test token exchange
                exchange_success = await self._test_token_exchange(
                    auth_manager, provider, config,
                    authorization_code=scenario["authorization_code"],
                    scenario=scenario_name
                )
                
                if scenario["should_succeed"]:
                    assert exchange_success, (
                        f"Token exchange scenario '{scenario_name}' should succeed but failed"
                    )
                else:
                    assert not exchange_success, (
                        f"Token exchange scenario '{scenario_name}' should fail but succeeded. "
                        f"This indicates insufficient error handling."
                    )
                
                self.record_metric(f"token_exchange_{scenario_name}", "passed")
        
        self.record_metric("oauth_token_exchange_security", "working")
        logger.info(f"✅ OAuth token exchange security working ({len(token_exchange_scenarios)} scenarios tested)")
    
    async def _test_token_exchange(
        self,
        auth_manager: IntegrationAuthServiceManager,
        provider: str,
        config: Dict[str, Any],
        authorization_code: str,
        scenario: str
    ) -> bool:
        """Test OAuth token exchange."""
        try:
            async with aiohttp.ClientSession() as session:
                exchange_data = {
                    "code": authorization_code,
                    "redirect_uri": config["redirect_uri"],
                    "provider": provider
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/oauth/{provider}/token",
                    json=exchange_data
                ) as response:
                    success = response.status == 200
                    
                    if success:
                        result = await response.json()
                        # Should return access_token or JWT
                        success = "access_token" in result or "jwt" in result
                    
                    self.record_metric(f"token_exchange_test_{scenario}", "success" if success else "failed")
                    self.increment_db_query_count(1)
                    
                    return success
                    
        except Exception as e:
            logger.warning(f"Token exchange test error for scenario {scenario}: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_user_data_extraction_security(
        self, auth_manager, oauth_test_config, mock_oauth_responses
    ):
        """
        Integration test for OAuth user data extraction security.
        
        Tests secure extraction and validation of user data from OAuth providers
        including email verification and data sanitization.
        """
        # Record test metadata
        self.record_metric("test_category", "oauth_user_data")
        self.record_metric("test_focus", "data_extraction_security")
        
        # Test user data extraction for different providers
        for provider in ["google", "github"]:
            logger.debug(f"Testing user data extraction for provider: {provider}")
            
            config = oauth_test_config[provider]
            mock_user_data = mock_oauth_responses[f"{provider}_user_info"]
            
            # Mock OAuth provider API responses
            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=mock_user_data)
                mock_get.return_value.__aenter__.return_value = mock_response
                
                # Test user data extraction
                extracted_data = await self._test_user_data_extraction(
                    auth_manager, provider, config,
                    access_token="mock-access-token"
                )
                
                assert extracted_data is not None, f"Failed to extract user data for {provider}"
                
                # Validate required user data fields
                required_fields = ["id", "email", "name"]
                for field in required_fields:
                    assert field in extracted_data, (
                        f"Missing required field '{field}' in extracted data for {provider}"
                    )
                
                # Validate email format
                email = extracted_data.get("email", "")
                assert "@" in email, f"Invalid email format for {provider}: {email}"
                
                # Validate data sanitization (no script tags, etc.)
                name = extracted_data.get("name", "")
                dangerous_patterns = ["<script", "javascript:", "data:"]
                for pattern in dangerous_patterns:
                    assert pattern.lower() not in name.lower(), (
                        f"Unsanitized user data contains dangerous pattern '{pattern}' for {provider}"
                    )
                
                self.record_metric(f"user_data_extraction_{provider}", "secure")
                self.increment_db_query_count(1)
        
        self.record_metric("oauth_user_data_extraction", "working")
        logger.info("✅ OAuth user data extraction security working (2 providers tested)")
    
    async def _test_user_data_extraction(
        self,
        auth_manager: IntegrationAuthServiceManager,
        provider: str,
        config: Dict[str, Any],
        access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Test OAuth user data extraction."""
        try:
            async with aiohttp.ClientSession() as session:
                request_data = {
                    "access_token": access_token,
                    "provider": provider
                }
                
                async with session.post(
                    f"{auth_manager.get_auth_url()}/auth/oauth/{provider}/user",
                    json=request_data
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"User data extraction failed for {provider}: {response.status}")
                        return None
                        
        except Exception as e:
            logger.warning(f"User data extraction error for {provider}: {e}")
            return None
    
    # === TEARDOWN AND VALIDATION ===
    
    def teardown_method(self, method=None):
        """Enhanced teardown with OAuth-specific metrics validation."""
        super().teardown_method(method)
        
        # Validate OAuth-specific metrics were recorded
        metrics = self.get_all_metrics()
        
        # Ensure OAuth tests recorded their metrics
        if "oauth" in method.__name__.lower() if method else "":
            assert "test_category" in metrics, "OAuth tests must record test_category metric"
            assert "test_focus" in metrics, "OAuth tests must record test_focus metric"
        
        # Log OAuth-specific metrics for analysis
        oauth_metrics = {k: v for k, v in metrics.items() if "oauth" in k.lower()}
        if oauth_metrics:
            logger.info(f"OAuth test metrics: {oauth_metrics}")
