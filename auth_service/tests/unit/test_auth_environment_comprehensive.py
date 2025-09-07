"""
Comprehensive unit tests for AuthEnvironment class - Complete coverage of auth service configuration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable auth service configuration across all environments
- Value Impact: Prevents configuration failures that cause authentication outages
- Strategic Impact: Core platform stability - auth failures can cause total system outages
- Revenue Impact: Protects $50K+ MRR by preventing WebSocket auth failures like JWT secret mismatches

This test suite provides 100% coverage of AuthEnvironment functionality including:
- Environment-specific configuration handling
- JWT secret management and unified secret integration
- Database and Redis connection configuration
- OAuth provider configuration with environment-specific behavior
- Service URL generation for different environments
- Security parameter validation
- Error handling and fallback mechanisms
"""

import pytest
import hashlib
import warnings
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import sys
import os

from auth_service.auth_core.auth_environment import AuthEnvironment, get_auth_env
from shared.isolated_environment import IsolatedEnvironment


class TestAuthEnvironmentInitialization:
    """Test AuthEnvironment initialization and validation."""

    def setup_method(self):
        """Setup for each test with fresh environment."""
        # Clear any existing environment state
        if 'auth_service.auth_core.auth_environment' in sys.modules:
            # Reset the singleton by clearing the module
            del sys.modules['auth_service.auth_core.auth_environment']

    def test_initialization_with_minimal_config(self):
        """Test AuthEnvironment initializes with minimal configuration."""
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.return_value = None
            
            env = AuthEnvironment()
            assert env is not None
            assert env.env is not None

    def test_initialization_validates_config(self):
        """Test initialization calls config validation."""
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.return_value = "test-jwt-secret"
            
            # Mock the validation method to verify it's called
            with patch.object(AuthEnvironment, '_validate_auth_config') as mock_validate:
                env = AuthEnvironment()
                mock_validate.assert_called_once()

    def test_validation_logs_missing_required_vars(self):
        """Test validation logs missing required environment variables."""
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Return None for JWT_SECRET_KEY
            mock_get.return_value = None
            
            with patch('auth_service.auth_core.auth_environment.logger') as mock_logger:
                env = AuthEnvironment()
                # Should log warning about missing JWT_SECRET_KEY
                mock_logger.warning.assert_called_once()
                assert "JWT_SECRET_KEY" in str(mock_logger.warning.call_args)


