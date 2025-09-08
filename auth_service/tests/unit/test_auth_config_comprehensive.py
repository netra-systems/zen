"""
Comprehensive unit tests for Auth Configuration
Tests configuration loading, environment handling, and defaults
"""
import os
import uuid
import pytest
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment


class TestAuthConfigBasics:
    """Test basic AuthConfig functionality"""
    
    def test_get_environment(self):
        """Test getting environment setting"""
        env = AuthConfig.get_environment()
        assert env in ["development", "test", "staging", "production"]
    
    def test_get_jwt_secret(self):
        """Test getting JWT secret"""
        secret = AuthConfig.get_jwt_secret()
        assert secret is not None
        # In test environment, should have a test secret
        assert len(secret) >= 32
    
    def test_get_jwt_algorithm(self):
        """Test getting JWT algorithm"""
        algo = AuthConfig.get_jwt_algorithm()
        assert algo == "HS256"  # Default algorithm
    
    def test_get_jwt_access_expiry_minutes(self):
        """Test getting JWT access token expiry"""
        expiry = AuthConfig.get_jwt_access_expiry_minutes()
        assert isinstance(expiry, int)
        assert expiry > 0
        assert expiry <= 60  # Should be relatively short
    
    def test_get_jwt_refresh_expiry_days(self):
        """Test getting JWT refresh token expiry"""
        expiry = AuthConfig.get_jwt_refresh_expiry_days()
        assert isinstance(expiry, int)
        assert expiry > 0
        assert expiry <= 30  # Reasonable refresh period
    
    def test_get_jwt_service_expiry_minutes(self):
        """Test getting JWT service token expiry"""
        expiry = AuthConfig.get_jwt_service_expiry_minutes()
        assert isinstance(expiry, int)
        assert expiry > 0
        assert expiry <= 120  # Service tokens may be longer-lived
    
    def test_get_service_secret(self):
        """Test getting service secret"""
        secret = AuthConfig.get_service_secret()
        assert secret is not None
        assert len(secret) >= 32
    
    def test_get_service_id(self):
        """Test getting service ID"""
        service_id = AuthConfig.get_service_id()
        assert service_id is not None
        assert len(service_id) > 0
    
    def test_get_database_url(self):
        """Test getting database URL"""
        url = AuthConfig.get_database_url()
        assert url is not None
        # In test mode, might be SQLite
        assert "sqlite" in url or "postgresql" in url
    
    def test_get_redis_url(self):
        """Test getting Redis URL"""
        url = AuthConfig.get_redis_url()
        # Might be None if Redis is disabled in test
        if url:
            assert "redis://" in url
    
    def test_get_cors_origins(self):
        """Test getting CORS origins"""
        origins = AuthConfig.get_cors_origins()
        assert isinstance(origins, list)
        # Should have at least localhost for development
        assert any("localhost" in origin for origin in origins)
    
    def test_get_api_base_url(self):
        """Test getting API base URL"""
        url = AuthConfig.get_api_base_url()
        assert url is not None
        assert url.startswith("http")
    
    def test_get_frontend_url(self):
        """Test getting frontend URL"""
        url = AuthConfig.get_frontend_url()
        assert url is not None
        assert url.startswith("http")
    
    def test_is_development(self):
        """Test checking if development environment"""
        env = get_env()
        env.set("ENVIRONMENT", "development", "test")
        assert AuthConfig.is_development() is True
        env.set("ENVIRONMENT", "production", "test")
        assert AuthConfig.is_development() is False
        env.set("ENVIRONMENT", "test", "test")  # Reset
    
    def test_is_production(self):
        """Test checking if production environment"""
        env = get_env()
        env.set("ENVIRONMENT", "production", "test")
        assert AuthConfig.is_production() is True
        env.set("ENVIRONMENT", "development", "test")
        assert AuthConfig.is_production() is False
        env.set("ENVIRONMENT", "test", "test")  # Reset
    
    def test_is_test(self):
        """Test checking if test environment"""
        env = get_env()
        env.set("ENVIRONMENT", "test", "test")
        assert AuthConfig.is_test() is True
        env.set("ENVIRONMENT", "production", "test")
        assert AuthConfig.is_test() is False
        env.set("ENVIRONMENT", "test", "test")  # Reset


