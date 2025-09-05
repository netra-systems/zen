"""
LLM Client Circuit Breaker Module

Provides circuit breaker functionality for LLM client operations.
Prevents cascade failures and enables graceful degradation.
"""

import logging
import time
import asyncio
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, blocking requests  
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Number of failures to open circuit
    recovery_timeout: int = 60          # Seconds to wait before trying again
    success_threshold: int = 2          # Successes needed to close circuit in half-open state
    timeout: float = 30.0               # Request timeout in seconds


class LLMClientCircuitBreaker:
    """
    Circuit breaker for LLM client operations.
    
    Implements the circuit breaker pattern to prevent cascade failures
    and provide graceful degradation when LLM services are failing.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.request_count = 0
        
        logger.info(f"LLMClientCircuitBreaker initialized: {name}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function call through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenException: When circuit is open
            Exception: Original function exceptions when circuit is closed
        """
        self.request_count += 1
        
        # Check if circuit should be opened
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time < self.config.recovery_timeout:
                raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is open")
            else:
                # Try to transition to half-open
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
        
        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            # Success - handle state transitions
            self._handle_success()
            return result
            
        except Exception as e:
            # Failure - handle state transitions
            self._handle_failure()
            raise e
    
    def _handle_success(self) -> None:
        """Handle successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} closed after recovery")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _handle_failure(self) -> None:
        """Handle failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} opened due to failures")
        elif self.state == CircuitState.HALF_OPEN:
            # Failed in half-open, go back to open
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} reopened after half-open failure")
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state"""
        return self.state
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'request_count': self.request_count,
            'last_failure_time': self.last_failure_time,
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'recovery_timeout': self.config.recovery_timeout,
                'success_threshold': self.config.success_threshold,
                'timeout': self.config.timeout
            }
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        logger.info(f"Circuit breaker {self.name} reset")
    
    def force_open(self) -> None:
        """Force circuit breaker to open state"""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        logger.warning(f"Circuit breaker {self.name} forced open")
    
    def force_close(self) -> None:
        """Force circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info(f"Circuit breaker {self.name} forced closed")


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class LLMCircuitBreakerManager:
    """
    Manager for multiple LLM circuit breakers.
    
    Provides centralized management of circuit breakers for different LLM clients.
    """
    
    def __init__(self):
        self._breakers: Dict[str, LLMClientCircuitBreaker] = {}
        logger.info("LLMCircuitBreakerManager initialized")
    
    def get_or_create_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> LLMClientCircuitBreaker:
        """
        Get existing circuit breaker or create a new one.
        
        Args:
            name: Circuit breaker name
            config: Circuit breaker configuration
            
        Returns:
            Circuit breaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = LLMClientCircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_breaker(self, name: str) -> Optional[LLMClientCircuitBreaker]:
        """Get circuit breaker by name"""
        return self._breakers.get(name)
    
    def remove_breaker(self, name: str) -> bool:
        """Remove circuit breaker by name"""
        if name in self._breakers:
            del self._breakers[name]
            logger.info(f"Removed circuit breaker: {name}")
            return True
        return False
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }
    
    def get_healthy_breakers(self) -> Dict[str, LLMClientCircuitBreaker]:
        """Get all circuit breakers in closed state"""
        return {
            name: breaker
            for name, breaker in self._breakers.items()
            if breaker.get_state() == CircuitState.CLOSED
        }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# Global circuit breaker manager
_circuit_breaker_manager = None


def get_circuit_breaker_manager() -> LLMCircuitBreakerManager:
    """Get global circuit breaker manager"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = LLMCircuitBreakerManager()
    return _circuit_breaker_manager


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> LLMClientCircuitBreaker:
    """Convenience function to get or create circuit breaker"""
    return get_circuit_breaker_manager().get_or_create_breaker(name, config)