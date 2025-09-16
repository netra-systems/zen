"""
Comprehensive Unit Tests for auth_service/auth_core/config.py

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Security  
- Business Goal: Ensure authentication configuration is 100% reliable
- Value Impact: Prevents auth failures that block user access (critical for revenue)
- Strategic Impact: Auth config manages JWT secrets, OAuth credentials, database connections
  that are fundamental to platform security and user experience

CRITICAL: This configuration module is the SSOT for all auth service settings.
Any failures in config loading could prevent users from logging in, causing
immediate revenue impact and customer churn.

Coverage Requirements:
- 100% code coverage of auth_service/auth_core/config.py
- All configuration methods tested with success and failure scenarios  
- Environment-specific behavior validated (test, development, staging, production)
- OAuth configuration validation
- JWT secret management testing
- Database and Redis URL configuration
- Security settings validation
- Service URL configuration
- Fallback behavior and error handling

Test Categories:
- Configuration Loading & Delegation
- Environment Detection & Defaults
- OAuth Configuration (Google)
- JWT Configuration & Security
- Database Configuration & URL Building
- Redis Configuration & Settings
- Security & Rate Limiting
- Service URLs & CORS
- Error Handling & Validation
- Environment-Specific Behavior
"""

import pytest
import warnings
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Import the module under test
from auth_service.auth_core.config import AuthConfig, get_config


class TestAuthConfigCore(SSotBaseTestCase):
    """Test core AuthConfig functionality and delegation."""

    def test_config_instance_creation(self):
        """Test AuthConfig can be instantiated."""
        config = AuthConfig()
        assert config is not None
        assert hasattr(config, '_auth_env')

    def test_get_config_function(self):
        """Test get_config function returns AuthConfig instance."""
        config = get_config()
        assert isinstance(config, AuthConfig)

    def test_environment_property_access(self):
        """Test ENVIRONMENT property delegates to AuthEnvironment."""
        config = AuthConfig()
        env = config.ENVIRONMENT
        assert env is not None
        assert isinstance(env, str)
        assert env in ["development", "test", "staging", "production"]

    def test_static_methods_exist(self):
        """Test all expected static methods exist on AuthConfig."""
        expected_methods = [
            'get_environment', 'get_google_client_id', 'get_google_client_secret',
            'get_jwt_secret', 'get_jwt_algorithm', 'get_jwt_access_expiry_minutes',
            'get_jwt_refresh_expiry_days', 'get_jwt_service_expiry_minutes',
            'get_service_secret', 'get_service_id', 'get_frontend_url',
            'get_auth_service_url', 'get_database_url', 'get_raw_database_url',
            'get_redis_url', 'is_development', 'is_production', 'is_test'
        ]
        
        for method_name in expected_methods:
            assert hasattr(AuthConfig, method_name)
            assert callable(getattr(AuthConfig, method_name))


class TestAuthConfigEnvironment(SSotBaseTestCase):
    """Test environment detection and defaults."""

    def test_get_environment_delegates_to_auth_env(self):
        """Test get_environment delegates to AuthEnvironment."""
        env = AuthConfig.get_environment()
        assert isinstance(env, str)
        assert env.lower() in ["development", "test", "staging", "production"]

    def test_environment_specific_checks(self):
        """Test environment-specific boolean checks."""
        current_env = AuthConfig.get_environment()
        
        # Test is_development
        is_dev = AuthConfig.is_development()
        assert isinstance(is_dev, bool)
        if current_env == "development":
            assert is_dev is True
        
        # Test is_production
        is_prod = AuthConfig.is_production()
        assert isinstance(is_prod, bool)
        if current_env == "production":
            assert is_prod is True
        
        # Test is_test
        is_test = AuthConfig.is_test()
        assert isinstance(is_test, bool)
        if current_env in ["test", "testing"]:
            assert is_test is True

    def test_environment_consistency(self):
        """Test environment detection is consistent."""
        env1 = AuthConfig.get_environment()
        env2 = AuthConfig.get_environment()
        assert env1 == env2
        
        # Environment should not change during test execution
        assert env1 == AuthConfig().ENVIRONMENT