class TestAuthConfigGoogleOAuth:
    """Test Google OAuth configuration"""
    
    def test_get_google_client_id(self):
        """Test getting Google OAuth client ID"""
        client_id = AuthConfig.get_google_client_id()
        # Might be None or test value
        if client_id:
            assert len(client_id) > 0
            assert ".apps.googleusercontent.com" in client_id or "test" in client_id
    
    def test_get_google_client_secret(self):
        """Test getting Google OAuth client secret"""
        secret = AuthConfig.get_google_client_secret()
        # Might be None or test value
        if secret:
            assert len(secret) > 0
    
    def test_google_oauth_enabled(self):
        """Test checking if Google OAuth is enabled"""
        enabled = AuthConfig.is_google_oauth_enabled()
        assert isinstance(enabled, bool)
        # Enabled if both client ID and secret are set
        if enabled:
            assert AuthConfig.get_google_client_id() is not None
            assert AuthConfig.get_google_client_secret() is not None
    
    def test_get_google_oauth_redirect_uri(self):
        """Test getting Google OAuth redirect URI"""
        uri = AuthConfig.get_google_oauth_redirect_uri()
        assert uri is not None
        assert "/auth/callback" in uri or "/oauth/callback" in uri
    
    def test_get_google_oauth_scopes(self):
        """Test getting Google OAuth scopes"""
        scopes = AuthConfig.get_google_oauth_scopes()
        assert isinstance(scopes, list)
        assert "openid" in scopes
        assert "email" in scopes
        assert "profile" in scopes


class TestAuthConfigDatabase:
    """Test database configuration"""
    
    def test_get_database_host(self):
        """Test getting database host"""
        host = AuthConfig.get_database_host()
        assert host is not None
        assert host in ["localhost", "127.0.0.1", "postgres", "auth-postgres"]
    
    def test_get_database_port(self):
        """Test getting database port"""
        port = AuthConfig.get_database_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535
    
    def test_get_database_name(self):
        """Test getting database name"""
        name = AuthConfig.get_database_name()
        assert name is not None
        assert len(name) > 0
    
    def test_get_database_user(self):
        """Test getting database user"""
        user = AuthConfig.get_database_user()
        # Might be None for SQLite
        if user:
            assert len(user) > 0
    
    def test_get_database_password(self):
        """Test getting database password"""
        password = AuthConfig.get_database_password()
        # Might be None for SQLite
        if password:
            assert len(password) > 0
    
    def test_get_database_pool_size(self):
        """Test getting database pool size"""
        size = AuthConfig.get_database_pool_size()
        assert isinstance(size, int)
        assert 1 <= size <= 100
    
    def test_get_database_max_overflow(self):
        """Test getting database max overflow"""
        overflow = AuthConfig.get_database_max_overflow()
        assert isinstance(overflow, int)
        assert 0 <= overflow <= 50
    
    def test_use_sqlite_in_test(self):
        """Test SQLite is used in test mode"""
        env = get_env()
        env.set("ENVIRONMENT", "test", "test")
        env.set("AUTH_FAST_TEST_MODE", "true", "test")
        url = AuthConfig.get_database_url()
        assert "sqlite" in url


