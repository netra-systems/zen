"""External Service Circuit Breakers and Resilience

Provides circuit breaker protection for external service dependencies:
- OAuth providers (Auth0, Google, etc.)
- LLM services (OpenAI, Anthropic, etc.)
- Third-party APIs

Business Value: Prevents cascade failures from external service outages.
Ensures system remains operational even when external dependencies fail.
"""

import asyncio
import time
from typing import Any, Dict, Optional, TypeVar

from netra_backend.app.core.circuit_breaker_types import CircuitConfig
from netra_backend.app.core.resilience.circuit_breaker import UnifiedCircuitBreaker
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


class ExternalServiceCircuitBreaker:
    """Circuit breaker specifically designed for external service dependencies."""
    
    def __init__(self, service_name: str, environment: str = "production"):
        """Initialize external service circuit breaker."""
        self.service_name = service_name
        self.environment = environment
        self._circuit_breaker = self._create_circuit_breaker()
        self._fallback_enabled = True
    
    def _create_circuit_breaker(self) -> UnifiedCircuitBreaker:
        """Create optimized circuit breaker for external services."""
        # External services get more aggressive timeouts and faster recovery
        config = CircuitConfig.create_for_environment(
            name=f"external_{self.service_name}",
            environment=self.environment
        )
        
        # Override for external service patterns
        if self.environment == "development":
            config.failure_threshold = 5  # Fail faster in dev
            config.recovery_timeout = 15.0  # Recover faster in dev
        elif self.environment == "staging":
            config.failure_threshold = 3  # More sensitive in staging
            config.recovery_timeout = 30.0
        else:  # production
            config.failure_threshold = 3  # Critical - fail fast
            config.recovery_timeout = 60.0  # Conservative recovery
        
        return UnifiedCircuitBreaker(config)
    
    async def call_external_service(self, func, *args, **kwargs) -> T:
        """Call external service with circuit breaker protection."""
        try:
            return await self._circuit_breaker.call(lambda: func(*args, **kwargs))
        except Exception as e:
            logger.warning(f"External service {self.service_name} failed: {e}")
            if self._fallback_enabled:
                return await self._handle_fallback(func, *args, **kwargs)
            raise
    
    async def _handle_fallback(self, func, *args, **kwargs):
        """Handle fallback when external service fails."""
        # Service-specific fallback logic
        if self.service_name.startswith("oauth_"):
            return await self._oauth_fallback()
        elif self.service_name.startswith("llm_"):
            return await self._llm_fallback()
        else:
            return await self._generic_fallback()
    
    async def _oauth_fallback(self) -> Dict[str, Any]:
        """Fallback for OAuth provider failures."""
        logger.info(f"OAuth fallback activated for {self.service_name}")
        return {
            "error": "oauth_temporarily_unavailable",
            "message": "Authentication service temporarily unavailable. Please try again.",
            "fallback": True
        }
    
    async def _llm_fallback(self) -> Dict[str, Any]:
        """Fallback for LLM service failures."""
        logger.info(f"LLM fallback activated for {self.service_name}")
        return {
            "error": "llm_temporarily_unavailable",
            "message": "AI service temporarily unavailable. Request queued for retry.",
            "fallback": True,
            "suggested_retry_seconds": 30
        }
    
    async def _generic_fallback(self) -> Dict[str, Any]:
        """Generic fallback for other external services."""
        logger.info(f"Generic fallback activated for {self.service_name}")
        return {
            "error": "service_temporarily_unavailable",
            "message": f"{self.service_name} temporarily unavailable",
            "fallback": True
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring."""
        return self._circuit_breaker.get_status()
    
    def is_healthy(self) -> bool:
        """Check if external service is considered healthy."""
        return not self._circuit_breaker.is_open


class ExternalServiceManager:
    """Centralized manager for all external service circuit breakers."""
    
    def __init__(self, environment: str = "production"):
        """Initialize external service manager."""
        self.environment = environment
        self._circuit_breakers: Dict[str, ExternalServiceCircuitBreaker] = {}
        self._initialize_default_services()
    
    def _initialize_default_services(self) -> None:
        """Initialize circuit breakers for common external services."""
        default_services = [
            "oauth_auth0",
            "oauth_google", 
            "oauth_github",
            "llm_openai",
            "llm_anthropic",
            "llm_azure",
            "analytics_mixpanel",
            "monitoring_datadog",
            "email_sendgrid"
        ]
        
        for service in default_services:
            self._circuit_breakers[service] = ExternalServiceCircuitBreaker(
                service_name=service,
                environment=self.environment
            )
    
    def get_circuit_breaker(self, service_name: str) -> ExternalServiceCircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self._circuit_breakers:
            self._circuit_breakers[service_name] = ExternalServiceCircuitBreaker(
                service_name=service_name,
                environment=self.environment
            )
        return self._circuit_breakers[service_name]
    
    async def call_service(self, service_name: str, func, *args, **kwargs):
        """Call external service through circuit breaker."""
        circuit_breaker = self.get_circuit_breaker(service_name)
        return await circuit_breaker.call_external_service(func, *args, **kwargs)
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all external service circuit breakers."""
        return {
            name: circuit_breaker.get_status()
            for name, circuit_breaker in self._circuit_breakers.items()
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of external services."""
        total_services = len(self._circuit_breakers)
        healthy_services = sum(
            1 for cb in self._circuit_breakers.values() if cb.is_healthy()
        )
        
        return {
            "total_external_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services,
            "overall_health": "healthy" if healthy_services == total_services else "degraded"
        }


# Global instance for application use
def get_external_service_manager() -> ExternalServiceManager:
    """Get the global external service manager instance."""
    try:
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        environment = getattr(config, 'environment', 'production')
    except Exception:
        environment = "production"
    
    if not hasattr(get_external_service_manager, '_instance'):
        get_external_service_manager._instance = ExternalServiceManager(environment)
    
    return get_external_service_manager._instance


# Convenience functions for common external service patterns
async def call_oauth_service(provider: str, func, *args, **kwargs):
    """Call OAuth service with circuit breaker protection."""
    manager = get_external_service_manager()
    service_name = f"oauth_{provider.lower()}"
    return await manager.call_service(service_name, func, *args, **kwargs)


async def call_llm_service(provider: str, func, *args, **kwargs):
    """Call LLM service with circuit breaker protection.""" 
    manager = get_external_service_manager()
    service_name = f"llm_{provider.lower()}"
    return await manager.call_service(service_name, func, *args, **kwargs)


async def call_external_api(service_name: str, func, *args, **kwargs):
    """Call any external API with circuit breaker protection."""
    manager = get_external_service_manager()
    return await manager.call_service(service_name, func, *args, **kwargs)