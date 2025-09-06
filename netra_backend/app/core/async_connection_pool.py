"""Async connection pooling utilities for resource management.

Enhanced with automatic recovery mechanisms and resilience patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Stability & Development Velocity
- Value Impact: Enables reliable database operations with automatic failure recovery
- Strategic Impact: Foundation for resilient data layer operations

Key Features:
- Automatic reconnection with exponential backoff (1s -> 60s max)
- Background reconnection task for permanent failure recovery
- Health monitoring with periodic connection validation (30s intervals)
- Circuit breaker pattern integration for resilience
- Force recovery methods for manual intervention
- Self-healing pool state management

Fixes Permanent Failure State Anti-Pattern:
- Previous: _closed = True (permanent, no recovery)
- Fixed: Self-healing with automatic pool recreation and recovery
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable, Set, TypeVar, Optional, Any, Dict

from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker, 
    UnifiedCircuitConfig, 
    UnifiedCircuitBreakerState
)

T = TypeVar('T')
logger = logging.getLogger(__name__)


class AsyncConnectionPool:
    """Enhanced async connection pool with automatic recovery and resilience.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Background reconnection task for permanent failure recovery
    - Health monitoring with periodic connection validation
    - Circuit breaker integration for resilience
    - Self-healing pool state management
    - Force recovery methods for manual intervention
    """
    
    def __init__(
        self,
        create_connection: Callable[[], Awaitable[T]],
        close_connection: Callable[[T], Awaitable[None]],
        max_size: int = 10,
        min_size: int = 1
    ):
        self._init_connection_handlers(create_connection, close_connection)
        self._init_size_parameters(max_size, min_size)
        self._setup_pool()
        self._setup_recovery_mechanisms()
    
    def _init_connection_handlers(self, create_connection: Callable[[], Awaitable[T]], close_connection: Callable[[T], Awaitable[None]]) -> None:
        """Initialize connection handler functions."""
        self._create_connection = create_connection
        self._close_connection = close_connection
    
    def _init_size_parameters(self, max_size: int, min_size: int) -> None:
        """Initialize pool size parameters."""
        self._max_size = max_size
        self._min_size = min_size
    
    def _setup_pool(self):
        """Initialize pool data structures."""
        self._available_connections: asyncio.Queue[T] = asyncio.Queue(maxsize=self._max_size)
        self._active_connections: Set[T] = set()
        self._lock = asyncio.Lock()
        self._closed = False
        self._healthy = True
        self._initialized = False
    
    def _setup_recovery_mechanisms(self):
        """Initialize recovery and monitoring mechanisms."""
        # Recovery state tracking
        self._consecutive_failures = 0
        self._last_failure_time = None
        self._recovery_in_progress = False
        
        # Exponential backoff configuration  
        self._base_retry_delay = 1.0  # Start at 1 second
        self._max_retry_delay = 60.0  # Max 60 seconds
        self._max_reconnect_attempts = 10
        self._current_retry_delay = self._base_retry_delay
        
        # Health monitoring configuration
        self._last_health_check = None
        self._health_check_interval = 30.0  # 30 seconds
        
        # Background tasks
        self._recovery_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Circuit breaker for pool operations
        circuit_config = UnifiedCircuitConfig(
            name="connection_pool_operations",
            failure_threshold=5,
            success_threshold=2,
            recovery_timeout=60,
            timeout_seconds=30.0
        )
        self._circuit_breaker = UnifiedCircuitBreaker(circuit_config)
        
        logger.info(f"Enhanced AsyncConnectionPool initialized with recovery mechanisms (max_size={self._max_size}, min_size={self._min_size})")
    
    async def initialize(self):
        """Initialize the connection pool with recovery setup."""
        if self._initialized:
            logger.debug("Connection pool already initialized")
            return
        
        # Attempt initial pool setup with recovery on failure
        success = await self._attempt_pool_initialization(is_initial=True)
        
        if success:
            # Start background tasks for monitoring and recovery
            self._start_background_tasks()
            self._initialized = True
            logger.info(f"Connection pool successfully initialized with {self._min_size} connections")
        else:
            # Start background recovery task even if initial setup failed
            self._start_background_tasks()
            logger.warning("Initial pool setup failed - background recovery will retry")
    
    def _start_background_tasks(self):
        """Start background tasks for recovery and health monitoring."""
        if not self._recovery_task or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(
                self._background_recovery_task(),
                name="connection_pool_recovery"
            )
        
        if not self._health_monitor_task or self._health_monitor_task.done():
            self._health_monitor_task = asyncio.create_task(
                self._health_monitoring_task(),
                name="connection_pool_health_monitor"
            )
        
        logger.info("Connection pool background monitoring tasks started")
    
    async def _attempt_pool_initialization(self, is_initial: bool = False) -> bool:
        """Attempt pool initialization with proper error handling.
        
        Args:
            is_initial: Whether this is the initial initialization attempt
            
        Returns:
            bool: True if initialization successful, False otherwise
        """
        async with self._lock:
            try:
                # Clear any existing connections first
                await self._clear_all_connections()
                
                # Create fresh pool structures
                self._available_connections = asyncio.Queue(maxsize=self._max_size)
                self._active_connections = set()
                
                # Create minimum required connections
                for i in range(self._min_size):
                    try:
                        connection = await asyncio.wait_for(
                            self._create_connection(), 
                            timeout=10.0
                        )
                        await self._available_connections.put(connection)
                        logger.debug(f"Created connection {i+1}/{self._min_size}")
                    except Exception as e:
                        logger.error(f"Failed to create connection {i+1}/{self._min_size}: {e}")
                        raise
                
                # Mark as healthy and reset failure counters
                self._healthy = True
                self._closed = False
                self._consecutive_failures = 0
                self._current_retry_delay = self._base_retry_delay
                self._circuit_breaker.record_success()
                
                initialization_type = "Initial" if is_initial else "Recovery"
                logger.info(f"{initialization_type} pool initialization successful with {self._min_size} connections")
                
                return True
                
            except Exception as e:
                self._healthy = False
                self._consecutive_failures += 1
                self._last_failure_time = time.time()
                self._circuit_breaker.record_failure(str(type(e).__name__))
                
                error_type = "Initial initialization" if is_initial else "Pool recovery"
                logger.error(
                    f"Pool {error_type.lower()} failed (attempt {self._consecutive_failures}): {e}"
                )
                
                return False
    
    async def _clear_all_connections(self):
        """Clear all existing connections safely."""
        # Close available connections
        while not self._available_connections.empty():
            try:
                connection = await asyncio.wait_for(self._available_connections.get(), timeout=1.0)
                try:
                    await self._close_connection(connection)
                except Exception as e:
                    logger.warning(f"Error closing available connection: {e}")
            except asyncio.TimeoutError:
                break
        
        # Close active connections
        for connection in list(self._active_connections):
            try:
                await self._close_connection(connection)
            except Exception as e:
                logger.warning(f"Error closing active connection: {e}")
        
        self._active_connections.clear()
    
    async def _background_recovery_task(self):
        """Background task for automatic pool recovery attempts.
        
        Implements exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
        Max 10 recovery attempts before giving up temporarily.
        """
        while not self._shutdown_event.is_set():
            try:
                # Only attempt recovery if pool is unhealthy and not already recovering
                if not self._healthy and not self._recovery_in_progress and self._consecutive_failures > 0:
                    
                    # Check if we should attempt recovery
                    if self._consecutive_failures <= self._max_reconnect_attempts:
                        logger.info(
                            f"Attempting pool recovery (attempt {self._consecutive_failures}/{self._max_reconnect_attempts}) "
                            f"after {self._current_retry_delay}s delay"
                        )
                        
                        self._recovery_in_progress = True
                        success = await self._attempt_pool_initialization()
                        self._recovery_in_progress = False
                        
                        if not success:
                            # Exponential backoff: double delay, cap at max
                            self._current_retry_delay = min(
                                self._current_retry_delay * 2,
                                self._max_retry_delay
                            )
                            
                            # Wait before next attempt
                            await asyncio.sleep(self._current_retry_delay)
                        else:
                            logger.info("Pool recovery successful")
                    else:
                        logger.warning(
                            f"Max recovery attempts ({self._max_reconnect_attempts}) reached. "
                            "Waiting 5 minutes before retrying..."
                        )
                        # Wait 5 minutes before resetting attempt counter
                        await asyncio.sleep(300)
                        self._consecutive_failures = 1  # Reset to 1 to allow retries
                        self._current_retry_delay = self._base_retry_delay
                else:
                    # Healthy or already recovering - check every 30 seconds
                    await asyncio.sleep(30)
                    
            except asyncio.CancelledError:
                logger.info("Pool recovery task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in pool recovery task: {e}")
                self._recovery_in_progress = False
                await asyncio.sleep(30)  # Wait before retrying task
    
    async def _health_monitoring_task(self):
        """Background task for periodic health monitoring.
        
        Validates pool health every 30 seconds and triggers
        recovery if connections are failing.
        """
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self._healthy and not self._closed:
                    try:
                        # Health check: try to create and close a test connection
                        test_connection = await asyncio.wait_for(
                            self._create_connection(), 
                            timeout=5.0
                        )
                        await self._close_connection(test_connection)
                        
                        self._last_health_check = time.time()
                        logger.debug("Pool health check passed")
                        
                    except Exception as e:
                        logger.warning(f"Pool health check failed: {e}")
                        self._healthy = False
                        self._consecutive_failures += 1
                        self._last_failure_time = time.time()
                        self._circuit_breaker.record_failure("HealthCheckFailed")
                        
                        # Trigger recovery attempt
                        logger.info("Triggering pool recovery due to failed health check")
                        
            except asyncio.CancelledError:
                logger.info("Pool health monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in pool health monitoring task: {e}")
                await asyncio.sleep(30)  # Wait before retrying task
    
    async def _get_available_connection(self) -> T:
        """Get an available connection from pool with recovery attempts."""
        if not self._circuit_breaker.can_execute():
            logger.debug("Pool circuit breaker is open - connection blocked")
            raise ServiceError(
                message="Connection pool circuit breaker is open",
                context=ErrorContext.get_all_context()
            )
        
        # If pool is unhealthy, attempt recovery
        if not self._healthy or self._closed:
            logger.info("Pool unhealthy - attempting recovery")
            success = await self._attempt_pool_initialization()
            if not success:
                raise ServiceError(
                    message="Connection pool recovery failed",
                    context=ErrorContext.get_all_context()
                )
        
        try:
            connection = await asyncio.wait_for(self._available_connections.get(), timeout=5.0)
            self._circuit_breaker.record_success()
            return connection
        except asyncio.TimeoutError:
            # Try to create a new connection if pool isn't full
            return await self._create_new_connection()
    
    async def _create_new_connection(self) -> T:
        """Create new connection if pool isn't full."""
        async with self._lock:
            total_connections = len(self._active_connections) + self._available_connections.qsize()
            if total_connections < self._max_size:
                try:
                    connection = await asyncio.wait_for(
                        self._create_connection(), 
                        timeout=10.0
                    )
                    self._circuit_breaker.record_success()
                    return connection
                except Exception as e:
                    self._circuit_breaker.record_failure(str(type(e).__name__))
                    logger.error(f"Failed to create new connection: {e}")
                    raise
            else:
                # Pool is full, wait for available connection
                return await asyncio.wait_for(self._available_connections.get(), timeout=10.0)
    
    def _add_to_active(self, connection: T):
        """Add connection to active set."""
        self._active_connections.add(connection)
    
    def _remove_from_active(self, connection: T):
        """Remove connection from active set."""
        self._active_connections.discard(connection)
    
    async def _return_connection(self, connection: T):
        """Return connection to pool or close if full."""
        if not self._closed and self._healthy:
            try:
                await self._available_connections.put(connection)
            except asyncio.QueueFull:
                # Pool is full, close the connection
                try:
                    await self._close_connection(connection)
                except Exception as e:
                    logger.warning(f"Error closing excess connection: {e}")
        else:
            # Pool is closed or unhealthy, close the connection
            try:
                await self._close_connection(connection)
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[T, None]:
        """Acquire a connection from the pool with automatic recovery."""
        await self._validate_pool_state()
        connection = None
        try:
            connection = await self._acquire_connection()
            yield connection
        finally:
            await self._release_connection(connection)
    
    async def _validate_pool_state(self) -> None:
        """Validate pool state and attempt recovery if needed.
        
        CRITICAL FIX: This method now enables recovery instead of permanent failure!
        Previous: Permanent failure with no recovery path
        Fixed: Automatic recovery with exponential backoff
        """
        if self._closed and not self._recovery_in_progress:
            logger.info("Pool is closed - attempting automatic recovery")
            
            # Attempt immediate recovery
            success = await self._attempt_pool_initialization()
            if not success:
                # If immediate recovery fails, let background task handle it
                if not self._recovery_task or self._recovery_task.done():
                    self._start_background_tasks()
                
                raise ServiceError(
                    message="Connection pool is closed and recovery failed - background recovery in progress",
                    context=ErrorContext.get_all_context()
                )
            
            logger.info("Pool recovery successful - continuing with connection acquisition")
    
    async def _acquire_connection(self) -> T:
        """Acquire connection and add to active set with error handling."""
        try:
            connection = await self._get_available_connection()
            self._add_to_active(connection)
            return connection
        except Exception as e:
            # Record failure but don't permanently disable the pool
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            self._circuit_breaker.record_failure(str(type(e).__name__))
            
            logger.error(f"Failed to acquire connection (attempt {self._consecutive_failures}): {e}")
            
            # Mark as unhealthy to trigger background recovery
            if self._consecutive_failures >= 3:
                self._healthy = False
                logger.warning("Pool marked unhealthy due to consecutive failures")
            
            raise
    
    async def _release_connection(self, connection: T) -> None:
        """Release connection from active set with error handling."""
        if connection:
            try:
                self._remove_from_active(connection)
                await self._return_connection(connection)
            except Exception as e:
                logger.warning(f"Error releasing connection: {e}")
                # Still remove from active set even if return fails
                self._remove_from_active(connection)
    
    async def close(self):
        """Close the connection pool and cleanup background tasks."""
        if self._closed:
            logger.debug("Pool already closed")
            return
        
        logger.info("Closing connection pool...")
        
        # Signal shutdown to background tasks
        self._shutdown_event.set()
        
        # Cancel background tasks
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
        
        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Mark as closed and unhealthy
        self._closed = True
        self._healthy = False
        
        # Close all connections
        await self._clear_all_connections()
        
        # Cleanup circuit breaker
        if hasattr(self._circuit_breaker, 'cleanup'):
            self._circuit_breaker.cleanup()
        
        logger.info("Connection pool closed successfully")
    
    async def force_reopen(self) -> bool:
        """Force pool to reopen with immediate recovery attempt.
        
        CRITICAL RECOVERY METHOD: Enables manual recovery from permanent failure state.
        
        Returns:
            bool: True if recovery successful, False otherwise
        """
        logger.info("Force reopen requested - attempting immediate pool recovery")
        
        # Reset all failure state
        self._closed = False
        self._healthy = False
        self._consecutive_failures = 0
        self._current_retry_delay = self._base_retry_delay
        self._last_failure_time = None
        self._recovery_in_progress = False
        
        # Clear shutdown event in case pool was closed
        self._shutdown_event.clear()
        
        # Attempt fresh initialization
        success = await self._attempt_pool_initialization(is_initial=True)
        
        if success:
            # Start background tasks if they're not running
            self._start_background_tasks()
            self._initialized = True
            logger.info("Force reopen successful - pool is healthy")
        else:
            # Start background tasks anyway for continued recovery attempts
            self._start_background_tasks()
            logger.warning("Force reopen failed - background recovery will continue trying")
        
        return success
    
    async def reset_circuit_breaker(self):
        """Reset the circuit breaker to closed state.
        
        Useful for manual recovery or testing scenarios.
        """
        await self._circuit_breaker.reset()
        logger.info("Pool circuit breaker reset to closed state")
    
    @property
    def active_count(self) -> int:
        """Get number of active connections."""
        return len(self._active_connections)
    
    @property
    def available_count(self) -> int:
        """Get number of available connections."""
        return self._available_connections.qsize()
    
    @property
    def total_count(self) -> int:
        """Get total number of connections."""
        return self.active_count + self.available_count
    
    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed
    
    @property
    def is_healthy(self) -> bool:
        """Check if pool is healthy and operational."""
        return self._healthy and not self._closed
    
    @property
    def is_recovering(self) -> bool:
        """Check if pool is currently in recovery mode."""
        return self._recovery_in_progress
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed pool status including health metrics and circuit breaker state.
        
        Returns:
            Dict containing connection status, health metrics, and recovery state
        """
        now = time.time()
        
        return {
            "healthy": self._healthy,
            "closed": self._closed,
            "initialized": self._initialized,
            "recovering": self._recovery_in_progress,
            "connections": {
                "active": self.active_count,
                "available": self.available_count,
                "total": self.total_count,
                "max_size": self._max_size,
                "min_size": self._min_size
            },
            "recovery": {
                "consecutive_failures": self._consecutive_failures,
                "current_retry_delay": self._current_retry_delay,
                "max_reconnect_attempts": self._max_reconnect_attempts,
                "last_failure_time": self._last_failure_time,
                "time_since_last_failure": (now - self._last_failure_time) if self._last_failure_time else None
            },
            "monitoring": {
                "last_health_check": self._last_health_check,
                "health_check_interval": self._health_check_interval,
                "time_since_health_check": (now - self._last_health_check) if self._last_health_check else None
            },
            "background_tasks": {
                "recovery_task_active": self._recovery_task is not None and not self._recovery_task.done(),
                "health_monitor_active": self._health_monitor_task is not None and not self._health_monitor_task.done(),
                "shutdown_event_set": self._shutdown_event.is_set()
            },
            "circuit_breaker": self._circuit_breaker.get_status()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform immediate health check and return detailed status.
        
        Returns:
            Dict containing health check results and recommendations
        """
        health_status = {
            "timestamp": time.time(),
            "overall_healthy": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check basic pool state
        if self._closed:
            health_status["overall_healthy"] = False
            health_status["issues"].append("Pool is closed")
            health_status["recommendations"].append("Call force_reopen() to recover")
        
        if not self._healthy:
            health_status["overall_healthy"] = False
            health_status["issues"].append("Pool is marked unhealthy")
            health_status["recommendations"].append("Background recovery should address this automatically")
        
        # Check connection counts
        if self.total_count == 0:
            health_status["overall_healthy"] = False
            health_status["issues"].append("No connections available")
            health_status["recommendations"].append("Pool initialization may have failed")
        
        if self.total_count < self._min_size:
            health_status["issues"].append(f"Connection count ({self.total_count}) below minimum ({self._min_size})")
            health_status["recommendations"].append("Pool should create more connections automatically")
        
        # Check circuit breaker state
        if not self._circuit_breaker.can_execute():
            health_status["overall_healthy"] = False
            health_status["issues"].append("Circuit breaker is open")
            health_status["recommendations"].append("Wait for circuit breaker recovery or call reset_circuit_breaker()")
        
        # Check background tasks
        if not (self._recovery_task and not self._recovery_task.done()):
            health_status["issues"].append("Recovery task not running")
            health_status["recommendations"].append("Background recovery may not work")
        
        if not (self._health_monitor_task and not self._health_monitor_task.done()):
            health_status["issues"].append("Health monitor task not running")
            health_status["recommendations"].append("Health monitoring disabled")
        
        # Test connection creation if pool claims to be healthy
        if self._healthy and not self._closed:
            try:
                test_connection = await asyncio.wait_for(
                    self._create_connection(), 
                    timeout=5.0
                )
                await self._close_connection(test_connection)
                health_status["connection_test"] = "PASSED"
            except Exception as e:
                health_status["overall_healthy"] = False
                health_status["connection_test"] = f"FAILED: {str(e)}"
                health_status["issues"].append("Connection creation test failed")
                health_status["recommendations"].append("Pool may need recovery")
        
        # Include full status for diagnostics
        health_status["detailed_status"] = self.get_status()
        
        return health_status