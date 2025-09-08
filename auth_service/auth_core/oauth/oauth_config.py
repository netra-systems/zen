"""OAuth Configuration - Single Source of Truth for OAuth Settings

**CRITICAL**: Enterprise-Grade OAuth Configuration Management
Centralizes OAuth provider configuration with environment-aware behavior
and comprehensive validation for staging and production environments.

Business Value: Prevents OAuth misconfiguration costing $75K+ MRR
Critical for OAuth provider integration and user authentication flows.

This module consolidates OAuth configuration from multiple existing sources
into a single SSOT while maintaining backward compatibility.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from auth_service.auth_core.auth_environment import get_auth_env
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class OAuthProviderConfig:
    """Configuration for a single OAuth provider."""
    provider_name: str
    client_id: str
    client_secret: str
    scopes: List[str]
    authorization_url: str
    token_url: str
    user_info_url: str
    redirect_uri: Optional[str] = None


class OAuthConfigError(Exception):
    """Raised when OAuth configuration is invalid or incomplete."""
    pass


class OAuthConfig:
    """
    Single Source of Truth for OAuth configuration management.
    
    **CRITICAL**: All OAuth operations MUST use this configuration class.
    Consolidates settings from AuthEnvironment and provides environment-aware
    validation and provider management.
    """
    
    def __init__(self, auth_env=None):
        """
        Initialize OAuth configuration with environment awareness.
        
        Args:
            auth_env: Optional AuthEnvironment instance for dependency injection
        """
        self.auth_env = auth_env or get_auth_env()
        self.env = get_env().get("ENVIRONMENT", "development").lower()
        self._providers_cache: Dict[str, OAuthProviderConfig] = {}
        
    @property
    def google_client_id(self) -> str:
        """Get Google OAuth client ID."""
        return self.auth_env.get_oauth_google_client_id()
    
    @property
    def google_client_secret(self) -> str:
        """Get Google OAuth client secret."""
        return self.auth_env.get_oauth_google_client_secret()
    
    @property
    def oauth_redirect_base_url(self) -> str:
        """Get OAuth redirect base URL."""
        return self.auth_env.get_auth_service_url()
    
    @property
    def oauth_state_secret(self) -> str:
        """Get OAuth state secret for CSRF protection."""
        # Use JWT secret as OAuth state secret for now
        return self.auth_env.get_jwt_secret_key()
    
    @property
    def github_client_id(self) -> Optional[str]:
        """Get GitHub OAuth client ID (if configured)."""
        try:
            # Try environment-specific GitHub client ID
            return self.auth_env.env_manager.get(f"GITHUB_OAUTH_CLIENT_ID_{self.env.upper()}")
        except:
            return None
    
    @property 
    def github_client_secret(self) -> Optional[str]:
        """Get GitHub OAuth client secret (if configured)."""
        try:
            # Try environment-specific GitHub client secret
            return self.auth_env.env_manager.get(f"GITHUB_OAUTH_CLIENT_SECRET_{self.env.upper()}")
        except:
            return None
    
    def get_google_oauth_config(self) -> OAuthProviderConfig:
        """
        Get comprehensive Google OAuth provider configuration.
        
        Returns:
            OAuthProviderConfig for Google OAuth
            
        Raises:
            OAuthConfigError: If Google OAuth is not properly configured
        """
        if "google" in self._providers_cache:
            return self._providers_cache["google"]
            
        client_id = self.google_client_id
        client_secret = self.google_client_secret
        
        if not client_id or not client_secret:
            raise OAuthConfigError(f"Google OAuth not configured for {self.env} environment")
        
        base_url = self.oauth_redirect_base_url
        redirect_uri = f"{base_url}/auth/callback"
        
        config = OAuthProviderConfig(
            provider_name="google",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["openid", "email", "profile"],
            authorization_url="https://accounts.google.com/o/oauth2/auth",
            token_url="https://oauth2.googleapis.com/token",
            user_info_url="https://www.googleapis.com/oauth2/v2/userinfo",
            redirect_uri=redirect_uri
        )
        
        self._providers_cache["google"] = config
        return config
    
    def get_github_oauth_config(self) -> OAuthProviderConfig:
        """
        Get comprehensive GitHub OAuth provider configuration.
        
        Returns:
            OAuthProviderConfig for GitHub OAuth
            
        Raises:
            OAuthConfigError: If GitHub OAuth is not properly configured
        """
        if "github" in self._providers_cache:
            return self._providers_cache["github"]
            
        client_id = self.github_client_id
        client_secret = self.github_client_secret
        
        if not client_id or not client_secret:
            raise OAuthConfigError(f"GitHub OAuth not configured for {self.env} environment")
        
        base_url = self.oauth_redirect_base_url
        redirect_uri = f"{base_url}/auth/callback/github"
        
        config = OAuthProviderConfig(
            provider_name="github",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["user:email", "read:user"],
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            user_info_url="https://api.github.com/user",
            redirect_uri=redirect_uri
        )
        
        self._providers_cache["github"] = config
        return config
    
    def get_provider_config(self, provider_name: str) -> OAuthProviderConfig:
        """
        Get OAuth configuration for any supported provider.
        
        Args:
            provider_name: Name of the OAuth provider
            
        Returns:
            OAuthProviderConfig for the requested provider
            
        Raises:
            OAuthConfigError: If provider is not supported or not configured
        """
        if provider_name.lower() == "google":
            return self.get_google_oauth_config()
        elif provider_name.lower() == "github":
            return self.get_github_oauth_config()
        else:
            raise OAuthConfigError(f"Unsupported OAuth provider: {provider_name}")
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of available OAuth providers.
        
        Returns:
            List of provider names that are properly configured
        """
        providers = []
        
        # Check Google OAuth
        if self.google_client_id and self.google_client_secret:
            providers.append("google")
        
        # Check GitHub OAuth
        if self.github_client_id and self.github_client_secret:
            providers.append("github")
            
        return providers
    
    def is_provider_configured(self, provider_name: str) -> bool:
        """
        Check if a specific OAuth provider is configured.
        
        Args:
            provider_name: Name of the OAuth provider to check
            
        Returns:
            True if provider is configured, False otherwise
        """
        try:
            self.get_provider_config(provider_name)
            return True
        except OAuthConfigError:
            return False
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate OAuth configuration for all providers.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "is_valid": True,
            "providers": {},
            "errors": [],
            "warnings": [],
            "environment": self.env
        }
        
        # Validate each available provider
        for provider_name in ["google", "github"]:
            try:
                config = self.get_provider_config(provider_name)
                results["providers"][provider_name] = {
                    "configured": True,
                    "client_id_length": len(config.client_id),
                    "has_client_secret": bool(config.client_secret),
                    "redirect_uri": config.redirect_uri,
                    "scopes": config.scopes
                }
                
                # Additional validation for Google
                if provider_name == "google":
                    if not config.client_id.endswith(".apps.googleusercontent.com"):
                        results["warnings"].append(f"Google client ID format may be invalid: {config.client_id[:30]}...")
                    if len(config.client_id) < 50:
                        results["warnings"].append(f"Google client ID appears too short ({len(config.client_id)} chars)")
                
            except OAuthConfigError as e:
                results["providers"][provider_name] = {
                    "configured": False,
                    "error": str(e)
                }
                # Only treat as error for critical environments
                if self.env in ["staging", "production"]:
                    results["errors"].append(f"{provider_name}: {str(e)}")
                    results["is_valid"] = False
                else:
                    results["warnings"].append(f"{provider_name}: {str(e)}")
        
        # Check OAuth state secret
        if not self.oauth_state_secret:
            results["errors"].append("OAuth state secret not configured")
            results["is_valid"] = False
        elif len(self.oauth_state_secret) < 32:
            results["warnings"].append(f"OAuth state secret may be too short ({len(self.oauth_state_secret)} chars)")
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of OAuth configuration.
        
        Returns:
            Dictionary with health check results
        """
        validation_result = self.validate_configuration()
        
        health_status = {
            "service": "oauth_config",
            "status": "healthy" if validation_result["is_valid"] else "degraded",
            "environment": self.env,
            "providers_configured": len([p for p in validation_result["providers"].values() if p.get("configured", False)]),
            "total_providers_available": len(validation_result["providers"]),
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"]
        }
        
        # Add provider-specific health
        for provider, config in validation_result["providers"].items():
            if config.get("configured", False):
                health_status[f"{provider}_health"] = "configured"
            else:
                health_status[f"{provider}_health"] = "not_configured"
        
        return health_status
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get summary of OAuth configuration for logging and monitoring.
        
        Returns:
            Dictionary with configuration summary (no secrets exposed)
        """
        return {
            "environment": self.env,
            "available_providers": self.get_available_providers(),
            "google_configured": bool(self.google_client_id and self.google_client_secret),
            "github_configured": bool(self.github_client_id and self.github_client_secret),
            "oauth_redirect_base": self.oauth_redirect_base_url,
            "state_secret_configured": bool(self.oauth_state_secret)
        }


__all__ = ["OAuthConfig", "OAuthProviderConfig", "OAuthConfigError"]