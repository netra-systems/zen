"""Database Manager - SSOT for Database Operations

Centralized database management with proper DatabaseURLBuilder integration.
This module uses DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH for URL construction.

CRITICAL: ALL URL manipulation MUST go through DatabaseURLBuilder methods:
- format_url_for_driver() for driver-specific formatting
- normalize_url() for URL normalization
- NO MANUAL STRING REPLACEMENT OPERATIONS ALLOWED

See Also:
- shared/database_url_builder.py - The ONLY source for URL construction
- SPEC/database_connectivity_architecture.xml - Database connection patterns
- docs/configuration_architecture.md - Configuration system overview

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database connection management
- Value Impact: Eliminates URL construction errors and ensures consistency
- Strategic Impact: Single source of truth for all database connection patterns
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text

from netra_backend.app.config import get_config  # SSOT UnifiedConfigManager
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env

# Issue #374: Enhanced database exception handling
from netra_backend.app.db.transaction_errors import (
    DeadlockError, ConnectionError, TransactionError, TimeoutError,
    PermissionError, SchemaError, classify_error, is_retryable_error
)
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError

# Expose specific exception classes for external detection (Issue #374)
DatabaseConnectionError = ConnectionError
DatabaseTimeoutError = TimeoutError
DatabasePermissionError = PermissionError
DatabaseDeadlockError = DeadlockError
DatabaseSchemaError = SchemaError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Centralized database connection and session management."""

    def __init__(self):
        self.config = get_config()
        self._engines: Dict[str, AsyncEngine] = {}
        self._initialized = False
        self._url_builder: Optional[DatabaseURLBuilder] = None

        # Session tracking and pool management
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._session_lifecycle_callbacks: List[Callable] = []
        self._pool_stats = {
            'total_sessions_created': 0,
            'active_sessions_count': 0,
            'sessions_cleaned_up': 0,
            'pool_exhaustion_warnings': 0,
            'context_isolation_violations': 0
        }

    async def initialize(self):
        """Initialize database connections using DatabaseURLBuilder."""
        if self._initialized:
            logger.debug("DatabaseManager already initialized, skipping")
            return

        init_start_time = time.time()
        logger.info("[🔗] Starting DatabaseManager initialization...")

        try:
            # Get database URL using DatabaseURLBuilder as SSOT
            logger.debug("Constructing database URL using DatabaseURLBuilder SSOT")
            database_url = self._get_database_url()

            # EMERGENCY DATABASE CONFIGURATION: Enhanced for golden path test execution
            echo = getattr(self.config, 'database_echo', False)
            pool_size = getattr(self.config, 'database_pool_size', 50)      # EMERGENCY: Doubled from 25 to 50
            max_overflow = getattr(self.config, 'database_max_overflow', 50) # EMERGENCY: Doubled from 25 to 50
            pool_timeout = getattr(self.config, 'database_pool_timeout', 600) # EMERGENCY: 600s timeout for infrastructure pressure

            logger.info(f"[🔧] Database configuration: echo={echo}, pool_size={pool_size}, max_overflow={max_overflow}, timeout={pool_timeout}s")

            # Use appropriate pool class for async engines
            pool_recycle = 900  # EMERGENCY: Reduced from 1800 to 900s (15 min) for high-load scenarios
            application_name = "netra_backend_pool"

            engine_kwargs = {
                "echo": echo,
                "pool_pre_ping": True,
                "pool_recycle": pool_recycle,
                "pool_timeout": pool_timeout,  # Add timeout to prevent hanging
                "connect_args": {
                    "command_timeout": 120,  # Issue #1278: 120 second query timeout for Cloud Run infrastructure delays
                    "server_settings": {
                        "application_name": application_name
                    }
                }
            }

            # Configure pooling for async engines
            if pool_size <= 0 or "sqlite" in database_url.lower():
                # Use NullPool for SQLite or disabled pooling
                engine_kwargs["poolclass"] = NullPool
                # Remove pool_timeout for SQLite as NullPool doesn't support it
                engine_kwargs.pop("pool_timeout", None)
                # Remove connect_args for SQLite as they're PostgreSQL-specific
                engine_kwargs["connect_args"] = {}
                logger.info("[🏊] Using NullPool for SQLite or disabled pooling")
            else:
                # Use AsyncAdaptedQueuePool for better concurrent handling with async engines
                engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
                engine_kwargs["pool_size"] = pool_size
                engine_kwargs["max_overflow"] = max_overflow
                logger.info(f"[🏊] Using AsyncAdaptedQueuePool: pool_size={pool_size}, max_overflow={max_overflow}")

            logger.debug("Creating async database engine...")
            primary_engine = create_async_engine(
                database_url,
                **engine_kwargs
            )

            # Test initial connection with retry logic
            connection_success = await self._test_connection_with_retry(primary_engine)
            if not connection_success:
                raise ConnectionError("Failed to establish database connection after all retry attempts")

            self._engines['primary'] = primary_engine
            self._initialized = True

            init_duration = time.time() - init_start_time
            logger.info(f"✅ DatabaseManager initialized successfully in {init_duration:.3f}s")

        except (ConnectionError, OperationalError) as e:
            # Issue #374: Database connection and operational errors during initialization
            init_duration = time.time() - init_start_time
            classified_error = classify_error(e)
            logger.critical(f"[💥] CRITICAL: Database connection failed during initialization after {init_duration:.3f}s")
            logger.error(f"Database connection error: {type(classified_error).__name__}: {str(classified_error)}")
            logger.error(f"Check database server availability, network connectivity, and credentials")
            logger.error(f"This will prevent all database operations including user data persistence")
            raise classified_error
        except Exception as e:
            # Issue #374: Fallback for unexpected initialization errors
            init_duration = time.time() - init_start_time
            classified_error = classify_error(e)
            logger.critical(f"[💥] CRITICAL: Unexpected database initialization failure after {init_duration:.3f}s")
            logger.error(f"Database initialization error: {type(e).__name__}: {str(e)}")
            raise classified_error

    async def _test_connection_with_retry(self, engine: AsyncEngine, max_retries: int = 3) -> bool:
        """Test database connection with enhanced retry logic for Issue #1278 infrastructure resilience."""
        import random
        # Get infrastructure-aware configuration
        env = get_env()
        environment = env.get("ENVIRONMENT", "development").lower()
        
        # Issue #1278: Infrastructure-aware retry configuration
        if environment in ["staging", "production"]:
            # Cloud environments need more retries and longer timeouts due to VPC/infrastructure delays
            max_retries = max(max_retries, 7)  # Issue #1278: Minimum 7 retries for cloud infrastructure resilience
            base_timeout = 30.0  # Issue #1278: 30 second base timeout for Cloud Run infrastructure delays
            retry_backoff = 2.0  # 2 second exponential backoff
        else:
            base_timeout = 5.0
            retry_backoff = 1.0
        
        # Try to get infrastructure-aware timeout if monitoring is available
        try:
            from netra_backend.app.infrastructure.vpc_connector_monitoring import get_capacity_aware_database_timeout
            infrastructure_timeout = get_capacity_aware_database_timeout(environment, "connection_test") 
            connection_timeout = max(base_timeout, infrastructure_timeout)
            logger.info(f"Using infrastructure-aware connection timeout: {connection_timeout}s for {environment}")
        except Exception:
            connection_timeout = base_timeout
            logger.debug(f"Using default connection timeout: {connection_timeout}s")
        
        # Track timing and success for monitoring
        start_time = time.time()
        
        for attempt in range(max_retries):
            attempt_start = time.time()
            try:
                # Issue #1278: Use asyncio.wait_for for timeout control
                async def test_connection():
                    async with engine.begin() as conn:
                        await conn.execute(text("SELECT 1"))
                
                await asyncio.wait_for(test_connection(), timeout=connection_timeout)
                attempt_duration = time.time() - attempt_start
                
                # Record successful connection attempt for monitoring
                try:
                    from netra_backend.app.core.database_timeout_config import monitor_connection_attempt
                    monitor_connection_attempt(environment, attempt_duration, True)
                except Exception:
                    pass  # Don't fail on monitoring errors
                
                logger.info(f"✅ Database connection test successful on attempt {attempt + 1}/{max_retries} ({environment} environment, {attempt_duration:.2f}s)")
                return True
                
            except asyncio.TimeoutError:
                attempt_duration = time.time() - attempt_start
                logger.warning(f"⏰ Database connection test timed out after {connection_timeout}s on attempt {attempt + 1}/{max_retries}")
                
                # Record failed connection attempt for monitoring
                try:
                    from netra_backend.app.core.database_timeout_config import monitor_connection_attempt
                    monitor_connection_attempt(environment, attempt_duration, False)
                except Exception:
                    pass  # Don't fail on monitoring errors
                
                if attempt < max_retries - 1:
                    # Enhanced exponential backoff with jitter to prevent thundering herd
                    wait_time = retry_backoff * (2 ** attempt)
                    # Add jitter: ±20% random variation
                    jitter = random.uniform(-0.2, 0.2) * wait_time
                    final_wait_time = max(0.1, wait_time + jitter)  # Minimum 100ms wait
                    logger.info(f"Waiting {final_wait_time:.1f}s before retry (infrastructure recovery time with jitter)")
                    await asyncio.sleep(final_wait_time)
                
            except Exception as e:
                attempt_duration = time.time() - attempt_start
                error_type = type(e).__name__
                logger.warning(f"❌ Database connection test failed on attempt {attempt + 1}/{max_retries}: {error_type}: {e}")
                
                # Record failed connection attempt for monitoring
                try:
                    from netra_backend.app.core.database_timeout_config import monitor_connection_attempt
                    monitor_connection_attempt(environment, attempt_duration, False)
                except Exception:
                    pass  # Don't fail on monitoring errors
                
                if attempt < max_retries - 1:
                    # Enhanced exponential backoff with jitter
                    wait_time = retry_backoff * (2 ** attempt)
                    jitter = random.uniform(-0.2, 0.2) * wait_time
                    final_wait_time = max(0.1, wait_time + jitter)
                    await asyncio.sleep(final_wait_time)
                else:
                    logger.error(f"🚨 Database connection test failed after all {max_retries} retry attempts in {environment} environment")
                    return False
        
        return False
    
    def get_engine(self, name: str = 'primary') -> AsyncEngine:
        """Get database engine by name with auto-initialization safety."""
        if not self._initialized:
            # Auto-initialize on first access
            logger.warning("DatabaseManager accessed before initialization - auto-initializing now")
            import asyncio
            try:
                # Try to initialize synchronously if possible
                asyncio.create_task(self.initialize())
                # Give the initialization task a moment to complete
                import time
                time.sleep(0.1)  # Brief pause for initialization

                if not self._initialized:
                    raise RuntimeError(
                        "DatabaseManager auto-initialization failed. "
                        "Ensure proper startup sequence calls await manager.initialize()"
                    )
            except Exception as init_error:
                logger.error(f"Auto-initialization failed: {init_error}")
                raise RuntimeError(
                    f"DatabaseManager not initialized and auto-initialization failed: {init_error}. "
                    "Fix: Call await manager.initialize() in startup sequence."
                ) from init_error

        if name not in self._engines:
            raise ValueError(f"Engine '{name}' not found")

        return self._engines[name]

    @asynccontextmanager
    async def get_session(self, engine_name: str = 'primary', user_context: Optional[Any] = None, operation_type: str = "unknown"):
        """Get async database session with enhanced exception handling and user isolation."""
        session_start_time = time.time()

        # Circuit breaker protection for database operations
        try:
            from netra_backend.app.core.resilience.circuit_breaker import get_circuit_breaker
            database_circuit_breaker = get_circuit_breaker("database")
            
            # Check circuit breaker state before attempting connection
            if database_circuit_breaker and not database_circuit_breaker.can_execute():
                from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError
                raise CircuitBreakerOpenError(
                    f"Database circuit breaker is OPEN for operation: {operation_type}. "
                    f"Database operations are temporarily blocked due to failures. "
                    f"User: {user_id or 'system'}"
                )
        except ImportError:
            # Circuit breaker not available during startup, proceed normally
            database_circuit_breaker = None
        except Exception as cb_error:
            # Log circuit breaker errors but don't fail the operation
            logger.warning(f"Circuit breaker check failed for {operation_type}: {cb_error}")
            database_circuit_breaker = None

        # Extract user information from context for proper isolation
        user_id = None
        context_valid = False
        if user_context:
            try:
                user_id = getattr(user_context, 'user_id', None)
                thread_id = getattr(user_context, 'thread_id', None)
                context_valid = bool(user_id and thread_id)

                if not context_valid:
                    logger.warning(f"Invalid user context for session: user_id={user_id}, thread_id={thread_id}")
                    self._pool_stats['context_isolation_violations'] += 1
            except Exception as e:
                logger.error(f"User context extraction error: {type(e).__name__}: {e}")
                self._pool_stats['context_isolation_violations'] += 1

        session_id = f"sess_{int(session_start_time * 1000)}_{hash(user_id or 'system') % 10000}"

        # Check for pool exhaustion before creating session
        current_active = self._pool_stats['active_sessions_count']
        pool_size = getattr(self.config, 'database_pool_size', 25)
        max_overflow = getattr(self.config, 'database_max_overflow', 25)
        total_capacity = pool_size + max_overflow

        if current_active >= total_capacity * 0.9:  # Warn at 90% capacity
            logger.warning(f"🚨 Database pool near exhaustion: {current_active}/{total_capacity} sessions active")
            self._pool_stats['pool_exhaustion_warnings'] += 1

        logger.debug(f"🔄 Starting database session {session_id} for {operation_type} (user: {user_id or 'system'})")

        # Enhanced initialization safety
        if not self._initialized:
            logger.info(f"[🔧] Auto-initializing DatabaseManager for session access (operation: {operation_type})")
            await self.initialize()

        # Track active session for pool management
        session_metadata = {
            'session_id': session_id,
            'user_id': user_id,
            'user_context': user_context,
            'operation_type': operation_type,
            'start_time': session_start_time,
            'engine_name': engine_name,
            'context_valid': context_valid
        }

        self._active_sessions[session_id] = session_metadata
        self._pool_stats['total_sessions_created'] += 1
        self._pool_stats['active_sessions_count'] += 1

        engine = self.get_engine(engine_name)

        # Circuit breaker monitoring for database operations
        circuit_breaker_start_time = time.time()
        session_success = False

        async with AsyncSession(engine) as session:
            original_exception = None
            transaction_start_time = time.time()
            logger.debug(f"[📝] Transaction started for session {session_id}")

            try:
                yield session

                # Log successful commit
                commit_start_time = time.time()
                await session.commit()
                commit_duration = time.time() - commit_start_time
                session_duration = time.time() - session_start_time

                logger.info(f"✅ Session {session_id} committed successfully - Operation: {operation_type}, "
                           f"User: {user_id or 'system'}, Duration: {session_duration:.3f}s, Commit: {commit_duration:.3f}s")

                # Record successful operation for circuit breaker
                session_success = True

            except (DeadlockError, ConnectionError) as e:
                # Handle specific transaction errors with enhanced context
                original_exception = classify_error(e)
                rollback_start_time = time.time()

                logger.critical(f"[💥] SPECIFIC TRANSACTION FAILURE ({type(original_exception).__name__}) in session {session_id}")
                logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {str(original_exception)}")

                try:
                    await session.rollback()
                    rollback_duration = time.time() - rollback_start_time
                    logger.warning(f"🔄 Rollback completed for session {session_id} in {rollback_duration:.3f}s")
                except Exception as rollback_error:
                    rollback_duration = time.time() - rollback_start_time
                    logger.critical(f"[💥] ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                    logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")

                session_duration = time.time() - session_start_time
                logger.error(f"❌ Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
                raise original_exception

            except Exception as e:
                # Handle general exceptions with enhanced error classification
                original_exception = classify_error(e)
                rollback_start_time = time.time()

                logger.critical(f"[💥] TRANSACTION FAILURE ({type(original_exception).__name__}) in session {session_id}")
                logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {str(original_exception)}")

                try:
                    await session.rollback()
                    rollback_duration = time.time() - rollback_start_time
                    logger.warning(f"🔄 Rollback completed for session {session_id} in {rollback_duration:.3f}s")
                except Exception as rollback_error:
                    rollback_duration = time.time() - rollback_start_time
                    logger.critical(f"[💥] ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                    logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")

                session_duration = time.time() - session_start_time
                logger.error(f"❌ Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
                raise original_exception

            finally:
                close_start_time = time.time()

                # Record circuit breaker metrics
                if database_circuit_breaker:
                    try:
                        operation_duration = time.time() - circuit_breaker_start_time
                        if session_success:
                            await database_circuit_breaker._record_success(operation_duration)
                        else:
                            from netra_backend.app.resilience.circuit_breaker import FailureType
                            if original_exception:
                                failure_type = database_circuit_breaker._classify_failure(original_exception)
                            else:
                                failure_type = FailureType.UNKNOWN_ERROR
                            await database_circuit_breaker._record_failure(failure_type, str(original_exception) if original_exception else "Unknown failure")
                    except Exception as cb_error:
                        logger.warning(f"Circuit breaker recording failed: {cb_error}")

                # Enhanced session cleanup and tracking
                try:
                    await session.close()
                    close_duration = time.time() - close_start_time
                    logger.debug(f"[🔒] Session {session_id} closed in {close_duration:.3f}s")
                except Exception as close_error:
                    close_duration = time.time() - close_start_time
                    logger.error(f"⚠️ Session close failed for {session_id} after {close_duration:.3f}s: {close_error}")

                # Remove session from active tracking and update stats
                try:
                    if session_id in self._active_sessions:
                        session_meta = self._active_sessions.pop(session_id)
                        self._pool_stats['active_sessions_count'] -= 1
                        self._pool_stats['sessions_cleaned_up'] += 1

                        # Call lifecycle callbacks for user context cleanup
                        for callback in self._session_lifecycle_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(session_meta)
                                else:
                                    callback(session_meta)
                            except Exception as callback_error:
                                logger.warning(f"Session lifecycle callback failed: {callback_error}")

                        total_session_time = time.time() - session_start_time
                        logger.debug(f"[🧹] Session {session_id} cleanup complete - Total time: {total_session_time:.3f}s, "
                                   f"User: {user_id or 'system'}, Active sessions: {self._pool_stats['active_sessions_count']}")

                except Exception as cleanup_error:
                    logger.error(f"Session tracking cleanup failed for {session_id}: {cleanup_error}")
                    # Ensure counter is decremented even if cleanup fails
                    self._pool_stats['active_sessions_count'] = max(0, self._pool_stats['active_sessions_count'] - 1)

    async def health_check(self, engine_name: str = 'primary') -> Dict[str, Any]:
        """Perform health check on database connection with comprehensive logging."""
        health_check_start = time.time()
        logger.debug(f"[🏥] Starting database health check for engine: {engine_name}")

        try:
            # Ensure initialization before health check
            if not self._initialized:
                logger.info(f"[🔧] Initializing DatabaseManager for health check (engine: {engine_name})")
                await self.initialize()

            engine = self.get_engine(engine_name)

            # Test connection with timeout
            query_start = time.time()
            async with AsyncSession(engine) as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                health_result = result.fetchone()

            query_duration = time.time() - query_start
            total_duration = time.time() - health_check_start

            logger.info(f"✅ Database health check PASSED for {engine_name} - "
                       f"Query: {query_duration:.3f}s, Total: {total_duration:.3f}s")

            return {
                "status": "healthy",
                "engine": engine_name,
                "connection": "ok",
                "query_duration_ms": round(query_duration * 1000, 2),
                "total_duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }

        except Exception as e:
            total_duration = time.time() - health_check_start
            classified_error = classify_error(e)

            logger.critical(f"[💥] Database health check FAILED for {engine_name} after {total_duration:.3f}s")
            logger.error(f"Health check error details: {type(classified_error).__name__}: {str(classified_error)}")

            return {
                "status": "unhealthy",
                "engine": engine_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current database pool statistics."""
        pool_size = getattr(self.config, 'database_pool_size', 25)
        max_overflow = getattr(self.config, 'database_max_overflow', 25)
        total_capacity = pool_size + max_overflow

        return {
            **self._pool_stats,
            'pool_configuration': {
                'pool_size': pool_size,
                'max_overflow': max_overflow,
                'total_capacity': total_capacity
            },
            'pool_utilization': {
                'utilization_percent': round((self._pool_stats['active_sessions_count'] / total_capacity) * 100, 2),
                'sessions_remaining': total_capacity - self._pool_stats['active_sessions_count']
            },
            'active_sessions_by_user': self._get_sessions_by_user(),
            'health_status': self._assess_pool_health()
        }

    def _get_sessions_by_user(self) -> Dict[str, int]:
        """Get count of active sessions per user."""
        user_counts = {}
        for metadata in self._active_sessions.values():
            user_id = metadata.get('user_id', 'unknown')
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts

    def _assess_pool_health(self) -> Dict[str, Any]:
        """Assess current pool health status."""
        pool_size = getattr(self.config, 'database_pool_size', 25)
        max_overflow = getattr(self.config, 'database_max_overflow', 25)
        total_capacity = pool_size + max_overflow
        
        current_active = self._pool_stats['active_sessions_count']
        utilization_percent = (current_active / total_capacity) * 100
        
        # Assess health based on utilization and error rates
        if utilization_percent > 90:
            health_status = "critical"
            health_message = f"Pool utilization critical: {utilization_percent:.1f}%"
        elif utilization_percent > 75:
            health_status = "warning"
            health_message = f"Pool utilization high: {utilization_percent:.1f}%"
        elif self._pool_stats['pool_exhaustion_warnings'] > 0:
            health_status = "warning"
            health_message = f"Pool exhaustion warnings: {self._pool_stats['pool_exhaustion_warnings']}"
        elif self._pool_stats['context_isolation_violations'] > 0:
            health_status = "warning"
            health_message = f"Context isolation violations: {self._pool_stats['context_isolation_violations']}"
        else:
            health_status = "healthy"
            health_message = f"Pool operating normally: {utilization_percent:.1f}% utilization"
        
        return {
            "status": health_status,
            "message": health_message,
            "utilization_percent": utilization_percent,
            "requires_attention": health_status != "healthy"
        }

    def log_pool_metrics(self, detailed: bool = False) -> None:
        """Log current pool metrics for monitoring and debugging."""
        stats = self.get_pool_stats()
        health = stats['health_status']
        
        # Always log basic health status
        logger.info(
            f"[📊] Database Pool Status: {health['status'].upper()} - {health['message']}"
        )
        
        if detailed or health['requires_attention']:
            # Log detailed metrics when requested or when attention is needed
            pool_config = stats['pool_configuration']
            utilization = stats['pool_utilization']
            
            logger.info(
                f"[📊] Pool Configuration: size={pool_config['pool_size']}, "
                f"overflow={pool_config['max_overflow']}, total={pool_config['total_capacity']}"
            )
            logger.info(
                f"[📊] Pool Utilization: {utilization['utilization_percent']}% "
                f"({self._pool_stats['active_sessions_count']}/{pool_config['total_capacity']} sessions), "
                f"{utilization['sessions_remaining']} remaining"
            )
            logger.info(
                f"[📊] Pool Lifetime Stats: created={self._pool_stats['total_sessions_created']}, "
                f"cleaned={self._pool_stats['sessions_cleaned_up']}, "
                f"warnings={self._pool_stats['pool_exhaustion_warnings']}"
            )
            
            # Log per-user session counts if there are active sessions
            user_sessions = stats['active_sessions_by_user']
            if user_sessions:
                user_breakdown = ", ".join([f"{user}:{count}" for user, count in user_sessions.items()])
                logger.info(f"[📊] Active Sessions by User: {user_breakdown}")

    async def handle_connection_failure(self, operation_type: str, error: Exception, user_context: Optional[Any] = None) -> bool:
        """Handle connection failures with graceful degradation strategies.
        
        Args:
            operation_type: Type of operation that failed
            error: The connection error that occurred
            user_context: User context for the failed operation
            
        Returns:
            bool: True if graceful degradation is possible, False if critical failure
        """
        user_id = getattr(user_context, 'user_id', 'system') if user_context else 'system'
        
        logger.error(f"[💥] Database connection failure for {operation_type} (user: {user_id}): {error}")
        
        # Determine if this is a recoverable failure
        error_str = str(error).lower()
        is_timeout = any(keyword in error_str for keyword in ['timeout', 'timed out'])
        is_connection_limit = any(keyword in error_str for keyword in ['connection', 'pool', 'exhausted'])
        is_network_issue = any(keyword in error_str for keyword in ['network', 'unreachable', 'refused'])
        
        graceful_degradation_possible = False
        degradation_strategy = None
        
        if is_timeout:
            # Timeout errors - can often retry with increased timeout
            degradation_strategy = "timeout_retry"
            graceful_degradation_possible = True
            logger.warning(f"[🔄] Timeout failure for {operation_type} - retry with extended timeout recommended")
            
        elif is_connection_limit:
            # Connection pool exhaustion - can implement queuing or delay
            degradation_strategy = "pool_backoff"
            graceful_degradation_possible = True
            logger.warning(f"[⏳] Pool exhaustion for {operation_type} - implementing backoff strategy")
            
        elif is_network_issue:
            # Network issues - might be temporary, can retry
            degradation_strategy = "network_retry"
            graceful_degradation_possible = True
            logger.warning(f"[🌐] Network issue for {operation_type} - network retry recommended")
            
        else:
            # Unknown or critical errors
            degradation_strategy = "critical_failure"
            graceful_degradation_possible = False
            logger.critical(f"[🚨] Critical database failure for {operation_type} - no graceful degradation available")
        
        # Update circuit breaker if available
        try:
            from netra_backend.app.core.resilience.circuit_breaker import get_circuit_breaker
            database_circuit_breaker = get_circuit_breaker("database")
            if database_circuit_breaker:
                # Record the failure for circuit breaker tracking
                database_circuit_breaker.record_failure(f"{operation_type}_{degradation_strategy}")
        except Exception:
            pass  # Don't fail on circuit breaker recording errors
        
        # Log degradation decision
        if graceful_degradation_possible:
            logger.info(f"[🛡️] Graceful degradation available for {operation_type}: {degradation_strategy}")
        else:
            logger.error(f"[💥] No graceful degradation possible for {operation_type} - service impact expected")
        
        return graceful_degradation_possible

    async def warmup_connection_pool(self, engine_name: str = 'primary', warmup_connections: Optional[int] = None) -> Dict[str, Any]:
        """Warmup connection pool by pre-establishing connections to reduce cold start delays.
        
        This helps avoid the initial connection setup delays when the first requests come in,
        especially important for staging/production environments with VPC connectors.
        
        Args:
            engine_name: Name of the engine to warmup
            warmup_connections: Number of connections to pre-establish (defaults to pool_size/2)
            
        Returns:
            Dictionary with warmup statistics
        """
        warmup_start = time.time()
        logger.info(f"[🔥] Starting connection pool warmup for engine: {engine_name}")
        
        try:
            # Ensure initialization before warmup
            if not self._initialized:
                logger.info(f"[🔧] Initializing DatabaseManager for pool warmup (engine: {engine_name})")
                await self.initialize()
            
            engine = self.get_engine(engine_name)
            
            # Determine number of connections to warmup
            pool_size = getattr(self.config, 'database_pool_size', 25)
            if warmup_connections is None:
                warmup_connections = max(1, pool_size // 2)  # Warmup half the pool by default
            
            logger.info(f"[🔥] Warming up {warmup_connections} connections (pool size: {pool_size})")
            
            warmup_stats = {
                "target_connections": warmup_connections,
                "successful_connections": 0,
                "failed_connections": 0,
                "total_warmup_time": 0.0,
                "average_connection_time": 0.0,
                "min_connection_time": float('inf'),
                "max_connection_time": 0.0
            }
            
            # Create and test connections
            connection_times = []
            successful_sessions = []
            
            for i in range(warmup_connections):
                connection_start = time.time()
                try:
                    # Create a brief test session to establish the connection
                    async with AsyncSession(engine) as session:
                        # Simple query to ensure connection is fully established
                        result = await session.execute(text("SELECT 1 as warmup_test"))
                        test_result = result.fetchone()
                        
                        if test_result and test_result[0] == 1:
                            connection_time = time.time() - connection_start
                            connection_times.append(connection_time)
                            warmup_stats["successful_connections"] += 1
                            
                            # Update timing statistics
                            if connection_time < warmup_stats["min_connection_time"]:
                                warmup_stats["min_connection_time"] = connection_time
                            if connection_time > warmup_stats["max_connection_time"]:
                                warmup_stats["max_connection_time"] = connection_time
                            
                            logger.debug(f"[🔥] Warmup connection {i+1}/{warmup_connections} established in {connection_time:.3f}s")
                        else:
                            warmup_stats["failed_connections"] += 1
                            logger.warning(f"[🔥] Warmup connection {i+1}/{warmup_connections} test query failed")
                            
                except Exception as e:
                    connection_time = time.time() - connection_start
                    warmup_stats["failed_connections"] += 1
                    logger.warning(f"[🔥] Warmup connection {i+1}/{warmup_connections} failed after {connection_time:.3f}s: {e}")
            
            # Calculate final statistics
            total_warmup_time = time.time() - warmup_start
            warmup_stats["total_warmup_time"] = total_warmup_time
            
            if connection_times:
                warmup_stats["average_connection_time"] = sum(connection_times) / len(connection_times)
            else:
                warmup_stats["min_connection_time"] = 0.0
            
            success_rate = (warmup_stats["successful_connections"] / warmup_connections) * 100
            
            if warmup_stats["successful_connections"] > 0:
                logger.info(
                    f"✅ Connection pool warmup completed for {engine_name} - "
                    f"{warmup_stats['successful_connections']}/{warmup_connections} connections "
                    f"({success_rate:.1f}% success rate) in {total_warmup_time:.3f}s"
                )
                logger.info(
                    f"[📊] Warmup timing: avg={warmup_stats['average_connection_time']:.3f}s, "
                    f"min={warmup_stats['min_connection_time']:.3f}s, "
                    f"max={warmup_stats['max_connection_time']:.3f}s"
                )
            else:
                logger.error(
                    f"❌ Connection pool warmup failed for {engine_name} - "
                    f"0/{warmup_connections} connections established"
                )
            
            return warmup_stats
            
        except Exception as e:
            total_warmup_time = time.time() - warmup_start
            logger.error(f"❌ Connection pool warmup failed for {engine_name} after {total_warmup_time:.3f}s: {e}")
            
            return {
                "target_connections": warmup_connections or 0,
                "successful_connections": 0,
                "failed_connections": warmup_connections or 0,
                "total_warmup_time": total_warmup_time,
                "error": str(e)
            }

    async def close_all(self):
        """Close all database engines with comprehensive logging."""
        if not self._engines:
            logger.debug("No database engines to close")
            return

        logger.info(f"[🔒] Closing {len(self._engines)} database engines...")

        for name, engine in self._engines.items():
            close_start = time.time()
            try:
                await engine.dispose()
                close_duration = time.time() - close_start
                logger.info(f"✅ Closed database engine '{name}' in {close_duration:.3f}s")
            except Exception as e:
                close_duration = time.time() - close_start
                logger.error(f"❌ Error closing engine '{name}' after {close_duration:.3f}s: {e}")

        engines_count = len(self._engines)
        self._engines.clear()
        self._initialized = False
        logger.info(f"[🔒] DatabaseManager shutdown complete - {engines_count} engines closed")

    def _get_database_url(self) -> str:
        """Get database URL using DatabaseURLBuilder as SSOT."""
        env = get_env()

        # Create DatabaseURLBuilder instance if not exists
        if not self._url_builder:
            self._url_builder = DatabaseURLBuilder(env.as_dict())

        # Get URL for current environment
        database_url = self._url_builder.get_url_for_environment(sync=False)

        if not database_url:
            # Let the config handle the fallback if needed
            database_url = self.config.database_url
            if not database_url:
                raise ValueError(
                    "DatabaseURLBuilder failed to construct URL and no config fallback available. "
                    "Ensure proper POSTGRES_* environment variables are set."
                )

        # Use DatabaseURLBuilder to format URL for asyncpg driver
        database_url = self._url_builder.format_url_for_driver(database_url, 'asyncpg')

        # Log safe connection info
        logger.info(self._url_builder.get_safe_log_message())

        return database_url

    async def _test_connection_with_retry(self, engine: AsyncEngine, max_retries: int = 3, timeout: float = 10.0) -> bool:
        """Test database connection with retry logic."""
        for attempt in range(max_retries):
            attempt_start = time.time()
            try:
                logger.info(f"Testing database connection (attempt {attempt + 1}/{max_retries})")

                # Test connection with timeout
                async with AsyncSession(engine) as test_session:
                    result = await asyncio.wait_for(
                        test_session.execute(text("SELECT 1")),
                        timeout=timeout
                    )
                    test_result = result.fetchone()

                    if test_result and test_result[0] == 1:
                        attempt_duration = time.time() - attempt_start
                        logger.info(f"✅ Database connection test successful in {attempt_duration:.3f}s (attempt {attempt + 1})")
                        return True

            except asyncio.TimeoutError:
                attempt_duration = time.time() - attempt_start
                logger.error(f"❌ Database connection timeout after {attempt_duration:.3f}s (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                attempt_duration = time.time() - attempt_start
                logger.error(f"❌ Database connection error after {attempt_duration:.3f}s (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        logger.error(f"Database connection failed after {max_retries} attempts")
        return False

    @classmethod
    @asynccontextmanager
    async def get_async_session(cls, name: str = 'primary', user_id: Optional[str] = None, operation_type: str = "legacy_access"):
        """Class method for backward compatibility with code expecting DatabaseManager.get_async_session()."""
        logger.debug(f"[📞] Legacy database session access: {operation_type} (user: {user_id or 'system'})")

        manager = get_database_manager()
        if not manager._initialized:
            logger.info(f"[🔧] Ensuring DatabaseManager initialization for class method access ({operation_type})")
            await manager.initialize()

        async with manager.get_session(name, user_context=user_id, operation_type=operation_type) as session:
            yield session

    @staticmethod
    def create_application_engine() -> AsyncEngine:
        """Create a new application engine for health checks."""
        config = get_config()
        env = get_env()
        builder = DatabaseURLBuilder(env.as_dict())

        # Get URL from builder
        database_url = builder.get_url_for_environment(sync=False)
        if not database_url:
            database_url = config.database_url

        # Use DatabaseURLBuilder to format URL for asyncpg driver
        database_url = builder.format_url_for_driver(database_url, 'asyncpg')

        return create_async_engine(
            database_url,
            echo=False,
            poolclass=NullPool,
            pool_pre_ping=True,
            pool_recycle=3600,
        )


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance with auto-initialization."""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
        # Auto-initialize using async pattern
        try:
            import asyncio
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.debug("No event loop available for immediate DatabaseManager initialization")

            if loop is not None:
                try:
                    asyncio.create_task(_database_manager.initialize())
                    logger.debug("Scheduled DatabaseManager initialization as async task")
                except Exception as init_error:
                    logger.warning(f"Could not schedule immediate initialization: {init_error}")
        except Exception as e:
            logger.warning(f"Auto-initialization setup failed, will initialize on first use: {e}")

    return _database_manager


@asynccontextmanager
async def get_db_session(engine_name: str = 'primary'):
    """Helper to get database session."""
    manager = get_database_manager()
    async with manager.get_session(engine_name) as session:
        yield session