class TestAuthConfigOAuth(SSotBaseTestCase):
    """Test OAuth configuration methods."""

    def test_get_google_client_id(self):
        """Test Google OAuth client ID retrieval."""
        client_id = AuthConfig.get_google_client_id()
        assert isinstance(client_id, str)
        # In test environment, might be empty
        if client_id:
            assert len(client_id) > 0

    def test_get_google_client_secret(self):
        """Test Google OAuth client secret retrieval."""
        client_secret = AuthConfig.get_google_client_secret()
        assert isinstance(client_secret, str)
        # In test environment, might be empty
        if client_secret:
            assert len(client_secret) > 0

    def test_is_google_oauth_enabled(self):
        """Test Google OAuth enabled check."""
        enabled = AuthConfig.is_google_oauth_enabled()
        assert isinstance(enabled, bool)
        
        # Verify logic: enabled if both client_id and client_secret are set
        client_id = AuthConfig.get_google_client_id()
        client_secret = AuthConfig.get_google_client_secret()
        expected_enabled = bool(client_id and client_secret)
        assert enabled == expected_enabled

    def test_get_google_oauth_redirect_uri(self):
        """Test Google OAuth redirect URI generation."""
        redirect_uri = AuthConfig.get_google_oauth_redirect_uri()
        assert isinstance(redirect_uri, str)
        assert len(redirect_uri) > 0
        assert "/auth/callback" in redirect_uri

    def test_get_google_oauth_scopes(self):
        """Test Google OAuth scopes."""
        scopes = AuthConfig.get_google_oauth_scopes()
        assert isinstance(scopes, list)
        assert len(scopes) > 0
        assert "openid" in scopes
        assert "email" in scopes
        assert "profile" in scopes

    def test_oauth_with_environment_variables(self):
        """Test OAuth configuration with custom environment variables."""
        with self.temp_env_vars(
            OAUTH_GOOGLE_CLIENT_ID="test_client_id",
            OAUTH_GOOGLE_CLIENT_SECRET="test_client_secret"
        ):
            client_id = AuthConfig.get_google_client_id()
            client_secret = AuthConfig.get_google_client_secret()
            
            assert client_id == "test_client_id"
            assert client_secret == "test_client_secret"
            assert AuthConfig.is_google_oauth_enabled() is True


class TestAuthConfigJWT(SSotBaseTestCase):
    """Test JWT configuration and security."""

    def test_get_jwt_secret(self):
        """Test JWT secret key retrieval."""
        secret = AuthConfig.get_jwt_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0
        # Should be sufficient length for security
        assert len(secret) >= 16

    def test_get_jwt_algorithm(self):
        """Test JWT algorithm setting."""
        algorithm = AuthConfig.get_jwt_algorithm()
        assert isinstance(algorithm, str)
        assert algorithm in ["HS256", "RS256", "ES256"]  # Common JWT algorithms

    def test_get_jwt_access_expiry_minutes(self):
        """Test JWT access token expiry."""
        expiry = AuthConfig.get_jwt_access_expiry_minutes()
        assert isinstance(expiry, int)
        assert expiry > 0
        assert expiry <= 1440  # Should not exceed 24 hours

    def test_get_jwt_refresh_expiry_days(self):
        """Test JWT refresh token expiry."""
        expiry = AuthConfig.get_jwt_refresh_expiry_days()
        assert isinstance(expiry, int)
        assert expiry > 0
        assert expiry <= 365  # Should not exceed 1 year

    def test_get_jwt_service_expiry_minutes(self):
        """Test JWT service token expiry."""
        expiry = AuthConfig.get_jwt_service_expiry_minutes()
        assert isinstance(expiry, int)
        assert expiry > 0
        # Should be same as access token expiry per implementation
        assert expiry == AuthConfig.get_jwt_access_expiry_minutes()

    def test_jwt_configuration_consistency(self):
        """Test JWT configuration values are consistent."""
        access_expiry = AuthConfig.get_jwt_access_expiry_minutes()
        refresh_expiry = AuthConfig.get_jwt_refresh_expiry_days()
        
        # Refresh should be longer than access
        refresh_minutes = refresh_expiry * 24 * 60
        assert refresh_minutes > access_expiry


