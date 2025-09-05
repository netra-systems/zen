"""OAuth Manager for Auth Service
Manages OAuth providers and authentication flows
"""

import logging
from typing import Dict, List, Optional, Any

from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError

logger = logging.getLogger(__name__)


class OAuthManager:
    """OAuth manager for handling multiple OAuth providers"""
    
    def __init__(self):
        """Initialize OAuth manager with available providers"""
        self._providers: Dict[str, GoogleOAuthProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize available OAuth providers"""
        try:
            # Initialize Google OAuth provider
            google_provider = GoogleOAuthProvider()
            self._providers["google"] = google_provider
            logger.info("Google OAuth provider initialized")
        except GoogleOAuthError as e:
            logger.error(f"Failed to initialize Google OAuth provider: {e}")
        except Exception as e:
            logger.error(f"Unexpected error initializing Google OAuth provider: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available OAuth providers"""
        return list(self._providers.keys())
    
    def get_provider(self, provider_name: str) -> Optional[GoogleOAuthProvider]:
        """Get OAuth provider by name"""
        return self._providers.get(provider_name)
    
    def is_provider_configured(self, provider_name: str) -> bool:
        """Check if provider is configured"""
        provider = self.get_provider(provider_name)
        if not provider:
            return False
        return provider.is_configured()
    
    def get_provider_status(self, provider_name: str) -> Dict[str, Any]:
        """Get provider status and configuration info"""
        provider = self.get_provider(provider_name)
        if not provider:
            return {
                "provider": provider_name,
                "available": False,
                "error": "Provider not found"
            }
        
        return {
            "provider": provider_name,
            "available": True,
            "configured": provider.is_configured(),
            "config_status": provider.get_configuration_status()
        }