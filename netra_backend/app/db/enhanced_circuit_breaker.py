"""
Enhanced Circuit Breaker for Database Connections - Issue #1278

CRITICAL PURPOSE: Implement application resilience patterns for database
connections to handle VPC connectivity issues, Cloud SQL timeouts, and
infrastructure failures gracefully.

Business Impact: Prevents cascade failures and maintains application
availability during infrastructure issues affecting $500K+ ARR platform.

Issue #1278 Focus:
- VPC connector timeout handling
- Cloud SQL connection timeout resilience
- Graceful degradation during infrastructure issues
- Connection pool health monitoring
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics
from contextlib import asynccontextmanager

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Blocking all requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class FailureType(Enum):
    """Types of database failures for Issue #1278."""
    CONNECTION_TIMEOUT = "connection_timeout"
    VPC_CONNECTIVITY = "vpc_connectivity"
    CLOUD_SQL_TIMEOUT = "cloud_sql_timeout"
    SSL_CERTIFICATE = "ssl_certificate"
    CONNECTION_POOL_EXHAUSTED = "connection_pool_exhausted"
    AUTHENTICATION_FAILURE = "authentication_failure"
    UNKNOWN = "unknown"


@dataclass
class CircuitBreakerMetrics:
    """Comprehensive metrics for circuit breaker monitoring."""
    # Basic metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Circuit breaker specific
    circuit_trips: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    
    # Timing metrics
    failure_window_start: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_trip_time: Optional[datetime] = None
    
    # Response time tracking
    response_times: List[float] = field(default_factory=list)
    
    # Failure categorization
    failure_types: Dict[str, int] = field(default_factory=dict)
    
    # Infrastructure context
    vpc_connector_failures: int = 0
    cloud_sql_timeouts: int = 0
    ssl_failures: int = 0
    
    def add_response_time(self, response_time: float):
        """Add response time and maintain sliding window."""
        self.response_times.append(response_time)
        # Keep only last 100 response times
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
    
    def get_average_response_time(self) -> float:
        """Get average response time."""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    def get_failure_rate(self) -> float:
        """Get current failure rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100


@dataclass
class CircuitBreakerConfig:
    """Configuration for enhanced circuit breaker."""
    # Failure thresholds
    failure_threshold: int = 5  # Number of failures to trip circuit
    failure_rate_threshold: float = 50.0  # Percentage failure rate to trip
    
    # Timing configuration
    timeout_seconds: float = 10.0  # Request timeout
    recovery_timeout_seconds: float = 60.0  # Time to wait before retry
    half_open_max_calls: int = 3  # Max calls in half-open state
    
    # Infrastructure-specific timeouts (Issue #1278)
    vpc_connector_timeout: float = 600.0  # VPC connector timeout
    cloud_sql_timeout: float = 600.0  # Cloud SQL timeout
    ssl_handshake_timeout: float = 30.0  # SSL handshake timeout
    
    # Response time thresholds
    slow_request_threshold: float = 5000.0  # ms - consider request slow
    critical_response_threshold: float = 30000.0  # ms - critical slowness
    
    # Monitoring configuration
    metrics_window_size: int = 100  # Number of recent requests to consider
    health_check_interval: int = 30  # Seconds between health checks


class EnhancedCircuitBreaker:
    """Enhanced circuit breaker with Issue #1278 infrastructure awareness."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """Initialize enhanced circuit breaker."""
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
        
        # State-specific tracking
        self._open_timestamp: Optional[datetime] = None
        self._half_open_calls: int = 0
        
        # Health check task
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def __call__(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if circuit breaker should block the call
            if await self._should_block_request():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value} - blocking request",
                    circuit_breaker_state=self.state.value,
                    failure_count=self.metrics.failed_requests,
                    failure_rate=self.metrics.get_failure_rate()
                )
            
            # Track the request
            self.metrics.total_requests += 1
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._half_open_calls += 1

        # Execute the function with timeout and monitoring
        start_time = time.time()
        try:
            # Apply infrastructure-aware timeout
            timeout = self._get_infrastructure_timeout(func)
            
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            await self._record_success(response_time)
            return result
            
        except asyncio.TimeoutError as e:
            response_time = (time.time() - start_time) * 1000
            await self._record_failure(e, FailureType.CONNECTION_TIMEOUT, response_time)
            raise DatabaseTimeoutError(f"Request timed out after {timeout}s") from e
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            failure_type = self._classify_failure(e)
            await self._record_failure(e, failure_type, response_time)
            raise

    async def _should_block_request(self) -> bool:
        """Determine if request should be blocked."""
        if self.state == CircuitBreakerState.CLOSED:
            return False
        
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has elapsed
            if self._open_timestamp:
                elapsed = datetime.now(timezone.utc) - self._open_timestamp
                if elapsed.total_seconds() >= self.config.recovery_timeout_seconds:
                    # Move to half-open for testing
                    self.state = CircuitBreakerState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    return False
            return True
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited number of calls for testing
            return self._half_open_calls >= self.config.half_open_max_calls
        
        return False

    def _get_infrastructure_timeout(self, func: Callable) -> float:
        """Get infrastructure-aware timeout based on function type."""
        # Analyze function to determine appropriate timeout
        func_name = getattr(func, '__name__', str(func)).lower()
        
        if 'connect' in func_name or 'establish' in func_name:
            # Database connection establishment
            return self.config.vpc_connector_timeout
        elif 'query' in func_name or 'execute' in func_name:
            # Query execution
            return self.config.cloud_sql_timeout
        elif 'ssl' in func_name or 'tls' in func_name:
            # SSL operations
            return self.config.ssl_handshake_timeout
        else:
            # Default timeout
            return self.config.timeout_seconds

    def _classify_failure(self, error: Exception) -> FailureType:
        """Classify failure type for Issue #1278 specific handling."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # VPC connectivity issues
        if any(pattern in error_str for pattern in [
            'connection refused', 'network unreachable', 'no route to host',
            'vpc connector', 'private ip'
        ]):
            return FailureType.VPC_CONNECTIVITY
        
        # Cloud SQL timeouts
        elif any(pattern in error_str for pattern in [
            'timeout', 'timed out', 'query timeout', 'connection timeout'
        ]):
            return FailureType.CLOUD_SQL_TIMEOUT
        
        # SSL/TLS issues
        elif any(pattern in error_str for pattern in [
            'ssl', 'tls', 'certificate', 'handshake'
        ]):
            return FailureType.SSL_CERTIFICATE
        
        # Connection pool exhaustion
        elif any(pattern in error_str for pattern in [
            'pool', 'too many connections', 'connection limit'
        ]):
            return FailureType.CONNECTION_POOL_EXHAUSTED
        
        # Authentication failures
        elif any(pattern in error_str for pattern in [
            'authentication', 'auth', 'credentials', 'permission denied'
        ]):
            return FailureType.AUTHENTICATION_FAILURE
        
        else:
            return FailureType.UNKNOWN

    async def _record_success(self, response_time: float):
        """Record successful request."""
        async with self._lock:
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = datetime.now(timezone.utc)
            self.metrics.add_response_time(response_time)
            
            # Check for slow requests
            if response_time > self.config.slow_request_threshold:
                logger.warning(f"Slow database request detected: {response_time:.0f}ms (threshold: {self.config.slow_request_threshold:.0f}ms)")
            
            # Handle state transitions
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Successful call in half-open, check if we should close circuit
                if self._half_open_calls >= self.config.half_open_max_calls:
                    await self._close_circuit()
            
            # Reset failure window if we had recent failures
            if self.metrics.failure_window_start:
                # Check if we've recovered (e.g., 5 successful requests)
                recent_successes = self.metrics.successful_requests
                if recent_successes >= 5:
                    self.metrics.failure_window_start = None

    async def _record_failure(self, error: Exception, failure_type: FailureType, response_time: float):
        """Record failed request with detailed categorization."""
        async with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = datetime.now(timezone.utc)
            self.metrics.add_response_time(response_time)
            
            # Track failure type
            failure_key = failure_type.value
            self.metrics.failure_types[failure_key] = self.metrics.failure_types.get(failure_key, 0) + 1
            
            # Track infrastructure-specific failures
            if failure_type == FailureType.VPC_CONNECTIVITY:
                self.metrics.vpc_connector_failures += 1
            elif failure_type == FailureType.CLOUD_SQL_TIMEOUT:
                self.metrics.cloud_sql_timeouts += 1
            elif failure_type == FailureType.SSL_CERTIFICATE:
                self.metrics.ssl_failures += 1
            
            # Set failure window start if not already set
            if not self.metrics.failure_window_start:
                self.metrics.failure_window_start = datetime.now(timezone.utc)
            
            # Check if we should trip the circuit
            await self._check_failure_threshold()
            
            # Log failure with context
            logger.error(f"Circuit breaker '{self.name}' recorded failure: {failure_type.value} - {error}")

    async def _check_failure_threshold(self):
        """Check if failure threshold is exceeded and trip circuit if needed."""
        # Check failure count threshold
        if self.metrics.failed_requests >= self.config.failure_threshold:
            await self._open_circuit("failure count threshold exceeded")
            return
        
        # Check failure rate threshold (only if we have enough requests)
        if self.metrics.total_requests >= 10:  # Minimum sample size
            failure_rate = self.metrics.get_failure_rate()
            if failure_rate >= self.config.failure_rate_threshold:
                await self._open_circuit(f"failure rate {failure_rate:.1f}% exceeded threshold")
                return
        
        # Check for critical response times
        avg_response_time = self.metrics.get_average_response_time()
        if avg_response_time > self.config.critical_response_threshold:
            await self._open_circuit(f"critical response time {avg_response_time:.0f}ms")

    async def _open_circuit(self, reason: str):
        """Open the circuit breaker."""
        if self.state != CircuitBreakerState.OPEN:
            self.state = CircuitBreakerState.OPEN
            self.metrics.circuit_trips += 1
            self._open_timestamp = datetime.now(timezone.utc)
            self.metrics.last_trip_time = self._open_timestamp
            
            logger.critical(f"Circuit breaker '{self.name}' OPENED: {reason}")
            
            # Log infrastructure context for Issue #1278
            if self.metrics.vpc_connector_failures > 0:
                logger.critical(f"VPC connector failures detected: {self.metrics.vpc_connector_failures}")
            if self.metrics.cloud_sql_timeouts > 0:
                logger.critical(f"Cloud SQL timeouts detected: {self.metrics.cloud_sql_timeouts}")

    async def _close_circuit(self):
        """Close the circuit breaker (return to normal operation)."""
        if self.state != CircuitBreakerState.CLOSED:
            self.state = CircuitBreakerState.CLOSED
            self.metrics.successful_recoveries += 1
            self._open_timestamp = None
            self._half_open_calls = 0
            
            logger.info(f"Circuit breaker '{self.name}' CLOSED - service recovered")

    async def health_check(self, health_check_func: Callable) -> bool:
        """Perform health check to test service availability."""
        try:
            self.metrics.recovery_attempts += 1
            result = await asyncio.wait_for(
                health_check_func(),
                timeout=self.config.ssl_handshake_timeout  # Shorter timeout for health checks
            )
            return bool(result)
        except Exception as e:
            logger.debug(f"Health check failed for '{self.name}': {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "failure_rate": round(self.metrics.get_failure_rate(), 2),
                "circuit_trips": self.metrics.circuit_trips,
                "successful_recoveries": self.metrics.successful_recoveries,
                "average_response_time_ms": round(self.metrics.get_average_response_time(), 2),
            },
            "infrastructure_metrics": {
                "vpc_connector_failures": self.metrics.vpc_connector_failures,
                "cloud_sql_timeouts": self.metrics.cloud_sql_timeouts,
                "ssl_failures": self.metrics.ssl_failures,
            },
            "failure_breakdown": dict(self.metrics.failure_types),
            "last_events": {
                "last_success": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
                "last_failure": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "last_trip": self.metrics.last_trip_time.isoformat() if self.metrics.last_trip_time else None,
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "failure_rate_threshold": self.config.failure_rate_threshold,
                "timeout_seconds": self.config.timeout_seconds,
                "recovery_timeout_seconds": self.config.recovery_timeout_seconds,
            }
        }


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker blocks a request."""
    
    def __init__(self, message: str, circuit_breaker_state: str, failure_count: int, failure_rate: float):
        super().__init__(message)
        self.circuit_breaker_state = circuit_breaker_state
        self.failure_count = failure_count
        self.failure_rate = failure_rate


