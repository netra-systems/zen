"""
Test AuthStartupValidator - Critical Authentication Configuration Validation

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Security and User Access Reliability
- Value Impact: Prevents authentication failures that would lock out 100% of users
- Strategic Impact: Critical security validation - single point of failure prevention

CRITICAL: This test suite validates the AuthStartupValidator that ensures all
authentication components are properly configured before system startup.
Failure in this validator means 100% user lockout and complete service unavailability.
"""

import asyncio
import logging
import os
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env
from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator, 
    AuthComponent, 
    AuthValidationResult,
    AuthValidationError,
    validate_auth_startup
)
from netra_backend.app.core.environment_constants import Environment


class TestAuthStartupValidatorInitialization(BaseIntegrationTest):
    """Test AuthStartupValidator initialization and basic setup."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        # Clear any cached values
        self.env.clear_cache()
    
    def test_validator_initialization_development(self):
        """Test validator initializes correctly in development environment."""
        self.env.set("ENVIRONMENT", "development", source="test")
        validator = AuthStartupValidator()
        
        assert validator.env is not None
        assert validator.environment == "development"
        assert validator.is_production is False
        assert validator.validation_results == []
    
    def test_validator_initialization_production(self):
        """Test validator initializes correctly in production environment."""
        self.env.set("ENVIRONMENT", "production", source="test")
        validator = AuthStartupValidator()
        
        assert validator.env is not None
        assert validator.environment == "production"
        assert validator.is_production is True
        assert validator.validation_results == []
    
    def test_validator_initialization_staging(self):
        """Test validator initializes correctly in staging environment."""
        self.env.set("ENVIRONMENT", "staging", source="test")
        validator = AuthStartupValidator()
        
        assert validator.env is not None
        assert validator.environment == "staging"
        assert validator.is_production is False
        assert validator.validation_results == []


class TestAuthStartupValidatorJWTSecretValidation(BaseIntegrationTest):
    """Test JWT secret validation using SSOT JWT manager integration."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
        # Clear JWT manager cache
        try:
            from shared.jwt_secret_manager import get_jwt_secret_manager
            get_jwt_secret_manager().clear_cache()
        except ImportError:
            pass
    
    @pytest.mark.asyncio
    async def test_jwt_secret_validation_success(self):
        """Test JWT secret validation passes with valid secret."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "this_is_a_very_secure_jwt_secret_with_32_plus_characters", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_jwt_secret()
        
        jwt_results = [r for r in validator.validation_results if r.component == AuthComponent.JWT_SECRET]
        assert len(jwt_results) == 1
        assert jwt_results[0].valid is True
        assert jwt_results[0].error is None
    
    @pytest.mark.asyncio
    async def test_jwt_secret_validation_missing_secret(self):
        """Test JWT secret validation fails when no secret configured."""
        self.env.set("ENVIRONMENT", "development", source="test")
        # Don't set any JWT secret variables
        
        validator = AuthStartupValidator()
        await validator._validate_jwt_secret()
        
        jwt_results = [r for r in validator.validation_results if r.component == AuthComponent.JWT_SECRET]
        assert len(jwt_results) == 1
        assert jwt_results[0].valid is False
        assert "No JWT secret configured" in jwt_results[0].error
        assert jwt_results[0].is_critical is True
    
    @pytest.mark.asyncio
    async def test_jwt_secret_validation_too_short(self):
        """Test JWT secret validation fails when secret is too short."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "short_secret", source="test")  # Only 12 chars
        
        validator = AuthStartupValidator()
        await validator._validate_jwt_secret()
        
        jwt_results = [r for r in validator.validation_results if r.component == AuthComponent.JWT_SECRET]
        assert len(jwt_results) == 1
        assert jwt_results[0].valid is False
        assert "too short" in jwt_results[0].error.lower()
        assert jwt_results[0].details["length"] == 12
        assert jwt_results[0].details["minimum"] == 32
    
    @pytest.mark.asyncio
    async def test_jwt_secret_validation_default_values(self):
        """Test JWT secret validation fails with default/weak values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        
        default_secrets = [
            "your-secret-key",
            "test-secret", 
            "secret",
            "emergency_jwt_secret_please_configure_properly",
            "fallback_jwt_secret_for_emergency_only"
        ]
        
        for default_secret in default_secrets:
            self.env.set("JWT_SECRET_KEY", default_secret, source="test")
            validator = AuthStartupValidator()
            await validator._validate_jwt_secret()
            
            jwt_results = [r for r in validator.validation_results if r.component == AuthComponent.JWT_SECRET]
            assert len(jwt_results) == 1
            assert jwt_results[0].valid is False
            assert "No JWT secret configured" in jwt_results[0].error
            
            # Clear results for next iteration
            validator.validation_results = []
    
    @pytest.mark.asyncio
    async def test_jwt_secret_validation_environment_specific(self):
        """Test JWT secret validation with environment-specific secrets."""
        self.env.set("ENVIRONMENT", "staging", source="test")
        self.env.set("JWT_SECRET_STAGING", "staging_specific_jwt_secret_with_32_chars", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_jwt_secret()
        
        jwt_results = [r for r in validator.validation_results if r.component == AuthComponent.JWT_SECRET]
        assert len(jwt_results) == 1
        assert jwt_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_jwt_secret_validation_exception_handling(self):
        """Test JWT secret validation handles exceptions gracefully."""
        self.env.set("ENVIRONMENT", "development", source="test")
        
        validator = AuthStartupValidator()
        
        # Mock JWT manager to raise exception
        with patch('netra_backend.app.core.auth_startup_validator.get_jwt_secret_manager') as mock_manager:
            mock_manager.side_effect = Exception("JWT manager error")
            
            await validator._validate_jwt_secret()
            
            jwt_results = [r for r in validator.validation_results if r.component == AuthComponent.JWT_SECRET]
            assert len(jwt_results) == 1
            assert jwt_results[0].valid is False
            assert "JWT validation error" in jwt_results[0].error


class TestAuthStartupValidatorServiceCredentials(BaseIntegrationTest):
    """Test SERVICE_SECRET validation - ULTRA CRITICAL with 173+ dependencies."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_service_credentials_validation_success(self):
        """Test SERVICE_SECRET validation passes with strong credentials."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")  # 32 hex chars
        
        validator = AuthStartupValidator()
        await validator._validate_service_credentials()
        
        service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
        assert len(service_results) == 1
        assert service_results[0].valid is True
        assert service_results[0].error is None
    
    @pytest.mark.asyncio
    async def test_service_credentials_missing_service_id_critical_failure(self):
        """Test SERVICE_SECRET validation fails critically when SERVICE_ID missing."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        # Don't set SERVICE_ID
        
        validator = AuthStartupValidator()
        await validator._validate_service_credentials()
        
        service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
        assert len(service_results) == 1
        assert service_results[0].valid is False
        assert service_results[0].is_critical is True
        assert "SERVICE_ID not configured" in service_results[0].error
        assert "inter-service auth" in service_results[0].error.lower()
        assert "auth_service" in service_results[0].details["affected_services"]
    
    @pytest.mark.asyncio
    async def test_service_credentials_missing_service_secret_single_point_failure(self):
        """Test SERVICE_SECRET missing causes SINGLE POINT OF FAILURE error."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        # Don't set SERVICE_SECRET
        
        validator = AuthStartupValidator()
        await validator._validate_service_credentials()
        
        service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
        assert len(service_results) == 1
        assert service_results[0].valid is False
        assert service_results[0].is_critical is True
        assert "SINGLE POINT OF FAILURE" in service_results[0].error
        assert "100% authentication failure" in service_results[0].details["impact"]
        assert "173+ files depend" in service_results[0].details["dependencies"]
        assert "WebSocket authentication" in service_results[0].details["affected_components"]
        assert "Circuit breaker functionality" in service_results[0].details["affected_components"]
    
    @pytest.mark.asyncio
    async def test_service_secret_too_short_validation(self):
        """Test SERVICE_SECRET validation fails when secret is too short."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "short", source="test")  # Only 5 chars
        
        validator = AuthStartupValidator()
        await validator._validate_service_credentials()
        
        service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
        assert len(service_results) == 1
        assert service_results[0].valid is False
        assert service_results[0].is_critical is True
        assert "Too short (5 chars, minimum 32)" in service_results[0].error
        assert service_results[0].details["current_length"] == 5
    
    @pytest.mark.asyncio
    async def test_service_secret_weak_patterns_detection(self):
        """Test SERVICE_SECRET validation detects weak patterns."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        
        weak_patterns = [
            "service_secret_with_weak_password_pattern",
            "this_secret_contains_test_and_is_weak",
            "demo_service_secret_for_default_usage",
            "admin_secret_with_changeme_pattern_12345",
            "example_service_secret_default_value"
        ]
        
        for weak_secret in weak_patterns:
            self.env.set("SERVICE_SECRET", weak_secret, source="test")
            validator = AuthStartupValidator()
            await validator._validate_service_credentials()
            
            service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
            assert len(service_results) == 1
            assert service_results[0].valid is False
            assert "weak/default pattern" in service_results[0].error.lower()
            
            # Clear results for next iteration
            validator.validation_results = []
    
    @pytest.mark.asyncio
    async def test_service_secret_hex_string_validation_acceptance(self):
        """Test SERVICE_SECRET accepts hex strings (from openssl rand -hex 32)."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        
        # Valid hex strings (lowercase + digits)
        hex_secrets = [
            "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",  # 32 chars hex
            "deadbeefcafebabe1234567890abcdef",    # 32 chars hex
            "123456789abcdef0123456789abcdef01",    # 32 chars hex
            "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"  # 64 chars hex
        ]
        
        for hex_secret in hex_secrets:
            self.env.set("SERVICE_SECRET", hex_secret, source="test")
            validator = AuthStartupValidator()
            await validator._validate_service_credentials()
            
            service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
            assert len(service_results) == 1
            assert service_results[0].valid is True, f"Hex secret failed: {hex_secret}"
            
            # Clear results for next iteration
            validator.validation_results = []
    
    @pytest.mark.asyncio
    async def test_service_secret_mixed_case_validation_acceptance(self):
        """Test SERVICE_SECRET accepts mixed case with good entropy."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        
        # Valid mixed case secrets
        mixed_secrets = [
            "MyVerySecure32CharServiceSecretAbc1",  # Mixed case + digits
            "SecureService123WithMixedCaseAndDigits2024",  # Mixed + digits
            "ProductionServiceSecret2024WithGoodEntropy"  # Mixed + digits, long
        ]
        
        for mixed_secret in mixed_secrets:
            self.env.set("SERVICE_SECRET", mixed_secret, source="test")
            validator = AuthStartupValidator()
            await validator._validate_service_credentials()
            
            service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
            assert len(service_results) == 1
            assert service_results[0].valid is True, f"Mixed case secret failed: {mixed_secret}"
            
            # Clear results for next iteration
            validator.validation_results = []
    
    @pytest.mark.asyncio
    async def test_service_secret_special_characters_acceptance(self):
        """Test SERVICE_SECRET accepts secrets with special characters."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "Secure!Service@Secret#2024$WithSpecial%Chars^", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_service_credentials()
        
        service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
        assert len(service_results) == 1
        assert service_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_service_secret_insufficient_entropy_failure(self):
        """Test SERVICE_SECRET fails with insufficient entropy."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        
        # Secrets with insufficient entropy
        low_entropy_secrets = [
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # All lowercase, 32+ chars
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",  # All uppercase, 32+ chars
            "11111111111111111111111111111111",    # All digits, 32+ chars
            "abcdefghijklmnopqrstuvwxyzabcdef",     # Only lowercase letters
            "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEF"      # Only uppercase letters
        ]
        
        for bad_secret in low_entropy_secrets:
            self.env.set("SERVICE_SECRET", bad_secret, source="test")
            validator = AuthStartupValidator()
            await validator._validate_service_credentials()
            
            service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
            assert len(service_results) == 1
            assert service_results[0].valid is False, f"Low entropy secret should have failed: {bad_secret}"
            assert "Insufficient entropy" in service_results[0].error
            
            # Clear results for next iteration
            validator.validation_results = []
    
    @pytest.mark.asyncio
    async def test_service_secret_production_64_char_requirement(self):
        """Test SERVICE_SECRET requires 64+ chars in production."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")  # 32 chars, valid for dev
        
        validator = AuthStartupValidator()
        await validator._validate_service_credentials()
        
        service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
        assert len(service_results) == 1
        assert service_results[0].valid is False
        assert service_results[0].is_critical is True
        assert "Production requires 64+ chars (current: 32)" in service_results[0].error
        assert service_results[0].details["current_length"] == 32
    
    @pytest.mark.asyncio
    async def test_service_secret_production_64_char_success(self):
        """Test SERVICE_SECRET passes with 64+ chars in production."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        # 64 character hex secret
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_service_credentials()
        
        service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
        assert len(service_results) == 1
        assert service_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_service_credentials_exception_handling(self):
        """Test service credentials validation handles exceptions gracefully."""
        validator = AuthStartupValidator()
        
        # Mock environment to raise exception
        with patch.object(validator.env, 'get', side_effect=Exception("Environment error")):
            await validator._validate_service_credentials()
            
            service_results = [r for r in validator.validation_results if r.component == AuthComponent.SERVICE_CREDENTIALS]
            assert len(service_results) == 1
            assert service_results[0].valid is False
            assert service_results[0].is_critical is True
            assert "Service credentials validation error" in service_results[0].error
            assert "Environment error" in service_results[0].details["exception"]


class TestAuthStartupValidatorAuthServiceURL(BaseIntegrationTest):
    """Test auth service URL configuration validation."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_auth_service_url_validation_success(self):
        """Test auth service URL validation passes with valid URL."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081", source="test")
        self.env.set("AUTH_SERVICE_ENABLED", "true", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_auth_service_url()
        
        url_results = [r for r in validator.validation_results if r.component == AuthComponent.AUTH_SERVICE_URL]
        assert len(url_results) == 1
        assert url_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_auth_service_url_validation_missing_url(self):
        """Test auth service URL validation fails when URL not configured."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_SERVICE_ENABLED", "true", source="test")
        # Don't set AUTH_SERVICE_URL
        
        validator = AuthStartupValidator()
        await validator._validate_auth_service_url()
        
        url_results = [r for r in validator.validation_results if r.component == AuthComponent.AUTH_SERVICE_URL]
        assert len(url_results) == 1
        assert url_results[0].valid is False
        assert "AUTH_SERVICE_URL not configured" in url_results[0].error
    
    @pytest.mark.asyncio
    async def test_auth_service_url_validation_invalid_format(self):
        """Test auth service URL validation fails with invalid URL format."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_SERVICE_URL", "invalid-url-format", source="test")
        self.env.set("AUTH_SERVICE_ENABLED", "true", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_auth_service_url()
        
        url_results = [r for r in validator.validation_results if r.component == AuthComponent.AUTH_SERVICE_URL]
        assert len(url_results) == 1
        assert url_results[0].valid is False
        assert "Invalid AUTH_SERVICE_URL format" in url_results[0].error
    
    @pytest.mark.asyncio
    async def test_auth_service_url_production_https_required(self):
        """Test auth service URL requires HTTPS in production."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("AUTH_SERVICE_URL", "http://auth.example.com", source="test")
        self.env.set("AUTH_SERVICE_ENABLED", "true", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_auth_service_url()
        
        url_results = [r for r in validator.validation_results if r.component == AuthComponent.AUTH_SERVICE_URL]
        assert len(url_results) == 1
        assert url_results[0].valid is False
        assert "must use HTTPS in production" in url_results[0].error
        assert url_results[0].details["url"] == "http://auth.example.com"
    
    @pytest.mark.asyncio
    async def test_auth_service_url_production_https_success(self):
        """Test auth service URL passes with HTTPS in production."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("AUTH_SERVICE_URL", "https://auth.example.com", source="test")
        self.env.set("AUTH_SERVICE_ENABLED", "true", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_auth_service_url()
        
        url_results = [r for r in validator.validation_results if r.component == AuthComponent.AUTH_SERVICE_URL]
        assert len(url_results) == 1
        assert url_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_auth_service_disabled_development_warning(self):
        """Test auth service can be disabled in development with warning."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_SERVICE_ENABLED", "false", source="test")
        # Don't set AUTH_SERVICE_URL
        
        validator = AuthStartupValidator()
        await validator._validate_auth_service_url()
        
        url_results = [r for r in validator.validation_results if r.component == AuthComponent.AUTH_SERVICE_URL]
        assert len(url_results) == 1
        assert url_results[0].valid is True
        assert url_results[0].is_critical is False  # Warning, not critical
    
    @pytest.mark.asyncio
    async def test_auth_service_exception_handling(self):
        """Test auth service URL validation handles exceptions gracefully."""
        validator = AuthStartupValidator()
        
        with patch.object(validator.env, 'get', side_effect=Exception("Environment error")):
            await validator._validate_auth_service_url()
            
            url_results = [r for r in validator.validation_results if r.component == AuthComponent.AUTH_SERVICE_URL]
            assert len(url_results) == 1
            assert url_results[0].valid is False
            assert "Auth service URL validation error" in url_results[0].error