class TestJWTConfiguration:
    """Test JWT-related configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_jwt_secret_key_uses_unified_manager(self):
        """Test JWT secret key uses unified manager for consistency."""
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_unified:
            mock_unified.return_value = "unified-jwt-secret"
            
            secret = self.env.get_jwt_secret_key()
            
            assert secret == "unified-jwt-secret"
            mock_unified.assert_called_once()

    def test_get_jwt_secret_key_falls_back_on_unified_failure(self):
        """Test JWT secret falls back to local resolution if unified manager fails."""
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_unified:
            mock_unified.side_effect = Exception("Unified manager failed")
            
            with patch.object(self.env.env, 'get') as mock_get:
                mock_get.side_effect = lambda key, default="": {
                    "JWT_SECRET_KEY": "fallback-secret"
                }.get(key, default)
                
                with patch.object(self.env, 'get_environment') as mock_env:
                    mock_env.return_value = "test"
                    
                    secret = self.env.get_jwt_secret_key()
                    
                    assert secret == "fallback-secret"

    def test_get_jwt_secret_key_environment_specific(self):
        """Test JWT secret key tries environment-specific keys first."""
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_unified:
            mock_unified.side_effect = Exception("Unified manager failed")
            
            with patch.object(self.env.env, 'get') as mock_get:
                mock_get.side_effect = lambda key, default="": {
                    "JWT_SECRET_STAGING": "staging-specific-secret"
                }.get(key, default)
                
                with patch.object(self.env, 'get_environment') as mock_env:
                    mock_env.return_value = "staging"
                    
                    secret = self.env.get_jwt_secret_key()
                    
                    assert secret == "staging-specific-secret"

    def test_get_jwt_secret_key_generates_dev_fallback(self):
        """Test JWT secret generates consistent development fallback."""
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_unified:
            mock_unified.side_effect = Exception("Unified manager failed")
            
            with patch.object(self.env.env, 'get') as mock_get:
                mock_get.return_value = ""  # No secrets configured
                
                with patch.object(self.env, 'get_environment') as mock_env:
                    mock_env.return_value = "development"
                    
                    secret = self.env.get_jwt_secret_key()
                    
                    expected = hashlib.sha256("netra_dev_jwt_key".encode()).hexdigest()[:32]
                    assert secret == expected

    def test_get_jwt_secret_key_generates_test_fallback(self):
        """Test JWT secret generates consistent test fallback."""
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_unified:
            mock_unified.side_effect = Exception("Unified manager failed")
            
            with patch.object(self.env.env, 'get') as mock_get:
                mock_get.return_value = ""  # No secrets configured
                
                with patch.object(self.env, 'get_environment') as mock_env:
                    mock_env.return_value = "test"
                    
                    secret = self.env.get_jwt_secret_key()
                    
                    expected = hashlib.sha256("netra_test_jwt_key".encode()).hexdigest()[:32]
                    assert secret == expected

    def test_get_jwt_secret_key_fails_for_staging_without_config(self):
        """Test JWT secret fails for staging without explicit configuration."""
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_unified:
            mock_unified.side_effect = Exception("Unified manager failed")
            
            with patch.object(self.env.env, 'get') as mock_get:
                mock_get.return_value = ""  # No secrets configured
                
                with patch.object(self.env, 'get_environment') as mock_env:
                    mock_env.return_value = "staging"
                    
                    with pytest.raises(ValueError, match="JWT secret not configured for staging"):
                        self.env.get_jwt_secret_key()

    def test_get_jwt_secret_key_fails_for_production_without_config(self):
        """Test JWT secret fails for production without explicit configuration."""
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret') as mock_unified:
            mock_unified.side_effect = Exception("Unified manager failed")
            
            with patch.object(self.env.env, 'get') as mock_get:
                mock_get.return_value = ""  # No secrets configured
                
                with patch.object(self.env, 'get_environment') as mock_env:
                    mock_env.return_value = "production"
                    
                    with pytest.raises(ValueError, match="JWT secret not configured for production"):
                        self.env.get_jwt_secret_key()

    def test_get_jwt_algorithm_environment_specific(self):
        """Test JWT algorithm returns environment-specific values."""
        test_cases = [
            ("production", None, ValueError),  # Must be explicit
            ("staging", None, "HS256"),        # Default
            ("development", None, "HS256"),    # Default
            ("test", None, "HS256"),           # Default
            ("unknown", None, "HS256")         # Default
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_jwt_algorithm()
                    else:
                        assert self.env.get_jwt_algorithm() == expected

    def test_get_jwt_algorithm_respects_explicit_config(self):
        """Test JWT algorithm respects explicit configuration."""
        with patch.object(self.env, 'get_environment', return_value="staging"):
            with patch.object(self.env.env, 'get', return_value="RS256"):
                assert self.env.get_jwt_algorithm() == "RS256"

    def test_get_jwt_expiration_minutes_environment_defaults(self):
        """Test JWT expiration returns environment-specific defaults."""
        test_cases = [
            ("production", None, 15),
            ("staging", None, 30),
            ("development", None, 120),
            ("test", None, 5),
            ("unknown", None, 60)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_jwt_expiration_minutes() == expected

    def test_get_jwt_expiration_minutes_respects_config(self):
        """Test JWT expiration respects explicit configuration."""
        with patch.object(self.env.env, 'get', return_value="45"):
            assert self.env.get_jwt_expiration_minutes() == 45

    def test_get_jwt_expiration_minutes_handles_invalid_config(self):
        """Test JWT expiration handles invalid configuration gracefully."""
        with patch.object(self.env, 'get_environment', return_value="production"):
            with patch.object(self.env.env, 'get', return_value="invalid"):
                assert self.env.get_jwt_expiration_minutes() == 15  # Environment default

    def test_get_refresh_token_expiration_days_environment_defaults(self):
        """Test refresh token expiration returns environment-specific defaults."""
        test_cases = [
            ("production", None, 7),
            ("staging", None, 14),
            ("development", None, 30),
            ("test", None, 1),
            ("unknown", None, 30)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_refresh_token_expiration_days() == expected


class TestSecretKeyConfiguration:
    """Test general secret key configuration."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_secret_key_with_explicit_config(self):
        """Test secret key with explicit configuration."""
        with patch.object(self.env.env, 'get', return_value="explicit-secret"):
            assert self.env.get_secret_key() == "explicit-secret"

    def test_get_secret_key_generates_dev_fallback(self):
        """Test secret key generates development fallback."""
        with patch.object(self.env.env, 'get', return_value=""):
            with patch.object(self.env, 'get_environment', return_value="development"):
                secret = self.env.get_secret_key()
                expected = hashlib.sha256("netra_dev_secret_key".encode()).hexdigest()
                assert secret == expected

    def test_get_secret_key_generates_test_fallback(self):
        """Test secret key generates test fallback."""
        with patch.object(self.env.env, 'get', return_value=""):
            with patch.object(self.env, 'get_environment', return_value="test"):
                secret = self.env.get_secret_key()
                expected = hashlib.sha256("netra_test_secret_key".encode()).hexdigest()
                assert secret == expected

    def test_get_secret_key_fails_for_staging_without_config(self):
        """Test secret key fails for staging without configuration."""
        with patch.object(self.env.env, 'get', return_value=""):
            with patch.object(self.env, 'get_environment', return_value="staging"):
                with pytest.raises(ValueError, match="SECRET_KEY must be explicitly set in staging"):
                    self.env.get_secret_key()

    def test_get_bcrypt_rounds_environment_defaults(self):
        """Test bcrypt rounds returns environment-specific defaults."""
        test_cases = [
            ("production", None, 12),
            ("staging", None, 10),
            ("development", None, 8),
            ("test", None, 4),
            ("unknown", None, 12)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_bcrypt_rounds() == expected


class TestDatabaseConfiguration:
    """Test database configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_database_url_uses_sqlite_for_test(self):
        """Test database URL uses in-memory SQLite for test environment."""
        with patch.object(self.env, 'get_environment', return_value="test"):
            url = self.env.get_database_url()
            assert url == "sqlite+aiosqlite:///:memory:"

    def test_get_database_url_uses_builder_for_non_test(self):
        """Test database URL uses DatabaseURLBuilder for non-test environments."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder:
                mock_instance = MagicMock()
                mock_instance.get_url_for_environment.return_value = "postgresql://test"
                mock_instance.get_safe_log_message.return_value = "Safe log message"
                mock_builder.return_value = mock_instance
                
                url = self.env.get_database_url()
                
                assert url == "postgresql://test"
                mock_builder.assert_called_once()
                mock_instance.get_url_for_environment.assert_called_with(sync=False)

    def test_get_database_url_fails_gracefully_when_builder_fails(self):
        """Test database URL fails gracefully when DatabaseURLBuilder fails."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder:
                mock_instance = MagicMock()
                mock_instance.get_url_for_environment.return_value = None
                mock_instance.debug_info.return_value = {"error": "config missing"}
                mock_builder.return_value = mock_instance
                
                with pytest.raises(ValueError, match="DatabaseURLBuilder failed"):
                    self.env.get_database_url()

    def test_get_postgres_host_environment_defaults(self):
        """Test PostgreSQL host returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, "localhost"),
            ("test", None, "localhost"),
            ("unknown", None, "localhost")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_postgres_host()
                    else:
                        assert self.env.get_postgres_host() == expected

    def test_get_postgres_port_environment_defaults(self):
        """Test PostgreSQL port returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, 5432),
            ("test", None, 5434),
            ("unknown", None, 5432)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_postgres_port()
                    else:
                        assert self.env.get_postgres_port() == expected

    def test_get_postgres_port_handles_invalid_config(self):
        """Test PostgreSQL port handles invalid configuration."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch.object(self.env.env, 'get', return_value="invalid-port"):
                with pytest.raises(ValueError, match="POSTGRES_PORT must be a valid integer"):
                    self.env.get_postgres_port()

    def test_get_postgres_user_environment_defaults(self):
        """Test PostgreSQL user returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, "postgres"),
            ("test", None, "postgres"),
            ("unknown", None, "postgres")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_postgres_user()
                    else:
                        assert self.env.get_postgres_user() == expected

    def test_get_postgres_password_environment_defaults(self):
        """Test PostgreSQL password returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, ""),
            ("test", None, ""),
            ("unknown", None, "")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_postgres_password()
                    else:
                        assert self.env.get_postgres_password() == expected

    def test_get_postgres_db_environment_defaults(self):
        """Test PostgreSQL database name returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, "netra_auth_dev"),
            ("test", None, "netra_auth_test"),
            ("unknown", None, "auth_db")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_postgres_db()
                    else:
                        assert self.env.get_postgres_db() == expected


class TestRedisConfiguration:
    """Test Redis configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_redis_url_environment_defaults(self):
        """Test Redis URL returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, "redis://localhost:6379/1"),
            ("test", None, "redis://localhost:6379/2"),
            ("unknown", None, "redis://localhost:6379/1")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_redis_url()
                    else:
                        assert self.env.get_redis_url() == expected

    def test_get_redis_host_environment_defaults(self):
        """Test Redis host returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, "localhost"),
            ("test", None, "localhost"),
            ("unknown", None, "localhost")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_redis_host()
                    else:
                        assert self.env.get_redis_host() == expected

    def test_get_redis_port_environment_defaults(self):
        """Test Redis port returns environment-specific defaults."""
        test_cases = [
            ("production", None, ValueError),
            ("staging", None, ValueError),
            ("development", None, 6379),
            ("test", None, 6381),
            ("unknown", None, 6379)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    if isinstance(expected, type) and issubclass(expected, Exception):
                        with pytest.raises(expected):
                            self.env.get_redis_port()
                    else:
                        assert self.env.get_redis_port() == expected

    def test_get_redis_port_handles_invalid_config(self):
        """Test Redis port handles invalid configuration."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch.object(self.env.env, 'get', return_value="invalid-port"):
                with pytest.raises(ValueError, match="REDIS_PORT must be a valid integer"):
                    self.env.get_redis_port()

    def test_get_session_ttl_environment_defaults(self):
        """Test session TTL returns environment-specific defaults."""
        test_cases = [
            ("production", None, 3600),
            ("staging", None, 7200),
            ("development", None, 86400),
            ("test", None, 300),
            ("unknown", None, 3600)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_session_ttl() == expected


class TestOAuthConfiguration:
    """Test OAuth configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_oauth_google_client_id_tries_environment_specific_keys(self):
        """Test Google OAuth client ID tries environment-specific keys first."""
        with patch.object(self.env, 'get_environment', return_value="staging"):
            with patch.object(self.env.env, 'get') as mock_get:
                # Mock the env.get to return value for environment-specific key
                def mock_get_side_effect(key):
                    if key == "GOOGLE_OAUTH_CLIENT_ID_STAGING":
                        return "staging-client-id"
                    return None
                    
                mock_get.side_effect = mock_get_side_effect
                
                client_id = self.env.get_oauth_google_client_id()
                assert client_id == "staging-client-id"

    def test_get_oauth_google_client_id_falls_back_to_generic(self):
        """Test Google OAuth client ID falls back to generic keys."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch.object(self.env.env, 'get') as mock_get:
                # Mock the env.get to return value for generic key
                def mock_get_side_effect(key):
                    if key == "OAUTH_GOOGLE_CLIENT_ID":
                        return "generic-client-id"
                    return None
                    
                mock_get.side_effect = mock_get_side_effect
                
                client_id = self.env.get_oauth_google_client_id()
                assert client_id == "generic-client-id"

    def test_get_oauth_google_client_id_returns_empty_for_missing_config(self):
        """Test Google OAuth client ID returns empty string when not configured."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch.object(self.env.env, 'get', return_value=None):
                client_id = self.env.get_oauth_google_client_id()
                assert client_id == ""

    def test_get_oauth_google_client_secret_environment_specific_behavior(self):
        """Test Google OAuth client secret follows same pattern as client ID."""
        with patch.object(self.env, 'get_environment', return_value="production"):
            with patch.object(self.env.env, 'get') as mock_get:
                def mock_get_side_effect(key):
                    if key == "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION":
                        return "production-secret"
                    return None
                    
                mock_get.side_effect = mock_get_side_effect
                
                secret = self.env.get_oauth_google_client_secret()
                assert secret == "production-secret"

    def test_get_oauth_github_client_id_simple_getter(self):
        """Test GitHub OAuth client ID is simple getter."""
        with patch.object(self.env.env, 'get', return_value="github-client-id"):
            assert self.env.get_oauth_github_client_id() == "github-client-id"

    def test_get_oauth_github_client_secret_simple_getter(self):
        """Test GitHub OAuth client secret is simple getter."""
        with patch.object(self.env.env, 'get', return_value="github-secret"):
            assert self.env.get_oauth_github_client_secret() == "github-secret"


class TestServiceURLConfiguration:
    """Test service URL configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_auth_service_port_environment_defaults(self):
        """Test auth service port returns environment-specific defaults."""
        test_cases = [
            ("production", None, 8080),
            ("staging", None, 8080),
            ("development", None, 8081),
            ("test", None, 8082),
            ("unknown", None, 8081)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_auth_service_port() == expected

    def test_get_auth_service_host_environment_defaults(self):
        """Test auth service host returns environment-specific defaults."""
        test_cases = [
            ("production", None, "0.0.0.0"),
            ("staging", None, "0.0.0.0"),
            ("development", None, "0.0.0.0"),
            ("test", None, "127.0.0.1"),
            ("unknown", None, "0.0.0.0")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_auth_service_host() == expected

    def test_get_backend_url_environment_defaults(self):
        """Test backend URL returns environment-specific defaults."""
        test_cases = [
            ("production", None, "https://api.netrasystems.ai"),
            ("staging", None, "https://api.staging.netrasystems.ai"),
            ("development", None, "http://localhost:8000"),
            ("test", None, "http://localhost:8001"),
            ("unknown", None, "http://localhost:8000")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_backend_url() == expected

    def test_get_frontend_url_environment_defaults(self):
        """Test frontend URL returns environment-specific defaults."""
        test_cases = [
            ("production", None, "https://app.netrasystems.ai"),
            ("staging", None, "https://app.staging.netrasystems.ai"),
            ("development", None, "http://localhost:3000"),
            ("test", None, "http://localhost:3001"),
            ("unknown", None, "http://localhost:3000")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_frontend_url() == expected

    def test_get_auth_service_url_constructs_from_host_and_port(self):
        """Test auth service URL constructs from host and port for development."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch.object(self.env.env, 'get', return_value=None):
                with patch.object(self.env, 'get_auth_service_host', return_value="0.0.0.0"):
                    with patch.object(self.env, 'get_auth_service_port', return_value=8081):
                        url = self.env.get_auth_service_url()
                        assert url == "http://localhost:8081"  # Converts 0.0.0.0 to localhost

    def test_get_auth_service_url_production_default(self):
        """Test auth service URL for production environment."""
        with patch.object(self.env, 'get_environment', return_value="production"):
            with patch.object(self.env.env, 'get', return_value=None):
                url = self.env.get_auth_service_url()
                assert url == "https://auth.netrasystems.ai"

    def test_get_oauth_redirect_uri_deprecated_warning(self):
        """Test OAuth redirect URI method shows deprecation warning."""
        with patch.object(self.env, 'get_auth_service_url', return_value="http://localhost:8081"):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                uri = self.env.get_oauth_redirect_uri()
                
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message).lower()
                assert uri == "http://localhost:8081/auth/callback"


