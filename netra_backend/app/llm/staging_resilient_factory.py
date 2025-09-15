"""Staging Resilient LLM Factory

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: System Stability - Enable graceful degradation of LLM services in staging
- Value Impact: Prevents staging deployment failures from blocking Golden Path validation
- Strategic Impact: Protects $500K+ ARR by maintaining reliable staging environment

This module provides a resilient LLM factory specifically designed for staging environments
where LLM services may be unavailable or have strict timeout constraints due to Cloud Run limitations.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from netra_backend.app.llm.llm_manager import LLMManager, create_llm_manager

logger = central_logger.get_logger(__name__)


class LLMFactoryMode(Enum):
    """Operating modes for LLM factory."""
    FULL_FUNCTIONALITY = "full"          # Normal operation with all features
    GRACEFUL_DEGRADATION = "degraded"    # Limited functionality with fallbacks
    FALLBACK_ONLY = "fallback"           # Only fallback responses, no real LLM calls
    DISABLED = "disabled"                # LLM functionality completely disabled


@dataclass
class LLMFactoryHealth:
    """Health status of the LLM factory."""
    mode: LLMFactoryMode
    available: bool
    last_successful_call: Optional[float]
    consecutive_failures: int
    last_error: Optional[str]
    performance_metrics: Dict[str, float]


class StagingResilientLLMFactory:
    """
    Resilient LLM factory designed for staging environments.

    This factory provides timeout protection, graceful degradation, and fallback mechanisms
    specifically designed to handle Cloud Run constraints and infrastructure limitations
    common in staging environments.

    Key Features:
    - Timeout-protected initialization and operations
    - Automatic fallback to degraded mode on failures
    - Circuit breaker pattern for failing LLM services
    - Environment-aware configuration
    - Comprehensive health monitoring
    """

    def __init__(self, environment: Optional[str] = None):
        """
        Initialize the resilient LLM factory.

        Args:
            environment: Target environment (defaults to current environment)
        """
        self.environment = environment or get_env().get('ENVIRONMENT', 'development')
        self.mode = LLMFactoryMode.FULL_FUNCTIONALITY
        self.consecutive_failures = 0
        self.last_successful_call: Optional[float] = None
        self.last_error: Optional[str] = None
        self.circuit_breaker_open_until: Optional[float] = None

        # Environment-specific configuration
        self.config = self._get_environment_config()

        # Performance tracking
        self.call_count = 0
        self.total_response_time = 0.0
        self.fastest_response = float('inf')
        self.slowest_response = 0.0

        logger.info(f"Initialized resilient LLM factory for {self.environment} environment")

    def _get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        base_config = {
            "initialization_timeout": 30.0,
            "call_timeout": 60.0,
            "circuit_breaker_failure_threshold": 3,
            "circuit_breaker_reset_timeout": 300.0,  # 5 minutes
            "max_consecutive_failures": 5,
            "health_check_interval": 60.0
        }

        environment_overrides = {
            "staging": {
                "initialization_timeout": 10.0,  # Stricter timeout for Cloud Run
                "call_timeout": 15.0,             # Faster failure for staging
                "circuit_breaker_failure_threshold": 2,  # More sensitive
                "circuit_breaker_reset_timeout": 120.0,  # Faster recovery
                "max_consecutive_failures": 3
            },
            "development": {
                "initialization_timeout": 15.0,
                "call_timeout": 30.0,
                "circuit_breaker_failure_threshold": 5,  # More lenient
                "max_consecutive_failures": 10
            }
        }

        if self.environment in environment_overrides:
            base_config.update(environment_overrides[self.environment])

        return base_config

    async def create_llm_manager_resilient(
        self,
        user_context: Optional['UserExecutionContext'] = None,
        timeout_override: Optional[float] = None
    ) -> Optional[LLMManager]:
        """
        Create an LLM manager with resilience and timeout protection.

        Args:
            user_context: Optional user execution context
            timeout_override: Override default timeout

        Returns:
            LLMManager instance or None if creation fails gracefully
        """
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            logger.warning(f"LLM factory circuit breaker is open, using fallback mode")
            self.mode = LLMFactoryMode.FALLBACK_ONLY
            return self._create_fallback_manager(user_context)

        timeout = timeout_override or self.config["initialization_timeout"]

        try:
            start_time = time.time()

            # Attempt to create LLM manager with timeout protection
            manager = await asyncio.wait_for(
                self._create_manager_with_validation(user_context),
                timeout=timeout
            )

            # Track successful creation
            response_time = time.time() - start_time
            self._record_successful_call(response_time)

            logger.info(f"Successfully created LLM manager in {response_time:.2f}s")
            return manager

        except asyncio.TimeoutError:
            error_msg = f"LLM manager creation timed out after {timeout}s"
            self._record_failure(error_msg)
            logger.warning(f"{error_msg}, switching to degraded mode")
            return self._create_degraded_manager(user_context)

        except Exception as e:
            error_msg = f"LLM manager creation failed: {str(e)}"
            self._record_failure(error_msg)
            logger.error(f"{error_msg}, attempting graceful fallback")
            return self._create_fallback_manager(user_context)

    async def _create_manager_with_validation(
        self,
        user_context: Optional['UserExecutionContext']
    ) -> LLMManager:
        """Create and validate LLM manager."""
        # Create the manager
        manager = create_llm_manager(user_context)

        # Initialize with timeout protection
        await asyncio.wait_for(
            manager.initialize(),
            timeout=self.config["initialization_timeout"] / 2
        )

        # Validate basic functionality (quick health check)
        health_result = await asyncio.wait_for(
            manager.health_check(),
            timeout=2.0
        )

        if not health_result.get("initialized", False):
            raise ValueError("LLM manager failed to initialize properly")

        return manager

    def _create_degraded_manager(
        self,
        user_context: Optional['UserExecutionContext']
    ) -> LLMManager:
        """Create a degraded LLM manager with limited functionality."""
        logger.info("Creating degraded LLM manager with limited functionality")
        self.mode = LLMFactoryMode.GRACEFUL_DEGRADATION

        # Create a basic manager without full initialization
        manager = create_llm_manager(user_context)

        # Override methods to provide degraded responses
        original_ask_llm = manager.ask_llm

        async def degraded_ask_llm(prompt: str, llm_config_name: str = "default", use_cache: bool = True) -> str:
            """Degraded ask_llm that provides fallback responses."""
            try:
                # Try the original method with very short timeout
                return await asyncio.wait_for(
                    original_ask_llm(prompt, llm_config_name, use_cache),
                    timeout=5.0
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"LLM call failed in degraded mode: {e}")
                return self._get_degraded_response(prompt)

        # Replace the method
        manager.ask_llm = degraded_ask_llm

        return manager

    def _create_fallback_manager(
        self,
        user_context: Optional['UserExecutionContext']
    ) -> Optional[LLMManager]:
        """Create a fallback manager that only provides static responses."""
        logger.info("Creating fallback LLM manager (static responses only)")
        self.mode = LLMFactoryMode.FALLBACK_ONLY

        # In staging environment, return None to indicate LLM is unavailable
        # This allows health checks to handle the absence gracefully
        if self.environment == "staging":
            logger.info("In staging environment, returning None for graceful LLM absence handling")
            return None

        # For other environments, create a minimal manager
        manager = create_llm_manager(user_context)

        # Override all LLM methods to provide fallback responses
        async def fallback_ask_llm(prompt: str, llm_config_name: str = "default", use_cache: bool = True) -> str:
            """Fallback ask_llm that provides static responses."""
            return self._get_fallback_response(prompt)

        async def fallback_health_check() -> Dict[str, Any]:
            """Fallback health check."""
            return {
                "status": "degraded",
                "initialized": False,
                "cache_size": 0,
                "available_configs": [],
                "fallback_mode": True
            }

        manager.ask_llm = fallback_ask_llm
        manager.health_check = fallback_health_check

        return manager

    def _get_degraded_response(self, prompt: str) -> str:
        """Get a degraded response for a prompt."""
        return (
            "I apologize, but our AI services are currently operating in limited mode. "
            "Your request has been noted, but I may not be able to provide the most "
            "accurate or complete response at this time. Please try again later for "
            "full AI functionality."
        )

    def _get_fallback_response(self, prompt: str) -> str:
        """Get a fallback response for a prompt."""
        return (
            "I apologize, but AI services are temporarily unavailable. "
            "Our team is working to restore full functionality. Please try again later "
            "or contact support if this issue persists."
        )

    def _record_successful_call(self, response_time: float) -> None:
        """Record a successful LLM operation."""
        self.consecutive_failures = 0
        self.last_successful_call = time.time()
        self.last_error = None

        # Update performance metrics
        self.call_count += 1
        self.total_response_time += response_time
        self.fastest_response = min(self.fastest_response, response_time)
        self.slowest_response = max(self.slowest_response, response_time)

        # Reset mode to full functionality if we were degraded
        if self.mode != LLMFactoryMode.FULL_FUNCTIONALITY:
            logger.info("LLM factory recovering to full functionality")
            self.mode = LLMFactoryMode.FULL_FUNCTIONALITY

    def _record_failure(self, error_message: str) -> None:
        """Record a failed LLM operation."""
        self.consecutive_failures += 1
        self.last_error = error_message

        # Check if we should open circuit breaker
        if self.consecutive_failures >= self.config["circuit_breaker_failure_threshold"]:
            self.circuit_breaker_open_until = time.time() + self.config["circuit_breaker_reset_timeout"]
            logger.error(f"Opening LLM factory circuit breaker after {self.consecutive_failures} failures")

        # Escalate degradation mode
        if self.consecutive_failures >= self.config["max_consecutive_failures"]:
            self.mode = LLMFactoryMode.DISABLED
            logger.error(f"LLM factory disabled after {self.consecutive_failures} consecutive failures")
        elif self.mode == LLMFactoryMode.FULL_FUNCTIONALITY:
            self.mode = LLMFactoryMode.GRACEFUL_DEGRADATION

    def _is_circuit_breaker_open(self) -> bool:
        """Check if the circuit breaker is currently open."""
        if self.circuit_breaker_open_until is None:
            return False

        if time.time() >= self.circuit_breaker_open_until:
            # Circuit breaker timeout expired, reset
            self.circuit_breaker_open_until = None
            self.consecutive_failures = 0
            logger.info("LLM factory circuit breaker reset")
            return False

        return True

    def get_health_status(self) -> LLMFactoryHealth:
        """Get current health status of the factory."""
        performance_metrics = {}

        if self.call_count > 0:
            performance_metrics = {
                "average_response_time": self.total_response_time / self.call_count,
                "fastest_response": self.fastest_response if self.fastest_response != float('inf') else 0.0,
                "slowest_response": self.slowest_response,
                "total_calls": self.call_count
            }

        return LLMFactoryHealth(
            mode=self.mode,
            available=self.mode != LLMFactoryMode.DISABLED,
            last_successful_call=self.last_successful_call,
            consecutive_failures=self.consecutive_failures,
            last_error=self.last_error,
            performance_metrics=performance_metrics
        )

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the LLM factory."""
        health = self.get_health_status()

        return {
            "status": "healthy" if health.available else "unhealthy",
            "mode": health.mode.value,
            "consecutive_failures": health.consecutive_failures,
            "last_successful_call": health.last_successful_call,
            "last_error": health.last_error,
            "circuit_breaker_open": self._is_circuit_breaker_open(),
            "environment": self.environment,
            "performance": health.performance_metrics
        }