class TestAuthConfigService(SSotBaseTestCase):
    """Test service configuration methods."""

    def test_get_service_secret(self):
        """Test service secret retrieval."""
        secret = AuthConfig.get_service_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0
        # Should be sufficient length
        assert len(secret) >= 16

    def test_get_service_id(self):
        """Test service ID generation."""
        service_id = AuthConfig.get_service_id()
        assert isinstance(service_id, str)
        assert len(service_id) > 0
        assert "netra_auth_service" in service_id
        
        # Should contain environment
        current_env = AuthConfig.get_environment()
        if current_env == "production":
            assert "prod" in service_id
        elif current_env == "staging":
            assert "staging" in service_id
        elif current_env == "development":
            assert "dev" in service_id
        elif current_env == "test":
            assert "test" in service_id

    def test_service_id_environment_specific(self):
        """Test service ID changes with environment."""
        current_env = AuthConfig.get_environment()
        service_id = AuthConfig.get_service_id()
        
        # Mock different environments and verify service ID changes
        with patch('auth_service.auth_core.config.get_auth_env') as mock_auth_env:
            mock_env = Mock()
            mock_auth_env.return_value = mock_env
            
            # Test production
            mock_env.get_environment.return_value = "production"
            prod_id = AuthConfig.get_service_id()
            assert "prod" in prod_id
            
            # Test staging  
            mock_env.get_environment.return_value = "staging"
            staging_id = AuthConfig.get_service_id()
            assert "staging" in staging_id
            
            # Verify they're different
            assert prod_id != staging_id


class TestAuthConfigURLs(SSotBaseTestCase):
    """Test URL configuration methods."""

    def test_get_frontend_url(self):
        """Test frontend URL retrieval."""
        url = AuthConfig.get_frontend_url()
        assert isinstance(url, str)
        assert len(url) > 0
        assert url.startswith("http")

    def test_get_auth_service_url(self):
        """Test auth service URL retrieval."""
        url = AuthConfig.get_auth_service_url()
        assert isinstance(url, str)
        assert len(url) > 0
        assert url.startswith("http")

    def test_get_api_base_url(self):
        """Test API base URL retrieval."""
        url = AuthConfig.get_api_base_url()
        assert isinstance(url, str)
        assert len(url) > 0
        assert url.startswith("http")

    def test_url_format_validation(self):
        """Test URLs have proper format."""
        urls_to_test = [
            AuthConfig.get_frontend_url(),
            AuthConfig.get_auth_service_url(), 
            AuthConfig.get_api_base_url()
        ]
        
        for url in urls_to_test:
            assert "://" in url
            assert not url.endswith("/")  # Should not have trailing slash
            # Should not contain localhost in production
            if AuthConfig.is_production():
                assert "localhost" not in url
                assert "127.0.0.1" not in url


