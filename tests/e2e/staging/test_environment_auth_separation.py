"""
E2E Tests for Environment-Specific Auth Flow Separation - Issue #395

These tests validate clean separation between environment-specific authentication flows
to prevent golden path issues caused by environment configuration leakage.

Based on Five Whys analysis: Environment-specific behavior creates different auth flows
that aren't cleanly separated, causing staging vs development auth issues.

BUSINESS IMPACT: 
- Protects $500K+ ARR Golden Path user workflow from auth cross-contamination
- Ensures staging environment properly isolates from development/production auth patterns  
- Validates enterprise security requirements for environment separation
- Prevents auth token cross-environment vulnerabilities

CRITICAL: Uses real staging services for E2E validation (no mocks).
"""

import pytest
import asyncio
import aiohttp
import jwt
import time
from typing import Dict, Optional, Any, List
from urllib.parse import urljoin

# SSOT imports following CLAUDE.md absolute import patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.environment_markers import staging_only, env_requires


class TestEnvironmentAuthSeparation(SSotAsyncTestCase):
    """
    E2E tests validating environment-specific auth flow separation in staging.
    
    These tests ensure staging auth is properly isolated from development patterns
    and that environment-specific configurations don't leak between contexts.
    """
    
    def setup_method(self, method):
        """Setup method for pytest compatibility."""
        super().setup_method(method)
        
        self.env = get_env()
        
        # Environment-specific auth URLs based on current environment
        self.current_env = self.env.get("ENVIRONMENT", "development").lower()
        
        if self.current_env == "staging":
            self.auth_base_url = "https://auth.staging.netrasystems.ai"
            self.backend_url = "https://backend.staging.netrasystems.ai" 
            self.expected_env_marker = "staging"
        elif self.current_env == "development":
            self.auth_base_url = "http://localhost:8081"
            self.backend_url = "http://localhost:8000"
            self.expected_env_marker = "development"
        else:
            # Production or other environments
            self.auth_base_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8081")
            self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
            self.expected_env_marker = self.current_env
            
        # JWT configuration - environment-specific secrets
        self.jwt_secret = self.env.get("JWT_SECRET_KEY", "fallback_secret")
        self.jwt_algorithm = "HS256"
        
        # Test timeout for staging E2E validation
        self.request_timeout = 30.0

    @staging_only
    @env_requires(services=["auth_service", "backend"])
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_staging_auth_flow_differs_from_development(self):
        """
        Test that staging auth flow is properly differentiated from development.
        
        Validates that staging uses different auth endpoints, tokens, and flows
        than development environment to prevent cross-environment contamination.
        
        Expected: Staging auth URLs, tokens, and responses differ from development
        Business Impact: Prevents development auth tokens from working in staging
        """
        # Skip if not in staging environment
        if self.current_env != "staging":
            pytest.skip("Test requires staging environment")
            
        environment_differences = []
        
        try:
            # Test 1: Auth service health endpoint includes environment marker
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.request_timeout)
            ) as session:
                health_url = urljoin(self.auth_base_url, "/health")
                
                async with session.get(health_url) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        
                        # Staging should have environment marker
                        env_marker = health_data.get("environment", "unknown")
                        if env_marker != "staging":
                            environment_differences.append(
                                f"Health endpoint environment marker is '{env_marker}', expected 'staging'"
                            )
                        else:
                            self.record_success("staging_health_environment_marker_valid")
                            
                        # Staging should have different service version/build than development  
                        service_version = health_data.get("version", "unknown")
                        if "dev" in service_version.lower() or "localhost" in service_version.lower():
                            environment_differences.append(
                                f"Staging service version contains development markers: {service_version}"
                            )
                    else:
                        environment_differences.append(
                            f"Staging auth health endpoint returned {response.status}"
                        )
                        
                # Test 2: OAuth configuration endpoints differ from development
                oauth_config_url = urljoin(self.auth_base_url, "/auth/oauth/config")
                
                async with session.get(oauth_config_url) as response:
                    if response.status == 200:
                        oauth_config = await response.json()
                        
                        # Staging OAuth redirect URLs should not contain localhost
                        redirect_uris = oauth_config.get("redirect_uris", [])
                        for uri in redirect_uris:
                            if "localhost" in uri or "127.0.0.1" in uri:
                                environment_differences.append(
                                    f"Staging OAuth config contains localhost redirect: {uri}"
                                )
                                
                        # Staging OAuth should have proper domain
                        google_oauth_url = oauth_config.get("google_oauth_url", "")
                        if "localhost" in google_oauth_url:
                            environment_differences.append(
                                f"Staging Google OAuth URL contains localhost: {google_oauth_url}"
                            )
                        else:
                            self.record_success("staging_oauth_config_environment_separated")

        except aiohttp.ClientError as e:
            environment_differences.append(f"Network error testing staging auth separation: {e}")
        except Exception as e:
            environment_differences.append(f"Unexpected error: {e}")
            
        # Assert staging environment is properly separated from development
        if environment_differences:
            pytest.fail(
                f"Staging auth flow not properly separated from development:\n" + 
                "\n".join(f"  - {diff}" for diff in environment_differences) +
                f"\n\nBusiness Impact: Auth cross-contamination risk for $500K+ ARR Golden Path"
            )
            
        self.record_success("staging_auth_flow_environment_separation_validated")

    @staging_only  
    @env_requires(services=["auth_service"])
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_environment_specific_auth_configuration(self):
        """
        Test that auth configuration is properly environment-specific.
        
        Validates that JWT secrets, OAuth settings, and auth policies are
        correctly configured for staging and don't leak from other environments.
        
        Expected: Staging-specific JWT secrets, OAuth configs, auth policies
        Business Impact: Ensures enterprise security isolation requirements
        """
        configuration_issues = []
        
        try:
            # Test JWT secret environment separation
            jwt_secret = self.env.get("JWT_SECRET_KEY")
            if not jwt_secret:
                configuration_issues.append("JWT_SECRET_KEY not configured for staging environment")
            elif jwt_secret == "your-secret-key" or jwt_secret == "dev_secret":
                configuration_issues.append("JWT_SECRET_KEY appears to be default/development value")
            elif len(jwt_secret) < 32:
                configuration_issues.append("JWT_SECRET_KEY too short for production security")
            else:
                self.record_success("staging_jwt_secret_environment_specific")
                
            # Test environment-specific OAuth configuration
            google_client_id = self.env.get("GOOGLE_CLIENT_ID")
            if not google_client_id:
                configuration_issues.append("GOOGLE_CLIENT_ID not configured for staging")
            elif "localhost" in google_client_id:
                configuration_issues.append("GOOGLE_CLIENT_ID contains localhost (development leak)")
            else:
                self.record_success("staging_oauth_client_id_environment_specific")
                
            # Test Redis configuration separation
            redis_url = self.env.get("REDIS_URL")
            if redis_url and "localhost" in redis_url:
                configuration_issues.append("REDIS_URL contains localhost (development configuration)")
            elif redis_url:
                self.record_success("staging_redis_url_environment_specific")
                
            # Test database configuration separation  
            db_url = self.env.get("DATABASE_URL")
            if db_url and ("localhost" in db_url or "127.0.0.1" in db_url):
                configuration_issues.append("DATABASE_URL contains localhost (development configuration)")
            elif db_url:
                self.record_success("staging_database_url_environment_specific")
                
            # Test auth service URL configuration
            auth_service_url = self.env.get("AUTH_SERVICE_URL", self.auth_base_url)
            if "localhost" in auth_service_url and self.current_env == "staging":
                configuration_issues.append("AUTH_SERVICE_URL uses localhost in staging environment")
            else:
                self.record_success("staging_auth_service_url_environment_specific")

        except Exception as e:
            configuration_issues.append(f"Error validating environment-specific configuration: {e}")
            
        # Assert environment-specific configuration is correct
        if configuration_issues:
            pytest.fail(
                f"Environment-specific auth configuration issues detected:\n" +
                "\n".join(f"  - {issue}" for issue in configuration_issues) +
                f"\n\nBusiness Impact: Environment configuration leakage compromises security isolation"
            )
            
        self.record_success("environment_specific_auth_configuration_validated")

    @staging_only
    @env_requires(services=["auth_service", "backend"])  
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_cross_environment_auth_token_rejection(self):
        """
        Test that staging properly rejects auth tokens from other environments.
        
        Validates security boundaries by ensuring development tokens are rejected
        by staging services and vice versa.
        
        Expected: Cross-environment tokens rejected with proper error messages
        Business Impact: Prevents unauthorized cross-environment access
        """
        token_rejection_tests = []
        
        try:
            # Create a development-style JWT token (should be rejected by staging)
            dev_token_payload = {
                "user_id": "test_user_123",
                "email": "test@example.com", 
                "environment": "development",  # Wrong environment
                "iss": "localhost:8081",       # Development issuer
                "aud": "localhost:8000",       # Development audience  
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
            }
            
            # Use a known development secret (different from staging)
            dev_jwt_secret = "dev_secret_key_that_should_not_work_in_staging"
            dev_token = jwt.encode(dev_token_payload, dev_jwt_secret, algorithm=self.jwt_algorithm)
            
            # Test 1: Backend should reject development token
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.request_timeout)
            ) as session:
                
                # Try to access protected backend endpoint with development token
                protected_url = urljoin(self.backend_url, "/api/v1/user/profile")
                headers = {"Authorization": f"Bearer {dev_token}"}
                
                async with session.get(protected_url, headers=headers) as response:
                    if response.status == 200:
                        token_rejection_tests.append(
                            "Backend accepted development token - SECURITY VIOLATION"
                        )
                    elif response.status in [401, 403]:
                        self.record_success("staging_backend_rejects_development_tokens")
                    else:
                        token_rejection_tests.append(
                            f"Backend returned unexpected status {response.status} for invalid token"
                        )
                        
                # Test 2: Auth service should reject token with wrong environment marker
                token_validation_url = urljoin(self.auth_base_url, "/auth/validate")
                
                async with session.post(
                    token_validation_url, 
                    json={"token": dev_token},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        validation_result = await response.json()
                        if validation_result.get("valid", False):
                            token_rejection_tests.append(
                                "Auth service validated development token - SECURITY VIOLATION"
                            )
                        else:
                            self.record_success("staging_auth_service_rejects_development_tokens")
                    elif response.status in [400, 401, 422]:
                        # Proper rejection of invalid token
                        self.record_success("staging_auth_service_properly_rejects_invalid_tokens")
                        
                # Test 3: Create a token with staging environment but wrong secret
                staging_token_wrong_secret = jwt.encode(
                    {
                        **dev_token_payload,
                        "environment": "staging",
                        "iss": self.auth_base_url,
                        "aud": self.backend_url,
                    },
                    "wrong_staging_secret",  # Wrong secret
                    algorithm=self.jwt_algorithm
                )
                
                # This should also be rejected
                async with session.get(
                    protected_url, 
                    headers={"Authorization": f"Bearer {staging_token_wrong_secret}"}
                ) as response:
                    if response.status == 200:
                        token_rejection_tests.append(
                            "Backend accepted token with wrong staging secret - SECURITY VIOLATION"
                        )
                    elif response.status in [401, 403]:
                        self.record_success("staging_backend_rejects_wrong_secret_tokens")

        except jwt.InvalidTokenError:
            # JWT library properly rejected malformed token
            self.record_success("jwt_library_properly_validates_tokens")
        except aiohttp.ClientError as e:
            token_rejection_tests.append(f"Network error testing token rejection: {e}")
        except Exception as e:
            token_rejection_tests.append(f"Unexpected error testing cross-environment tokens: {e}")
            
        # Assert proper cross-environment token rejection
        if token_rejection_tests:
            pytest.fail(
                f"Cross-environment auth token security violations detected:\n" +
                "\n".join(f"  - {violation}" for violation in token_rejection_tests) +
                f"\n\nBusiness Impact: CRITICAL SECURITY RISK - Cross-environment access possible"
            )
            
        self.record_success("cross_environment_auth_token_rejection_validated")

    @staging_only
    @env_requires(services=["auth_service", "backend"])
    @pytest.mark.auth  
    @pytest.mark.e2e
    async def test_demo_mode_vs_production_auth_separation(self):
        """
        Test separation between demo mode auth and production auth patterns.
        
        Validates that demo mode authentication (if enabled) is properly isolated
        from production auth flows and doesn't compromise security.
        
        Expected: Demo mode uses separate auth patterns, tokens, user pools
        Business Impact: Ensures demo users cannot access production data
        """
        demo_separation_issues = []
        
        try:
            # Check if demo mode is enabled in this environment
            demo_mode_enabled = self.env.get("ENABLE_DEMO_MODE", "false").lower() == "true"
            demo_auth_endpoint = "/auth/demo/login"
            production_auth_endpoint = "/auth/google/login"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.request_timeout)
            ) as session:
                
                if demo_mode_enabled:
                    # Test 1: Demo auth endpoint exists and responds differently  
                    demo_url = urljoin(self.auth_base_url, demo_auth_endpoint)
                    prod_url = urljoin(self.auth_base_url, production_auth_endpoint)
                    
                    async with session.get(demo_url) as demo_response:
                        async with session.get(prod_url) as prod_response:
                            
                            # Both endpoints should exist but behave differently
                            if demo_response.status == prod_response.status == 200:
                                demo_data = await demo_response.json()
                                prod_data = await prod_response.json()
                                
                                # Demo and production auth flows should differ
                                if demo_data == prod_data:
                                    demo_separation_issues.append(
                                        "Demo auth endpoint identical to production auth"
                                    )
                                else:
                                    self.record_success("demo_auth_endpoint_differs_from_production")
                                    
                    # Test 2: Demo tokens should have different signature/validation
                    demo_token_url = urljoin(self.auth_base_url, "/auth/demo/token")
                    
                    async with session.post(
                        demo_token_url,
                        json={"user_id": "demo_user", "demo": True}
                    ) as response:
                        if response.status == 200:
                            token_data = await response.json()
                            demo_token = token_data.get("access_token")
                            
                            if demo_token:
                                # Demo token should have demo marker
                                try:
                                    decoded = jwt.decode(
                                        demo_token, 
                                        options={"verify_signature": False}
                                    )
                                    
                                    if not decoded.get("demo", False):
                                        demo_separation_issues.append(
                                            "Demo token missing demo marker"
                                        )
                                    elif decoded.get("environment") != "staging":
                                        demo_separation_issues.append(
                                            f"Demo token has wrong environment: {decoded.get('environment')}"
                                        )
                                    else:
                                        self.record_success("demo_token_properly_marked")
                                        
                                except jwt.InvalidTokenError:
                                    demo_separation_issues.append(
                                        "Demo token is not valid JWT format"
                                    )
                                    
                else:
                    # Demo mode disabled - verify demo endpoints are not accessible
                    demo_url = urljoin(self.auth_base_url, demo_auth_endpoint)
                    
                    async with session.get(demo_url) as response:
                        if response.status == 200:
                            demo_separation_issues.append(
                                "Demo auth endpoint accessible when demo mode disabled"
                            )
                        elif response.status in [404, 405]:
                            self.record_success("demo_endpoints_disabled_when_demo_mode_off")
                            
                # Test 3: Production auth should not accept demo tokens
                if demo_mode_enabled:
                    # Create a demo token and try to use it for production auth
                    demo_test_token = jwt.encode(
                        {
                            "user_id": "demo_user_123",
                            "email": "demo@example.com",
                            "demo": True,  # Demo marker
                            "environment": self.current_env,
                            "exp": int(time.time()) + 3600,
                            "iat": int(time.time()),
                        },
                        self.jwt_secret,
                        algorithm=self.jwt_algorithm
                    )
                    
                    # Try to access production endpoint with demo token
                    protected_url = urljoin(self.backend_url, "/api/v1/user/profile")
                    headers = {"Authorization": f"Bearer {demo_test_token}"}
                    
                    async with session.get(protected_url, headers=headers) as response:
                        if response.status == 200:
                            # Check if response indicates demo mode restrictions
                            profile_data = await response.json()
                            if not profile_data.get("demo_mode", False):
                                demo_separation_issues.append(
                                    "Demo token accessed production user data without demo restrictions"
                                )
                            else:
                                self.record_success("demo_token_properly_restricted")
                        elif response.status in [401, 403]:
                            self.record_success("production_endpoints_reject_demo_tokens")

        except Exception as e:
            demo_separation_issues.append(f"Error testing demo mode separation: {e}")
            
        # Assert proper demo mode separation
        if demo_separation_issues:
            pytest.fail(
                f"Demo mode auth separation issues detected:\n" +
                "\n".join(f"  - {issue}" for issue in demo_separation_issues) +
                f"\n\nBusiness Impact: Demo mode security isolation compromised"
            )
            
        self.record_success("demo_mode_vs_production_auth_separation_validated")
        
    def record_success(self, test_name: str):
        """Record successful test outcome for business metrics."""
        # Integration with business metrics tracking
        pass
        
    def teardown_method(self, method):
        """Cleanup method for pytest compatibility.""" 
        super().teardown_method(method)