class TestEnvironmentDetection:
    """Test environment detection methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_environment_returns_lowercase(self):
        """Test get_environment returns lowercase environment name."""
        with patch.object(self.env.env, 'get', return_value="PRODUCTION"):
            assert self.env.get_environment() == "production"

    def test_get_environment_defaults_to_development(self):
        """Test get_environment defaults to development."""
        with patch.object(self.env.env, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: default if key == "ENVIRONMENT" else None
            assert self.env.get_environment() == "development"

    def test_is_production_detection(self):
        """Test production environment detection."""
        with patch.object(self.env, 'get_environment', return_value="production"):
            assert self.env.is_production() is True
        
        with patch.object(self.env, 'get_environment', return_value="staging"):
            assert self.env.is_production() is False

    def test_is_staging_detection(self):
        """Test staging environment detection."""
        with patch.object(self.env, 'get_environment', return_value="staging"):
            assert self.env.is_staging() is True
        
        with patch.object(self.env, 'get_environment', return_value="production"):
            assert self.env.is_staging() is False

    def test_is_development_detection(self):
        """Test development environment detection."""
        dev_environments = ["development", "dev", "local"]
        
        for env in dev_environments:
            with patch.object(self.env, 'get_environment', return_value=env):
                assert self.env.is_development() is True
        
        with patch.object(self.env, 'get_environment', return_value="production"):
            assert self.env.is_development() is False

    def test_is_testing_detection(self):
        """Test testing environment detection."""
        test_environments = ["test", "testing"]
        
        for env in test_environments:
            with patch.object(self.env, 'get_environment', return_value=env):
                assert self.env.is_testing() is True
        
        # Also check TESTING environment variable
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch.object(self.env.env, 'get', return_value="true"):
                assert self.env.is_testing() is True


class TestCORSConfiguration:
    """Test CORS configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_cors_origins_from_config(self):
        """Test CORS origins from explicit configuration."""
        with patch.object(self.env.env, 'get', return_value="https://custom1.com,https://custom2.com"):
            origins = self.env.get_cors_origins()
            assert set(origins) == {"https://custom1.com", "https://custom2.com"}

    def test_get_cors_origins_environment_defaults(self):
        """Test CORS origins environment-specific defaults."""
        test_cases = [
            ("production", ["https://netrasystems.ai", "https://app.netrasystems.ai"]),
            ("staging", ["https://app.staging.netrasystems.ai", "https://staging.netrasystems.ai"]),
            ("development", ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]),
            ("test", ["http://localhost:3001", "http://localhost:8001", "http://127.0.0.1:3001"]),
            ("unknown", ["http://localhost:3000"])
        ]
        
        for env, expected_origins in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=None):
                    origins = self.env.get_cors_origins()
                    assert set(origins) == set(expected_origins)


