"""LLM Provider failover management.

Business Value Justification (BVJ):
- Segment: All customer segments (service reliability)
- Business Goal: Ensure continuous AI service availability through provider failover
- Value Impact: Prevents service disruptions when primary LLM providers fail
- Strategic Impact: Reduces single points of failure and improves customer experience
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.llm.llm_provider_manager import LLMProviderManager, LLMProviderResponse

logger = central_logger.get_logger(__name__)


class FailoverResponse:
    """Response from failover operations."""
    
    def __init__(
        self,
        success: bool = False,
        text: Optional[str] = None,
        error: Optional[str] = None,
        provider_used: Optional[str] = None,
        failover_occurred: bool = False,
        primary_provider_failure: Optional[str] = None
    ):
        self.success = success
        self.text = text
        self.error = error
        self.provider_used = provider_used
        self.failover_occurred = failover_occurred
        self.primary_provider_failure = primary_provider_failure


class ProviderFailover:
    """Handles failover between LLM providers."""

    def __init__(self):
        """Initialize provider failover manager."""
        self.provider_manager = LLMProviderManager()
        self._failover_config = {}
        self._circuit_breaker_state = {}

    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure failover settings.
        
        Args:
            config: Failover configuration including providers and settings
        """
        try:
            self._failover_config = {
                "providers": config.get("providers", []),
                "max_retries": config.get("max_retries", 3),
                "retry_delay_seconds": config.get("retry_delay_seconds", 1),
                "circuit_breaker_threshold": config.get("circuit_breaker_threshold", 5),
                "circuit_breaker_timeout": config.get("circuit_breaker_timeout", 300)
            }
            
            logger.debug(f"Configured failover with {len(self._failover_config['providers'])} providers")
            
        except Exception as e:
            logger.error(f"Failed to configure failover: {str(e)}")
            raise

    async def generate_with_failover(
        self,
        prompt: str,
        test_prefix: Optional[str] = None
    ) -> FailoverResponse:
        """Generate completion with automatic failover.
        
        Args:
            prompt: The prompt to process
            test_prefix: Optional test prefix for isolation
            
        Returns:
            Failover response with results
        """
        providers = self._failover_config.get("providers", [])
        max_retries = self._failover_config.get("max_retries", 3)
        retry_delay = self._failover_config.get("retry_delay_seconds", 1)
        
        if not providers:
            return FailoverResponse(
                success=False,
                error="No providers configured for failover"
            )
        
        # Sort providers by priority
        sorted_providers = sorted(providers, key=lambda p: p.get("priority", 999))
        
        primary_failure = None
        attempts = 0
        
        for provider_config in sorted_providers:
            provider_name = provider_config.get("provider", "unknown")
            
            # Check circuit breaker
            if self._is_circuit_breaker_open(provider_name):
                logger.debug(f"Circuit breaker open for {provider_name}, skipping")
                continue
            
            attempts += 1
            
            try:
                logger.debug(f"Attempting generation with {provider_name} (attempt {attempts})")
                
                response = await self.provider_manager.generate_completion(
                    provider_config=provider_config,
                    prompt=prompt,
                    test_prefix=test_prefix
                )
                
                if response.success:
                    # Reset circuit breaker on success
                    self._reset_circuit_breaker(provider_name)
                    
                    failover_occurred = attempts > 1
                    
                    return FailoverResponse(
                        success=True,
                        text=response.text,
                        provider_used=provider_name,
                        failover_occurred=failover_occurred,
                        primary_provider_failure=primary_failure
                    )
                else:
                    # Record failure
                    failure_reason = response.error or "Unknown error"
                    
                    if attempts == 1:
                        primary_failure = failure_reason
                    
                    logger.warning(f"Provider {provider_name} failed: {failure_reason}")
                    self._record_failure(provider_name)
                    
                    # Wait before trying next provider
                    if retry_delay > 0:
                        await asyncio.sleep(retry_delay)
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Provider {provider_name} exception: {error_msg}")
                
                if attempts == 1:
                    primary_failure = error_msg
                
                self._record_failure(provider_name)
                
                if retry_delay > 0:
                    await asyncio.sleep(retry_delay)
        
        # All providers failed
        return FailoverResponse(
            success=False,
            error="All providers failed",
            primary_provider_failure=primary_failure
        )

    def _is_circuit_breaker_open(self, provider: str) -> bool:
        """Check if circuit breaker is open for provider."""
        try:
            breaker_state = self._circuit_breaker_state.get(provider, {})
            failure_count = breaker_state.get("failure_count", 0)
            last_failure = breaker_state.get("last_failure")
            
            threshold = self._failover_config.get("circuit_breaker_threshold", 5)
            timeout = self._failover_config.get("circuit_breaker_timeout", 300)
            
            # If failure count exceeds threshold, check if timeout has passed
            if failure_count >= threshold:
                if last_failure:
                    time_since_failure = time.time() - last_failure
                    if time_since_failure < timeout:
                        return True
                    else:
                        # Timeout passed, allow one retry
                        self._circuit_breaker_state[provider]["failure_count"] = threshold - 1
                        return False
                else:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking circuit breaker: {str(e)}")
            return False

    def _record_failure(self, provider: str) -> None:
        """Record a failure for circuit breaker tracking."""
        try:
            if provider not in self._circuit_breaker_state:
                self._circuit_breaker_state[provider] = {
                    "failure_count": 0,
                    "last_failure": None
                }
            
            self._circuit_breaker_state[provider]["failure_count"] += 1
            self._circuit_breaker_state[provider]["last_failure"] = time.time()
            
            logger.debug(f"Recorded failure for {provider}: {self._circuit_breaker_state[provider]['failure_count']} failures")
            
        except Exception as e:
            logger.error(f"Error recording failure: {str(e)}")

    def _reset_circuit_breaker(self, provider: str) -> None:
        """Reset circuit breaker for provider after successful request."""
        try:
            if provider in self._circuit_breaker_state:
                self._circuit_breaker_state[provider] = {
                    "failure_count": 0,
                    "last_failure": None
                }
                logger.debug(f"Reset circuit breaker for {provider}")
            
        except Exception as e:
            logger.error(f"Error resetting circuit breaker: {str(e)}")

    async def get_provider_health_status(self) -> Dict[str, Any]:
        """Get health status of all configured providers.
        
        Returns:
            Dictionary with provider health information
        """
        try:
            providers = self._failover_config.get("providers", [])
            health_status = {}
            
            for provider_config in providers:
                provider_name = provider_config.get("provider", "unknown")
                breaker_state = self._circuit_breaker_state.get(provider_name, {})
                
                is_healthy = not self._is_circuit_breaker_open(provider_name)
                failure_count = breaker_state.get("failure_count", 0)
                last_failure = breaker_state.get("last_failure")
                
                health_status[provider_name] = {
                    "healthy": is_healthy,
                    "failure_count": failure_count,
                    "last_failure": datetime.fromtimestamp(last_failure, UTC) if last_failure else None,
                    "priority": provider_config.get("priority", 999)
                }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting provider health status: {str(e)}")
            return {}

    async def test_provider_connectivity(self, provider_config: Dict[str, Any]) -> bool:
        """Test connectivity to a specific provider.
        
        Args:
            provider_config: Provider configuration to test
            
        Returns:
            True if provider is reachable, False otherwise
        """
        try:
            test_prompt = "Test connectivity"
            
            response = await self.provider_manager.generate_completion(
                provider_config=provider_config,
                prompt=test_prompt,
                test_prefix="connectivity_test"
            )
            
            return response.success
            
        except Exception as e:
            logger.error(f"Provider connectivity test failed: {str(e)}")
            return False