class TestAuthConfigDatabase(SSotBaseTestCase):
    """Test database configuration methods."""

    def test_get_database_url(self):
        """Test database URL retrieval."""
        url = AuthConfig.get_database_url()
        assert isinstance(url, str)
        assert len(url) > 0
        # Should be valid database URL format
        assert any(db_type in url for db_type in ["postgresql", "sqlite"])

    def test_get_raw_database_url(self):
        """Test raw (sync) database URL conversion."""
        raw_url = AuthConfig.get_raw_database_url()
        assert isinstance(raw_url, str)
        assert len(raw_url) > 0
        
        # Should not contain async drivers
        assert "asyncpg" not in raw_url
        assert "aiosqlite" not in raw_url
        
        # Should contain sync drivers
        if "postgresql" in raw_url:
            assert "postgresql:" in raw_url or "postgresql+psycopg2:" in raw_url
        elif "sqlite" in raw_url:
            assert "sqlite:" in raw_url

    def test_database_url_conversion(self):
        """Test async to sync URL conversion logic."""
        # Test with mock async URLs
        with patch('auth_service.auth_core.config.get_auth_env') as mock_auth_env:
            mock_env = Mock()
            mock_auth_env.return_value = mock_env
            
            # Test PostgreSQL async to sync conversion
            mock_env.get_database_url.return_value = "postgresql+asyncpg://user:pass@host/db"
            raw_url = AuthConfig.get_raw_database_url()
            assert raw_url == "postgresql://user:pass@host/db"
            
            # Test SQLite async to sync conversion
            mock_env.get_database_url.return_value = "sqlite+aiosqlite:///path/to/db"
            raw_url = AuthConfig.get_raw_database_url()
            assert raw_url == "sqlite:///path/to/db"

    def test_get_database_host(self):
        """Test database host retrieval."""
        host = AuthConfig.get_database_host()
        assert isinstance(host, str)
        assert len(host) > 0

    def test_get_database_port(self):
        """Test database port retrieval."""
        port = AuthConfig.get_database_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_get_database_name(self):
        """Test database name retrieval."""
        name = AuthConfig.get_database_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_database_user(self):
        """Test database user retrieval."""
        user = AuthConfig.get_database_user()
        assert isinstance(user, str)
        # Might be empty for SQLite

    def test_get_database_password(self):
        """Test database password retrieval."""
        password = AuthConfig.get_database_password()
        assert isinstance(password, str)
        # Might be empty for local development

    def test_get_database_pool_size(self):
        """Test database pool size configuration."""
        pool_size = AuthConfig.get_database_pool_size()
        assert isinstance(pool_size, int)
        assert pool_size > 0
        assert pool_size <= 100  # Reasonable upper limit

    def test_get_database_max_overflow(self):
        """Test database max overflow configuration."""
        max_overflow = AuthConfig.get_database_max_overflow()
        assert isinstance(max_overflow, int)
        assert max_overflow >= 0
        assert max_overflow <= 50  # Reasonable upper limit

    def test_database_pool_environment_specific(self):
        """Test database pool settings vary by environment."""
        current_env = AuthConfig.get_environment()
        pool_size = AuthConfig.get_database_pool_size()
        max_overflow = AuthConfig.get_database_max_overflow()
        
        if current_env == "test":
            # Test should have minimal pool
            assert pool_size <= 5
            assert max_overflow <= 5
        elif current_env == "production":
            # Production should have larger pool
            assert pool_size >= 10


