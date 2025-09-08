"""Auth Client Configuration - Minimal implementation.

This module provides configuration management for authentication client.
Created as a minimal implementation to resolve missing module imports.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability & Security
- Value Impact: Enables proper auth client configuration and connectivity
- Strategic Impact: Foundation for secure authentication workflows
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from shared.isolated_environment import get_env
from netra_backend.app.core.environment_constants import EnvironmentDetector

logger = logging.getLogger(__name__)


class OAuthConfigGenerator:
    """Generates OAuth configuration for different environments."""
    
    def __init__(self):
        self.env = get_env()
        detector = EnvironmentDetector()
        current_env = detector.get_environment()
        
        # Dynamically set redirect URI based on environment
        dev_redirect_uri = self.env.get('OAUTH_REDIRECT_URI', 'http://localhost:3000/auth/callback')
        prod_redirect_uri = self.env.get('OAUTH_REDIRECT_URI', 'https://app.netra.ai/auth/callback')
        
        self.env_configs = {
            'development': {
                'google': {
                    'client_id': self.env.get('GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT', 'dev-google-client-id'),
                    'client_secret': self.env.get('GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT', 'dev-google-client-secret'),
                    'redirect_uri': dev_redirect_uri
                }
            },
            'production': {
                'google': {
                    'client_id': self.env.get('GOOGLE_OAUTH_CLIENT_ID_PRODUCTION', 'prod-google-client-id'),
                    'client_secret': self.env.get('GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION', 'prod-google-client-secret'),
                    'redirect_uri': prod_redirect_uri
                }
            },
            'staging': {
                'google': {
                    'client_id': self.env.get('GOOGLE_OAUTH_CLIENT_ID_STAGING', 'staging-google-client-id'),
                    'client_secret': self.env.get('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', 'staging-google-client-secret'),
                    'redirect_uri': self.env.get('OAUTH_REDIRECT_URI', 'https://app.staging.netra.ai/auth/callback')
                }
            }
        }
    
    def generate(self, environment: str = 'development') -> Dict[str, Any]:
        """Generate OAuth configuration for the specified environment."""
        return self.env_configs.get(environment, self.env_configs['development'])
    
    def get_provider_config(self, provider: str, environment: str = 'development') -> Dict[str, Any]:
        """Get configuration for a specific OAuth provider."""
        env_config = self.generate(environment)
        return env_config.get(provider, {})
    
    def get_oauth_config(self, environment: str = 'development') -> 'OAuthConfig':
        """Get OAuth configuration for startup validator compatibility."""
        from dataclasses import dataclass
        
        @dataclass
        class OAuthConfig:
            redirect_uri: str
            environment: str
            
        config = self.generate(environment)
        google_config = config.get('google', {})
        
        return OAuthConfig(
            redirect_uri=google_config.get('redirect_uri', ''),
            environment=environment
        )


@dataclass
class AuthClientConfig:
    """Configuration for auth client."""
    service_url: str = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = True
    api_version: str = "v1"
    
    def __post_init__(self):
        """Initialize service URL based on environment."""
        if not self.service_url:
            env = get_env()
            detector = EnvironmentDetector()
            current_env = detector.get_environment()
            
            if current_env == 'production':
                self.service_url = env.get('AUTH_SERVICE_URL', 'https://auth.netrasystems.ai')
            elif current_env == 'staging':
                self.service_url = env.get('AUTH_SERVICE_URL', 'https://auth.staging.netrasystems.ai')
            else:
                self.service_url = env.get('AUTH_SERVICE_URL', 'http://localhost:8081')
    
    @property
    def base_url(self) -> str:
        """Get base URL with API version."""
        return f"{self.service_url}/api/{self.api_version}"
    
    @property  
    def health_url(self) -> str:
        """Get health check URL."""
        return f"{self.service_url}/health"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "service_url": self.service_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "verify_ssl": self.verify_ssl,
            "api_version": self.api_version,
        }


@dataclass
class AuthClientSecurityConfig:
    """Security configuration for auth client."""
    service_secret: Optional[str] = None
    jwt_secret: Optional[str] = None
    encryption_key: Optional[str] = None
    require_https: bool = False
    token_validation_enabled: bool = True
    
    def is_valid(self) -> bool:
        """Check if security config is valid."""
        return bool(self.service_secret)


def load_auth_client_config() -> AuthClientConfig:
    """Load auth client configuration from environment."""
    env = get_env()
    
    config = AuthClientConfig(
        service_url=env.get("AUTH_SERVICE_URL", "http://localhost:8081"),
        timeout=int(env.get("AUTH_CLIENT_TIMEOUT", "30")),
        max_retries=int(env.get("AUTH_CLIENT_MAX_RETRIES", "3")),
        retry_delay=float(env.get("AUTH_CLIENT_RETRY_DELAY", "1.0")),
        verify_ssl=env.get("AUTH_CLIENT_VERIFY_SSL", "true").lower() == "true",
        api_version=env.get("AUTH_API_VERSION", "v1"),
    )
    
    logger.info(f"Loaded auth client config: {config.service_url}")
    return config


def load_auth_security_config() -> AuthClientSecurityConfig:
    """Load auth security configuration from environment."""
    env = get_env()
    
    config = AuthClientSecurityConfig(
        service_secret=env.get("SERVICE_SECRET"),
        jwt_secret=env.get("JWT_SECRET_KEY"),
        encryption_key=env.get("FERNET_KEY"),
        require_https=env.get("REQUIRE_HTTPS", "false").lower() == "true",
        token_validation_enabled=env.get("TOKEN_VALIDATION_ENABLED", "true").lower() == "true",
    )
    
    if not config.is_valid():
        logger.warning("Auth security config is incomplete - some features may not work")
    
    return config


class AuthClientConfigManager:
    """Manager for auth client configuration."""
    
    def __init__(self):
        self._config: Optional[AuthClientConfig] = None
        self._security_config: Optional[AuthClientSecurityConfig] = None
        logger.info("AuthClientConfigManager initialized")
    
    def get_config(self) -> AuthClientConfig:
        """Get auth client configuration."""
        if self._config is None:
            self._config = load_auth_client_config()
        return self._config
    
    def get_security_config(self) -> AuthClientSecurityConfig:
        """Get auth security configuration."""
        if self._security_config is None:
            self._security_config = load_auth_security_config()
        return self._security_config
    
    def reload_config(self) -> None:
        """Reload configuration from environment."""
        self._config = None
        self._security_config = None
        logger.info("Auth client configuration reloaded")
    
    def validate_config(self) -> bool:
        """Validate current configuration."""
        try:
            config = self.get_config()
            security_config = self.get_security_config()
            
            # Basic validation
            if not config.service_url:
                return False
            if not security_config.is_valid():
                return False
            
            return True
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            return False


# Global configuration manager
auth_config_manager = AuthClientConfigManager()


def get_auth_config() -> AuthClientConfig:
    """Get global auth client configuration."""
    return auth_config_manager.get_config()


def get_auth_security_config() -> AuthClientSecurityConfig:
    """Get global auth security configuration."""
    return auth_config_manager.get_security_config()


@dataclass
class OAuthConfig:
    """OAuth configuration for auth client."""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    auth_url: Optional[str] = None
    token_url: Optional[str] = None
    scope: str = "openid profile email"
    
    @classmethod
    def from_env(cls) -> 'OAuthConfig':
        """Create OAuth config from environment variables."""
        env = get_env()
        return cls(
            client_id=env.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT"),
            client_secret=env.get("GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT"),
            redirect_uri=env.get("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback"),
            auth_url=env.get("OAUTH_AUTH_URL", "https://accounts.google.com/o/oauth2/v2/auth"),
            token_url=env.get("OAUTH_TOKEN_URL", "https://oauth2.googleapis.com/token"),
            scope=env.get("OAUTH_SCOPE", "openid profile email"),
        )
    
    def is_configured(self) -> bool:
        """Check if OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)