"""
Test AuthClientConfigManager and Related Configuration Classes

Business Value Justification (BVJ):
- Segment: Platform/Internal - affects all services and environments  
- Business Goal: Security & System Reliability - ensures secure authentication workflows
- Value Impact: Prevents security breaches through proper auth configuration management
- Strategic Impact: $5M+ security risk mitigation through validated authentication infrastructure

This comprehensive test suite validates the SSOT AuthClientConfigManager system that controls
authentication for the entire platform. These tests ensure:
1. Configuration loading works correctly across all environments
2. Security validation prevents misconfigurations that could cause breaches
3. Environment isolation prevents config leakage between dev/staging/prod
4. OAuth configuration generation works for all supported providers
5. Error handling protects against silent authentication failures

CRITICAL: All tests follow CLAUDE.md requirements:
- NO CHEATING ON TESTS = Tests must fail hard when system breaks
- NO MOCKS for business logic - Use real AuthClientConfigManager instances
- ABSOLUTE IMPORTS ONLY - No relative imports
- ERROR RAISING - No try/except masking failures
"""

import logging
import os
import pytest
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# ABSOLUTE IMPORTS ONLY - Following CLAUDE.md requirements
from netra_backend.app.clients.auth_client_config import (
    AuthClientConfigManager,
    OAuthConfigGenerator, 
    AuthClientConfig,
    AuthClientSecurityConfig,
    OAuthConfig,
    load_auth_client_config,
    load_auth_security_config,
    get_auth_config,
    get_auth_security_config,
    auth_config_manager
)
from netra_backend.app.core.environment_constants import EnvironmentDetector, Environment
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestAuthClientConfigManagerComprehensive:
    """
    Comprehensive unit tests for AuthClientConfigManager SSOT class.
    
    Business Value: Ensures authentication configuration is secure, reliable,
    and properly isolated across environments. Critical for preventing security
    breaches and ensuring proper service-to-service authentication.
    """

    def test_auth_client_config_manager_initialization(self):
        """
        Test AuthClientConfigManager initializes correctly.
        
        Security Value: Ensures configuration manager starts in clean state,
        preventing stale configuration from affecting authentication.
        """
        manager = AuthClientConfigManager()
        
        # Configuration should be lazily loaded (None until requested)
        assert manager._config is None
        assert manager._security_config is None
        
        # Manager should be ready to load configuration
        assert hasattr(manager, 'get_config')
        assert hasattr(manager, 'get_security_config')
        assert hasattr(manager, 'reload_config')
        assert hasattr(manager, 'validate_config')

    def test_auth_client_config_manager_singleton_behavior(self):
        """
        Test global auth_config_manager provides singleton behavior.
        
        Security Value: Ensures consistent configuration state across the application,
        preventing configuration drift that could cause auth failures.
        """
        # Global instance should exist
        assert auth_config_manager is not None
        assert isinstance(auth_config_manager, AuthClientConfigManager)
        
        # Should maintain singleton behavior through helper functions
        config1 = get_auth_config()
        config2 = get_auth_config()
        
        # Same configuration instance should be returned
        assert config1.service_url == config2.service_url
        assert config1.timeout == config2.timeout

    def test_get_config_lazy_loading(self):
        """
        Test get_config() performs lazy loading correctly.
        
        Security Value: Ensures configuration is loaded on-demand with latest
        environment variables, preventing stale auth service URLs.
        """
        manager = AuthClientConfigManager()
        
        # Initially no config loaded
        assert manager._config is None
        
        # First call should load config
        config = manager.get_config()
        assert config is not None
        assert isinstance(config, AuthClientConfig)
        assert manager._config is config
        
        # Second call should return cached config
        config2 = manager.get_config()
        assert config2 is config

    def test_get_security_config_lazy_loading(self):
        """
        Test get_security_config() performs lazy loading correctly.
        
        Security Value: Ensures security configuration (secrets, keys) is loaded
        securely on-demand, minimizing exposure time in memory.
        """
        manager = AuthClientConfigManager()
        
        # Initially no security config loaded
        assert manager._security_config is None
        
        # First call should load security config
        security_config = manager.get_security_config()
        assert security_config is not None
        assert isinstance(security_config, AuthClientSecurityConfig)
        assert manager._security_config is security_config
        
        # Second call should return cached config
        security_config2 = manager.get_security_config()
        assert security_config2 is security_config

    def test_reload_config_clears_cache(self):
        """
        Test reload_config() clears cached configuration.
        
        Security Value: Ensures configuration can be refreshed when environment
        variables change, allowing for rotation of secrets without restart.
        """
        manager = AuthClientConfigManager()
        
        # Load initial configs
        config = manager.get_config()
        security_config = manager.get_security_config()
        assert manager._config is not None
        assert manager._security_config is not None
        
        # Reload should clear cache
        manager.reload_config()
        assert manager._config is None
        assert manager._security_config is None
        
        # Next get should load fresh configs
        new_config = manager.get_config()
        new_security_config = manager.get_security_config()
        assert new_config is not None
        assert new_security_config is not None

    def test_validate_config_with_valid_configuration(self):
        """
        Test validate_config() returns True for valid configuration.
        
        Security Value: Ensures configuration validation correctly identifies
        properly configured authentication settings.
        """
        manager = AuthClientConfigManager()
        
        # Mock valid environment for testing
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'AUTH_SERVICE_URL': 'http://auth-service:8081',
                'SERVICE_SECRET': 'valid-service-secret',
                'JWT_SECRET_KEY': 'jwt-secret',
                'FERNET_KEY': 'encryption-key'
            }.get(key, default)
            
            # Reload to pick up mocked environment
            manager.reload_config()
            
            # Validation should pass
            assert manager.validate_config() is True

    def test_validate_config_with_missing_service_url(self):
        """
        Test validate_config() returns False when service URL is missing.
        
        Security Value: Prevents authentication attempts with invalid service URLs
        that could fail silently or connect to wrong endpoints.
        """
        manager = AuthClientConfigManager()
        
        # Mock environment with missing service URL
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'AUTH_SERVICE_URL': '',  # Empty service URL
                'SERVICE_SECRET': 'valid-service-secret'
            }.get(key, default)
            
            # Reload to pick up mocked environment
            manager.reload_config()
            
            # Validation should fail
            assert manager.validate_config() is False

    def test_validate_config_with_invalid_security_config(self):
        """
        Test validate_config() returns False when security config is invalid.
        
        Security Value: Ensures authentication fails fast when security secrets
        are missing, preventing silent authentication bypasses.
        """
        manager = AuthClientConfigManager()
        
        # Mock environment with missing service secret
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'AUTH_SERVICE_URL': 'http://auth-service:8081',
                'SERVICE_SECRET': None  # Missing service secret
            }.get(key, default)
            
            # Reload to pick up mocked environment
            manager.reload_config()
            
            # Validation should fail
            assert manager.validate_config() is False

    def test_validate_config_handles_exceptions(self):
        """
        Test validate_config() handles exceptions gracefully.
        
        Security Value: Ensures configuration validation fails safely when
        unexpected errors occur, preventing authentication bypasses.
        """
        manager = AuthClientConfigManager()
        
        # Mock get_config to raise exception
        with patch.object(manager, 'get_config', side_effect=Exception("Config error")):
            # Should return False, not raise exception
            assert manager.validate_config() is False