class TestAuthConfigRedis(SSotBaseTestCase):
    """Test Redis configuration methods."""

    def test_get_redis_url(self):
        """Test Redis URL retrieval."""
        url = AuthConfig.get_redis_url()
        assert isinstance(url, str)
        if url:  # Might be empty if Redis disabled
            assert "redis://" in url

    def test_get_session_ttl_hours(self):
        """Test session TTL in hours conversion."""
        ttl_hours = AuthConfig.get_session_ttl_hours()
        assert isinstance(ttl_hours, int)
        assert ttl_hours > 0
        assert ttl_hours <= 720  # Should not exceed 30 days

    def test_is_redis_disabled(self):
        """Test Redis disabled check."""
        disabled = AuthConfig.is_redis_disabled()
        assert isinstance(disabled, bool)

    def test_get_redis_host(self):
        """Test Redis host retrieval."""
        host = AuthConfig.get_redis_host()
        assert isinstance(host, str)
        if host:  # Might be empty if Redis disabled
            assert len(host) > 0

    def test_get_redis_port(self):
        """Test Redis port retrieval."""
        port = AuthConfig.get_redis_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_get_redis_db(self):
        """Test Redis database number configuration."""
        db_num = AuthConfig.get_redis_db()
        assert isinstance(db_num, int)
        assert 0 <= db_num <= 15  # Valid Redis DB range

    def test_get_redis_password(self):
        """Test Redis password retrieval."""
        password = AuthConfig.get_redis_password()
        assert isinstance(password, str)
        # Might be empty for local development

    def test_is_redis_enabled(self):
        """Test Redis enabled check."""
        enabled = AuthConfig.is_redis_enabled()
        assert isinstance(enabled, bool)
        # Should be opposite of is_redis_disabled
        assert enabled == (not AuthConfig.is_redis_disabled())

    def test_get_redis_default_ttl(self):
        """Test Redis default TTL retrieval."""
        ttl = AuthConfig.get_redis_default_ttl()
        assert isinstance(ttl, int)
        assert ttl > 0

    def test_redis_environment_specific(self):
        """Test Redis settings vary by environment."""
        current_env = AuthConfig.get_environment()
        db_num = AuthConfig.get_redis_db()
        
        if current_env == "production":
            assert db_num == 0
        elif current_env == "staging":
            assert db_num == 1
        elif current_env == "development":
            assert db_num == 2
        elif current_env == "test":
            assert db_num == 3


class TestAuthConfigSecurity(SSotBaseTestCase):
    """Test security configuration methods."""

    def test_get_bcrypt_rounds(self):
        """Test bcrypt rounds configuration."""
        rounds = AuthConfig.get_bcrypt_rounds()
        assert isinstance(rounds, int)
        assert 4 <= rounds <= 16  # Valid bcrypt range

    def test_get_password_min_length(self):
        """Test minimum password length."""
        min_length = AuthConfig.get_password_min_length()
        assert isinstance(min_length, int)
        assert min_length >= 4  # Reasonable minimum

    def test_get_max_login_attempts(self):
        """Test maximum login attempts."""
        max_attempts = AuthConfig.get_max_login_attempts()
        assert isinstance(max_attempts, int)
        assert max_attempts > 0

    def test_get_account_lockout_duration_minutes(self):
        """Test account lockout duration."""
        duration = AuthConfig.get_account_lockout_duration_minutes()
        assert isinstance(duration, int)
        assert duration > 0

    def test_get_session_timeout_minutes(self):
        """Test session timeout."""
        timeout = AuthConfig.get_session_timeout_minutes()
        assert isinstance(timeout, int)
        assert timeout > 0

    def test_require_email_verification(self):
        """Test email verification requirement."""
        required = AuthConfig.require_email_verification()
        assert isinstance(required, bool)

    def test_get_token_blacklist_ttl_hours(self):
        """Test token blacklist TTL."""
        ttl = AuthConfig.get_token_blacklist_ttl_hours()
        assert isinstance(ttl, int)
        assert ttl > 0

    def test_get_rate_limit_requests_per_minute(self):
        """Test rate limit requests per minute."""
        rate_limit = AuthConfig.get_rate_limit_requests_per_minute()
        assert isinstance(rate_limit, int)
        assert rate_limit > 0

    def test_security_environment_specific(self):
        """Test security settings vary by environment."""
        current_env = AuthConfig.get_environment()
        bcrypt_rounds = AuthConfig.get_bcrypt_rounds()
        min_password_length = AuthConfig.get_password_min_length()
        
        if current_env == "production":
            # Production should have higher security
            assert bcrypt_rounds >= 10
            assert min_password_length >= 8
        elif current_env == "test":
            # Test should prioritize speed over security
            assert bcrypt_rounds <= 8


