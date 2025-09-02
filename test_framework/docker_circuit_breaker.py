"""
Docker Circuit Breaker - Protects against cascading Docker failures

This module implements the Circuit Breaker pattern for Docker operations to prevent
cascading failures and provide fast failure modes when Docker daemon becomes unstable.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Risk Reduction, Development Velocity
2. Business Goal: Prevent cascading Docker failures, enable fast failure recovery
3. Value Impact: Prevents complete test suite failures from single Docker daemon issues
4. Revenue Impact: Protects $2M+ ARR by ensuring resilient CI/CD infrastructure
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from test_framework.docker_rate_limiter import execute_docker_command, DockerCommandResult

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast, not executing operations  
    HALF_OPEN = "half_open" # Testing if service is recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5           # Failures before opening circuit
    recovery_timeout: int = 30           # Seconds before trying half-open
    success_threshold: int = 2           # Successes in half-open to close
    timeout_threshold: int = 3           # Timeouts count as failures
    health_check_interval: int = 60      # Seconds between health checks


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    total_requests: int = 0
    successful_requests: int = 0 
    failed_requests: int = 0
    timeout_requests: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_state: CircuitBreakerState = CircuitBreakerState.CLOSED


class DockerCircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class DockerCircuitBreaker:
    """
    Circuit breaker for Docker operations with health monitoring.
    
    Implements the Circuit Breaker pattern to protect against Docker daemon
    instability and provide fast failure modes during outages.
    """
    
    def __init__(self, 
                 name: str,
                 config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize Docker circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        
        # Thread synchronization
        self._lock = threading.RLock()
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._next_attempt_time: Optional[datetime] = None
        
        logger.info(f"Docker circuit breaker '{name}' initialized")
    
    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            return self._state
    
    @property
    def is_available(self) -> bool:
        """Check if circuit breaker allows operations."""
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            elif self._state == CircuitBreakerState.HALF_OPEN:
                return True  # Allow limited testing
            else:  # OPEN
                # Check if we should transition to half-open
                if (self._next_attempt_time and 
                    datetime.now() >= self._next_attempt_time):
                    self._transition_to_half_open()
                    return True
                return False
    
    def execute_docker_command(self, 
                             cmd: List[str], 
                             timeout: Optional[float] = 30,
                             **kwargs) -> DockerCommandResult:
        """
        Execute Docker command through circuit breaker.
        
        Args:
            cmd: Docker command as list of strings
            timeout: Command timeout in seconds
            **kwargs: Additional arguments for docker execution
            
        Returns:
            DockerCommandResult with execution details
            
        Raises:
            DockerCircuitBreakerError: If circuit is open
            RuntimeError: If command execution fails
        """
        with self._lock:
            self.stats.total_requests += 1
            
            # Check if circuit allows the operation
            if not self.is_available:
                self.stats.failed_requests += 1
                raise DockerCircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN - "
                    f"failing fast to prevent cascading failures"
                )
            
            # Execute the command
            start_time = time.time()
            try:
                logger.debug(f"Circuit breaker '{self.name}': Executing Docker command: {' '.join(cmd)}")
                result = execute_docker_command(cmd, timeout=timeout, **kwargs)
                
                # Handle the result
                if result.returncode == 0:
                    self._on_success(result)
                    return result
                else:
                    self._on_failure(result, "command_failed")
                    # Still return the result so caller can handle the error
                    return result
                    
            except Exception as e:
                # Classify the exception
                error_type = "timeout" if "timeout" in str(e).lower() else "exception"
                
                # Create a failure result
                duration = time.time() - start_time
                failure_result = DockerCommandResult(
                    returncode=-1,
                    stdout="",
                    stderr=str(e),
                    duration=duration,
                    retry_count=0
                )
                
                self._on_failure(failure_result, error_type)
                raise  # Re-raise the original exception
    
    def _on_success(self, result: DockerCommandResult):
        """Handle successful Docker command execution."""
        with self._lock:
            self.stats.successful_requests += 1
            self.stats.last_success_time = datetime.now()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                logger.info(f"Circuit breaker '{self.name}': Success in HALF_OPEN state "
                           f"({self._success_count}/{self.config.success_threshold})")
                
                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in closed state
                self._failure_count = 0
    
    def _on_failure(self, result: DockerCommandResult, error_type: str):
        """Handle failed Docker command execution."""
        with self._lock:
            self.stats.failed_requests += 1
            self.stats.last_failure_time = datetime.now()
            
            if error_type == "timeout":
                self.stats.timeout_requests += 1
            
            if self._state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN]:
                self._failure_count += 1
                
                logger.warning(f"Circuit breaker '{self.name}': Docker command failed "
                              f"(failure {self._failure_count}/{self.config.failure_threshold}) "
                              f"- {error_type}: {result.stderr}")
                
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition circuit breaker to OPEN state."""
        if self._state != CircuitBreakerState.OPEN:
            self._state = CircuitBreakerState.OPEN
            self._last_failure_time = datetime.now()
            self._next_attempt_time = datetime.now() + timedelta(seconds=self.config.recovery_timeout)
            self.stats.circuit_opened_count += 1
            
            logger.error(f"Circuit breaker '{self.name}' OPENED due to repeated failures. "
                        f"Will retry in {self.config.recovery_timeout} seconds")
    
    def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state."""
        self._state = CircuitBreakerState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN - testing recovery")
    
    def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._next_attempt_time = None
        
        logger.info(f"Circuit breaker '{self.name}' CLOSED - normal operation resumed")
    
    def force_open(self, reason: str = "Manual intervention"):
        """
        Manually open the circuit breaker.
        
        Args:
            reason: Reason for opening the circuit
        """
        with self._lock:
            logger.warning(f"Circuit breaker '{self.name}' manually OPENED: {reason}")
            self._transition_to_open()
    
    def force_close(self, reason: str = "Manual intervention"):
        """
        Manually close the circuit breaker.
        
        Args:
            reason: Reason for closing the circuit
        """
        with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually CLOSED: {reason}")
            self._transition_to_closed()
    
    def health_check(self) -> bool:
        """
        Perform a lightweight health check on Docker.
        
        Returns:
            True if Docker is responsive
        """
        try:
            result = self.execute_docker_command(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                timeout=5
            )
            return result.returncode == 0
        except DockerCircuitBreakerError:
            # Circuit is open
            return False
        except Exception as e:
            logger.debug(f"Docker health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "is_available": self.is_available,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "timeout_requests": self.stats.timeout_requests,
                "circuit_opened_count": self.stats.circuit_opened_count,
                "success_rate": (
                    (self.stats.successful_requests / self.stats.total_requests * 100)
                    if self.stats.total_requests > 0 else 0
                ),
                "last_failure_time": (
                    self.stats.last_failure_time.isoformat() 
                    if self.stats.last_failure_time else None
                ),
                "last_success_time": (
                    self.stats.last_success_time.isoformat() 
                    if self.stats.last_success_time else None
                ),
                "next_attempt_time": (
                    self._next_attempt_time.isoformat() 
                    if self._next_attempt_time else None
                )
            }
    
    def reset_stats(self):
        """Reset all statistics."""
        with self._lock:
            self.stats = CircuitBreakerStats()
            logger.info(f"Circuit breaker '{self.name}' statistics reset")


class DockerCircuitBreakerManager:
    """
    Manages multiple circuit breakers for different Docker operation types.
    """
    
    def __init__(self):
        self._breakers: Dict[str, DockerCircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def get_breaker(self, 
                   name: str, 
                   config: Optional[CircuitBreakerConfig] = None) -> DockerCircuitBreaker:
        """
        Get or create a circuit breaker for the given name.
        
        Args:
            name: Circuit breaker name
            config: Configuration for new circuit breakers
            
        Returns:
            DockerCircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = DockerCircuitBreaker(name, config)
            return self._breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {name: breaker.get_stats() 
                   for name, breaker in self._breakers.items()}
    
    def health_check_all(self) -> Dict[str, bool]:
        """Perform health checks on all circuit breakers."""
        with self._lock:
            return {name: breaker.health_check() 
                   for name, breaker in self._breakers.items()}