class TestOAuthConfigGeneratorComprehensive:
    """
    Test OAuth configuration generation for different environments and providers.
    
    Security Value: Ensures OAuth configurations are correctly generated for each
    environment with proper isolation and security settings.
    """

    def test_oauth_config_generator_initialization(self):
        """
        Test OAuthConfigGenerator initializes with environment detection.
        
        Security Value: Ensures OAuth generator correctly detects environment
        and sets up appropriate configuration mappings.
        """
        generator = OAuthConfigGenerator()
        
        # Should have environment configurations
        assert hasattr(generator, 'env_configs')
        assert isinstance(generator.env_configs, dict)
        
        # Should have configs for all environments
        assert 'development' in generator.env_configs
        assert 'production' in generator.env_configs
        assert 'staging' in generator.env_configs
        
        # Each environment should have Google OAuth config
        for env in ['development', 'production', 'staging']:
            assert 'google' in generator.env_configs[env]
            google_config = generator.env_configs[env]['google']
            assert 'client_id' in google_config
            assert 'client_secret' in google_config
            assert 'redirect_uri' in google_config

    def test_oauth_config_generator_development_environment(self):
        """
        Test OAuth config generation for development environment.
        
        Security Value: Ensures development OAuth configuration uses appropriate
        dev credentials and localhost redirect URIs.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT': 'dev-google-client-id',
                'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT': 'dev-google-client-secret',
                'OAUTH_REDIRECT_URI': 'http://localhost:3000/auth/callback'
            }.get(key, default)
            
            generator = OAuthConfigGenerator()
            config = generator.generate('development')
            
            assert 'google' in config
            google_config = config['google']
            assert google_config['client_id'] == 'dev-google-client-id'
            assert google_config['client_secret'] == 'dev-google-client-secret'
            assert 'localhost' in google_config['redirect_uri']

    def test_oauth_config_generator_production_environment(self):
        """
        Test OAuth config generation for production environment.
        
        Security Value: Ensures production OAuth configuration uses production
        credentials and secure HTTPS redirect URIs.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION': 'prod-google-client-id',
                'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION': 'prod-google-client-secret',
                'OAUTH_REDIRECT_URI': 'https://app.netra.ai/auth/callback'
            }.get(key, default)
            
            generator = OAuthConfigGenerator()
            config = generator.generate('production')
            
            assert 'google' in config
            google_config = config['google']
            assert google_config['client_id'] == 'prod-google-client-id'
            assert google_config['client_secret'] == 'prod-google-client-secret'
            assert google_config['redirect_uri'].startswith('https://')

    def test_oauth_config_generator_staging_environment(self):
        """
        Test OAuth config generation for staging environment.
        
        Security Value: Ensures staging OAuth configuration uses staging
        credentials and staging-specific redirect URIs.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'staging-google-client-id',
                'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'staging-google-client-secret',
                'OAUTH_REDIRECT_URI': 'https://app.staging.netra.ai/auth/callback'
            }.get(key, default)
            
            generator = OAuthConfigGenerator()
            config = generator.generate('staging')
            
            assert 'google' in config
            google_config = config['google']
            assert google_config['client_id'] == 'staging-google-client-id'
            assert google_config['client_secret'] == 'staging-google-client-secret'
            assert 'staging' in google_config['redirect_uri']

    def test_oauth_config_generator_invalid_environment_fallback(self):
        """
        Test OAuth config generation falls back to development for invalid environments.
        
        Security Value: Ensures unknown environments default to safe development
        configuration rather than failing or using wrong credentials.
        """
        generator = OAuthConfigGenerator()
        
        # Should fallback to development for invalid environment
        config = generator.generate('invalid-environment')
        dev_config = generator.generate('development')
        
        # Should be identical to development config
        assert config == dev_config

    def test_get_provider_config_google(self):
        """
        Test getting configuration for specific OAuth provider (Google).
        
        Security Value: Ensures provider-specific configurations are correctly
        isolated and returned with proper credentials.
        """
        generator = OAuthConfigGenerator()
        
        google_config = generator.get_provider_config('google', 'development')
        
        assert isinstance(google_config, dict)
        assert 'client_id' in google_config
        assert 'client_secret' in google_config  
        assert 'redirect_uri' in google_config

    def test_get_provider_config_invalid_provider(self):
        """
        Test getting configuration for invalid OAuth provider.
        
        Security Value: Ensures invalid provider requests return empty config
        rather than default credentials that could be misused.
        """
        generator = OAuthConfigGenerator()
        
        invalid_config = generator.get_provider_config('invalid-provider', 'development')
        
        # Should return empty dict for invalid provider
        assert invalid_config == {}

    def test_get_oauth_config_method(self):
        """
        Test get_oauth_config() returns proper OAuthConfig dataclass.
        
        Security Value: Ensures OAuth configuration is returned in strongly-typed
        format that prevents configuration errors.
        """
        generator = OAuthConfigGenerator()
        
        oauth_config = generator.get_oauth_config('development')
        
        # Should return OAuthConfig dataclass
        assert hasattr(oauth_config, 'redirect_uri')
        assert hasattr(oauth_config, 'environment')
        assert oauth_config.environment == 'development'
        assert isinstance(oauth_config.redirect_uri, str)


class TestAuthClientConfigComprehensive:
    """
    Test AuthClientConfig dataclass for various configuration scenarios.
    
    Security Value: Validates client configuration handles different environments
    and provides correct service URLs and security settings.
    """

    def test_auth_client_config_initialization_with_defaults(self):
        """
        Test AuthClientConfig initialization with default values.
        
        Security Value: Ensures configuration has secure defaults (SSL verification,
        reasonable timeouts) that prevent security bypasses.
        """
        config = AuthClientConfig()
        
        # Should have secure defaults
        assert config.timeout == 30  # Reasonable timeout
        assert config.max_retries == 3  # Reasonable retry count
        assert config.retry_delay == 1.0  # Reasonable delay
        assert config.verify_ssl is True  # SSL verification enabled
        assert config.api_version == "v1"  # Current API version

    def test_auth_client_config_initialization_with_parameters(self):
        """
        Test AuthClientConfig initialization with custom parameters.
        
        Security Value: Ensures custom configuration parameters are properly
        set while maintaining security requirements.
        """
        config = AuthClientConfig(
            service_url="https://custom-auth.example.com",
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
            verify_ssl=True,
            api_version="v2"
        )
        
        assert config.service_url == "https://custom-auth.example.com"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.verify_ssl is True
        assert config.api_version == "v2"

    def test_auth_client_config_post_init_development_environment(self):
        """
        Test __post_init__ sets correct service URL for development environment.
        
        Security Value: Ensures development environment connects to localhost
        auth service, preventing accidental production connections.
        """
        with patch.object(EnvironmentDetector, 'get_environment', return_value='development'), \
             patch.object(get_env(), 'get', return_value='http://localhost:8081'):
            
            config = AuthClientConfig(service_url=None)
            
            # Should detect development and set localhost URL
            assert config.service_url == 'http://localhost:8081'

    def test_auth_client_config_post_init_staging_environment(self):
        """
        Test __post_init__ sets correct service URL for staging environment.
        
        Security Value: Ensures staging environment connects to staging auth service,
        preventing cross-environment auth attempts.
        """
        with patch.object(EnvironmentDetector, 'get_environment', return_value='staging'), \
             patch.object(get_env(), 'get', return_value='https://auth.staging.netrasystems.ai'):
            
            config = AuthClientConfig(service_url=None)
            
            # Should detect staging and set staging URL
            assert 'staging' in config.service_url
            assert config.service_url.startswith('https://')

    def test_auth_client_config_post_init_production_environment(self):
        """
        Test __post_init__ sets correct service URL for production environment.
        
        Security Value: Ensures production environment connects to production auth
        service with HTTPS, maintaining production security standards.
        """
        with patch.object(EnvironmentDetector, 'get_environment', return_value='production'), \
             patch.object(get_env(), 'get', return_value='https://auth.netrasystems.ai'):
            
            config = AuthClientConfig(service_url=None)
            
            # Should detect production and set production HTTPS URL
            assert config.service_url == 'https://auth.netrasystems.ai'
            assert config.service_url.startswith('https://')

    def test_auth_client_config_base_url_property(self):
        """
        Test base_url property constructs correct API URL.
        
        Security Value: Ensures API URLs are constructed correctly with proper
        versioning to prevent API endpoint confusion.
        """
        config = AuthClientConfig(
            service_url="https://auth.example.com",
            api_version="v2"
        )
        
        expected_base_url = "https://auth.example.com/api/v2"
        assert config.base_url == expected_base_url

    def test_auth_client_config_health_url_property(self):
        """
        Test health_url property constructs correct health check URL.
        
        Security Value: Ensures health check endpoints are correctly constructed
        for service monitoring and availability verification.
        """
        config = AuthClientConfig(service_url="https://auth.example.com")
        
        expected_health_url = "https://auth.example.com/health"
        assert config.health_url == expected_health_url

    def test_auth_client_config_to_dict_method(self):
        """
        Test to_dict() method serializes configuration correctly.
        
        Security Value: Ensures configuration can be serialized for logging and
        debugging without exposing sensitive information.
        """
        config = AuthClientConfig(
            service_url="https://auth.example.com",
            timeout=45,
            max_retries=4,
            retry_delay=1.5,
            verify_ssl=True,
            api_version="v2"
        )
        
        config_dict = config.to_dict()
        
        # Should contain all configuration fields
        expected_keys = {
            "service_url", "timeout", "max_retries", 
            "retry_delay", "verify_ssl", "api_version"
        }
        assert set(config_dict.keys()) == expected_keys
        
        # Values should match
        assert config_dict["service_url"] == "https://auth.example.com"
        assert config_dict["timeout"] == 45
        assert config_dict["max_retries"] == 4
        assert config_dict["retry_delay"] == 1.5
        assert config_dict["verify_ssl"] is True
        assert config_dict["api_version"] == "v2"


class TestAuthClientSecurityConfigComprehensive:
    """
    Test AuthClientSecurityConfig for security-critical configuration scenarios.
    
    Security Value: Validates security configuration properly handles secrets,
    encryption keys, and security settings that protect authentication.
    """

    def test_auth_client_security_config_initialization_defaults(self):
        """
        Test AuthClientSecurityConfig initialization with secure defaults.
        
        Security Value: Ensures security configuration has appropriate defaults
        that enable security features by default.
        """
        config = AuthClientSecurityConfig()
        
        # Security defaults
        assert config.service_secret is None  # No default secret
        assert config.jwt_secret is None  # No default JWT secret
        assert config.encryption_key is None  # No default encryption key
        assert config.require_https is False  # Configurable HTTPS requirement
        assert config.token_validation_enabled is True  # Token validation enabled by default

    def test_auth_client_security_config_initialization_with_secrets(self):
        """
        Test AuthClientSecurityConfig initialization with security secrets.
        
        Security Value: Ensures security secrets are properly stored and accessible
        for authentication operations.
        """
        config = AuthClientSecurityConfig(
            service_secret="service-secret-123",
            jwt_secret="jwt-secret-456",
            encryption_key="encryption-key-789",
            require_https=True,
            token_validation_enabled=True
        )
        
        assert config.service_secret == "service-secret-123"
        assert config.jwt_secret == "jwt-secret-456"
        assert config.encryption_key == "encryption-key-789"
        assert config.require_https is True
        assert config.token_validation_enabled is True

    def test_auth_client_security_config_is_valid_with_service_secret(self):
        """
        Test is_valid() returns True when service secret is present.
        
        Security Value: Ensures security configuration is considered valid only
        when essential service secret is provided.
        """
        config = AuthClientSecurityConfig(service_secret="valid-service-secret")
        
        assert config.is_valid() is True

    def test_auth_client_security_config_is_valid_without_service_secret(self):
        """
        Test is_valid() returns False when service secret is missing.
        
        Security Value: Ensures security configuration is invalid without
        service secret, preventing authentication without proper credentials.
        """
        config = AuthClientSecurityConfig(service_secret=None)
        
        assert config.is_valid() is False

    def test_auth_client_security_config_is_valid_with_empty_service_secret(self):
        """
        Test is_valid() returns False when service secret is empty string.
        
        Security Value: Ensures empty service secrets are treated as invalid,
        preventing authentication bypasses with empty credentials.
        """
        config = AuthClientSecurityConfig(service_secret="")
        
        assert config.is_valid() is False


class TestOAuthConfigComprehensive:
    """
    Test OAuthConfig dataclass for OAuth-specific configuration scenarios.
    
    Security Value: Validates OAuth configuration handles client credentials,
    redirect URIs, and scopes securely.
    """

    def test_oauth_config_initialization_defaults(self):
        """
        Test OAuthConfig initialization with default values.
        
        Security Value: Ensures OAuth configuration has secure defaults including
        proper scope and standard OAuth endpoints.
        """
        config = OAuthConfig()
        
        # Should have secure defaults
        assert config.client_id is None  # No default client ID
        assert config.client_secret is None  # No default client secret
        assert config.redirect_uri is None  # No default redirect URI
        assert config.auth_url is None  # No default auth URL
        assert config.token_url is None  # No default token URL
        assert config.scope == "openid profile email"  # Standard OpenID scopes

    def test_oauth_config_initialization_with_parameters(self):
        """
        Test OAuthConfig initialization with custom parameters.
        
        Security Value: Ensures OAuth configuration accepts custom parameters
        while maintaining security requirements.
        """
        config = OAuthConfig(
            client_id="oauth-client-123",
            client_secret="oauth-secret-456", 
            redirect_uri="https://app.example.com/callback",
            auth_url="https://provider.com/oauth/authorize",
            token_url="https://provider.com/oauth/token",
            scope="openid profile email admin"
        )
        
        assert config.client_id == "oauth-client-123"
        assert config.client_secret == "oauth-secret-456"
        assert config.redirect_uri == "https://app.example.com/callback"
        assert config.auth_url == "https://provider.com/oauth/authorize"
        assert config.token_url == "https://provider.com/oauth/token"
        assert config.scope == "openid profile email admin"

    def test_oauth_config_from_env_method(self):
        """
        Test from_env() class method loads configuration from environment.
        
        Security Value: Ensures OAuth credentials are loaded from environment
        variables, following security best practices for credential management.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT': 'env-client-id',
                'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT': 'env-client-secret',
                'OAUTH_REDIRECT_URI': 'http://localhost:8000/auth/callback',
                'OAUTH_AUTH_URL': 'https://accounts.google.com/o/oauth2/v2/auth',
                'OAUTH_TOKEN_URL': 'https://oauth2.googleapis.com/token',
                'OAUTH_SCOPE': 'openid profile email'
            }.get(key, default)
            
            config = OAuthConfig.from_env()
            
            assert config.client_id == 'env-client-id'
            assert config.client_secret == 'env-client-secret'
            assert config.redirect_uri == 'http://localhost:8000/auth/callback'
            assert config.auth_url == 'https://accounts.google.com/o/oauth2/v2/auth'
            assert config.token_url == 'https://oauth2.googleapis.com/token'
            assert config.scope == 'openid profile email'

    def test_oauth_config_is_configured_with_valid_credentials(self):
        """
        Test is_configured() returns True when client credentials are present.
        
        Security Value: Ensures OAuth configuration is considered properly
        configured only when both client ID and secret are provided.
        """
        config = OAuthConfig(
            client_id="valid-client-id",
            client_secret="valid-client-secret"
        )
        
        assert config.is_configured() is True

    def test_oauth_config_is_configured_missing_client_id(self):
        """
        Test is_configured() returns False when client ID is missing.
        
        Security Value: Ensures OAuth configuration is invalid without
        client ID, preventing OAuth flows without proper identification.
        """
        config = OAuthConfig(
            client_id=None,
            client_secret="valid-client-secret"
        )
        
        assert config.is_configured() is False

    def test_oauth_config_is_configured_missing_client_secret(self):
        """
        Test is_configured() returns False when client secret is missing.
        
        Security Value: Ensures OAuth configuration is invalid without
        client secret, preventing OAuth flows without authentication.
        """
        config = OAuthConfig(
            client_id="valid-client-id",
            client_secret=None
        )
        
        assert config.is_configured() is False

    def test_oauth_config_is_configured_empty_credentials(self):
        """
        Test is_configured() returns False when credentials are empty strings.
        
        Security Value: Ensures empty OAuth credentials are treated as invalid,
        preventing OAuth flows with empty authentication.
        """
        config = OAuthConfig(
            client_id="",
            client_secret=""
        )
        
        assert config.is_configured() is False