class TestAuthConfigRedis:
    """Test Redis configuration"""
    
    def test_get_redis_host(self):
        """Test getting Redis host"""
        host = AuthConfig.get_redis_host()
        if host:  # Might be None if disabled
            assert host in ["localhost", "127.0.0.1", "redis", "auth-redis"]
    
    def test_get_redis_port(self):
        """Test getting Redis port"""
        port = AuthConfig.get_redis_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535
    
    def test_get_redis_db(self):
        """Test getting Redis database number"""
        db = AuthConfig.get_redis_db()
        assert isinstance(db, int)
        assert 0 <= db <= 15
    
    def test_get_redis_password(self):
        """Test getting Redis password"""
        password = AuthConfig.get_redis_password()
        # Usually None in development/test
        if password:
            assert len(password) > 0
    
    def test_redis_enabled(self):
        """Test checking if Redis is enabled"""
        enabled = AuthConfig.is_redis_enabled()
        assert isinstance(enabled, bool)
    
    def test_redis_disabled_in_test(self):
        """Test Redis can be disabled in test"""
        env = get_env()
        # Save current value to restore later
        original_value = env.get("REDIS_DISABLED")
        
        env.set("REDIS_DISABLED", "true", "test")
        enabled = AuthConfig.is_redis_enabled()
        assert enabled is False
        
        # Restore original value
        if original_value is not None:
            env.set("REDIS_DISABLED", original_value, "test")
        else:
            env.delete("REDIS_DISABLED", "test")
    
    def test_get_redis_ttl(self):
        """Test getting Redis TTL settings"""
        ttl = AuthConfig.get_redis_default_ttl()
        assert isinstance(ttl, int)
        assert ttl > 0


class TestAuthConfigSecurity:
    """Test security-related configuration"""
    
    def test_get_bcrypt_rounds(self):
        """Test getting bcrypt rounds"""
        rounds = AuthConfig.get_bcrypt_rounds()
        assert isinstance(rounds, int)
        assert 4 <= rounds <= 16  # Reasonable range
    
    def test_get_password_min_length(self):
        """Test getting minimum password length"""
        min_len = AuthConfig.get_password_min_length()
        assert isinstance(min_len, int)
        # In test environment, should be 4 for fast testing
        assert min_len >= 4
    
    def test_get_max_login_attempts(self):
        """Test getting max login attempts"""
        attempts = AuthConfig.get_max_login_attempts()
        assert isinstance(attempts, int)
        # In test environment, should be 100 for fast testing
        assert 3 <= attempts <= 100
    
    def test_get_account_lockout_duration(self):
        """Test getting account lockout duration"""
        duration = AuthConfig.get_account_lockout_duration_minutes()
        assert isinstance(duration, int)
        assert duration > 0
    
    def test_get_session_timeout(self):
        """Test getting session timeout"""
        timeout = AuthConfig.get_session_timeout_minutes()
        assert isinstance(timeout, int)
        assert timeout > 0
    
    def test_require_email_verification(self):
        """Test email verification requirement"""
        required = AuthConfig.require_email_verification()
        assert isinstance(required, bool)
    
    def test_get_token_blacklist_ttl(self):
        """Test getting token blacklist TTL"""
        ttl = AuthConfig.get_token_blacklist_ttl_hours()
        assert isinstance(ttl, int)
        assert ttl > 0
    
    def test_get_rate_limit_requests(self):
        """Test getting rate limit requests"""
        requests = AuthConfig.get_rate_limit_requests_per_minute()
        assert isinstance(requests, int)
        assert requests > 0
    
    def test_get_allowed_origins(self):
        """Test getting allowed origins for CORS"""
        origins = AuthConfig.get_allowed_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0