class TestAuthConfigCORS(SSotBaseTestCase):
    """Test CORS configuration methods."""

    def test_get_cors_origins(self):
        """Test CORS origins retrieval."""
        origins = AuthConfig.get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0
        for origin in origins:
            assert isinstance(origin, str)
            assert origin.startswith("http")

    def test_get_allowed_origins(self):
        """Test allowed origins (same as CORS origins)."""
        cors_origins = AuthConfig.get_cors_origins()
        allowed_origins = AuthConfig.get_allowed_origins()
        assert cors_origins == allowed_origins

    def test_cors_environment_specific(self):
        """Test CORS origins vary by environment."""
        current_env = AuthConfig.get_environment()
        origins = AuthConfig.get_cors_origins()
        
        if current_env == "production":
            # Production should only allow production domains
            assert all("netrasystems.ai" in origin for origin in origins)
            assert not any("localhost" in origin for origin in origins)
        elif current_env in ["development", "test"]:
            # Development/test should allow localhost
            assert any("localhost" in origin for origin in origins)


class TestAuthConfigLogging(SSotBaseTestCase):
    """Test configuration logging and status methods."""

    def test_log_configuration(self):
        """Test configuration logging method."""
        # This method should not raise exceptions
        try:
            AuthConfig.log_configuration()
        except Exception as e:
            pytest.fail(f"log_configuration() raised {e}")

    def test_log_configuration_masks_secrets(self):
        """Test configuration logging masks sensitive values."""
        # Capture log output to verify secrets are masked
        import logging
        from io import StringIO
        import sys
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('auth_service.auth_core.config')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            AuthConfig.log_configuration()
            log_output = log_capture.getvalue()
            
            # Should contain masked secrets, not actual values
            assert "***" in log_output or "*" * 10 in log_output
            # Should not contain actual secret values
            jwt_secret = AuthConfig.get_jwt_secret()
            if len(jwt_secret) > 10:
                assert jwt_secret not in log_output
                
        finally:
            logger.removeHandler(handler)


class TestAuthConfigErrorHandling(SSotBaseTestCase):
    """Test configuration error handling and edge cases."""

    def test_handles_missing_auth_env(self):
        """Test graceful handling when AuthEnvironment is unavailable."""
        with patch('auth_service.auth_core.config.get_auth_env') as mock_get_env:
            mock_get_env.side_effect = ImportError("Module not found")
            
            # Should handle the error gracefully
            with pytest.raises((ImportError, AttributeError)):
                AuthConfig.get_environment()

    def test_handles_auth_env_method_errors(self):
        """Test handling when AuthEnvironment methods raise errors."""
        with patch('auth_service.auth_core.config.get_auth_env') as mock_get_env:
            mock_env = Mock()
            mock_get_env.return_value = mock_env
            
            # Simulate AuthEnvironment method error
            mock_env.get_jwt_secret_key.side_effect = ValueError("Invalid configuration")
            
            with pytest.raises(ValueError):
                AuthConfig.get_jwt_secret()

    def test_handles_type_conversion_errors(self):
        """Test handling of type conversion errors."""
        with patch('auth_service.auth_core.config.get_auth_env') as mock_get_env:
            mock_env = Mock()
            mock_get_env.return_value = mock_env
            
            # Return non-integer for integer method
            mock_env.get_jwt_expiration_minutes.return_value = "not_a_number"
            
            # Should handle conversion error
            with pytest.raises((ValueError, TypeError)):
                result = AuthConfig.get_jwt_access_expiry_minutes()
                # Ensure it's actually an integer
                assert isinstance(result, int)

    def test_environment_fallbacks(self):
        """Test environment-specific fallback behavior."""
        current_env = AuthConfig.get_environment()
        
        # Test that methods return reasonable defaults even in edge cases
        methods_to_test = [
            (AuthConfig.get_jwt_access_expiry_minutes, int, lambda x: x > 0),
            (AuthConfig.get_bcrypt_rounds, int, lambda x: 4 <= x <= 16),
            (AuthConfig.get_database_pool_size, int, lambda x: x > 0),
            (AuthConfig.get_redis_db, int, lambda x: 0 <= x <= 15),
        ]
        
        for method, expected_type, validator in methods_to_test:
            result = method()
            assert isinstance(result, expected_type)
            assert validator(result), f"{method.__name__} returned invalid value: {result}"


