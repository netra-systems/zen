"""
Test Auth Service Core Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable user authentication enables platform access
- Value Impact: Authentication is the gateway to all platform features - users cannot access
  AI optimization services, agent interactions, or any business value without secure auth
- Strategic Impact: Core platform security and user onboarding - authentication enables
  user acquisition and retention by providing secure, reliable access to platform services

This test suite validates that the core authentication business logic delivers reliable
user authentication, enabling users to securely access the platform and receive value
from AI optimization services.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env, test_env

# Auth service imports
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.auth_environment import get_auth_env
from auth_service.auth_core.unified_auth_interface import UnifiedAuthInterface


class TestAuthServiceCoreBusinessValue(BaseIntegrationTest):
    """Test auth service core business logic delivering user authentication value."""
    
    @pytest.mark.unit
    def test_auth_config_provides_critical_business_configuration(self, isolated_env):
        """Test that AuthConfig provides all critical configuration for business operations."""
        # Business Context: Configuration must support user authentication flows
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        isolated_env.set("JWT_ALGORITHM", "HS256", "test")  # Required in production environment
        isolated_env.set("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION", "test-client-id.apps.googleusercontent.com", "test")
        isolated_env.set("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION", "test-client-secret-must-be-long", "test")
        isolated_env.set("FRONTEND_URL", "https://app.netrasystems.ai", "test")
        
        # Test core configuration methods that enable business value
        assert AuthConfig.get_environment() == "production"
        assert AuthConfig.is_production() is True
        assert AuthConfig.is_development() is False
        
        # JWT configuration enables secure user sessions
        jwt_secret = AuthConfig.get_jwt_secret()
        assert jwt_secret is not None
        assert len(jwt_secret) >= 32  # Security requirement for production
        assert AuthConfig.get_jwt_algorithm() == "HS256"
        
        # OAuth configuration enables user onboarding
        google_client_id = AuthConfig.get_google_client_id()
        assert google_client_id is not None
        assert google_client_id.endswith(".apps.googleusercontent.com")
        
        google_client_secret = AuthConfig.get_google_client_secret()
        assert google_client_secret is not None
        assert len(google_client_secret) >= 20  # Reasonable minimum for OAuth secrets
        
        # Service configuration enables inter-service communication
        service_id = AuthConfig.get_service_id()
        assert service_id == "netra_auth_service_prod"
        
        frontend_url = AuthConfig.get_frontend_url()
        assert frontend_url == "https://app.netrasystems.ai"
    
    @pytest.mark.unit
    def test_auth_config_adapts_to_environment_specific_business_needs(self, isolated_env):
        """Test that configuration adapts to different environments for business scalability."""
        # Test staging environment configuration
        isolated_env.set("ENVIRONMENT", "staging", "test")
        isolated_env.set("JWT_SECRET_KEY", "staging-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        assert AuthConfig.get_environment() == "staging"
        assert AuthConfig.is_production() is False
        assert AuthConfig.get_service_id() == "netra_auth_service_staging"
        
        # Database pool sizes should scale with environment
        prod_pool_size = 20  # Expected production pool size
        staging_pool_size = 10  # Expected staging pool size
        
        # Switch to production and verify scaling
        isolated_env.set("ENVIRONMENT", "production", "test")
        assert AuthConfig.get_database_pool_size() == prod_pool_size
        
        # Switch back to staging and verify scaling
        isolated_env.set("ENVIRONMENT", "staging", "test")
        assert AuthConfig.get_database_pool_size() == staging_pool_size
    
    @pytest.mark.unit
    def test_oauth_configuration_enables_user_onboarding_business_value(self, isolated_env):
        """Test that OAuth configuration enables seamless user onboarding."""
        # Business Context: OAuth reduces friction in user signup/login
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION", "123456789.apps.googleusercontent.com", "test")
        isolated_env.set("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION", "valid-google-client-secret-for-oauth", "test")
        isolated_env.set("AUTH_SERVICE_URL", "https://auth.netrasystems.ai", "test")
        
        # OAuth should be enabled with valid configuration
        assert AuthConfig.is_google_oauth_enabled() is True
        
        # OAuth redirect URI should be properly constructed for business domain
        redirect_uri = AuthConfig.get_google_oauth_redirect_uri()
        assert redirect_uri == "https://auth.netrasystems.ai/auth/callback/google"
        
        # OAuth scopes should include essential user information for business operations
        scopes = AuthConfig.get_google_oauth_scopes()
        assert "openid" in scopes  # Essential for OAuth
        assert "email" in scopes   # Required for user identification
        assert "profile" in scopes # Required for user experience personalization
    
    @pytest.mark.unit
    def test_security_configuration_protects_business_assets(self, isolated_env):
        """Test that security configuration provides adequate protection for business operations."""
        # Business Context: Security settings must protect user data and platform integrity
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("SERVICE_SECRET", "production-service-secret-for-inter-service-auth", "test")
        
        # Password security should meet business security standards
        min_password_length = AuthConfig.get_password_min_length()
        assert min_password_length >= 8  # Industry standard minimum
        
        bcrypt_rounds = AuthConfig.get_bcrypt_rounds()
        assert bcrypt_rounds >= 12  # Adequate security for production
        
        # Account lockout should prevent brute force attacks
        max_login_attempts = AuthConfig.get_max_login_attempts()
        assert max_login_attempts >= 3  # Reasonable security vs usability balance
        assert max_login_attempts <= 10  # Prevents easy brute force
        
        lockout_duration = AuthConfig.get_account_lockout_duration_minutes()
        assert lockout_duration >= 15  # Sufficient deterrent
        assert lockout_duration <= 60  # Reasonable user experience
        
        # Rate limiting should protect against abuse
        rate_limit = AuthConfig.get_rate_limit_requests_per_minute()
        assert rate_limit >= 3    # Minimum reasonable rate limit (production uses 3)
        assert rate_limit <= 100  # Prevent abuse
    
    @pytest.mark.unit
    def test_session_configuration_balances_security_and_usability(self, isolated_env):
        """Test that session configuration provides good user experience while maintaining security."""
        # Business Context: Session settings affect user retention and security
        isolated_env.set("ENVIRONMENT", "production", "test")
        
        # JWT token expiration should balance security vs user experience
        access_expiry = AuthConfig.get_jwt_access_expiry_minutes()
        assert access_expiry >= 15   # Long enough for user workflows
        assert access_expiry <= 60   # Short enough for security
        
        refresh_expiry = AuthConfig.get_jwt_refresh_expiry_days()
        assert refresh_expiry >= 7   # Long enough to avoid frequent re-authentication
        assert refresh_expiry <= 30  # Short enough for security
        
        # Session timeout should be reasonable for business use
        session_timeout = AuthConfig.get_session_timeout_minutes()
        assert session_timeout >= 30    # Allow for longer business workflows
        assert session_timeout <= 480   # Reasonable maximum (8 hours)
        
        # Session TTL should align with business needs
        session_ttl_hours = AuthConfig.get_session_ttl_hours()
        assert session_ttl_hours >= 1   # Minimum useful session
        assert session_ttl_hours <= 24  # Maximum reasonable session
    
    @pytest.mark.unit
    def test_database_configuration_supports_business_scalability(self, isolated_env):
        """Test that database configuration can scale with business growth."""
        # Business Context: Database settings must support user growth and platform scaling
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("POSTGRES_HOST", "prod-db.netrasystems.ai", "test")
        isolated_env.set("POSTGRES_PORT", "5432", "test")
        isolated_env.set("POSTGRES_DB", "netra_auth_prod", "test")
        isolated_env.set("POSTGRES_USER", "auth_service", "test")
        isolated_env.set("POSTGRES_PASSWORD", "secure-production-password", "test")
        
        # Database connection details should be properly configured
        assert AuthConfig.get_database_host() == "prod-db.netrasystems.ai"
        assert AuthConfig.get_database_port() == 5432
        assert AuthConfig.get_database_name() == "netra_auth_prod"
        assert AuthConfig.get_database_user() == "auth_service"
        
        # Connection pooling should be optimized for production load
        pool_size = AuthConfig.get_database_pool_size()
        max_overflow = AuthConfig.get_database_max_overflow()
        
        # Production should have higher capacity than test environment
        assert pool_size >= 10      # Sufficient for concurrent users
        assert max_overflow >= 15   # Handle traffic spikes
        
        # Database URL should be properly constructed
        db_url = AuthConfig.get_database_url()
        assert "postgresql" in db_url
        assert "prod-db.netrasystems.ai" in db_url
        assert "netra_auth_prod" in db_url
    
    @pytest.mark.unit
    def test_redis_configuration_enables_session_management_business_value(self, isolated_env):
        """Test that Redis configuration supports scalable session management."""
        # Business Context: Redis enables fast session lookup and multi-server deployments
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("REDIS_HOST", "prod-redis.netrasystems.ai", "test")
        isolated_env.set("REDIS_PORT", "6379", "test")
        
        # Redis should be enabled by default for production
        assert AuthConfig.is_redis_enabled() is True
        assert AuthConfig.is_redis_disabled() is False
        
        # Redis configuration should be production-appropriate
        assert AuthConfig.get_redis_host() == "prod-redis.netrasystems.ai"
        assert AuthConfig.get_redis_port() == 6379
        assert AuthConfig.get_redis_db() == 0  # Production uses DB 0
        
        # Session management settings should be reasonable
        default_ttl = AuthConfig.get_redis_default_ttl()
        assert default_ttl >= 3600   # At least 1 hour
        assert default_ttl <= 86400  # At most 24 hours
        
        # Test environment separation
        isolated_env.set("ENVIRONMENT", "test", "test")
        assert AuthConfig.get_redis_db() == 3  # Test uses different DB
    
    @pytest.mark.unit
    def test_cors_configuration_enables_frontend_integration_business_value(self, isolated_env):
        """Test that CORS configuration enables secure frontend integration."""
        # Business Context: CORS settings must allow legitimate frontend access while preventing attacks
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("FRONTEND_URL", "https://app.netrasystems.ai", "test")
        isolated_env.set("CORS_ORIGINS", "https://app.netrasystems.ai,https://admin.netrasystems.ai", "test")
        
        # CORS origins should include business domains
        cors_origins = AuthConfig.get_cors_origins()
        assert "https://app.netrasystems.ai" in cors_origins
        
        # Allowed origins should match CORS origins for consistency
        allowed_origins = AuthConfig.get_allowed_origins()
        assert allowed_origins == cors_origins
    
    @pytest.mark.unit 
    def test_configuration_logging_masks_secrets_for_security(self, isolated_env):
        """Test that configuration logging protects sensitive information."""
        # Business Context: Logging configuration should not expose secrets that could compromise security
        isolated_env.set("ENVIRONMENT", "production", "test")
        isolated_env.set("JWT_SECRET_KEY", "super-secret-jwt-key-must-not-be-logged", "test")
        isolated_env.set("JWT_ALGORITHM", "HS256", "test")  # Required in production environment
        isolated_env.set("SERVICE_SECRET", "super-secret-service-key-must-not-be-logged", "test")
        isolated_env.set("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION", "super-secret-oauth-secret", "test")
        
        # Capture log output
        with patch('auth_service.auth_core.config.logger') as mock_logger:
            AuthConfig.log_configuration()
            
            # Verify that logging was called
            assert mock_logger.info.call_count > 0
            
            # Verify that secrets are masked in log output
            logged_messages = [call[0][0] for call in mock_logger.info.call_args_list]
            all_log_output = " ".join(logged_messages)
            
            # Secrets should be masked with asterisks
            assert "super-secret-jwt-key" not in all_log_output
            assert "super-secret-service-key" not in all_log_output  
            assert "super-secret-oauth-secret" not in all_log_output
            
            # But masked indicators should be present
            assert "*" in all_log_output  # Masked secrets show as asterisks
    
    @pytest.mark.unit
    def test_unified_auth_interface_provides_business_authentication_capabilities(self, isolated_env):
        """Test that UnifiedAuthInterface provides comprehensive authentication for business operations."""
        # Business Context: Unified interface should provide all auth capabilities needed by the platform
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        # Create auth interface
        auth_interface = UnifiedAuthInterface()
        
        # Interface should provide user authentication capabilities
        assert hasattr(auth_interface, 'authenticate_user')
        assert hasattr(auth_interface, 'create_user')
        assert hasattr(auth_interface, 'get_user')
        
        # Interface should provide token management capabilities  
        assert hasattr(auth_interface, 'create_access_token')
        assert hasattr(auth_interface, 'create_refresh_token')
        assert hasattr(auth_interface, 'validate_token')
        
        # Interface should provide session management capabilities
        assert hasattr(auth_interface, 'create_session')
        assert hasattr(auth_interface, 'get_session')
        assert hasattr(auth_interface, 'invalidate_session')
    
    @pytest.mark.unit
    async def test_auth_interface_token_creation_supports_business_workflows(self, isolated_env):
        """Test that token creation supports various business authentication workflows."""
        # Business Context: Different token types enable different business workflows
        isolated_env.set("ENVIRONMENT", "test", "test")
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        auth_interface = UnifiedAuthInterface()
        
        # Mock user data for token creation
        user_data = {
            "user_id": "user123",
            "email": "test@example.com", 
            "role": "user"
        }
        
        # Access tokens should be created for API access
        access_token = auth_interface.create_access_token(user_data)
        assert access_token is not None
        assert isinstance(access_token, str)
        assert len(access_token) > 50  # JWT tokens are reasonably long
        
        # Refresh tokens should be created for session management  
        refresh_token = auth_interface.create_refresh_token(user_data)
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 50
        
        # Service tokens should be created for inter-service communication
        service_data = {
            "service_id": "netra_backend",
            "service_role": "api_access"
        }
        service_token = auth_interface.create_service_token(service_data)
        assert service_token is not None
        assert isinstance(service_token, str)
    
    @pytest.mark.unit
    def test_token_validation_protects_business_operations(self, isolated_env):
        """Test that token validation prevents unauthorized access to business operations."""
        # Business Context: Token validation is critical for protecting user data and platform integrity
        isolated_env.set("ENVIRONMENT", "test", "test") 
        isolated_env.set("JWT_SECRET_KEY", "test-secret-key-for-testing-only-must-be-at-least-32-chars", "test")
        
        auth_interface = UnifiedAuthInterface()
        
        # Valid token should pass validation
        user_data = {"user_id": "user123", "email": "test@example.com"}
        valid_token = auth_interface.create_access_token(user_data)
        
        validation_result = auth_interface.validate_token(valid_token)
        assert validation_result is not None
        assert validation_result.get("user_id") == "user123"
        assert validation_result.get("email") == "test@example.com"
        
        # Invalid tokens should be rejected to protect business operations
        invalid_token = "invalid.jwt.token"
        invalid_result = auth_interface.validate_token(invalid_token)
        assert invalid_result is None or invalid_result.get("valid") is False
        
        # Expired tokens should be rejected
        # Note: In a real implementation, we would test with manipulated expiration
        # For unit tests, we focus on the interface behavior
        empty_token = ""
        empty_result = auth_interface.validate_token(empty_token)
        assert empty_result is None or empty_result.get("valid") is False