class TestAuthConfigDefaults:
    """Test configuration defaults"""
    
    def test_default_values_when_env_empty(self):
        """Test default values are used when environment is empty"""
        env = get_env()
        # Temporarily clear a value
        original = env.get("JWT_EXPIRATION_MINUTES")
        env.delete("JWT_EXPIRATION_MINUTES", "test")
        
        expiry = AuthConfig.get_jwt_access_expiry_minutes()
        assert expiry == 5  # Test environment default value
        
        # Restore
        if original:
            env.set("JWT_EXPIRATION_MINUTES", original, "test")
    
    def test_type_conversion(self):
        """Test configuration values are properly type converted"""
        env = get_env()
        env.set("JWT_EXPIRATION_MINUTES", "30", "test")
        expiry = AuthConfig.get_jwt_access_expiry_minutes()
        assert isinstance(expiry, int)
        assert expiry == 30
        # Clean up
        env.delete("JWT_EXPIRATION_MINUTES", "test")
    
    def test_boolean_conversion(self):
        """Test boolean configuration values"""
        env = get_env()
        # Note: require_email_verification() delegates to require_password_complexity()
        env.set("REQUIRE_PASSWORD_COMPLEXITY", "true", "test")
        assert AuthConfig.require_email_verification() is True
        env.set("REQUIRE_PASSWORD_COMPLEXITY", "false", "test")
        assert AuthConfig.require_email_verification() is False
        env.set("REQUIRE_PASSWORD_COMPLEXITY", "1", "test")  
        assert AuthConfig.require_email_verification() is True
        env.set("REQUIRE_PASSWORD_COMPLEXITY", "0", "test")
        assert AuthConfig.require_email_verification() is False
        # Clean up
        env.delete("REQUIRE_PASSWORD_COMPLEXITY", "test")
    
    def test_list_conversion(self):
        """Test list configuration values"""
        env = get_env()
        env.set("CORS_ORIGINS", "http://localhost:3000,https://app.example.com", "test")
        origins = AuthConfig.get_cors_origins()
        assert isinstance(origins, list)
        assert "http://localhost:3000" in origins
        assert "https://app.example.com" in origins
    
    def test_environment_specific_defaults(self):
        """Test environment-specific default values"""
        env = get_env()
        
        # Development defaults
        env.set("ENVIRONMENT", "development", "test")
        assert AuthConfig.get_bcrypt_rounds() <= 10  # Faster in development
        
        # Production defaults
        env.set("ENVIRONMENT", "production", "test")
        assert AuthConfig.get_bcrypt_rounds() >= 10  # More secure in production
        
        # Reset
        env.set("ENVIRONMENT", "test", "test")


class TestAuthConfigValidation:
    """Test configuration validation"""
    
    def test_validate_jwt_secret_length(self):
        """Test JWT secret length validation"""
        env = get_env()
        env.set("ENVIRONMENT", "production", "test")
        env.set("JWT_SECRET_KEY", "short", "test")
        env.set("JWT_ALGORITHM", "HS256", "test")  # Set algorithm to avoid production validation error
        
        with pytest.raises(ValueError, match="at least 32 characters"):
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            handler = JWTHandler()
        
        # Reset
        env.set("ENVIRONMENT", "test", "test")
        env.set("JWT_SECRET_KEY", "test_jwt_secret_key_that_is_long_enough_for_testing", "test")
        env.delete("JWT_ALGORITHM", "test")
    
    def test_validate_service_secret_length(self):
        """Test service secret length validation"""
        env = get_env()
        original = env.get("SERVICE_SECRET")
        env.set("SERVICE_SECRET", "short", "test")
        
        secret = AuthConfig.get_service_secret()
        # Should use default or generate one if too short
        assert len(secret) >= 32
        
        # Restore
        if original:
            env.set("SERVICE_SECRET", original, "test")
    
    def test_validate_database_url_format(self):
        """Test database URL format validation"""
        env = get_env()
        urls = [
            "postgresql://user:pass@localhost/db",
            "postgresql+asyncpg://user:pass@localhost/db",
            "sqlite:///path/to/db.sqlite",
            "sqlite+aiosqlite:///path/to/db.sqlite"
        ]
        for url in urls:
            env.set("DATABASE_URL", url, "test")
            db_url = AuthConfig.get_database_url()
            assert db_url is not None
    
    def test_validate_redis_url_format(self):
        """Test Redis URL format validation"""
        env = get_env()
        urls = [
            "redis://localhost",
            "redis://localhost:6379",
            "redis://localhost:6379/0",
            "redis://:password@localhost:6379/0"
        ]
        for url in urls:
            env.set("REDIS_URL", url, "test")
            redis_url = AuthConfig.get_redis_url()
            if redis_url:  # Might be None if disabled
                assert "redis://" in redis_url