class TestAuthConfigDeprecatedMethods(SSotBaseTestCase):
    """Test deprecated methods and warnings."""

    def test_deprecated_oauth_redirect_uri_warning(self):
        """Test deprecated OAuth redirect URI method shows warning."""
        # This method is deprecated in AuthEnvironment and should show warning
        with patch('auth_service.auth_core.config.get_auth_env') as mock_get_env:
            mock_env = Mock()
            mock_get_env.return_value = mock_env
            mock_env.get_oauth_redirect_uri.side_effect = lambda provider: f"http://localhost:8081/auth/callback"
            
            # Should not raise exception but might show warning
            redirect_uri = AuthConfig.get_google_oauth_redirect_uri()
            assert isinstance(redirect_uri, str)
            assert "callback" in redirect_uri


class TestAuthConfigIntegration(SSotBaseTestCase):
    """Test integration between config methods."""

    def test_jwt_and_service_secrets_consistency(self):
        """Test JWT and service secrets are independently configured."""
        jwt_secret = AuthConfig.get_jwt_secret()
        service_secret = AuthConfig.get_service_secret()
        
        assert isinstance(jwt_secret, str)
        assert isinstance(service_secret, str)
        assert len(jwt_secret) > 0
        assert len(service_secret) > 0

    def test_database_url_and_components_consistency(self):
        """Test database URL and individual components are consistent."""
        db_url = AuthConfig.get_database_url()
        
        if "postgresql" in db_url:
            host = AuthConfig.get_database_host()
            port = AuthConfig.get_database_port()
            db_name = AuthConfig.get_database_name()
            user = AuthConfig.get_database_user()
            
            # URL should contain these components
            assert host in db_url or db_url.startswith("sqlite")
            if host != "localhost" or port != 5432:
                assert str(port) in db_url or db_url.startswith("sqlite")

    def test_redis_url_and_components_consistency(self):
        """Test Redis URL and individual components are consistent."""
        redis_url = AuthConfig.get_redis_url()
        
        if redis_url and "redis://" in redis_url:
            host = AuthConfig.get_redis_host()
            port = AuthConfig.get_redis_port()
            
            # URL should contain these components
            if host and host != "localhost":
                assert host in redis_url
            if port != 6379:
                assert str(port) in redis_url

    def test_service_urls_environment_consistency(self):
        """Test service URLs are consistent with environment."""
        current_env = AuthConfig.get_environment()
        frontend_url = AuthConfig.get_frontend_url()
        auth_service_url = AuthConfig.get_auth_service_url()
        api_base_url = AuthConfig.get_api_base_url()
        
        if current_env == "production":
            assert "https://" in frontend_url
            assert "https://" in auth_service_url
            assert "https://" in api_base_url
            assert "netrasystems.ai" in frontend_url
        elif current_env in ["development", "test"]:
            # Local environments can use http
            assert any("http" in url for url in [frontend_url, auth_service_url, api_base_url])

    def test_ttl_and_timeout_consistency(self):
        """Test TTL and timeout values are reasonable and consistent."""
        session_ttl_hours = AuthConfig.get_session_ttl_hours()
        session_timeout_minutes = AuthConfig.get_session_timeout_minutes()
        jwt_access_minutes = AuthConfig.get_jwt_access_expiry_minutes()
        jwt_refresh_days = AuthConfig.get_jwt_refresh_expiry_days()
        
        # Session timeout should be less than or equal to session TTL
        session_ttl_minutes = session_ttl_hours * 60
        assert session_timeout_minutes <= session_ttl_minutes
        
        # JWT access should be shorter than session timeout
        assert jwt_access_minutes <= session_timeout_minutes
        
        # Refresh should be much longer than access
        jwt_refresh_minutes = jwt_refresh_days * 24 * 60
        assert jwt_refresh_minutes > jwt_access_minutes