class TestAuthStartupValidatorOAuthCredentials(BaseIntegrationTest):
    """Test OAuth provider credentials validation."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_oauth_validation_google_success(self):
        """Test OAuth validation passes with Google credentials."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("GOOGLE_CLIENT_ID", "google_client_id_12345", source="test")
        self.env.set("GOOGLE_CLIENT_SECRET", "google_client_secret_67890", source="test")
        self.env.set("FRONTEND_URL", "http://localhost:3000", source="test")
        
        validator = AuthStartupValidator()
        
        # Mock OAuthConfigGenerator to return predictable results
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "http://localhost:3000/auth/callback"
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            await validator._validate_oauth_credentials()
            
            oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
            assert len(oauth_results) == 1
            assert oauth_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_oauth_validation_github_success(self):
        """Test OAuth validation passes with GitHub credentials."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("GITHUB_CLIENT_ID", "github_client_id_12345", source="test")
        self.env.set("GITHUB_CLIENT_SECRET", "github_client_secret_67890", source="test")
        self.env.set("FRONTEND_URL", "http://localhost:3000", source="test")
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "http://localhost:3000/auth/callback"
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            await validator._validate_oauth_credentials()
            
            oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
            assert len(oauth_results) == 1
            assert oauth_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_oauth_validation_both_providers_success(self):
        """Test OAuth validation passes with both Google and GitHub credentials."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("GOOGLE_CLIENT_ID", "google_client_id_12345", source="test")
        self.env.set("GOOGLE_CLIENT_SECRET", "google_client_secret_67890", source="test")
        self.env.set("GITHUB_CLIENT_ID", "github_client_id_12345", source="test")
        self.env.set("GITHUB_CLIENT_SECRET", "github_client_secret_67890", source="test")
        self.env.set("FRONTEND_URL", "http://localhost:3000", source="test")
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "http://localhost:3000/auth/callback"
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            await validator._validate_oauth_credentials()
            
            oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
            assert len(oauth_results) == 1
            assert oauth_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_oauth_validation_no_providers_development_warning(self):
        """Test OAuth validation gives warning in development when no providers configured."""
        self.env.set("ENVIRONMENT", "development", source="test")
        # Don't set any OAuth credentials
        
        validator = AuthStartupValidator()
        await validator._validate_oauth_credentials()
        
        oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
        assert len(oauth_results) == 1
        assert oauth_results[0].valid is False
        assert oauth_results[0].is_critical is False  # Not critical in development
        assert "No OAuth providers configured" in oauth_results[0].error
        assert oauth_results[0].details["google_configured"] is False
        assert oauth_results[0].details["github_configured"] is False
    
    @pytest.mark.asyncio
    async def test_oauth_validation_no_providers_production_critical(self):
        """Test OAuth validation fails critically in production when no providers configured."""
        self.env.set("ENVIRONMENT", "production", source="test")
        # Don't set any OAuth credentials
        
        validator = AuthStartupValidator()
        await validator._validate_oauth_credentials()
        
        oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
        assert len(oauth_results) == 1
        assert oauth_results[0].valid is False
        assert oauth_results[0].is_critical is True  # Critical in production
        assert "No OAuth providers configured" in oauth_results[0].error
    
    @pytest.mark.asyncio
    async def test_oauth_validation_partial_google_credentials(self):
        """Test OAuth validation fails with partial Google credentials."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("GOOGLE_CLIENT_ID", "google_client_id_12345", source="test")
        # Missing GOOGLE_CLIENT_SECRET
        
        validator = AuthStartupValidator()
        await validator._validate_oauth_credentials()
        
        oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
        assert len(oauth_results) == 1
        assert oauth_results[0].valid is False
        assert "No OAuth providers configured" in oauth_results[0].error
        assert oauth_results[0].details["google_configured"] is False
        assert oauth_results[0].details["github_configured"] is False
    
    @pytest.mark.asyncio
    async def test_oauth_validation_redirect_uri_mismatch_production_critical(self):
        """Test OAuth redirect URI mismatch is critical in production."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("GOOGLE_CLIENT_ID", "google_client_id_12345", source="test")
        self.env.set("GOOGLE_CLIENT_SECRET", "google_client_secret_67890", source="test")
        self.env.set("FRONTEND_URL", "https://app.example.com", source="test")
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "https://different.example.com/auth/callback"  # Mismatch
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            await validator._validate_oauth_credentials()
            
            oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
            assert len(oauth_results) == 1
            assert oauth_results[0].valid is False
            assert "doesn't match FRONTEND_URL (production)" in oauth_results[0].error
            assert oauth_results[0].details["frontend_url"] == "https://app.example.com"
    
    @pytest.mark.asyncio
    async def test_oauth_validation_redirect_uri_mismatch_staging_warning(self):
        """Test OAuth redirect URI mismatch is warning in staging."""
        self.env.set("ENVIRONMENT", "staging", source="test")
        self.env.set("GOOGLE_CLIENT_ID", "google_client_id_12345", source="test")
        self.env.set("GOOGLE_CLIENT_SECRET", "google_client_secret_67890", source="test")
        self.env.set("FRONTEND_URL", "https://staging.example.com", source="test")
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "https://different.example.com/auth/callback"  # Mismatch
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            await validator._validate_oauth_credentials()
            
            oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
            assert len(oauth_results) == 1
            assert oauth_results[0].valid is True  # Don't fail in staging
    
    @pytest.mark.asyncio
    async def test_oauth_validation_exception_handling(self):
        """Test OAuth validation handles exceptions gracefully."""
        validator = AuthStartupValidator()
        
        with patch.object(validator.env, 'get', side_effect=Exception("Environment error")):
            await validator._validate_oauth_credentials()
            
            oauth_results = [r for r in validator.validation_results if r.component == AuthComponent.OAUTH_CREDENTIALS]
            assert len(oauth_results) == 1
            assert oauth_results[0].valid is False
            assert "OAuth validation error" in oauth_results[0].error


