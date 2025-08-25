"""Connection Pool Manager with Circuit Breaker Pattern

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Prevent database connection storms during cold starts
- Value Impact: Ensures system stability under concurrent initialization load
- Strategic Impact: Enables reliable horizontal scaling and prevents cascading failures

This module provides connection pool management with circuit breaker pattern,
exponential backoff, and jitter to prevent thundering herd problems.
"""

import asyncio
import random
import time
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError as SQLTimeoutError

from netra_backend.app.logging_config import central_logger
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.core.configuration.base import get_unified_config

logger = central_logger.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: float = 30.0  # Seconds before trying half-open
    success_threshold: int = 3  # Successes to close from half-open
    timeout: float = 10.0  # Request timeout in seconds


@dataclass
class ConnectionMetrics:
    """Connection pool metrics tracking."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    avg_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)


class DatabaseCircuitBreaker:
    """Circuit breaker for database connections with exponential backoff."""
    
    def __init__(self, config: CircuitBreakerConfig = None, name: str = "database"):
        """Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
            name: Name for logging purposes
        """
        self.config = config or CircuitBreakerConfig()
        self.name = name
        self.state = CircuitState.CLOSED
        self.metrics = ConnectionMetrics()
        self._lock = asyncio.Lock()
        self._last_state_change = time.time()
    
    async def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset to half-open."""
        if self.state != CircuitState.OPEN:
            return False
        
        time_since_open = time.time() - self._last_state_change
        return time_since_open >= self.config.recovery_timeout
    
    async def _record_success(self, response_time: float):
        """Record successful operation."""
        now = time.time()
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.consecutive_successes += 1
        self.metrics.consecutive_failures = 0
        self.metrics.last_success_time = now
        
        # Track response times (keep last 100)
        self.metrics.response_times.append(response_time)
        if len(self.metrics.response_times) > 100:
            self.metrics.response_times.pop(0)
        
        # Calculate average response time
        if self.metrics.response_times:
            self.metrics.avg_response_time = sum(self.metrics.response_times) / len(self.metrics.response_times)
        
        # State transitions based on success
        if self.state == CircuitState.HALF_OPEN:
            if self.metrics.consecutive_successes >= self.config.success_threshold:
                logger.info(f"Circuit breaker {self.name}: HALF_OPEN -> CLOSED (recovery successful)")
                self.state = CircuitState.CLOSED
                self._last_state_change = now
    
    async def _record_failure(self, error: Exception):
        """Record failed operation."""
        now = time.time()
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.consecutive_failures += 1
        self.metrics.consecutive_successes = 0
        self.metrics.last_failure_time = now
        
        # State transitions based on failure
        if self.state == CircuitState.CLOSED:
            if self.metrics.consecutive_failures >= self.config.failure_threshold:
                logger.warning(f"Circuit breaker {self.name}: CLOSED -> OPEN (failure threshold reached)")
                self.state = CircuitState.OPEN
                self._last_state_change = now
        
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker {self.name}: HALF_OPEN -> OPEN (recovery failed)")
            self.state = CircuitState.OPEN
            self._last_state_change = now
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function positional arguments  
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenException: When circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            # Check if we should attempt reset
            if await self._should_attempt_reset():
                logger.info(f"Circuit breaker {self.name}: OPEN -> HALF_OPEN (attempting recovery)")
                self.state = CircuitState.HALF_OPEN
                self._last_state_change = time.time()
            
            # Reject requests when circuit is open
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is OPEN")
        
        # Execute function with timeout
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            response_time = time.time() - start_time
            async with self._lock:
                await self._record_success(response_time)
            
            return result
            
        except Exception as e:
            async with self._lock:
                await self._record_failure(e)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": (
                self.metrics.successful_requests / self.metrics.total_requests
                if self.metrics.total_requests > 0 else 0.0
            ),
            "consecutive_failures": self.metrics.consecutive_failures,
            "consecutive_successes": self.metrics.consecutive_successes,
            "avg_response_time_ms": self.metrics.avg_response_time * 1000,
            "last_failure_time": self.metrics.last_failure_time,
            "last_success_time": self.metrics.last_success_time,
            "state_duration": time.time() - self._last_state_change
        }


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class ConnectionPoolManager:
    """DEPRECATED: Use DatabaseManager for single source of truth.
    
    This class manages database connection pools with circuit breaker and retry logic,
    but has been DEPRECATED to eliminate SSOT violations. Use DatabaseManager instead.
    """
    
    def __init__(self, db_url: str = None):
        """DEPRECATED: Initialize connection pool manager."""
        import warnings
        warnings.warn(
            "ConnectionPoolManager is deprecated. Use DatabaseManager from netra_backend.app.db.database_manager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.db_url = db_url or DatabaseManager.get_application_url_async()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._initialization_lock = asyncio.Lock()
        self._initialized = False
        self._database_manager = DatabaseManager.get_connection_manager()
        
        # Circuit breaker for database operations
        self.circuit_breaker = DatabaseCircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,  # More sensitive for cold starts
                recovery_timeout=20.0,  # Faster recovery attempts
                success_threshold=2,   # Fewer successes needed
                timeout=15.0           # Longer timeout for cold starts
            ),
            name="connection_pool"
        )
    
    def _get_pool_configuration(self) -> Dict[str, Any]:
        """Get optimal pool configuration for asyncio compatibility.
        
        Returns:
            Dictionary of pool configuration parameters
        """
        config = get_unified_config()
        
        # Use NullPool for SQLite, AsyncAdaptedQueuePool for PostgreSQL
        if "sqlite" in self.db_url:
            return {
                "poolclass": NullPool,
                "echo": config.db_echo,
            }
        
        # PostgreSQL configuration optimized for concurrent cold starts
        return {
            "poolclass": AsyncAdaptedQueuePool,  # CRITICAL: Use AsyncAdaptedQueuePool for asyncio
            "pool_size": max(config.db_pool_size, 20),  # Increased for concurrent startups
            "max_overflow": max(config.db_max_overflow, 30),  # Handle startup bursts
            "pool_timeout": 120,  # Longer timeout for cold start scenarios  
            "pool_recycle": config.db_pool_recycle,
            "pool_pre_ping": True,  # Always validate connections
            "pool_reset_on_return": "rollback",  # Safe connection resets
            "echo": config.db_echo,
            "echo_pool": config.db_echo_pool,
        }
    
    def _get_connection_arguments(self) -> Dict[str, Any]:
        """Get connection-specific arguments for PostgreSQL.
        
        Returns:
            Dictionary of connection arguments
        """
        if "postgresql" not in self.db_url:
            return {}
        
        return {
            "connect_args": {
                "server_settings": {
                    "application_name": "netra_pool_manager",
                    "tcp_keepalives_idle": "600",
                    "tcp_keepalives_interval": "30",
                    "tcp_keepalives_count": "3",
                    # Reduce lock timeout to prevent deadlocks during concurrent startup
                    "lock_timeout": "30s",
                    "statement_timeout": "60s",
                }
            }
        }
    
    async def _create_engine_with_retry(self, max_retries: int = 5) -> AsyncEngine:
        """Create database engine with retry logic and jitter.
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Configured AsyncEngine
        """
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Validate URL for asyncpg compatibility
                if not DatabaseManager.validate_application_url(self.db_url):
                    raise RuntimeError(f"Database URL validation failed: {self.db_url}")
                
                # Get pool and connection configuration
                pool_config = self._get_pool_configuration()
                conn_config = self._get_connection_arguments()
                
                # Merge configurations
                engine_config = {**pool_config, **conn_config}
                
                # Create engine
                engine = create_async_engine(self.db_url, **engine_config)
                
                # Test engine creation with a simple connection
                async with engine.begin() as conn:
                    from sqlalchemy import text
                    await conn.execute(text("SELECT 1"))
                
                logger.info(f"Database engine created successfully (attempt {attempt + 1})")
                return engine
                
            except Exception as e:
                if attempt < max_retries - 1:
                    # Calculate delay with exponential backoff and jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Engine creation attempt {attempt + 1} failed: {e}. "
                                 f"Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to create engine after {max_retries} attempts: {e}")
                    raise
    
    async def _ensure_initialized(self):
        """Ensure connection pool is initialized with thread-safe lazy loading."""
        if self._initialized and self._engine and self._session_factory:
            return
        
        async with self._initialization_lock:
            # Double-check after acquiring lock
            if self._initialized and self._engine and self._session_factory:
                return
            
            logger.info("Initializing database connection pool...")
            
            # Create engine through circuit breaker
            self._engine = await self.circuit_breaker.call(self._create_engine_with_retry)
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            
            self._initialized = True
            logger.info("Connection pool initialization completed")
    
    async def get_session(self) -> AsyncSession:
        """Get database session through circuit breaker.
        
        Returns:
            Configured AsyncSession
        """
        await self._ensure_initialized()
        return self._session_factory()
    
    async def execute_with_circuit_breaker(self, operation: Callable, *args, **kwargs):
        """Execute database operation through circuit breaker.
        
        Args:
            operation: Async operation to execute
            *args: Operation positional arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
        """
        await self._ensure_initialized()
        return await self.circuit_breaker.call(operation, *args, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of connection pool.
        
        Returns:
            Health status dictionary
        """
        try:
            await self._ensure_initialized()
            
            start_time = time.time()
            
            # Test basic connectivity
            async with self._engine.begin() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Get pool status
            pool_status = {}
            if hasattr(self._engine.pool, 'size'):
                pool_status = {
                    "pool_size": self._engine.pool.size(),
                    "checked_in": self._engine.pool.checkedin(),
                    "checked_out": self._engine.pool.checkedout(),
                    "overflow": self._engine.pool.overflow(),
                    "invalid": self._engine.pool.invalid(),
                }
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "pool_status": pool_status,
                "circuit_breaker": self.circuit_breaker.get_status(),
                "initialized": self._initialized,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.get_status(),
                "initialized": self._initialized,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Close connection pool gracefully."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Connection pool closed")
            self._engine = None
            self._session_factory = None
            self._initialized = False


# Global connection pool manager instance
_connection_pool_manager: Optional[ConnectionPoolManager] = None
_pool_lock = asyncio.Lock()


async def get_connection_pool_manager(db_url: str = None) -> ConnectionPoolManager:
    """Get or create global connection pool manager instance.
    
    Args:
        db_url: Optional database URL override
        
    Returns:
        ConnectionPoolManager instance
    """
    global _connection_pool_manager
    
    if _connection_pool_manager is None:
        async with _pool_lock:
            if _connection_pool_manager is None:
                _connection_pool_manager = ConnectionPoolManager(db_url)
                await _connection_pool_manager._ensure_initialized()
    
    return _connection_pool_manager


async def reset_connection_pool():
    """Reset global connection pool (for testing or recovery)."""
    global _connection_pool_manager
    
    async with _pool_lock:
        if _connection_pool_manager:
            await _connection_pool_manager.close()
            _connection_pool_manager = None


# Export main classes and functions
__all__ = [
    "ConnectionPoolManager", "DatabaseCircuitBreaker", "CircuitBreakerOpenException",
    "get_connection_pool_manager", "reset_connection_pool"
]