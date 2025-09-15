"""
Database Resilience Module
Implements circuit breaker and retry patterns for database connectivity issues.

Specifically designed to handle Cloud SQL VPC connector connectivity problems
while maintaining application availability during infrastructure failures.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable, Union
from enum import Enum
from datetime import datetime, timedelta, UTC
from contextlib import asynccontextmanager
import statistics

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class DatabaseError(Exception):
    """Base class for database-related errors"""
    pass


class InfrastructureError(DatabaseError):
    """Error indicating infrastructure-level problem (not application bug)"""

    def __init__(self, message: str, error_type: str = "infrastructure", underlying_error: Exception = None):
        super().__init__(message)
        self.error_type = error_type
        self.underlying_error = underlying_error
        self.timestamp = datetime.now(UTC)


class ApplicationError(DatabaseError):
    """Error indicating application-level problem"""

    def __init__(self, message: str, error_type: str = "application", underlying_error: Exception = None):
        super().__init__(message)
        self.error_type = error_type
        self.underlying_error = underlying_error
        self.timestamp = datetime.now(UTC)


class DatabaseCircuitBreaker:
    """
    Circuit breaker for database connections.

    Helps distinguish between infrastructure failures (Cloud SQL VPC issues)
    and application failures, providing resilience during infrastructure problems.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        name: str = "database"
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes needed to close circuit from half-open
            timeout_seconds: Time to wait before attempting half-open
            max_retries: Maximum number of retry attempts
            retry_delay_seconds: Base delay between retries
            name: Name for logging purposes
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.name = name

        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_attempt_time = None

        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.response_times = []
        self.error_types = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            InfrastructureError: When circuit is open or infrastructure failure detected
            ApplicationError: When application error occurs
        """
        async with self._lock:
            self.total_requests += 1
            self.last_attempt_time = datetime.now(UTC)

            # Check circuit state
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker '{self.name}': Attempting reset to half-open")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    logger.warning(f"Circuit breaker '{self.name}': Circuit is open, rejecting request")
                    raise InfrastructureError(
                        f"Circuit breaker '{self.name}' is open. Last failure: {self.last_failure_time}",
                        error_type="circuit_breaker_open"
                    )

        # Execute with retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()

                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Record success
                response_time = time.time() - start_time
                await self._record_success(response_time)

                return result

            except Exception as e:
                last_error = e
                error_classification = self._classify_error(e)

                logger.warning(
                    f"Circuit breaker '{self.name}': Attempt {attempt + 1}/{self.max_retries + 1} failed: {error_classification['type']} - {str(e)}"
                )

                # Record failure
                await self._record_failure(error_classification)

                # Don't retry for certain error types
                if not error_classification.get('should_retry', True):
                    break

                # Apply exponential backoff for retries
                if attempt < self.max_retries:
                    delay = self.retry_delay_seconds * (2 ** attempt)
                    logger.info(f"Circuit breaker '{self.name}': Retrying in {delay:.2f} seconds")
                    await asyncio.sleep(delay)

        # All retries exhausted, raise classified error
        error_classification = self._classify_error(last_error)
        if error_classification['type'] == 'infrastructure':
            raise InfrastructureError(
                f"Database operation failed after {self.max_retries + 1} attempts: {str(last_error)}",
                error_type=error_classification.get('category', 'unknown'),
                underlying_error=last_error
            )
        else:
            raise ApplicationError(
                f"Database operation failed: {str(last_error)}",
                error_type=error_classification.get('category', 'unknown'),
                underlying_error=last_error
            )

    def _classify_error(self, error: Exception) -> Dict[str, Any]:
        """
        Classify error as infrastructure or application level.

        Args:
            error: Exception to classify

        Returns:
            Dictionary with error classification information
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Infrastructure-level errors (Cloud SQL VPC, network, etc.)
        infrastructure_patterns = [
            'connection refused',
            'connection timeout',
            'connection reset',
            'network is unreachable',
            'no route to host',
            'connection aborted',
            'connection closed unexpectedly',
            'could not connect to server',
            'server closed the connection unexpectedly',
            'timeout expired',
            'operation timed out',
            'ssl connection has been closed unexpectedly',
            'could not translate host name',
            'temporary failure in name resolution',
            'cloudsql',
            'vpc connector',
            'unix socket',
        ]

        # Authentication/permission errors (could be either, but often config)
        auth_patterns = [
            'authentication failed',
            'password authentication failed',
            'role does not exist',
            'permission denied',
            'access denied',
            'invalid authorization specification',
        ]

        # Application-level errors (SQL syntax, constraints, etc.)
        application_patterns = [
            'syntax error',
            'column does not exist',
            'table does not exist',
            'constraint violation',
            'unique constraint',
            'foreign key constraint',
            'check constraint',
            'not null constraint',
            'invalid input syntax',
            'data type',
            'division by zero',
        ]

        # Check for infrastructure patterns
        for pattern in infrastructure_patterns:
            if pattern in error_str:
                return {
                    'type': 'infrastructure',
                    'category': 'connectivity',
                    'pattern': pattern,
                    'should_retry': True,
                    'description': f'Infrastructure connectivity issue: {pattern}'
                }

        # Check for authentication patterns
        for pattern in auth_patterns:
            if pattern in error_str:
                return {
                    'type': 'infrastructure',  # Treat auth as infrastructure (config issue)
                    'category': 'authentication',
                    'pattern': pattern,
                    'should_retry': False,  # Don't retry auth failures
                    'description': f'Authentication/authorization issue: {pattern}'
                }

        # Check for application patterns
        for pattern in application_patterns:
            if pattern in error_str:
                return {
                    'type': 'application',
                    'category': 'sql_error',
                    'pattern': pattern,
                    'should_retry': False,  # Don't retry application errors
                    'description': f'Application SQL error: {pattern}'
                }

        # Default classification based on exception type
        if error_type in ['ConnectionError', 'TimeoutError', 'OSError', 'ConnectionRefusedError']:
            return {
                'type': 'infrastructure',
                'category': 'network',
                'pattern': error_type,
                'should_retry': True,
                'description': f'Network-level error: {error_type}'
            }

        # Default to application error for unknown patterns
        return {
            'type': 'application',
            'category': 'unknown',
            'pattern': 'unknown',
            'should_retry': False,
            'description': f'Unknown error pattern: {error_str[:100]}'
        }

    async def _record_success(self, response_time: float):
        """Record successful operation."""
        self.total_successes += 1
        self.response_times.append(response_time)

        # Keep only last 100 response times for memory efficiency
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(f"Circuit breaker '{self.name}': Closing circuit after {self.success_count} successes")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on successful operation
            if self.failure_count > 0:
                logger.info(f"Circuit breaker '{self.name}': Resetting failure count after success")
                self.failure_count = 0

    async def _record_failure(self, error_classification: Dict[str, Any]):
        """Record failed operation."""
        self.total_failures += 1
        self.last_failure_time = datetime.now(UTC)

        # Track error types for monitoring
        error_category = error_classification.get('category', 'unknown')
        self.error_types[error_category] = self.error_types.get(error_category, 0) + 1

        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker '{self.name}': Opening circuit after {self.failure_count} failures. "
                    f"Error type: {error_classification['type']}"
                )
                self.state = CircuitState.OPEN
                self.last_failure_time = datetime.now(UTC)
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}': Failed in half-open state, reopening circuit")
            self.state = CircuitState.OPEN
            self.last_failure_time = datetime.now(UTC)
            self.success_count = 0

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt circuit reset."""
        if not self.last_failure_time:
            return True

        time_since_failure = datetime.now(UTC) - self.last_failure_time
        return time_since_failure.total_seconds() >= self.timeout_seconds

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics for monitoring."""
        now = datetime.now(UTC)
        avg_response_time = statistics.mean(self.response_times) if self.response_times else 0

        return {
            'name': self.name,
            'state': self.state.value,
            'total_requests': self.total_requests,
            'total_successes': self.total_successes,
            'total_failures': self.total_failures,
            'success_rate': self.total_successes / max(self.total_requests, 1) * 100,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_attempt_time': self.last_attempt_time.isoformat() if self.last_attempt_time else None,
            'avg_response_time_ms': avg_response_time * 1000,
            'error_types': dict(self.error_types),
            'thresholds': {
                'failure_threshold': self.failure_threshold,
                'success_threshold': self.success_threshold,
                'timeout_seconds': self.timeout_seconds
            }
        }

    def reset(self):
        """Reset circuit breaker to closed state."""
        logger.info(f"Circuit breaker '{self.name}': Manual reset to closed state")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class DatabaseResilientConnection:
    """
    Resilient database connection wrapper that uses circuit breaker pattern.
    """

    def __init__(
        self,
        connection_factory: Callable,
        circuit_breaker: Optional[DatabaseCircuitBreaker] = None,
        connection_timeout: int = 30
    ):
        """
        Initialize resilient connection.

        Args:
            connection_factory: Function that creates database connections
            circuit_breaker: Circuit breaker instance (creates default if None)
            connection_timeout: Connection timeout in seconds
        """
        self.connection_factory = connection_factory
        self.circuit_breaker = circuit_breaker or DatabaseCircuitBreaker()
        self.connection_timeout = connection_timeout
        self._current_connection = None

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection through circuit breaker."""
        connection = None
        try:
            # Get connection through circuit breaker
            connection = await self.circuit_breaker.call(
                self._create_connection_with_timeout
            )
            yield connection
        finally:
            if connection:
                try:
                    if hasattr(connection, 'close'):
                        if asyncio.iscoroutinefunction(connection.close):
                            await connection.close()
                        else:
                            connection.close()
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")

    async def _create_connection_with_timeout(self):
        """Create database connection with timeout."""
        try:
            if asyncio.iscoroutinefunction(self.connection_factory):
                connection = await asyncio.wait_for(
                    self.connection_factory(),
                    timeout=self.connection_timeout
                )
            else:
                connection = self.connection_factory()

            return connection
        except asyncio.TimeoutError:
            raise InfrastructureError(
                f"Database connection timeout after {self.connection_timeout} seconds",
                error_type="connection_timeout"
            )

    async def execute_query(self, query: str, *args, **kwargs):
        """Execute query through resilient connection."""
        async with self.get_connection() as connection:
            return await self.circuit_breaker.call(
                self._execute_query_on_connection,
                connection,
                query,
                *args,
                **kwargs
            )

    async def _execute_query_on_connection(self, connection, query: str, *args, **kwargs):
        """Execute query on specific connection."""
        if hasattr(connection, 'execute'):
            if asyncio.iscoroutinefunction(connection.execute):
                return await connection.execute(query, *args, **kwargs)
            else:
                return connection.execute(query, *args, **kwargs)
        else:
            raise ApplicationError("Connection does not support execute method")

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status including circuit breaker metrics."""
        metrics = self.circuit_breaker.get_metrics()

        # Determine overall health
        is_healthy = (
            metrics['state'] != CircuitState.OPEN.value and
            metrics['success_rate'] > 50
        )

        status = "healthy" if is_healthy else "degraded"
        if metrics['state'] == CircuitState.OPEN.value:
            status = "unhealthy"

        return {
            'status': status,
            'component': 'database_connection',
            'circuit_breaker': metrics,
            'connection_timeout': self.connection_timeout,
            'timestamp': datetime.now(UTC).isoformat()
        }


# Global circuit breakers for different database types
_circuit_breakers: Dict[str, DatabaseCircuitBreaker] = {}


def get_circuit_breaker(name: str) -> DatabaseCircuitBreaker:
    """Get or create a circuit breaker instance."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = DatabaseCircuitBreaker(name=name)
    return _circuit_breakers[name]


def get_all_circuit_breaker_metrics() -> Dict[str, Any]:
    """Get metrics from all circuit breakers."""
    return {
        name: breaker.get_metrics()
        for name, breaker in _circuit_breakers.items()
    }


def reset_all_circuit_breakers():
    """Reset all circuit breakers to closed state."""
    for breaker in _circuit_breakers.values():
        breaker.reset()