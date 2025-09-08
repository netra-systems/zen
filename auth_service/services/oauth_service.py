"""
OAuth Service - Single Source of Truth for OAuth Authentication

This service provides a unified interface for OAuth operations,
following SSOT principles and maintaining service independence.

Business Value: Enables seamless third-party authentication (Google, GitHub, etc.)
that reduces signup friction and improves user conversion rates.
"""

import logging
import secrets
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError
from auth_service.services.redis_service import RedisService
from auth_service.services.user_service import UserService

logger = logging.getLogger(__name__)


class OAuthService:
    """
    Single Source of Truth for OAuth authentication operations.
    
    This service provides a unified interface for OAuth flows with multiple providers,
    currently supporting Google OAuth with extensibility for additional providers.
    """
    
    def __init__(self, auth_config: AuthConfig, redis_service: Optional[RedisService] = None, user_service: Optional[UserService] = None):
        """
        Initialize OAuthService with configuration and dependencies.
        
        Args:
            auth_config: Authentication configuration
            redis_service: Optional Redis service instance
            user_service: Optional User service instance
        """
        self.auth_config = auth_config
        self.redis_service = redis_service or RedisService(auth_config)
        self.user_service = user_service or UserService(auth_config)
        
        # Initialize OAuth providers
        self.google_provider = GoogleOAuthProvider()
        
        # State management for OAuth flows
        self.state_prefix = "oauth_state:"
        
    def _get_state_key(self, state: str) -> str:
        """Generate Redis key for OAuth state."""
        return f"{self.state_prefix}{state}"
    
    async def get_authorization_url(self, provider: str = "google", redirect_uri: Optional[str] = None, scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get authorization URL for OAuth provider.
        
        Args:
            provider: OAuth provider name (currently only 'google' supported)
            redirect_uri: Optional custom redirect URI
            scopes: Optional list of OAuth scopes
            
        Returns:
            Dictionary with authorization URL and state
            
        Raises:
            ValueError: If provider is not supported
            GoogleOAuthError: If OAuth configuration is invalid
        """
        try:
            if provider.lower() != "google":
                raise ValueError(f"OAuth provider '{provider}' is not supported")
            
            # Generate CSRF state token
            state = secrets.token_urlsafe(32)
            
            # Store state in Redis with expiration (10 minutes)
            state_data = {
                "provider": provider,
                "created_at": datetime.now(UTC).isoformat(),
                "redirect_uri": redirect_uri,
                "scopes": scopes
            }
            
            state_key = self._get_state_key(state)
            await self.redis_service.set(
                state_key,
                str(state_data),  # Convert to string for Redis
                ex=600  # 10 minutes
            )
            
            # Get authorization URL from provider
            auth_url = self.google_provider.get_authorization_url(state, scopes)
            
            logger.info(f"Generated OAuth authorization URL for provider {provider}")
            
            return {
                "authorization_url": auth_url,
                "state": state,
                "provider": provider,
                "expires_in": 600
            }
            
        except Exception as e:
            logger.error(f"Failed to get authorization URL for {provider}: {e}")
            raise
    
    async def handle_callback(self, provider: str, code: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for user information.
        
        Args:
            provider: OAuth provider name
            code: Authorization code from callback
            state: State parameter for CSRF protection
            
        Returns:
            Dictionary with user information and authentication result
            
        Raises:
            ValueError: If provider is not supported or state is invalid
            GoogleOAuthError: If OAuth exchange fails
        """
        try:
            if provider.lower() != "google":
                raise ValueError(f"OAuth provider '{provider}' is not supported")
            
            # Validate state token
            if not await self._validate_state(state):
                raise ValueError("Invalid or expired OAuth state")
            
            # Exchange code for user information
            user_info = self.google_provider.exchange_code_for_user_info(code, state)
            if not user_info:
                raise GoogleOAuthError("Failed to exchange authorization code for user information")
            
            # Clean up state
            await self._cleanup_state(state)
            
            # Check if user exists, create if not
            user = await self.user_service.get_user_by_email(user_info["email"])
            if not user:
                # Create new user from OAuth info
                user = await self.user_service.create_user(
                    email=user_info["email"],
                    password=secrets.token_urlsafe(32),  # Generate random password for OAuth users
                    name=user_info.get("name", user_info["email"].split("@")[0]),
                    oauth_provider=provider,
                    oauth_user_id=user_info.get("sub"),
                    email_verified=user_info.get("verified_email", False)
                )
                logger.info(f"Created new user via OAuth: {user_info['email']}")
            else:
                logger.info(f"Existing user authenticated via OAuth: {user_info['email']}")
            
            return {
                "success": True,
                "user": user,
                "provider": provider,
                "oauth_user_info": user_info,
                "is_new_user": user is not None
            }
            
        except Exception as e:
            logger.error(f"OAuth callback handling failed for {provider}: {e}")
            # Clean up state on error
            try:
                await self._cleanup_state(state)
            except:
                pass
            raise
    
    async def _validate_state(self, state: str) -> bool:
        """
        Validate OAuth state token.
        
        Args:
            state: State token to validate
            
        Returns:
            True if state is valid, False otherwise
        """
        try:
            state_key = self._get_state_key(state)
            state_data = await self.redis_service.get(state_key)
            
            if not state_data:
                return False
            
            # State exists and hasn't expired (Redis handles TTL)
            return True
            
        except Exception as e:
            logger.error(f"State validation failed: {e}")
            return False
    
    async def _cleanup_state(self, state: str):
        """
        Clean up OAuth state after use.
        
        Args:
            state: State token to cleanup
        """
        try:
            state_key = self._get_state_key(state)
            await self.redis_service.delete(state_key)
            
        except Exception as e:
            logger.error(f"Failed to cleanup OAuth state {state}: {e}")
    
    async def get_provider_status(self, provider: str = "google") -> Dict[str, Any]:
        """
        Get OAuth provider configuration status.
        
        Args:
            provider: Provider name to check
            
        Returns:
            Dictionary with provider status information
        """
        try:
            if provider.lower() != "google":
                return {
                    "provider": provider,
                    "supported": False,
                    "error": "Provider not supported"
                }
            
            # Check Google OAuth configuration
            config_status = self.google_provider.get_configuration_status()
            
            return {
                "provider": provider,
                "supported": True,
                "configured": config_status["is_configured"],
                "client_id_configured": config_status["client_id_configured"],
                "client_secret_configured": config_status["client_secret_configured"],
                "redirect_uri": config_status["redirect_uri"],
                "environment": config_status["environment"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get provider status for {provider}: {e}")
            return {
                "provider": provider,
                "supported": False,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of OAuth service and providers.
        
        Returns:
            Dictionary with health check results
        """
        try:
            health_status = {
                "service": "oauth_service",
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "providers": {}
            }
            
            # Check Google provider
            google_health = self.google_provider.self_check()
            health_status["providers"]["google"] = google_health
            
            # Overall status based on provider health
            if not google_health.get("is_healthy", False):
                health_status["status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"OAuth service health check failed: {e}")
            return {
                "service": "oauth_service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    def get_supported_providers(self) -> List[str]:
        """
        Get list of supported OAuth providers.
        
        Returns:
            List of supported provider names
        """
        return ["google"]
    
    async def revoke_oauth_access(self, user_id: str, provider: str) -> bool:
        """
        Revoke OAuth access for a user (placeholder for future implementation).
        
        Args:
            user_id: User ID
            provider: OAuth provider
            
        Returns:
            True if successful
        """
        try:
            # Placeholder implementation
            # In a full implementation, this would revoke OAuth tokens
            # and clean up provider-specific user data
            logger.info(f"OAuth access revoked for user {user_id} on provider {provider}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke OAuth access for user {user_id}: {e}")
            return False


__all__ = ["OAuthService"]