class TestLoggingConfiguration:
    """Test logging configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_log_level_environment_defaults(self):
        """Test log level returns environment-specific defaults."""
        test_cases = [
            ("production", None, "WARNING"),
            ("staging", None, "INFO"),
            ("development", None, "DEBUG"),
            ("test", None, "ERROR"),
            ("unknown", None, "INFO")
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_log_level() == expected

    def test_get_log_level_respects_config(self):
        """Test log level respects explicit configuration."""
        with patch.object(self.env.env, 'get', return_value="critical"):
            assert self.env.get_log_level() == "CRITICAL"

    def test_should_enable_debug_environment_defaults(self):
        """Test debug enable returns environment-specific defaults."""
        test_cases = [
            ("production", None, False),
            ("staging", None, False),
            ("development", None, True),
            ("test", None, False),
            ("unknown", None, False)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.should_enable_debug() == expected

    def test_should_enable_debug_respects_config(self):
        """Test debug enable respects explicit configuration."""
        with patch.object(self.env.env, 'get', return_value="true"):
            assert self.env.should_enable_debug() is True
        
        with patch.object(self.env.env, 'get', return_value="false"):
            assert self.env.should_enable_debug() is False


class TestRateLimitingConfiguration:
    """Test rate limiting configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_login_rate_limit_environment_defaults(self):
        """Test login rate limit returns environment-specific defaults."""
        test_cases = [
            ("production", None, 3),
            ("staging", None, 5),
            ("development", None, 10),
            ("test", None, 100),
            ("unknown", None, 5)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_login_rate_limit() == expected

    def test_get_login_rate_limit_period_environment_defaults(self):
        """Test login rate limit period returns environment-specific defaults."""
        test_cases = [
            ("production", None, 600),
            ("staging", None, 300),
            ("development", None, 60),
            ("test", None, 10),
            ("unknown", None, 300)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_login_rate_limit_period() == expected

    def test_get_max_failed_login_attempts_environment_defaults(self):
        """Test max failed login attempts returns environment-specific defaults."""
        test_cases = [
            ("production", None, 3),
            ("staging", None, 5),
            ("development", None, 10),
            ("test", None, 100),
            ("unknown", None, 5)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_max_failed_login_attempts() == expected

    def test_get_account_lockout_duration_default(self):
        """Test account lockout duration has correct default."""
        with patch.object(self.env.env, 'get', return_value=None):
            assert self.env.get_account_lockout_duration() == 900

    def test_get_account_lockout_duration_handles_invalid(self):
        """Test account lockout duration handles invalid configuration."""
        with patch.object(self.env.env, 'get', return_value="invalid"):
            assert self.env.get_account_lockout_duration() == 900


class TestPasswordPolicyConfiguration:
    """Test password policy configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_min_password_length_environment_defaults(self):
        """Test minimum password length returns environment-specific defaults."""
        test_cases = [
            ("production", None, 12),
            ("staging", None, 10),
            ("development", None, 6),
            ("test", None, 4),
            ("unknown", None, 8)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.get_min_password_length() == expected

    def test_require_password_complexity_environment_defaults(self):
        """Test password complexity requirement returns environment-specific defaults."""
        test_cases = [
            ("production", None, True),
            ("staging", None, True),
            ("development", None, False),
            ("test", None, False),
            ("unknown", None, True)
        ]
        
        for env, config_value, expected in test_cases:
            with patch.object(self.env, 'get_environment', return_value=env):
                with patch.object(self.env.env, 'get', return_value=config_value):
                    assert self.env.require_password_complexity() == expected


class TestEmailConfiguration:
    """Test email configuration methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_smtp_host_simple_getter(self):
        """Test SMTP host is simple getter with default."""
        with patch.object(self.env.env, 'get', return_value="smtp.example.com"):
            assert self.env.get_smtp_host() == "smtp.example.com"
        
        with patch.object(self.env.env, 'get', return_value=None):
            assert self.env.get_smtp_host() == ""

    def test_get_smtp_port_handles_conversion(self):
        """Test SMTP port handles string to int conversion."""
        with patch.object(self.env.env, 'get', return_value="2525"):
            assert self.env.get_smtp_port() == 2525
        
        with patch.object(self.env.env, 'get', return_value="invalid"):
            assert self.env.get_smtp_port() == 587

    def test_get_smtp_from_email_default(self):
        """Test SMTP from email has correct default."""
        with patch.object(self.env.env, 'get', return_value=None):
            assert self.env.get_smtp_from_email() == "noreply@netra.ai"

    def test_is_smtp_enabled_checks_required_fields(self):
        """Test SMTP enabled checks for required host and username."""
        # Both present
        with patch.object(self.env, 'get_smtp_host', return_value="smtp.example.com"):
            with patch.object(self.env, 'get_smtp_username', return_value="user"):
                assert self.env.is_smtp_enabled() is True
        
        # Missing host
        with patch.object(self.env, 'get_smtp_host', return_value=""):
            with patch.object(self.env, 'get_smtp_username', return_value="user"):
                assert self.env.is_smtp_enabled() is False
        
        # Missing username
        with patch.object(self.env, 'get_smtp_host', return_value="smtp.example.com"):
            with patch.object(self.env, 'get_smtp_username', return_value=""):
                assert self.env.is_smtp_enabled() is False


class TestGenericAccessors:
    """Test generic accessor methods."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_get_method(self):
        """Test generic get method."""
        with patch.object(self.env.env, 'get', return_value="test-value"):
            assert self.env.get("TEST_KEY", "default") == "test-value"

    def test_set_method(self):
        """Test generic set method."""
        with patch.object(self.env.env, 'set', return_value=True):
            result = self.env.set("TEST_KEY", "test-value", "test-source")
            assert result is True

    def test_exists_method(self):
        """Test generic exists method."""
        with patch.object(self.env.env, 'exists', return_value=True):
            assert self.env.exists("TEST_KEY") is True

    def test_get_all_method(self):
        """Test generic get_all method."""
        with patch.object(self.env.env, 'get_all', return_value={"KEY": "value"}):
            result = self.env.get_all()
            assert result == {"KEY": "value"}


class TestValidationMethod:
    """Test the validate method."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_validate_success_with_all_required(self):
        """Test validation succeeds when all required variables are present."""
        with patch.object(self.env, 'get_jwt_secret_key', return_value="test-secret"):
            with patch.object(self.env, 'is_development', return_value=True):
                with patch.object(self.env, 'get_bcrypt_rounds', return_value=8):
                    with patch.object(self.env, 'get_jwt_expiration_minutes', return_value=120):
                        with patch.object(self.env, 'get_min_password_length', return_value=6):
                            with patch.object(self.env, 'is_production', return_value=False):
                                with patch.object(self.env, 'get_login_rate_limit', return_value=10):
                                    with patch.object(self.env, 'is_smtp_enabled', return_value=False):
                                        result = self.env.validate()
                                        
                                        assert result["valid"] is True
                                        assert len(result["issues"]) == 0

    def test_validate_fails_with_missing_jwt_secret(self):
        """Test validation fails when JWT secret is missing."""
        with patch.object(self.env, 'get_jwt_secret_key', return_value=""):
            result = self.env.validate()
            
            assert result["valid"] is False
            assert any("JWT_SECRET_KEY" in issue for issue in result["issues"])

    def test_validate_warns_about_insecure_defaults_in_production(self):
        """Test validation warns about insecure defaults in production."""
        with patch.object(self.env, 'get_jwt_secret_key', return_value="test-secret"):
            with patch.object(self.env, 'is_development', return_value=False):
                with patch.object(self.env, 'is_production', return_value=True):
                    with patch.object(self.env, 'get_bcrypt_rounds', return_value=8):  # Too low
                        with patch.object(self.env, 'get_login_rate_limit', return_value=15):  # Too high
                            with patch.object(self.env, 'is_smtp_enabled', return_value=False):  # Missing
                                result = self.env.validate()
                                
                                # Should have warnings
                                assert len(result["warnings"]) > 0

    def test_validate_warns_about_long_jwt_expiration(self):
        """Test validation warns about very long JWT expiration."""
        with patch.object(self.env, 'get_jwt_secret_key', return_value="test-secret"):
            with patch.object(self.env, 'is_development', return_value=True):
                with patch.object(self.env, 'get_jwt_expiration_minutes', return_value=2000):  # > 24 hours
                    result = self.env.validate()
                    
                    assert any("JWT_EXPIRATION_MINUTES" in warning for warning in result["warnings"])

    def test_validate_warns_about_weak_password_policy(self):
        """Test validation warns about weak password policy."""
        with patch.object(self.env, 'get_jwt_secret_key', return_value="test-secret"):
            with patch.object(self.env, 'is_development', return_value=True):
                with patch.object(self.env, 'get_min_password_length', return_value=4):  # Too short
                    result = self.env.validate()
                    
                    assert any("MIN_PASSWORD_LENGTH" in warning for warning in result["warnings"])


class TestSingletonBehavior:
    """Test singleton behavior of auth environment."""

    def test_get_auth_env_returns_same_instance(self):
        """Test get_auth_env returns the same instance."""
        # Import here to get fresh instance
        from auth_service.auth_core.auth_environment import get_auth_env
        
        env1 = get_auth_env()
        env2 = get_auth_env()
        
        assert env1 is env2

    def test_convenience_functions_use_singleton(self):
        """Test convenience functions use singleton instance."""
        from auth_service.auth_core.auth_environment import (
            get_jwt_secret_key, get_database_url, get_environment,
            is_production, is_development
        )
        
        with patch('auth_service.auth_core.auth_environment.get_auth_env') as mock_get_env:
            mock_env = MagicMock()
            mock_env.get_jwt_secret_key.return_value = "test-secret"
            mock_env.get_database_url.return_value = "test-db-url"
            mock_env.get_environment.return_value = "test"
            mock_env.is_production.return_value = False
            mock_env.is_development.return_value = True
            mock_get_env.return_value = mock_env
            
            # Test each convenience function
            assert get_jwt_secret_key() == "test-secret"
            assert get_database_url() == "test-db-url"
            assert get_environment() == "test"
            assert is_production() is False
            assert is_development() is True
            
            # Verify singleton was called for each
            assert mock_get_env.call_count == 5


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    def setup_method(self):
        """Setup for each test."""
        self.env = AuthEnvironment()

    def test_handles_environment_variable_not_found_gracefully(self):
        """Test handles missing environment variables gracefully."""
        with patch.object(self.env.env, 'get', side_effect=KeyError("Variable not found")):
            # Should not raise exception, should return defaults
            try:
                result = self.env.get_environment()
                # Should get default
                assert result == "development"
            except KeyError:
                pytest.fail("Should handle missing environment variables gracefully")

    def test_handles_invalid_integer_configurations(self):
        """Test handles invalid integer configurations gracefully."""
        # Test various integer config methods with invalid values
        test_methods = [
            ('get_jwt_expiration_minutes', 60),
            ('get_refresh_token_expiration_days', 30),
            ('get_bcrypt_rounds', 12),
            ('get_session_ttl', 3600),
            ('get_login_rate_limit', 5),
            ('get_login_rate_limit_period', 300),
            ('get_max_failed_login_attempts', 5),
            ('get_min_password_length', 8)
        ]
        
        for method_name, expected_default in test_methods:
            with patch.object(self.env, 'get_environment', return_value="unknown"):
                with patch.object(self.env.env, 'get', return_value="invalid-integer"):
                    method = getattr(self.env, method_name)
                    result = method()
                    # Should return environment-specific default, not crash
                    assert isinstance(result, int)

    def test_oauth_redirect_uri_with_different_providers(self):
        """Test OAuth redirect URI with different provider parameters."""
        with patch.object(self.env, 'get_auth_service_url', return_value="http://localhost:8081"):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                
                # Different providers should all return same auth service callback
                for provider in ["google", "github", "facebook", "custom"]:
                    uri = self.env.get_oauth_redirect_uri(provider)
                    assert uri == "http://localhost:8081/auth/callback"

    def test_database_url_builder_with_missing_dependencies(self):
        """Test database URL builder handles missing shared dependencies."""
        with patch.object(self.env, 'get_environment', return_value="development"):
            with patch('auth_service.auth_core.auth_environment.DatabaseURLBuilder', side_effect=ImportError("Module not found")):
                # Should raise error when DatabaseURLBuilder can't be imported
                with pytest.raises(ImportError):
                    self.env.get_database_url()

    def test_unified_jwt_secret_with_import_error(self):
        """Test unified JWT secret handles import errors gracefully."""
        with patch('auth_service.auth_core.auth_environment.get_unified_jwt_secret', side_effect=ImportError("Module not found")):
            with patch.object(self.env, 'get_environment', return_value="test"):
                with patch.object(self.env.env, 'get', return_value=""):
                    # Should fall back to test environment generation
                    secret = self.env.get_jwt_secret_key()
                    expected = hashlib.sha256("netra_test_jwt_key".encode()).hexdigest()[:32]
                    assert secret == expected

    def test_cors_origins_with_whitespace_in_config(self):
        """Test CORS origins handles whitespace in configuration."""
        with patch.object(self.env.env, 'get', return_value=" https://example1.com , https://example2.com , "):
            origins = self.env.get_cors_origins()
            assert set(origins) == {"https://example1.com", "https://example2.com"}

    def test_environment_detection_case_insensitive(self):
        """Test environment detection is case insensitive."""
        test_cases = ["PRODUCTION", "Production", "production", "PROD"]
        
        for env_value in test_cases:
            with patch.object(self.env.env, 'get', return_value=env_value):
                result = self.env.get_environment()
                assert result.islower()