class TestAuthConfigBusinessValue(SSotBaseTestCase):
    """Test configuration provides business value."""

    def test_production_security_standards(self):
        """Test production configuration meets security standards."""
        if AuthConfig.is_production():
            # Production should have strict security settings
            bcrypt_rounds = AuthConfig.get_bcrypt_rounds()
            assert bcrypt_rounds >= 10, "Production bcrypt rounds too low"
            
            min_password_length = AuthConfig.get_password_min_length()
            assert min_password_length >= 8, "Production password length too short"
            
            max_attempts = AuthConfig.get_max_login_attempts()
            assert max_attempts <= 5, "Production login attempts too permissive"
            
            jwt_access_expiry = AuthConfig.get_jwt_access_expiry_minutes()
            assert jwt_access_expiry <= 60, "Production JWT expiry too long"

    def test_oauth_business_readiness(self):
        """Test OAuth configuration supports business operations."""
        # OAuth should be properly configured for customer acquisition
        if AuthConfig.is_google_oauth_enabled():
            client_id = AuthConfig.get_google_client_id()
            client_secret = AuthConfig.get_google_client_secret()
            redirect_uri = AuthConfig.get_google_oauth_redirect_uri()
            scopes = AuthConfig.get_google_oauth_scopes()
            
            # Business requirements for OAuth
            assert len(client_id) > 20, "Google client ID too short"
            assert len(client_secret) > 20, "Google client secret too short"
            assert "https://" in redirect_uri or AuthConfig.is_development(), "OAuth redirect should use HTTPS in production"
            assert len(scopes) >= 3, "Need sufficient OAuth scopes"

    def test_database_performance_configuration(self):
        """Test database configuration supports performance requirements."""
        pool_size = AuthConfig.get_database_pool_size()
        max_overflow = AuthConfig.get_database_max_overflow()
        
        if AuthConfig.is_production():
            # Production needs sufficient connection pool
            assert pool_size >= 10, "Production pool size too small"
            assert max_overflow >= 10, "Production overflow too small"
        
        # Total connections should be reasonable
        total_connections = pool_size + max_overflow
        assert total_connections <= 100, "Total database connections too high"

    def test_session_management_business_logic(self):
        """Test session configuration supports business requirements."""
        session_ttl_hours = AuthConfig.get_session_ttl_hours()
        jwt_access_minutes = AuthConfig.get_jwt_access_expiry_minutes()
        jwt_refresh_days = AuthConfig.get_jwt_refresh_expiry_days()
        
        # Business requirement: users shouldn't need to login too frequently
        if AuthConfig.is_production():
            assert session_ttl_hours >= 1, "Production sessions too short"
            assert jwt_refresh_days >= 1, "Production refresh tokens too short"
        
        # But not too long for security
        assert session_ttl_hours <= 720, "Sessions too long (> 30 days)"
        assert jwt_refresh_days <= 90, "Refresh tokens too long (> 90 days)"

    def test_rate_limiting_business_protection(self):
        """Test rate limiting protects business from abuse."""
        rate_limit = AuthConfig.get_rate_limit_requests_per_minute()
        max_attempts = AuthConfig.get_max_login_attempts()
        lockout_duration = AuthConfig.get_account_lockout_duration_minutes()
        
        # Should prevent brute force but allow legitimate users
        assert rate_limit >= 3, "Rate limit too restrictive"
        assert rate_limit <= 100, "Rate limit too permissive"
        assert max_attempts >= 3, "Max attempts too restrictive"
        assert max_attempts <= 10, "Max attempts too permissive"
        assert lockout_duration >= 5, "Lockout too short"
        assert lockout_duration <= 1440, "Lockout too long (> 24 hours)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])