class TestAuthStartupValidatorCORSConfiguration(BaseIntegrationTest):
    """Test CORS allowed origins configuration validation."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_cors_validation_success(self):
        """Test CORS validation passes with proper configuration."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("CORS_ALLOWED_ORIGINS", "http://localhost:3000,https://app.example.com", source="test")
        self.env.set("FRONTEND_URL", "http://localhost:3000", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_cors_configuration()
        
        cors_results = [r for r in validator.validation_results if r.component == AuthComponent.CORS_ORIGINS]
        assert len(cors_results) == 1
        assert cors_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_cors_validation_missing_origins_warning(self):
        """Test CORS validation gives warning when origins not configured."""
        self.env.set("ENVIRONMENT", "development", source="test")
        # Don't set CORS_ALLOWED_ORIGINS
        
        validator = AuthStartupValidator()
        await validator._validate_cors_configuration()
        
        cors_results = [r for r in validator.validation_results if r.component == AuthComponent.CORS_ORIGINS]
        assert len(cors_results) == 1
        assert cors_results[0].valid is False
        assert cors_results[0].is_critical is False  # Warning, not critical
        assert "CORS_ALLOWED_ORIGINS not configured" in cors_results[0].error
    
    @pytest.mark.asyncio
    async def test_cors_validation_frontend_url_not_in_origins_warning(self):
        """Test CORS validation warns when FRONTEND_URL not in allowed origins."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("CORS_ALLOWED_ORIGINS", "https://other.example.com", source="test")
        self.env.set("FRONTEND_URL", "http://localhost:3000", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_cors_configuration()
        
        cors_results = [r for r in validator.validation_results if r.component == AuthComponent.CORS_ORIGINS]
        assert len(cors_results) == 1
        assert cors_results[0].valid is False
        assert cors_results[0].is_critical is False  # Warning, not critical
        assert "FRONTEND_URL not in CORS_ALLOWED_ORIGINS" in cors_results[0].error
        assert cors_results[0].details["frontend_url"] == "http://localhost:3000"
        assert cors_results[0].details["cors_origins"] == "https://other.example.com"
    
    @pytest.mark.asyncio
    async def test_cors_validation_wildcard_production_forbidden(self):
        """Test CORS validation forbids wildcards in production."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("CORS_ALLOWED_ORIGINS", "*", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_cors_configuration()
        
        cors_results = [r for r in validator.validation_results if r.component == AuthComponent.CORS_ORIGINS]
        assert len(cors_results) == 1
        assert cors_results[0].valid is False
        assert "CORS wildcard (*) not allowed in production" in cors_results[0].error
        assert cors_results[0].details["cors_origins"] == "*"
    
    @pytest.mark.asyncio
    async def test_cors_validation_wildcard_development_allowed(self):
        """Test CORS validation allows wildcards in development."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("CORS_ALLOWED_ORIGINS", "*", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_cors_configuration()
        
        cors_results = [r for r in validator.validation_results if r.component == AuthComponent.CORS_ORIGINS]
        assert len(cors_results) == 1
        assert cors_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_cors_validation_multiple_origins_counting(self):
        """Test CORS validation counts multiple origins correctly."""
        self.env.set("ENVIRONMENT", "development", source="test")
        origins = "http://localhost:3000,https://app.example.com,https://admin.example.com"
        self.env.set("CORS_ALLOWED_ORIGINS", origins, source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_cors_configuration()
        
        cors_results = [r for r in validator.validation_results if r.component == AuthComponent.CORS_ORIGINS]
        assert len(cors_results) == 1
        assert cors_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_cors_validation_exception_handling(self):
        """Test CORS validation handles exceptions gracefully."""
        validator = AuthStartupValidator()
        
        with patch.object(validator.env, 'get', side_effect=Exception("Environment error")):
            await validator._validate_cors_configuration()
            
            cors_results = [r for r in validator.validation_results if r.component == AuthComponent.CORS_ORIGINS]
            assert len(cors_results) == 1
            assert cors_results[0].valid is False
            assert "CORS validation error" in cors_results[0].error


class TestAuthStartupValidatorTokenExpirySettings(BaseIntegrationTest):
    """Test token expiry configuration validation."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_default_success(self):
        """Test token expiry validation passes with default values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        # Use defaults: ACCESS_TOKEN_EXPIRE_MINUTES=30, REFRESH_TOKEN_EXPIRE_DAYS=7
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_custom_success(self):
        """Test token expiry validation passes with custom valid values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("ACCESS_TOKEN_EXPIRE_MINUTES", "60", source="test")
        self.env.set("REFRESH_TOKEN_EXPIRE_DAYS", "14", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_access_token_too_short(self):
        """Test token expiry validation fails when access token expiry is too short."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("ACCESS_TOKEN_EXPIRE_MINUTES", "2", source="test")  # Less than 5 minutes
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is False
        assert "ACCESS_TOKEN_EXPIRE_MINUTES too short (2 min)" in token_results[0].error
        assert token_results[0].details["minimum"] == 5
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_access_token_too_long(self):
        """Test token expiry validation fails when access token expiry is too long."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("ACCESS_TOKEN_EXPIRE_MINUTES", "1500", source="test")  # More than 24 hours
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is False
        assert "ACCESS_TOKEN_EXPIRE_MINUTES too long (1500 min)" in token_results[0].error
        assert token_results[0].details["maximum"] == 1440
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_refresh_token_too_short(self):
        """Test token expiry validation fails when refresh token expiry is too short."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("REFRESH_TOKEN_EXPIRE_DAYS", "0", source="test")  # Less than 1 day
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is False
        assert "REFRESH_TOKEN_EXPIRE_DAYS too short (0 days)" in token_results[0].error
        assert token_results[0].details["minimum"] == 1
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_refresh_token_too_long(self):
        """Test token expiry validation fails when refresh token expiry is too long."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("REFRESH_TOKEN_EXPIRE_DAYS", "100", source="test")  # More than 90 days
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is False
        assert "REFRESH_TOKEN_EXPIRE_DAYS too long (100 days)" in token_results[0].error
        assert token_results[0].details["maximum"] == 90
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_boundary_values(self):
        """Test token expiry validation with boundary values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("ACCESS_TOKEN_EXPIRE_MINUTES", "5", source="test")  # Minimum
        self.env.set("REFRESH_TOKEN_EXPIRE_DAYS", "90", source="test")  # Maximum
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_invalid_integer_values(self):
        """Test token expiry validation handles invalid integer values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("ACCESS_TOKEN_EXPIRE_MINUTES", "invalid", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_token_expiry_settings()
        
        token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
        assert len(token_results) == 1
        assert token_results[0].valid is False
        assert "Invalid token expiry values" in token_results[0].error
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation_exception_handling(self):
        """Test token expiry validation handles exceptions gracefully."""
        validator = AuthStartupValidator()
        
        with patch.object(validator.env, 'get', side_effect=Exception("Environment error")):
            await validator._validate_token_expiry_settings()
            
            token_results = [r for r in validator.validation_results if r.component == AuthComponent.TOKEN_EXPIRY]
            assert len(token_results) == 1
            assert token_results[0].valid is False
            assert "Token expiry validation error" in token_results[0].error


class TestAuthStartupValidatorCircuitBreakerConfig(BaseIntegrationTest):
    """Test auth circuit breaker configuration validation."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_validation_default_success(self):
        """Test circuit breaker validation passes with default values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        # Use defaults: AUTH_CIRCUIT_FAILURE_THRESHOLD=3, AUTH_CIRCUIT_TIMEOUT=30
        
        validator = AuthStartupValidator()
        await validator._validate_circuit_breaker_config()
        
        cb_results = [r for r in validator.validation_results if r.component == AuthComponent.CIRCUIT_BREAKER]
        assert len(cb_results) == 1
        assert cb_results[0].valid is True
        assert cb_results[0].is_critical is False  # Not critical
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_validation_custom_success(self):
        """Test circuit breaker validation passes with custom valid values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CIRCUIT_FAILURE_THRESHOLD", "5", source="test")
        self.env.set("AUTH_CIRCUIT_TIMEOUT", "60", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_circuit_breaker_config()
        
        cb_results = [r for r in validator.validation_results if r.component == AuthComponent.CIRCUIT_BREAKER]
        assert len(cb_results) == 1
        assert cb_results[0].valid is True
        assert cb_results[0].is_critical is False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_validation_failure_threshold_too_low(self):
        """Test circuit breaker validation fails when failure threshold is too low."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CIRCUIT_FAILURE_THRESHOLD", "0", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_circuit_breaker_config()
        
        cb_results = [r for r in validator.validation_results if r.component == AuthComponent.CIRCUIT_BREAKER]
        assert len(cb_results) == 1
        assert cb_results[0].valid is False
        assert cb_results[0].is_critical is False  # Not critical, just warning
        assert "Circuit breaker failure threshold too low" in cb_results[0].error
        assert cb_results[0].details["threshold"] == 0
        assert cb_results[0].details["minimum"] == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_validation_timeout_too_short(self):
        """Test circuit breaker validation fails when timeout is too short."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CIRCUIT_TIMEOUT", "5", source="test")  # Less than 10 seconds
        
        validator = AuthStartupValidator()
        await validator._validate_circuit_breaker_config()
        
        cb_results = [r for r in validator.validation_results if r.component == AuthComponent.CIRCUIT_BREAKER]
        assert len(cb_results) == 1
        assert cb_results[0].valid is False
        assert cb_results[0].is_critical is False
        assert "Circuit breaker timeout too short" in cb_results[0].error
        assert cb_results[0].details["timeout"] == 5
        assert cb_results[0].details["minimum"] == 10
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_validation_boundary_values(self):
        """Test circuit breaker validation with boundary values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CIRCUIT_FAILURE_THRESHOLD", "1", source="test")  # Minimum
        self.env.set("AUTH_CIRCUIT_TIMEOUT", "10", source="test")  # Minimum
        
        validator = AuthStartupValidator()
        await validator._validate_circuit_breaker_config()
        
        cb_results = [r for r in validator.validation_results if r.component == AuthComponent.CIRCUIT_BREAKER]
        assert len(cb_results) == 1
        assert cb_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_validation_exception_handling(self):
        """Test circuit breaker validation handles exceptions gracefully."""
        validator = AuthStartupValidator()
        
        with patch.object(validator.env, 'get', side_effect=Exception("Environment error")):
            await validator._validate_circuit_breaker_config()
            
            cb_results = [r for r in validator.validation_results if r.component == AuthComponent.CIRCUIT_BREAKER]
            assert len(cb_results) == 1
            assert cb_results[0].valid is False
            assert cb_results[0].is_critical is False  # Not critical
            assert "Circuit breaker validation error" in cb_results[0].error


class TestAuthStartupValidatorCacheConfiguration(BaseIntegrationTest):
    """Test auth cache configuration validation."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_cache_validation_default_enabled_success(self):
        """Test cache validation passes with default enabled settings."""
        self.env.set("ENVIRONMENT", "development", source="test")
        # Use defaults: AUTH_CACHE_TTL=300, AUTH_CACHE_ENABLED=true
        
        validator = AuthStartupValidator()
        await validator._validate_cache_configuration()
        
        cache_results = [r for r in validator.validation_results if r.component == AuthComponent.CACHE_CONFIG]
        assert len(cache_results) == 1
        assert cache_results[0].valid is True
        assert cache_results[0].is_critical is False  # Not critical
    
    @pytest.mark.asyncio
    async def test_cache_validation_disabled_success(self):
        """Test cache validation passes when cache is disabled."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CACHE_ENABLED", "false", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_cache_configuration()
        
        cache_results = [r for r in validator.validation_results if r.component == AuthComponent.CACHE_CONFIG]
        assert len(cache_results) == 1
        assert cache_results[0].valid is True
        assert cache_results[0].is_critical is False
    
    @pytest.mark.asyncio
    async def test_cache_validation_ttl_too_short(self):
        """Test cache validation fails when TTL is too short."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CACHE_ENABLED", "true", source="test")
        self.env.set("AUTH_CACHE_TTL", "30", source="test")  # Less than 60 seconds
        
        validator = AuthStartupValidator()
        await validator._validate_cache_configuration()
        
        cache_results = [r for r in validator.validation_results if r.component == AuthComponent.CACHE_CONFIG]
        assert len(cache_results) == 1
        assert cache_results[0].valid is False
        assert cache_results[0].is_critical is False  # Not critical
        assert "AUTH_CACHE_TTL too short (30s)" in cache_results[0].error
        assert cache_results[0].details["minimum"] == 60
    
    @pytest.mark.asyncio
    async def test_cache_validation_ttl_too_long(self):
        """Test cache validation fails when TTL is too long."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CACHE_ENABLED", "true", source="test")
        self.env.set("AUTH_CACHE_TTL", "4000", source="test")  # More than 3600 seconds
        
        validator = AuthStartupValidator()
        await validator._validate_cache_configuration()
        
        cache_results = [r for r in validator.validation_results if r.component == AuthComponent.CACHE_CONFIG]
        assert len(cache_results) == 1
        assert cache_results[0].valid is False
        assert cache_results[0].is_critical is False
        assert "AUTH_CACHE_TTL too long (4000s)" in cache_results[0].error
        assert cache_results[0].details["maximum"] == 3600
    
    @pytest.mark.asyncio
    async def test_cache_validation_boundary_values(self):
        """Test cache validation with boundary values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("AUTH_CACHE_ENABLED", "true", source="test")
        self.env.set("AUTH_CACHE_TTL", "60", source="test")  # Minimum
        
        validator = AuthStartupValidator()
        await validator._validate_cache_configuration()
        
        cache_results = [r for r in validator.validation_results if r.component == AuthComponent.CACHE_CONFIG]
        assert len(cache_results) == 1
        assert cache_results[0].valid is True
        
        # Test maximum
        self.env.set("AUTH_CACHE_TTL", "3600", source="test")  # Maximum
        validator = AuthStartupValidator()
        await validator._validate_cache_configuration()
        
        cache_results = [r for r in validator.validation_results if r.component == AuthComponent.CACHE_CONFIG]
        assert len(cache_results) == 1
        assert cache_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_cache_validation_exception_handling(self):
        """Test cache validation handles exceptions gracefully."""
        validator = AuthStartupValidator()
        
        with patch.object(validator.env, 'get', side_effect=Exception("Environment error")):
            await validator._validate_cache_configuration()
            
            cache_results = [r for r in validator.validation_results if r.component == AuthComponent.CACHE_CONFIG]
            assert len(cache_results) == 1
            assert cache_results[0].valid is False
            assert cache_results[0].is_critical is False
            assert "Cache validation error" in cache_results[0].error


class TestAuthStartupValidatorProductionRequirements(BaseIntegrationTest):
    """Test production-specific authentication validation requirements."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_production_requirements_https_frontend_success(self):
        """Test production requirements pass with HTTPS frontend URL."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("FRONTEND_URL", "https://app.example.com", source="test")
        self.env.set("BACKEND_URL", "https://api.example.com", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_production_requirements()
        
        # Should not add any failure results for HTTPS URLs
        https_failures = [
            r for r in validator.validation_results 
            if not r.valid and "must use HTTPS in production" in r.error
        ]
        assert len(https_failures) == 0
    
    @pytest.mark.asyncio
    async def test_production_requirements_http_frontend_failure(self):
        """Test production requirements fail with HTTP frontend URL."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("FRONTEND_URL", "http://app.example.com", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_production_requirements()
        
        frontend_failures = [
            r for r in validator.validation_results 
            if r.component == AuthComponent.CORS_ORIGINS and not r.valid
        ]
        assert len(frontend_failures) == 1
        assert "FRONTEND_URL must use HTTPS in production" in frontend_failures[0].error
        assert frontend_failures[0].details["url"] == "http://app.example.com"
    
    @pytest.mark.asyncio
    async def test_production_requirements_http_backend_failure(self):
        """Test production requirements fail with HTTP backend URL."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("BACKEND_URL", "http://api.example.com", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_production_requirements()
        
        backend_failures = [
            r for r in validator.validation_results 
            if r.component == AuthComponent.AUTH_SERVICE_URL and not r.valid
        ]
        assert len(backend_failures) == 1
        assert "BACKEND_URL must use HTTPS in production" in backend_failures[0].error
        assert backend_failures[0].details["url"] == "http://api.example.com"
    
    @pytest.mark.asyncio
    async def test_production_requirements_both_http_urls_failures(self):
        """Test production requirements fail with both HTTP URLs."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("FRONTEND_URL", "http://app.example.com", source="test")
        self.env.set("BACKEND_URL", "http://api.example.com", source="test")
        
        validator = AuthStartupValidator()
        await validator._validate_production_requirements()
        
        https_failures = [
            r for r in validator.validation_results 
            if not r.valid and "must use HTTPS in production" in r.error
        ]
        assert len(https_failures) == 2  # Both frontend and backend
    
    @pytest.mark.asyncio
    async def test_production_requirements_missing_urls_no_failure(self):
        """Test production requirements don't fail when URLs are missing."""
        self.env.set("ENVIRONMENT", "production", source="test")
        # Don't set FRONTEND_URL or BACKEND_URL
        
        validator = AuthStartupValidator()
        await validator._validate_production_requirements()
        
        # Should not add failures for missing URLs - other validations handle this
        https_failures = [
            r for r in validator.validation_results 
            if not r.valid and "must use HTTPS in production" in r.error
        ]
        assert len(https_failures) == 0


class TestAuthStartupValidatorValidateAll(BaseIntegrationTest):
    """Test complete AuthStartupValidator.validate_all() orchestration."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_validate_all_development_complete_success(self):
        """Test validate_all passes with complete valid development configuration."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081", source="test")
        self.env.set("GOOGLE_CLIENT_ID", "google_client_id", source="test")
        self.env.set("GOOGLE_CLIENT_SECRET", "google_client_secret", source="test")
        self.env.set("CORS_ALLOWED_ORIGINS", "http://localhost:3000", source="test")
        self.env.set("FRONTEND_URL", "http://localhost:3000", source="test")
        
        validator = AuthStartupValidator()
        
        # Mock OAuthConfigGenerator
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "http://localhost:3000/auth/callback"
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            success, results = await validator.validate_all()
            
            assert success is True
            assert len(results) == 8  # All components validated
            
            # Verify all components passed
            components_validated = {r.component for r in results}
            expected_components = {
                AuthComponent.JWT_SECRET,
                AuthComponent.SERVICE_CREDENTIALS,
                AuthComponent.AUTH_SERVICE_URL,
                AuthComponent.OAUTH_CREDENTIALS,
                AuthComponent.CORS_ORIGINS,
                AuthComponent.TOKEN_EXPIRY,
                AuthComponent.CIRCUIT_BREAKER,
                AuthComponent.CACHE_CONFIG
            }
            assert components_validated == expected_components
            
            # All should be valid
            assert all(r.valid for r in results)
    
    @pytest.mark.asyncio
    async def test_validate_all_production_complete_success(self):
        """Test validate_all passes with complete valid production configuration."""
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("JWT_SECRET_KEY", "production_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        # Production requires 64+ char SERVICE_SECRET
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        self.env.set("AUTH_SERVICE_URL", "https://auth.example.com", source="test")
        self.env.set("GOOGLE_CLIENT_ID", "google_client_id", source="test")
        self.env.set("GOOGLE_CLIENT_SECRET", "google_client_secret", source="test")
        self.env.set("CORS_ALLOWED_ORIGINS", "https://app.example.com", source="test")
        self.env.set("FRONTEND_URL", "https://app.example.com", source="test")
        self.env.set("BACKEND_URL", "https://api.example.com", source="test")
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "https://app.example.com/auth/callback"
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            success, results = await validator.validate_all()
            
            assert success is True
            assert len(results) == 8  # All non-production components + production checks
            assert all(r.valid for r in results)
    
    @pytest.mark.asyncio
    async def test_validate_all_critical_failure_missing_service_secret(self):
        """Test validate_all fails with critical failure when SERVICE_SECRET missing."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        # Don't set SERVICE_SECRET - critical failure
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator') as MockOAuthGen:
            mock_oauth_gen = MockOAuthGen.return_value
            mock_config = Mock()
            mock_config.redirect_uri = "http://localhost:3000/auth/callback"
            mock_oauth_gen.get_oauth_config.return_value = mock_config
            
            success, results = await validator.validate_all()
            
            assert success is False
            
            # Find the critical failure
            critical_failures = [r for r in results if not r.valid and r.is_critical]
            assert len(critical_failures) > 0
            
            # Should include SERVICE_SECRET failure
            service_failures = [r for r in critical_failures if r.component == AuthComponent.SERVICE_CREDENTIALS]
            assert len(service_failures) == 1
            assert "SINGLE POINT OF FAILURE" in service_failures[0].error
    
    @pytest.mark.asyncio
    async def test_validate_all_warning_non_critical_failures(self):
        """Test validate_all succeeds with warnings but no critical failures."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081", source="test")
        # Don't set OAuth credentials - warning in development
        # Don't set CORS - warning
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator'):
            success, results = await validator.validate_all()
            
            assert success is True  # Should succeed despite warnings
            
            warnings = [r for r in results if not r.valid and not r.is_critical]
            assert len(warnings) > 0  # Should have warnings
            
            critical_failures = [r for r in results if not r.valid and r.is_critical]
            assert len(critical_failures) == 0  # No critical failures
    
    @pytest.mark.asyncio
    async def test_validate_all_results_summary_logging(self):
        """Test validate_all produces proper summary logging."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        # Create mixed results: some pass, some warn, some fail critically
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.logger') as mock_logger:
            success, results = await validator.validate_all()
            
            # Should have logged summary information
            mock_logger.info.assert_called()
            
            # Check that summary info was logged
            info_calls = mock_logger.info.call_args_list
            summary_calls = [call for call in info_calls if "VALIDATION SUMMARY" in str(call)]
            assert len(summary_calls) > 0
    
    @pytest.mark.asyncio
    async def test_validate_all_component_coverage(self):
        """Test validate_all covers all AuthComponent enum values."""
        self.env.set("ENVIRONMENT", "development", source="test")
        
        validator = AuthStartupValidator()
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator'):
            success, results = await validator.validate_all()
            
            components_tested = {r.component for r in results}
            
            # All enum values should be tested
            all_components = set(AuthComponent)
            assert components_tested == all_components


class TestAuthStartupValidatorConvenienceFunction(BaseIntegrationTest):
    """Test the validate_auth_at_startup convenience function."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_validate_auth_at_startup_success(self):
        """Test validate_auth_at_startup succeeds with valid configuration."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081", source="test")
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator'):
            # Should not raise exception
            await validate_auth_startup()
    
    @pytest.mark.asyncio
    async def test_validate_auth_at_startup_critical_failure_raises_exception(self):
        """Test validate_auth_at_startup raises AuthValidationError on critical failure."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        # Don't set SERVICE_SECRET - critical failure
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator'):
            with pytest.raises(AuthValidationError) as exc_info:
                await validate_auth_startup()
                
            assert "Critical auth validation failures" in str(exc_info.value)
            assert "service_credentials" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_validate_auth_at_startup_warning_only_succeeds(self):
        """Test validate_auth_at_startup succeeds with warnings but no critical failures."""
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_with_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081", source="test")
        # Don't set OAuth - warning only
        
        with patch('netra_backend.app.core.auth_startup_validator.OAuthConfigGenerator'):
            # Should not raise exception despite warnings
            await validate_auth_startup()


class TestAuthStartupValidatorEnvironmentIntegration(BaseIntegrationTest):
    """Test AuthStartupValidator integration with different environments."""
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.clear_cache()
    
    @pytest.mark.asyncio
    async def test_validator_testing_environment_behavior(self):
        """Test validator behavior in testing environment."""
        self.env.set("ENVIRONMENT", "testing", source="test")
        
        validator = AuthStartupValidator()
        assert validator.environment == "testing"
        assert validator.is_production is False
        
        # Testing environment should behave like development
        success, results = await validator.validate_all()
        # Should complete without crashing, but may have failures due to missing config
    
    @pytest.mark.asyncio
    async def test_validator_staging_environment_behavior(self):
        """Test validator behavior in staging environment."""
        self.env.set("ENVIRONMENT", "staging", source="test")
        self.env.set("JWT_SECRET_STAGING", "staging_specific_jwt_secret_32_chars", source="test")
        self.env.set("SERVICE_ID", "netra-backend-service", source="test")
        self.env.set("SERVICE_SECRET", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", source="test")
        
        validator = AuthStartupValidator()
        assert validator.environment == "staging"
        assert validator.is_production is False
        
        # Should use staging-specific JWT secret
        await validator._validate_jwt_secret()
        jwt_results = [r for r in validator.validation_results if r.component == AuthComponent.JWT_SECRET]
        assert len(jwt_results) == 1
        assert jwt_results[0].valid is True
    
    @pytest.mark.asyncio
    async def test_validator_unknown_environment_handling(self):
        """Test validator handles unknown environment gracefully."""
        self.env.set("ENVIRONMENT", "unknown_env", source="test")
        
        validator = AuthStartupValidator()
        assert validator.environment == "unknown_env"
        assert validator.is_production is False  # Should default to non-production
        
        # Should still attempt validation
        success, results = await validator.validate_all()
        # May have failures but should not crash


class TestAuthStartupValidatorDataClassesAndEnums(BaseIntegrationTest):
    """Test AuthValidationResult and AuthComponent data structures."""
    
    def test_auth_component_enum_values(self):
        """Test all AuthComponent enum values are properly defined."""
        expected_components = {
            "JWT_SECRET",
            "SERVICE_CREDENTIALS", 
            "AUTH_SERVICE_URL",
            "OAUTH_CREDENTIALS",
            "CORS_ORIGINS",
            "TOKEN_EXPIRY",
            "CIRCUIT_BREAKER",
            "CACHE_CONFIG"
        }
        
        actual_components = {component.name for component in AuthComponent}
        assert actual_components == expected_components
        
        # Test enum values
        assert AuthComponent.JWT_SECRET.value == "jwt_secret"
        assert AuthComponent.SERVICE_CREDENTIALS.value == "service_credentials"
        assert AuthComponent.AUTH_SERVICE_URL.value == "auth_service_url"
        assert AuthComponent.OAUTH_CREDENTIALS.value == "oauth_credentials"
        assert AuthComponent.CORS_ORIGINS.value == "cors_origins"
        assert AuthComponent.TOKEN_EXPIRY.value == "token_expiry"
        assert AuthComponent.CIRCUIT_BREAKER.value == "circuit_breaker"
        assert AuthComponent.CACHE_CONFIG.value == "cache_config"
    
    def test_auth_validation_result_success(self):
        """Test AuthValidationResult for successful validation."""
        result = AuthValidationResult(
            component=AuthComponent.JWT_SECRET,
            valid=True,
            error=None,
            details={"length": 32},
            is_critical=True
        )
        
        assert result.component == AuthComponent.JWT_SECRET
        assert result.valid is True
        assert result.error is None
        assert result.details["length"] == 32
        assert result.is_critical is True
    
    def test_auth_validation_result_failure(self):
        """Test AuthValidationResult for failed validation."""
        result = AuthValidationResult(
            component=AuthComponent.SERVICE_CREDENTIALS,
            valid=False,
            error="SERVICE_SECRET not configured",
            details={
                "impact": "100% authentication failure",
                "dependencies": "173+ files depend on SERVICE_SECRET"
            },
            is_critical=True
        )
        
        assert result.component == AuthComponent.SERVICE_CREDENTIALS
        assert result.valid is False
        assert "SERVICE_SECRET not configured" in result.error
        assert "100% authentication failure" in result.details["impact"]
        assert "173+ files" in result.details["dependencies"]
        assert result.is_critical is True
    
    def test_auth_validation_result_default_critical(self):
        """Test AuthValidationResult defaults to critical=True."""
        result = AuthValidationResult(
            component=AuthComponent.JWT_SECRET,
            valid=False,
            error="Test error"
        )
        
        assert result.is_critical is True  # Default value
        assert result.details is None  # Default value
    
    def test_auth_validation_error_exception(self):
        """Test AuthValidationError exception class."""
        error_message = "Critical auth validation failures: jwt_secret: No JWT secret configured"
        
        with pytest.raises(AuthValidationError) as exc_info:
            raise AuthValidationError(error_message)
        
        assert str(exc_info.value) == error_message
        assert isinstance(exc_info.value, Exception)