# Global factory instance per environment
_factory_instances: Dict[str, StagingResilientLLMFactory] = {}


def get_resilient_llm_factory(environment: Optional[str] = None) -> StagingResilientLLMFactory:
    """
    Get the resilient LLM factory for the specified environment.

    Args:
        environment: Target environment (defaults to current environment)

    Returns:
        StagingResilientLLMFactory: Factory instance for the environment
    """
    if environment is None:
        environment = get_env().get('ENVIRONMENT', 'development')

    if environment not in _factory_instances:
        _factory_instances[environment] = StagingResilientLLMFactory(environment)
        logger.info(f"Created new resilient LLM factory instance for {environment}")

    return _factory_instances[environment]


async def create_resilient_llm_manager(
    user_context: Optional['UserExecutionContext'] = None,
    environment: Optional[str] = None
) -> Optional[LLMManager]:
    """
    Create a resilient LLM manager using the appropriate factory for the environment.

    This is the main entry point for creating LLM managers in environments where
    resilience and graceful degradation are important.

    Args:
        user_context: Optional user execution context
        environment: Target environment (defaults to current environment)

    Returns:
        LLMManager instance or None if LLM services are unavailable
    """
    factory = get_resilient_llm_factory(environment)
    return await factory.create_llm_manager_resilient(user_context)


# Export main classes and functions
__all__ = [
    "StagingResilientLLMFactory",
    "LLMFactoryMode",
    "LLMFactoryHealth",
    "get_resilient_llm_factory",
    "create_resilient_llm_manager"
]