"""
OAuth Provider Manager

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: User acquisition & retention
- Value Impact: Ensures reliable OAuth authentication across all providers
- Strategic Impact: Prevents authentication failures that block user onboarding

Implements OAuth provider validation, health checks, and fallback logic.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from netra_backend.app.logging_config import central_logger
from netra_backend.app.config import get_config

logger = central_logger.get_logger(__name__)


class ProviderStatus(Enum):
    """OAuth provider status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class OAuthProviderConfig:
    """Configuration for OAuth provider."""
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    redirect_uri: str
    scopes: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    retry_attempts: int = 3
    health_check_interval: int = 300  # 5 minutes


@dataclass
class ProviderHealthStatus:
    """Health status for an OAuth provider."""
    provider_name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_check: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None


class OAuthProviderManager:
    """Manages OAuth providers with health checks and fallback logic."""
    
    def __init__(self):
        """Initialize OAuth provider manager."""
        self.providers: Dict[str, OAuthProviderConfig] = {}
        self.provider_health: Dict[str, ProviderHealthStatus] = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Load configuration
        self._load_provider_configs()
    
    def _load_provider_configs(self) -> None:
        """Load OAuth provider configurations."""
        config = get_config()
        
        # Google OAuth
        google_config = self._create_google_provider_config(config)
        if google_config:
            self.providers['google'] = google_config
            self.provider_health['google'] = ProviderHealthStatus('google')
        
        # GitHub OAuth  
        github_config = self._create_github_provider_config(config)
        if github_config:
            self.providers['github'] = github_config
            self.provider_health['github'] = ProviderHealthStatus('github')
        
        # Microsoft OAuth
        microsoft_config = self._create_microsoft_provider_config(config)
        if microsoft_config:
            self.providers['microsoft'] = microsoft_config
            self.provider_health['microsoft'] = ProviderHealthStatus('microsoft')
        
        logger.info(f"Loaded {len(self.providers)} OAuth provider configurations")
    
    def _create_google_provider_config(self, config) -> Optional[OAuthProviderConfig]:
        """Create Google OAuth provider configuration."""
        try:
            client_id = config.oauth_google_client_id
            client_secret = config.oauth_google_client_secret
            
            if not client_id or not client_secret:
                logger.warning("Google OAuth credentials not configured")
                return None
            
            return OAuthProviderConfig(
                name='google',
                client_id=client_id,
                client_secret=client_secret,
                authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
                token_url='https://oauth2.googleapis.com/token',
                userinfo_url='https://www.googleapis.com/oauth2/v2/userinfo',
                redirect_uri=self._build_redirect_uri('google'),
                scopes=['openid', 'email', 'profile']
            )
        except Exception as e:
            logger.error(f"Failed to configure Google OAuth: {e}")
            return None
    
    def _create_github_provider_config(self, config) -> Optional[OAuthProviderConfig]:
        """Create GitHub OAuth provider configuration."""
        try:
            client_id = getattr(config, 'oauth_github_client_id', None)
            client_secret = getattr(config, 'oauth_github_client_secret', None)
            
            if not client_id or not client_secret:
                logger.debug("GitHub OAuth credentials not configured")
                return None
            
            return OAuthProviderConfig(
                name='github',
                client_id=client_id,
                client_secret=client_secret,
                authorize_url='https://github.com/login/oauth/authorize',
                token_url='https://github.com/login/oauth/access_token',
                userinfo_url='https://api.github.com/user',
                redirect_uri=self._build_redirect_uri('github'),
                scopes=['user:email']
            )
        except Exception as e:
            logger.error(f"Failed to configure GitHub OAuth: {e}")
            return None
    
    def _create_microsoft_provider_config(self, config) -> Optional[OAuthProviderConfig]:
        """Create Microsoft OAuth provider configuration."""
        try:
            client_id = getattr(config, 'oauth_microsoft_client_id', None)
            client_secret = getattr(config, 'oauth_microsoft_client_secret', None)
            
            if not client_id or not client_secret:
                logger.debug("Microsoft OAuth credentials not configured")
                return None
            
            tenant_id = getattr(config, 'oauth_microsoft_tenant_id', 'common')
            
            return OAuthProviderConfig(
                name='microsoft',
                client_id=client_id,
                client_secret=client_secret,
                authorize_url=f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize',
                token_url=f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
                userinfo_url='https://graph.microsoft.com/v1.0/me',
                redirect_uri=self._build_redirect_uri('microsoft'),
                scopes=['openid', 'email', 'profile']
            )
        except Exception as e:
            logger.error(f"Failed to configure Microsoft OAuth: {e}")
            return None
    
    def _build_redirect_uri(self, provider: str) -> str:
        """Build redirect URI for provider."""
        config = get_config()
        base_url = getattr(config, 'auth_service_base_url', 'http://localhost:8081')
        return urljoin(base_url, f'/auth/oauth/{provider}/callback')
    
    async def start(self) -> None:
        """Start OAuth provider manager."""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Initial health check
        await self._check_all_providers_health()
        
        logger.info("OAuth provider manager started")
    
    async def stop(self) -> None:
        """Stop OAuth provider manager."""
        self._shutdown = True
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        await self.http_client.aclose()
        logger.info("OAuth provider manager stopped")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available OAuth providers."""
        return list(self.providers.keys())
    
    def get_healthy_providers(self) -> List[str]:
        """Get list of currently healthy providers."""
        return [
            name for name, health in self.provider_health.items()
            if health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]
        ]
    
    def get_provider_config(self, provider_name: str) -> Optional[OAuthProviderConfig]:
        """Get configuration for specific provider."""
        return self.providers.get(provider_name)
    
    def get_provider_health(self, provider_name: str) -> Optional[ProviderHealthStatus]:
        """Get health status for specific provider."""
        return self.provider_health.get(provider_name)
    
    async def validate_provider_availability(self, provider_name: str) -> bool:
        """Validate if provider is available for authentication."""
        if provider_name not in self.providers:
            logger.error(f"Unknown OAuth provider: {provider_name}")
            return False
        
        health = self.provider_health.get(provider_name)
        if not health:
            # Try to check health if not known
            await self._check_provider_health(provider_name)
            health = self.provider_health.get(provider_name)
        
        if health and health.status == ProviderStatus.HEALTHY:
            return True
        
        # Check circuit breaker
        if self._is_circuit_breaker_open(provider_name):
            logger.warning(f"Circuit breaker open for {provider_name}")
            return False
        
        # Try a quick health check
        try:
            return await self._quick_health_check(provider_name)
        except Exception as e:
            logger.error(f"Quick health check failed for {provider_name}: {e}")
            self._trip_circuit_breaker(provider_name)
            return False
    
    async def get_authorization_url(self, provider_name: str, state: str, nonce: Optional[str] = None) -> Optional[str]:
        """Get OAuth authorization URL for provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            return None
        
        # Check availability
        if not await self.validate_provider_availability(provider_name):
            logger.warning(f"Provider {provider_name} not available for authorization")
            return None
        
        # Build authorization URL
        params = {
            'client_id': provider.client_id,
            'response_type': 'code',
            'redirect_uri': provider.redirect_uri,
            'scope': ' '.join(provider.scopes),
            'state': state
        }
        
        if nonce:
            params['nonce'] = nonce
        
        # Add provider-specific parameters
        if provider_name == 'microsoft':
            params['response_mode'] = 'query'
        
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        return f"{provider.authorize_url}?{query_string}"
    
    async def exchange_code_for_token(self, provider_name: str, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        provider = self.providers.get(provider_name)
        if not provider:
            return None
        
        try:
            data = {
                'client_id': provider.client_id,
                'client_secret': provider.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': provider.redirect_uri
            }
            
            headers = {'Accept': 'application/json'}
            
            response = await self.http_client.post(
                provider.token_url,
                data=data,
                headers=headers,
                timeout=provider.timeout_seconds
            )
            
            if response.status_code == 200:
                self._record_provider_success(provider_name)
                return response.json()
            else:
                logger.error(f"Token exchange failed for {provider_name}: {response.status_code}")
                self._record_provider_failure(provider_name, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Token exchange error for {provider_name}: {e}")
            self._record_provider_failure(provider_name, str(e))
            return None
    
    async def get_user_info(self, provider_name: str, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            return None
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = await self.http_client.get(
                provider.userinfo_url,
                headers=headers,
                timeout=provider.timeout_seconds
            )
            
            if response.status_code == 200:
                self._record_provider_success(provider_name)
                return response.json()
            else:
                logger.error(f"User info request failed for {provider_name}: {response.status_code}")
                self._record_provider_failure(provider_name, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"User info request error for {provider_name}: {e}")
            self._record_provider_failure(provider_name, str(e))
            return None
    
    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while not self._shutdown:
            try:
                await self._check_all_providers_health()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in OAuth health check loop: {e}")
    
    async def _check_all_providers_health(self) -> None:
        """Check health of all providers."""
        tasks = [
            self._check_provider_health(provider_name)
            for provider_name in self.providers.keys()
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_provider_health(self, provider_name: str) -> None:
        """Check health of specific provider."""
        provider = self.providers.get(provider_name)
        health = self.provider_health.get(provider_name)
        
        if not provider or not health:
            return
        
        start_time = time.time()
        
        try:
            # Try to connect to the authorization URL
            response = await self.http_client.head(
                provider.authorize_url,
                timeout=10.0,
                follow_redirects=True
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 302, 405]:  # 405 is OK for HEAD requests
                health.status = ProviderStatus.HEALTHY
                health.response_time_ms = response_time
                health.error_message = None
                health.consecutive_failures = 0
                health.last_success = datetime.now()
            else:
                health.status = ProviderStatus.DEGRADED
                health.error_message = f"HTTP {response.status_code}"
                health.consecutive_failures += 1
            
        except Exception as e:
            health.status = ProviderStatus.UNAVAILABLE
            health.error_message = str(e)
            health.consecutive_failures += 1
            health.response_time_ms = None
        
        health.last_check = datetime.now()
        
        logger.debug(f"OAuth provider {provider_name} health: {health.status.value}")
    
    async def _quick_health_check(self, provider_name: str) -> bool:
        """Perform quick health check for provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            return False
        
        try:
            response = await self.http_client.head(
                provider.authorize_url,
                timeout=5.0,
                follow_redirects=True
            )
            return response.status_code in [200, 302, 405]
        except Exception:
            return False
    
    def _is_circuit_breaker_open(self, provider_name: str) -> bool:
        """Check if circuit breaker is open for provider."""
        breaker = self.circuit_breakers.get(provider_name)
        if not breaker:
            return False
        
        if breaker['state'] == 'open':
            # Check if we should try half-open
            if time.time() >= breaker['next_attempt_time']:
                breaker['state'] = 'half-open'
                return False
            return True
        
        return False
    
    def _trip_circuit_breaker(self, provider_name: str) -> None:
        """Trip circuit breaker for provider."""
        self.circuit_breakers[provider_name] = {
            'state': 'open',
            'next_attempt_time': time.time() + 300,  # 5 minute timeout
            'failure_count': self.circuit_breakers.get(provider_name, {}).get('failure_count', 0) + 1
        }
        logger.warning(f"Circuit breaker tripped for OAuth provider {provider_name}")
    
    def _record_provider_success(self, provider_name: str) -> None:
        """Record successful provider interaction."""
        # Reset circuit breaker
        if provider_name in self.circuit_breakers:
            self.circuit_breakers[provider_name]['state'] = 'closed'
            self.circuit_breakers[provider_name]['failure_count'] = 0
        
        # Update health status
        health = self.provider_health.get(provider_name)
        if health:
            health.consecutive_failures = 0
            health.last_success = datetime.now()
            if health.status == ProviderStatus.UNAVAILABLE:
                health.status = ProviderStatus.HEALTHY
    
    def _record_provider_failure(self, provider_name: str, error: str) -> None:
        """Record failed provider interaction."""
        health = self.provider_health.get(provider_name)
        if health:
            health.consecutive_failures += 1
            health.error_message = error
            
            if health.consecutive_failures >= 3:
                health.status = ProviderStatus.UNAVAILABLE
                self._trip_circuit_breaker(provider_name)
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get OAuth manager statistics."""
        provider_stats = {}
        
        for name, health in self.provider_health.items():
            provider_stats[name] = {
                'status': health.status.value,
                'consecutive_failures': health.consecutive_failures,
                'last_check': health.last_check.isoformat() if health.last_check else None,
                'last_success': health.last_success.isoformat() if health.last_success else None,
                'response_time_ms': health.response_time_ms,
                'error_message': health.error_message
            }
        
        return {
            'total_providers': len(self.providers),
            'healthy_providers': len(self.get_healthy_providers()),
            'providers': provider_stats,
            'circuit_breakers': self.circuit_breakers
        }


# Global OAuth manager instance
_oauth_manager: Optional[OAuthProviderManager] = None


def get_oauth_manager() -> OAuthProviderManager:
    """Get global OAuth provider manager instance."""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthProviderManager()
    return _oauth_manager


async def validate_oauth_provider(provider_name: str) -> bool:
    """Convenience function to validate OAuth provider availability."""
    manager = get_oauth_manager()
    return await manager.validate_provider_availability(provider_name)


async def get_oauth_authorization_url(provider_name: str, state: str, nonce: Optional[str] = None) -> Optional[str]:
    """Convenience function to get OAuth authorization URL."""
    manager = get_oauth_manager()
    return await manager.get_authorization_url(provider_name, state, nonce)