class DatabaseTimeoutError(Exception):
    """Exception raised when database operation times out."""
    pass


# Global circuit breaker registry
_circuit_breakers: Dict[str, EnhancedCircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> EnhancedCircuitBreaker:
    """Get or create a circuit breaker instance."""
    if name not in _circuit_breakers:
        if config is None:
            # Default configuration for Issue #1278
            config = CircuitBreakerConfig(
                failure_threshold=5,
                failure_rate_threshold=50.0,
                timeout_seconds=10.0,
                recovery_timeout_seconds=60.0,
                vpc_connector_timeout=600.0,  # Issue #1278 specific
                cloud_sql_timeout=600.0,      # Issue #1278 specific
                ssl_handshake_timeout=30.0
            )
        
        _circuit_breakers[name] = EnhancedCircuitBreaker(name, config)
        logger.info(f"Created circuit breaker '{name}' with Issue #1278 configuration")
    
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, EnhancedCircuitBreaker]:
    """Get all circuit breaker instances."""
    return _circuit_breakers.copy()


@asynccontextmanager
async def circuit_breaker_protection(name: str, func: Callable, *args, **kwargs):
    """Context manager for circuit breaker protection."""
    circuit_breaker = get_circuit_breaker(name)
    
    try:
        result = await circuit_breaker(func, *args, **kwargs)
        yield result
    except CircuitBreakerError:
        # Circuit breaker is open, handle gracefully
        logger.warning(f"Circuit breaker '{name}' blocked request - service may be experiencing issues")
        raise
    except Exception:
        # Other errors pass through
        raise


async def monitor_all_circuit_breakers() -> Dict[str, Any]:
    """Get status of all circuit breakers for monitoring."""
    status_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_circuit_breakers": len(_circuit_breakers),
        "circuit_breakers": {},
        "summary": {
            "healthy": 0,
            "degraded": 0,
            "failed": 0,
            "total_trips": 0,
            "total_recoveries": 0
        }
    }
    
    for name, cb in _circuit_breakers.items():
        cb_status = cb.get_status()
        status_report["circuit_breakers"][name] = cb_status
        
        # Update summary
        if cb.state == CircuitBreakerState.CLOSED:
            status_report["summary"]["healthy"] += 1
        elif cb.state == CircuitBreakerState.HALF_OPEN:
            status_report["summary"]["degraded"] += 1
        else:
            status_report["summary"]["failed"] += 1
        
        status_report["summary"]["total_trips"] += cb.metrics.circuit_trips
        status_report["summary"]["total_recoveries"] += cb.metrics.successful_recoveries
    
    return status_report