# Global circuit breaker manager
_global_manager = None
_manager_lock = threading.Lock()


def get_circuit_breaker_manager() -> DockerCircuitBreakerManager:
    """
    Get the global circuit breaker manager.
    
    Returns:
        Singleton DockerCircuitBreakerManager instance
    """
    global _global_manager
    
    if _global_manager is None:
        with _manager_lock:
            if _global_manager is None:
                _global_manager = DockerCircuitBreakerManager()
    
    return _global_manager


def execute_docker_command_with_circuit_breaker(cmd: List[str], 
                                               breaker_name: str = "default",
                                               **kwargs) -> DockerCommandResult:
    """
    Convenience function to execute Docker command with circuit breaker protection.
    
    Args:
        cmd: Docker command as list of strings
        breaker_name: Name of circuit breaker to use
        **kwargs: Additional arguments for docker execution
        
    Returns:
        DockerCommandResult with execution details
    """
    manager = get_circuit_breaker_manager()
    breaker = manager.get_breaker(breaker_name)
    return breaker.execute_docker_command(cmd, **kwargs)


def docker_health_check_with_circuit_breaker(breaker_name: str = "health") -> bool:
    """
    Convenience function for Docker health check with circuit breaker.
    
    Args:
        breaker_name: Name of circuit breaker to use
        
    Returns:
        True if Docker is healthy
    """
    manager = get_circuit_breaker_manager()
    breaker = manager.get_breaker(breaker_name)
    return breaker.health_check()