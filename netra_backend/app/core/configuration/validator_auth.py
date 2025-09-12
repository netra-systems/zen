"""Authentication Configuration Validation

**CRITICAL: Enterprise-Grade Authentication Validation**

Authentication-specific validation helpers for configuration validation.
Business Value: Prevents security vulnerabilities that risk data breaches.

Each function  <= 8 lines, file  <= 300 lines.
"""

from typing import List
from urllib.parse import urlparse

from netra_backend.app.schemas.config import AppConfig


class AuthValidator:
    """Authentication configuration validation helpers."""
    
    def __init__(self, validation_rules: dict, environment: str):
        """Initialize auth validator."""
        self._validation_rules = validation_rules
        self._environment = environment
    
    def validate_auth_config(self, config: AppConfig) -> List[str]:
        """Validate authentication configuration."""
        errors = self._check_auth_secrets_requirement(config)
        errors.extend(self._validate_oauth_config(config))
        return errors
    
    def _check_auth_secrets_requirement(self, config: AppConfig) -> List[str]:
        """Check if auth secrets are required and validate them."""
        rules = self._validation_rules.get(self._environment, {})
        if rules.get("require_secrets", False):
            return self._validate_auth_secrets(config)
        return []
    
    def _validate_auth_secrets(self, config: AppConfig) -> List[str]:
        """Validate authentication secrets."""
        errors = []
        self._check_jwt_secret(config, errors)
        self._check_fernet_key(config, errors)
        return errors
    
    def _check_jwt_secret(self, config: AppConfig, errors: List[str]) -> None:
        """Check JWT secret key validation."""
        if not config.jwt_secret_key:
            errors.append("JWT secret key is required")
        elif len(config.jwt_secret_key) < 32:
            errors.append("JWT secret key too short (minimum 32 characters)")
    
    def _check_fernet_key(self, config: AppConfig, errors: List[str]) -> None:
        """Check Fernet encryption key validation."""
        if not config.fernet_key:
            errors.append("Fernet encryption key is required")
    
    def _validate_oauth_config(self, config: AppConfig) -> List[str]:
        """Validate OAuth configuration."""
        if not self._has_oauth_config(config):
            return []
        return self._check_oauth_redirect_uris(config)
    
    def _has_oauth_config(self, config: AppConfig) -> bool:
        """Check if OAuth configuration exists."""
        return hasattr(config, 'oauth_config') and config.oauth_config
    
    def _check_oauth_redirect_uris(self, config: AppConfig) -> List[str]:
        """Check OAuth redirect URIs configuration."""
        if not config.oauth_config.authorized_redirect_uris:
            return ["OAuth redirect URIs are required"]
        return self._validate_oauth_urls(config)
    
    def _validate_oauth_urls(self, config: AppConfig) -> List[str]:
        """Validate OAuth redirect URLs."""
        errors = []
        for uri in config.oauth_config.authorized_redirect_uris:
            if not self._is_valid_url(uri):
                errors.append(f"Invalid OAuth redirect URI: {uri}")
        return errors
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False