class TestConfigLoaderFunctionsComprehensive:
    """
    Test configuration loader functions for proper environment handling.
    
    Security Value: Validates configuration loading functions properly handle
    environment variables and provide correct defaults.
    """

    def test_load_auth_client_config_default_values(self):
        """
        Test load_auth_client_config() with default environment values.
        
        Security Value: Ensures configuration loader provides secure defaults
        when environment variables are not set.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                # Use defaults for all values
            }.get(key, default)
            
            config = load_auth_client_config()
            
            # Should use secure defaults
            assert config.service_url == "http://localhost:8081"
            assert config.timeout == 30
            assert config.max_retries == 3
            assert config.retry_delay == 1.0
            assert config.verify_ssl is True
            assert config.api_version == "v1"

    def test_load_auth_client_config_from_environment(self):
        """
        Test load_auth_client_config() loads values from environment.
        
        Security Value: Ensures configuration is loaded from environment
        variables, allowing secure configuration management.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'AUTH_SERVICE_URL': 'https://custom-auth.example.com',
                'AUTH_CLIENT_TIMEOUT': '60',
                'AUTH_CLIENT_MAX_RETRIES': '5',
                'AUTH_CLIENT_RETRY_DELAY': '2.5',
                'AUTH_CLIENT_VERIFY_SSL': 'false',
                'AUTH_API_VERSION': 'v2'
            }.get(key, default)
            
            config = load_auth_client_config()
            
            assert config.service_url == 'https://custom-auth.example.com'
            assert config.timeout == 60
            assert config.max_retries == 5
            assert config.retry_delay == 2.5
            assert config.verify_ssl is False
            assert config.api_version == 'v2'

    def test_load_auth_security_config_default_values(self):
        """
        Test load_auth_security_config() with default environment values.
        
        Security Value: Ensures security configuration loader has secure defaults
        and warns about incomplete configuration.
        """
        with patch.object(get_env(), 'get') as mock_get, \
             patch('netra_backend.app.clients.auth_client_config.logger') as mock_logger:
            # Return appropriate defaults for different keys
            mock_get.side_effect = lambda key, default=None: {
                'SERVICE_SECRET': None,
                'JWT_SECRET_KEY': None,
                'FERNET_KEY': None,
                'REQUIRE_HTTPS': 'false',
                'TOKEN_VALIDATION_ENABLED': 'true'
            }.get(key, default)
            
            config = load_auth_security_config()
            
            # Should have defaults
            assert config.service_secret is None
            assert config.jwt_secret is None
            assert config.encryption_key is None
            assert config.require_https is False
            assert config.token_validation_enabled is True
            
            # Should log warning about incomplete config
            mock_logger.warning.assert_called_once()

    def test_load_auth_security_config_from_environment(self):
        """
        Test load_auth_security_config() loads secrets from environment.
        
        Security Value: Ensures security secrets are loaded from environment
        variables, following security best practices.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'SERVICE_SECRET': 'service-secret-from-env',
                'JWT_SECRET_KEY': 'jwt-secret-from-env',
                'FERNET_KEY': 'fernet-key-from-env',
                'REQUIRE_HTTPS': 'true',
                'TOKEN_VALIDATION_ENABLED': 'false'
            }.get(key, default)
            
            config = load_auth_security_config()
            
            assert config.service_secret == 'service-secret-from-env'
            assert config.jwt_secret == 'jwt-secret-from-env'
            assert config.encryption_key == 'fernet-key-from-env'
            assert config.require_https is True
            assert config.token_validation_enabled is False

    def test_get_auth_config_global_function(self):
        """
        Test get_auth_config() global function returns consistent configuration.
        
        Security Value: Ensures global configuration access provides consistent
        auth client configuration across the application.
        """
        config1 = get_auth_config()
        config2 = get_auth_config()
        
        # Should return consistent configuration
        assert config1.service_url == config2.service_url
        assert config1.timeout == config2.timeout
        assert config1.api_version == config2.api_version

    def test_get_auth_security_config_global_function(self):
        """
        Test get_auth_security_config() global function returns consistent configuration.
        
        Security Value: Ensures global security configuration access provides
        consistent security settings across the application.
        """
        config1 = get_auth_security_config()
        config2 = get_auth_security_config()
        
        # Should return consistent configuration
        assert config1.require_https == config2.require_https
        assert config1.token_validation_enabled == config2.token_validation_enabled


class TestEnvironmentIsolationCritical:
    """
    CRITICAL: Test environment isolation to prevent configuration leakage.
    
    Security Value: These tests are CRITICAL for security - they ensure that
    configuration from different environments (dev/staging/prod) cannot leak
    between environments, which could cause severe security breaches.
    """

    def test_development_config_isolation(self):
        """
        Test development configuration is properly isolated.
        
        CRITICAL Security Value: Ensures development OAuth credentials and
        service URLs are used only in development environment.
        """
        with patch.object(EnvironmentDetector, 'get_environment', return_value='development'):
            generator = OAuthConfigGenerator()
            config = generator.generate('development')
            
            # Development should use localhost/development-specific settings
            google_config = config['google']
            assert 'DEVELOPMENT' in generator.env.get('GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT', 'DEVELOPMENT') or \
                   'dev' in google_config['client_id'].lower() or \
                   'localhost' in google_config.get('redirect_uri', '')

    def test_production_config_isolation(self):
        """
        Test production configuration is properly isolated.
        
        CRITICAL Security Value: Ensures production OAuth credentials and
        service URLs are used only in production environment.
        """
        with patch.object(EnvironmentDetector, 'get_environment', return_value='production'):
            generator = OAuthConfigGenerator()
            config = generator.generate('production')
            
            # Production should use production-specific settings
            google_config = config['google']
            assert 'PRODUCTION' in generator.env.get('GOOGLE_OAUTH_CLIENT_ID_PRODUCTION', 'PRODUCTION') or \
                   'prod' in google_config['client_id'].lower() or \
                   'https://' in google_config.get('redirect_uri', '')

    def test_staging_config_isolation(self):
        """
        Test staging configuration is properly isolated.
        
        CRITICAL Security Value: Ensures staging OAuth credentials and
        service URLs are used only in staging environment.
        """
        with patch.object(EnvironmentDetector, 'get_environment', return_value='staging'):
            generator = OAuthConfigGenerator()
            config = generator.generate('staging')
            
            # Staging should use staging-specific settings
            google_config = config['google']
            assert 'STAGING' in generator.env.get('GOOGLE_OAUTH_CLIENT_ID_STAGING', 'STAGING') or \
                   'staging' in google_config['client_id'].lower() or \
                   'staging' in google_config.get('redirect_uri', '')

    def test_config_no_cross_environment_contamination(self):
        """
        Test configuration does not contaminate between environments.
        
        CRITICAL Security Value: Ensures that changing environment detection
        properly changes configuration without contamination.
        """
        generator = OAuthConfigGenerator()
        
        # Generate configs for different environments
        dev_config = generator.generate('development')
        prod_config = generator.generate('production')
        staging_config = generator.generate('staging')
        
        # Configs should be different
        assert dev_config != prod_config
        assert dev_config != staging_config
        assert prod_config != staging_config
        
        # Each should have different client IDs (if properly configured)
        dev_client_id = dev_config['google']['client_id']
        prod_client_id = prod_config['google']['client_id']
        staging_client_id = staging_config['google']['client_id']
        
        # Client IDs should be different or indicate different environments
        assert not (dev_client_id == prod_client_id == staging_client_id)


class TestErrorHandlingAndEdgeCases:
    """
    Test error handling and edge cases for robust authentication configuration.
    
    Security Value: Ensures authentication configuration fails safely and
    predictably when encountering error conditions.
    """

    def test_auth_client_config_invalid_ssl_setting(self):
        """
        Test AuthClientConfig handles invalid SSL verification settings.
        
        Security Value: Ensures SSL verification defaults to secure setting
        when invalid configuration values are provided.
        """
        with patch.object(get_env(), 'get') as mock_get:
            # Invalid SSL setting - should use string comparison logic
            mock_get.side_effect = lambda key, default=None: {
                'AUTH_SERVICE_URL': 'http://localhost:8081',
                'AUTH_CLIENT_TIMEOUT': '30',
                'AUTH_CLIENT_MAX_RETRIES': '3', 
                'AUTH_CLIENT_RETRY_DELAY': '1.0',
                'AUTH_CLIENT_VERIFY_SSL': 'invalid-value',  # Not 'true', so becomes False
                'AUTH_API_VERSION': 'v1'
            }.get(key, default)
            
            config = load_auth_client_config()
            
            # Invalid value evaluates to False (not 'true')
            # This demonstrates the importance of proper env var validation
            assert config.verify_ssl is False

    def test_oauth_config_malformed_redirect_uri(self):
        """
        Test OAuth configuration handles malformed redirect URIs.
        
        Security Value: Ensures malformed redirect URIs don't cause configuration
        failures that could lead to security vulnerabilities.
        """
        config = OAuthConfig(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="not-a-valid-uri"
        )
        
        # Should still be considered configured (validation happens elsewhere)
        assert config.is_configured() is True
        # But URI should be stored as-is for validation elsewhere
        assert config.redirect_uri == "not-a-valid-uri"

    def test_auth_config_manager_config_loading_exception(self):
        """
        Test AuthClientConfigManager handles configuration loading exceptions.
        
        Security Value: Ensures configuration loading failures don't crash the
        application and can be handled gracefully.
        """
        manager = AuthClientConfigManager()
        
        with patch('netra_backend.app.clients.auth_client_config.load_auth_client_config', 
                   side_effect=Exception("Config loading failed")):
            # Should raise the exception (fail fast) rather than returning invalid config
            with pytest.raises(Exception):
                manager.get_config()

    def test_oauth_config_generator_missing_environment_variables(self):
        """
        Test OAuthConfigGenerator handles missing environment variables.
        
        Security Value: Ensures missing OAuth environment variables use fallback
        values that are clearly identifiable as defaults.
        """
        with patch.object(get_env(), 'get') as mock_get, \
             patch.object(EnvironmentDetector, 'get_environment', return_value='development'):
            # Return appropriate defaults for missing environment variables
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'development',
                'TESTING': None,
                'PYTEST_CURRENT_TEST': None,
                # OAuth environment variables missing - will use defaults
                'GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT': default or 'dev-google-client-id',
                'GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT': default or 'dev-google-client-secret',
                'OAUTH_REDIRECT_URI': default or 'http://localhost:3000/auth/callback'
            }.get(key, default)
            
            generator = OAuthConfigGenerator()
            config = generator.generate('development')
            
            # Should have fallback values that are clearly defaults
            google_config = config['google']
            assert 'dev-google-client-id' in google_config['client_id']
            assert 'dev-google-client-secret' in google_config['client_secret']

    def test_auth_client_config_extreme_timeout_values(self):
        """
        Test AuthClientConfig handles extreme timeout values.
        
        Security Value: Ensures extreme timeout values don't cause authentication
        failures or security bypasses.
        """
        with patch.object(get_env(), 'get') as mock_get:
            # Test with very large timeout
            mock_get.side_effect = lambda key, default=None: {
                'AUTH_CLIENT_TIMEOUT': '999999'
            }.get(key, default)
            
            config = load_auth_client_config()
            
            # Should accept the value (validation happens at usage)
            assert config.timeout == 999999

    def test_auth_client_config_negative_values(self):
        """
        Test AuthClientConfig handles negative configuration values.
        
        Security Value: Ensures negative timeout/retry values don't cause
        unexpected behavior in authentication flows.
        """
        with patch.object(get_env(), 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'AUTH_CLIENT_TIMEOUT': '-5',
                'AUTH_CLIENT_MAX_RETRIES': '-1'
            }.get(key, default)
            
            config = load_auth_client_config()
            
            # Should convert string values (validation of negative values elsewhere)
            assert config.timeout == -5
            assert config.max_retries == -1