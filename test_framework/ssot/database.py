"""
Single Source of Truth (SSOT) Database Test Utility

This module provides the unified DatabaseTestUtility for ALL database test setup
and management across the entire test suite. It eliminates database test duplication.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Ensures consistent database test setup, proper isolation, and reliable cleanup.

CRITICAL: This is the ONLY source for database test utilities in the system.
ALL database tests must use DatabaseTestUtility for setup and management.
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, Union
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Import SSOT environment management
from shared.isolated_environment import get_env

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


class DatabaseTestMetrics:
    """Track database test performance and usage metrics."""
    
    def __init__(self):
        self.connection_time = 0.0
        self.query_count = 0
        self.transaction_count = 0
        self.cleanup_time = 0.0
        self.data_created_count = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def record_connection(self, duration: float):
        """Record database connection timing."""
        self.connection_time = duration
        
    def record_query(self):
        """Record a database query execution."""
        self.query_count += 1
        
    def record_transaction(self):
        """Record a database transaction."""
        self.transaction_count += 1
        
    def record_cleanup(self, duration: float):
        """Record cleanup timing."""
        self.cleanup_time = duration
        
    def record_data_creation(self, count: int = 1):
        """Record test data creation."""
        self.data_created_count += count
        
    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)
        
    def add_warning(self, warning: str):
        """Record a warning."""
        self.warnings.append(warning)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "connection_time": self.connection_time,
            "query_count": self.query_count,
            "transaction_count": self.transaction_count,
            "cleanup_time": self.cleanup_time,
            "data_created_count": self.data_created_count,
            "errors": self.errors,
            "warnings": self.warnings
        }


class DatabaseTestUtility:
    """
    Single Source of Truth (SSOT) utility for ALL database testing needs.
    
    This utility provides:
    - Consistent database connection management
    - Test database isolation and cleanup
    - Transaction management for tests
    - Test data factory methods
    - Performance monitoring
    - Multi-service database support
    
    Features:
    - Automatic test database creation/cleanup
    - Transaction rollback for test isolation
    - Connection pooling management
    - Schema migration support
    - Test data seeding utilities
    - Cross-service database testing
    
    Usage:
        async with DatabaseTestUtility() as db_util:
            session = await db_util.get_test_session()
            user = await db_util.create_test_user(session)
    """
    
    def __init__(self, service: str = "netra_backend", env: Optional[Any] = None):
        """
        Initialize DatabaseTestUtility for a specific service.
        
        Args:
            service: Service name (netra_backend, auth_service, analytics_service)
            env: Environment manager instance
        """
        self.env = env or get_env()
        self.service = service
        self.test_id = f"dbtest_{uuid.uuid4().hex[:8]}"
        self.metrics = DatabaseTestMetrics()
        
        # Database configuration
        self.database_config = self._get_database_config()
        
        # Engine and session management
        self.async_engine = None
        self.sync_engine = None
        self.async_session_factory = None
        self.sync_session_factory = None
        
        # Test state tracking
        self.active_sessions: List[AsyncSession] = []
        self.created_tables: List[str] = []
        self.test_data_ids: Dict[str, List[Any]] = {}
        self.is_initialized = False
        
        logger.debug(f"DatabaseTestUtility initialized for service: {service} [{self.test_id}]")
    
    def _get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for the service."""
        config = {
            "isolation_level": "READ_COMMITTED",
            "pool_size": 1,  # Minimal for tests
            "max_overflow": 0,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "echo": self.env.get("DATABASE_ECHO", "false").lower() == "true",
            "test_db_suffix": "_test"
        }
        
        # Service-specific configurations
        if self.service == "netra_backend":
            config.update({
                "url_env_var": "DATABASE_URL",
                "default_url": "postgresql://postgres:postgres@localhost:5432/netra_test"
            })
        elif self.service == "auth_service":
            config.update({
                "url_env_var": "AUTH_DATABASE_URL", 
                "default_url": "postgresql://postgres:postgres@localhost:5432/auth_test"
            })
        elif self.service == "analytics_service":
            config.update({
                "url_env_var": "CLICKHOUSE_URL",
                "default_url": "clickhouse://localhost:8123/analytics_test"
            })
        else:
            config.update({
                "url_env_var": "DATABASE_URL",
                "default_url": f"postgresql://postgres:postgres@localhost:5432/{self.service}_test"
            })
        
        return config
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize database connections and setup test environment."""
        if self.is_initialized:
            return
            
        start_time = time.time()
        
        try:
            # Get database URL
            db_url = self._get_test_database_url()
            
            # Create engines
            await self._create_engines(db_url)
            
            # Create session factories
            self._create_session_factories()
            
            # Ensure test database exists
            await self._ensure_test_database()
            
            # Run migrations if needed
            await self._run_migrations()
            
            self.is_initialized = True
            self.metrics.record_connection(time.time() - start_time)
            
            logger.info(f"DatabaseTestUtility initialized for {self.service} in {self.metrics.connection_time:.2f}s")
            
        except Exception as e:
            self.metrics.add_error(f"Initialization failed: {str(e)}")
            logger.error(f"Database test utility initialization failed: {e}")
            raise
    
    def _get_test_database_url(self) -> str:
        """Get the test database URL with proper configuration."""
        # Get base URL from environment
        url_env_var = self.database_config["url_env_var"]
        base_url = self.env.get(url_env_var) or self.database_config["default_url"]
        
        # Ensure it's a test database URL
        if "test" not in base_url.lower():
            # Convert to test URL
            if self.service == "analytics_service" and "clickhouse://" in base_url:
                # ClickHouse test database
                base_url = base_url.replace("analytics", "analytics_test")
            else:
                # PostgreSQL test database  
                if "netra" in base_url and "test" not in base_url:
                    base_url = base_url.replace("netra", "netra_test")
                elif self.service in base_url and "test" not in base_url:
                    base_url = base_url.replace(self.service, f"{self.service}_test")
                else:
                    # Add test suffix to database name
                    base_url += self.database_config["test_db_suffix"]
        
        # Add test isolation parameters
        if "postgresql://" in base_url:
            separator = "&" if "?" in base_url else "?"
            base_url += f"{separator}application_name=test_{self.test_id}"
        
        return base_url
    
    async def _create_engines(self, db_url: str):
        """Create database engines for async and sync operations."""
        engine_kwargs = {
            "echo": self.database_config["echo"],
            "pool_size": self.database_config["pool_size"],
            "max_overflow": self.database_config["max_overflow"],
            "pool_timeout": self.database_config["pool_timeout"],
            "pool_recycle": self.database_config["pool_recycle"]
        }
        
        # Create async engine
        if "postgresql://" in db_url:
            async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            self.async_engine = create_async_engine(async_url, **engine_kwargs)
        elif "clickhouse://" in db_url:
            # For ClickHouse testing, we might need a different approach
            self.async_engine = create_async_engine(db_url, **engine_kwargs)
        else:
            self.async_engine = create_async_engine(db_url, **engine_kwargs)
        
        # Create sync engine for migrations and setup
        self.sync_engine = create_engine(db_url.replace("postgresql+asyncpg://", "postgresql://"), **engine_kwargs)
        
        logger.debug(f"Database engines created for {self.service}")
    
    def _create_session_factories(self):
        """Create session factories for async and sync operations."""
        # Async session factory
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        
        # Sync session factory
        self.sync_session_factory = sessionmaker(
            bind=self.sync_engine,
            autoflush=False,
            autocommit=False
        )
        
        logger.debug(f"Session factories created for {self.service}")
    
    async def _ensure_test_database(self):
        """Ensure test database exists and is accessible."""
        try:
            # Test connection
            async with self.async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.debug(f"Test database connection verified for {self.service}")
            
        except Exception as e:
            self.metrics.add_error(f"Database connection failed: {str(e)}")
            logger.error(f"Test database connection failed for {self.service}: {e}")
            
            # Check if we should try to use in-memory SQLite for offline testing
            if self._should_use_fallback_database(e):
                logger.warning(f"Switching to in-memory SQLite fallback for {self.service}")
                await self._setup_fallback_database()
            else:
                raise

    def _should_use_fallback_database(self, error: Exception) -> bool:
        """Check if we should fallback to in-memory SQLite for integration tests."""
        error_str = str(error).lower()
        
        # Only fallback for connection issues, not authentication/permission issues
        fallback_conditions = [
            "connection refused" in error_str,
            "could not connect" in error_str,
            "network unreachable" in error_str,
            "timeout" in error_str and "connection" in error_str,
            "no route to host" in error_str,
        ]
        
        # Don't fallback for auth/permission errors - these should be fixed
        non_fallback_conditions = [
            "authentication failed" in error_str,
            "password authentication failed" in error_str,
            "permission denied" in error_str,
            "access denied" in error_str,
        ]
        
        if any(condition for condition in non_fallback_conditions):
            return False
            
        return any(condition for condition in fallback_conditions)

    async def _setup_fallback_database(self):
        """Setup in-memory SQLite database as fallback."""
        try:
            # Create in-memory SQLite engine
            sqlite_url = "sqlite+aiosqlite:///:memory:"
            
            from sqlalchemy.ext.asyncio import create_async_engine
            self.async_engine = create_async_engine(
                sqlite_url,
                echo=self.database_config["echo"],
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                }
            )
            
            # Update sync engine too
            from sqlalchemy import create_engine
            self.sync_engine = create_engine(
                "sqlite:///:memory:",
                echo=self.database_config["echo"],
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                }
            )
            
            # Recreate session factories
            self._create_session_factories()
            
            # Test the fallback connection
            async with self.async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info(f"Successfully setup in-memory SQLite fallback for {self.service}")
            self.metrics.add_warning("Using in-memory SQLite fallback - some features may be limited")
            
        except Exception as fallback_error:
            logger.error(f"Fallback database setup failed: {fallback_error}")
            raise RuntimeError(f"Both main database and fallback failed: {fallback_error}")from fallback_error
    
    async def _run_migrations(self):
        """Run database migrations if needed."""
        try:
            if self.service == "netra_backend":
                # Import and run netra_backend migrations
                from netra_backend.app.db.database import Base
                async with self.async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                    
            elif self.service == "auth_service":
                # Import and run auth_service migrations
                from auth_service.auth_core.database.models import Base
                async with self.async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                    
            elif self.service == "analytics_service":
                # ClickHouse schema setup would go here
                pass
                
            logger.debug(f"Database migrations completed for {self.service}")
            
        except ImportError as e:
            self.metrics.add_warning(f"Could not import models for {self.service}: {str(e)}")
            logger.warning(f"Could not run migrations for {self.service}: {e}")
        except Exception as e:
            self.metrics.add_error(f"Migration failed: {str(e)}")
            logger.error(f"Database migration failed for {self.service}: {e}")
            raise
    
    async def get_test_session(self) -> AsyncSession:
        """
        Get an async database session for testing with automatic cleanup.
        
        Returns:
            AsyncSession configured for testing
        """
        if not self.is_initialized:
            await self.initialize()
        
        session = self.async_session_factory()
        self.active_sessions.append(session)
        
        logger.debug(f"Created test session for {self.service} [{len(self.active_sessions)} active]")
        return session
    
    def get_sync_test_session(self):
        """Get a sync database session for testing."""
        if not self.is_initialized:
            raise RuntimeError("DatabaseTestUtility not initialized. Use async context manager.")
        
        session = self.sync_session_factory()
        logger.debug(f"Created sync test session for {self.service}")
        return session
    
    @asynccontextmanager
    async def transaction_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database transactions that automatically rollback.
        
        Usage:
            async with db_util.transaction_scope() as session:
                # Database operations here
                # Transaction will be rolled back automatically
        """
        session = await self.get_test_session()
        transaction = None
        
        try:
            # Begin transaction
            transaction = await session.begin()
            self.metrics.record_transaction()
            
            yield session
            
            # Rollback transaction to maintain test isolation
            await transaction.rollback()
            
        except Exception as e:
            if transaction:
                await transaction.rollback()
            self.metrics.add_error(f"Transaction failed: {str(e)}")
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            await session.close()
            if session in self.active_sessions:
                self.active_sessions.remove(session)
    
    @asynccontextmanager
    async def committed_transaction_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for transactions that commit changes.
        
        WARNING: Use sparingly - this commits actual changes to test database.
        Only use when you need persistent data across test methods.
        """
        session = await self.get_test_session()
        
        try:
            yield session
            await session.commit()
            self.metrics.record_transaction()
            
        except Exception as e:
            await session.rollback()
            self.metrics.add_error(f"Committed transaction failed: {str(e)}")
            logger.error(f"Committed transaction failed: {e}")
            raise
        finally:
            await session.close()
            if session in self.active_sessions:
                self.active_sessions.remove(session)
    
    # ========== Test Data Factory Methods ==========
    
    async def create_test_user(self, session: AsyncSession, **kwargs) -> Any:
        """Create a test user with default or custom attributes."""
        try:
            if self.service == "netra_backend":
                # Create netra_backend user - this would normally require a User model
                # For now, return a mock user dict
                user_data = {
                    "id": f"user_{uuid.uuid4().hex[:8]}",
                    "email": kwargs.get("email", f"test_{self.test_id}@example.com"),
                    "username": kwargs.get("username", f"testuser_{self.test_id}"),
                    "created_at": datetime.now(),
                    **kwargs
                }
                
            elif self.service == "auth_service":
                from auth_service.auth_core.database.models import AuthUser
                user_data = AuthUser(
                    email=kwargs.get("email", f"test_{self.test_id}@example.com"),
                    password_hash="test_hash_123",
                    is_verified=kwargs.get("is_verified", True),
                    **{k: v for k, v in kwargs.items() if k not in ['email', 'is_verified']}
                )
                session.add(user_data)
                await session.flush()
                
            else:
                # Generic user data
                user_data = {
                    "id": f"user_{uuid.uuid4().hex[:8]}",
                    "email": kwargs.get("email", f"test_{self.test_id}@example.com"),
                    **kwargs
                }
            
            self.metrics.record_data_creation()
            self._track_created_data("user", getattr(user_data, "id", user_data.get("id")))
            
            logger.debug(f"Created test user for {self.service}")
            return user_data
            
        except Exception as e:
            self.metrics.add_error(f"Test user creation failed: {str(e)}")
            logger.error(f"Failed to create test user: {e}")
            raise
    
    async def create_test_thread(self, session: AsyncSession, user_id: str, **kwargs) -> Any:
        """Create a test thread."""
        try:
            if self.service == "netra_backend":
                from netra_backend.app.db.models_postgres import Thread
                thread_data = Thread(
                    id=kwargs.get("id", f"thread_{uuid.uuid4().hex[:8]}"),
                    created_at=kwargs.get("created_at", int(time.time())),
                    metadata_=kwargs.get("metadata", {"user_id": user_id}),
                    **{k: v for k, v in kwargs.items() if k not in ['id', 'created_at', 'metadata']}
                )
                session.add(thread_data)
                await session.flush()
                
            else:
                # Generic thread data
                thread_data = {
                    "id": f"thread_{uuid.uuid4().hex[:8]}",
                    "user_id": user_id,
                    "created_at": datetime.now(),
                    **kwargs
                }
            
            self.metrics.record_data_creation()
            self._track_created_data("thread", getattr(thread_data, "id", thread_data.get("id")))
            
            logger.debug(f"Created test thread for {self.service}")
            return thread_data
            
        except Exception as e:
            self.metrics.add_error(f"Test thread creation failed: {str(e)}")
            logger.error(f"Failed to create test thread: {e}")
            raise
    
    async def create_test_message(self, session: AsyncSession, thread_id: str, **kwargs) -> Any:
        """Create a test message."""
        try:
            if self.service == "netra_backend":
                from netra_backend.app.db.models_postgres import Message
                message_data = Message(
                    id=kwargs.get("id", f"msg_{uuid.uuid4().hex[:8]}"),
                    thread_id=thread_id,
                    role=kwargs.get("role", "user"),
                    content=kwargs.get("content", [{"type": "text", "text": {"value": "Test message"}}]),
                    created_at=kwargs.get("created_at", int(time.time())),
                    **{k: v for k, v in kwargs.items() if k not in ['id', 'thread_id', 'role', 'content', 'created_at']}
                )
                session.add(message_data)
                await session.flush()
                
            else:
                # Generic message data
                message_data = {
                    "id": f"msg_{uuid.uuid4().hex[:8]}",
                    "thread_id": thread_id,
                    "role": kwargs.get("role", "user"),
                    "content": kwargs.get("content", "Test message"),
                    "created_at": datetime.now(),
                    **kwargs
                }
            
            self.metrics.record_data_creation()
            self._track_created_data("message", getattr(message_data, "id", message_data.get("id")))
            
            logger.debug(f"Created test message for {self.service}")
            return message_data
            
        except Exception as e:
            self.metrics.add_error(f"Test message creation failed: {str(e)}")
            logger.error(f"Failed to create test message: {e}")
            raise
    
    def _track_created_data(self, data_type: str, data_id: Any):
        """Track created test data for cleanup."""
        if data_type not in self.test_data_ids:
            self.test_data_ids[data_type] = []
        self.test_data_ids[data_type].append(data_id)
    
    # ========== Database Query Utilities ==========
    
    async def execute_query(self, session: AsyncSession, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a raw SQL query with parameter binding."""
        try:
            result = await session.execute(text(query), params or {})
            self.metrics.record_query()
            return result
        except Exception as e:
            self.metrics.add_error(f"Query execution failed: {str(e)}")
            logger.error(f"Database query failed: {e}")
            raise
    
    async def count_records(self, session: AsyncSession, table_name: str, where_clause: str = "") -> int:
        """Count records in a table with optional where clause."""
        query = f"SELECT COUNT(*) FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        result = await self.execute_query(session, query)
        count = result.scalar()
        return count or 0
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            if "postgresql" in self.database_config.get("url_env_var", "").lower():
                query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
                """
            else:
                query = f"SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
            
            async with self.get_test_session() as session:
                result = await self.execute_query(session, query, {"table_name": table_name})
                return bool(result.scalar())
                
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False
    
    # ========== Cleanup and Resource Management ==========
    
    async def cleanup_test_data(self):
        """Clean up all test data created during the test session."""
        start_time = time.time()
        cleanup_errors = []
        
        try:
            async with self.get_test_session() as session:
                # Clean up tracked test data in reverse order
                for data_type, ids in reversed(list(self.test_data_ids.items())):
                    for data_id in ids:
                        try:
                            if data_type == "message":
                                await session.execute(text("DELETE FROM messages WHERE id = :id"), {"id": data_id})
                            elif data_type == "thread":
                                await session.execute(text("DELETE FROM threads WHERE id = :id"), {"id": data_id})
                            elif data_type == "user":
                                await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": data_id})
                        except Exception as e:
                            cleanup_errors.append(f"Failed to cleanup {data_type} {data_id}: {str(e)}")
                
                await session.commit()
                
        except Exception as e:
            cleanup_errors.append(f"Test data cleanup failed: {str(e)}")
        
        if cleanup_errors:
            self.metrics.errors.extend(cleanup_errors)
            logger.warning(f"Test data cleanup had errors: {cleanup_errors}")
        
        self.test_data_ids.clear()
        self.metrics.record_cleanup(time.time() - start_time)
        logger.debug(f"Test data cleanup completed in {self.metrics.cleanup_time:.2f}s")
    
    async def cleanup(self):
        """Clean up database connections and resources."""
        start_time = time.time()
        
        try:
            # Close all active sessions
            for session in self.active_sessions[:]:
                try:
                    await session.close()
                except Exception as e:
                    logger.warning(f"Error closing session: {e}")
            
            self.active_sessions.clear()
            
            # Clean up test data
            await self.cleanup_test_data()
            
            # Dispose engines
            if self.async_engine:
                await self.async_engine.dispose()
            
            if self.sync_engine:
                self.sync_engine.dispose()
            
            self.is_initialized = False
            cleanup_time = time.time() - start_time
            
            logger.info(f"DatabaseTestUtility cleanup completed for {self.service} in {cleanup_time:.2f}s")
            
            # Log metrics if there were issues
            if self.metrics.errors or self.metrics.warnings or cleanup_time > 2.0:
                logger.info(f"Database test metrics: {self.metrics.to_dict()}")
                
        except Exception as e:
            logger.error(f"Database test utility cleanup failed: {e}")
    
    # ========== Health and Status ==========
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get database connection health status."""
        status = {
            "service": self.service,
            "test_id": self.test_id,
            "is_initialized": self.is_initialized,
            "active_sessions": len(self.active_sessions),
            "engine_pool_size": None,
            "engine_pool_checked_in": None,
            "engine_pool_checked_out": None,
            "can_connect": False
        }
        
        try:
            if self.async_engine:
                pool = self.async_engine.pool
                status.update({
                    "engine_pool_size": pool.size(),
                    "engine_pool_checked_in": pool.checkedin(),
                    "engine_pool_checked_out": pool.checkedout()
                })
                
                # Test connection
                async with self.async_engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                    status["can_connect"] = True
                    
        except Exception as e:
            status["connection_error"] = str(e)
        
        return status


# ========== Specialized Database Utilities ==========

class PostgreSQLTestUtility(DatabaseTestUtility):
    """Specialized PostgreSQL test utility with PostgreSQL-specific features."""
    
    async def vacuum_analyze(self, table_name: str):
        """Run VACUUM ANALYZE on a table for performance testing."""
        async with self.get_test_session() as session:
            await session.execute(text(f"VACUUM ANALYZE {table_name}"))
    
    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get PostgreSQL table statistics."""
        query = """
        SELECT 
            schemaname,
            tablename,
            attname,
            null_frac,
            avg_width,
            n_distinct,
            most_common_vals,
            most_common_freqs,
            histogram_bounds
        FROM pg_stats 
        WHERE tablename = :table_name
        """
        async with self.get_test_session() as session:
            result = await self.execute_query(session, query, {"table_name": table_name})
            return [dict(row) for row in result.fetchall()]


class ClickHouseTestUtility(DatabaseTestUtility):
    """Specialized ClickHouse test utility for analytics testing."""
    
    async def optimize_table(self, table_name: str):
        """Run OPTIMIZE on a ClickHouse table."""
        async with self.get_test_session() as session:
            await session.execute(text(f"OPTIMIZE TABLE {table_name}"))
    
    async def get_table_parts(self, table_name: str) -> List[Dict[str, Any]]:
        """Get ClickHouse table parts information."""
        query = """
        SELECT 
            partition,
            name,
            active,
            rows,
            bytes_on_disk,
            data_compressed_bytes,
            data_uncompressed_bytes,
            compression_ratio
        FROM system.parts 
        WHERE table = :table_name
        """
        async with self.get_test_session() as session:
            result = await self.execute_query(session, query, {"table_name": table_name})
            return [dict(row) for row in result.fetchall()]


# ========== Factory Functions ==========

def create_database_test_utility(service: str = "netra_backend", env: Optional[Any] = None) -> DatabaseTestUtility:
    """
    Factory function to create the appropriate DatabaseTestUtility.
    
    Args:
        service: Service name
        env: Environment manager
        
    Returns:
        DatabaseTestUtility instance
    """
    if service == "analytics_service":
        return ClickHouseTestUtility(service, env)
    else:
        return PostgreSQLTestUtility(service, env)


# ========== Global Utility Management ==========

_global_db_utilities: Dict[str, DatabaseTestUtility] = {}


async def get_database_test_utility(service: str = "netra_backend") -> DatabaseTestUtility:
    """Get or create global database test utility for a service."""
    if service not in _global_db_utilities:
        _global_db_utilities[service] = create_database_test_utility(service)
        await _global_db_utilities[service].initialize()
    
    return _global_db_utilities[service]


async def cleanup_all_database_utilities():
    """Clean up all global database utilities."""
    for utility in _global_db_utilities.values():
        try:
            await utility.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up database utility: {e}")
    
    _global_db_utilities.clear()


# ========== Legacy Compatibility Layer ==========

class DatabaseTestManager:
    """
    SSOT Database Test Manager - provides backward compatibility for legacy tests.
    
    This class maintains compatibility with existing test imports while providing
    modern database test utilities. It delegates to DatabaseTestUtility internally
    but maintains the legacy interface that existing tests expect.
    
    Business Value: Platform/Internal - Maintains test compatibility while migrating to SSOT
    Ensures existing tests continue working during SSOT migration without breaking changes.
    
    Usage (Legacy Pattern):
        manager = DatabaseTestManager()
        await manager.initialize()
        session = await manager.create_session()
    
    Modern Pattern (Preferred):
        async with DatabaseTestUtility() as db_util:
            session = await db_util.get_test_session()
    """
    
    def __init__(self, service: str = "netra_backend", env: Optional[Any] = None):
        """Initialize DatabaseTestManager with backward compatibility."""
        self._utility = DatabaseTestUtility(service=service, env=env)
        self.engine = None
        self.session = None
        self.connection_pool = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the database manager (legacy interface)."""
        await self._utility.initialize()
        self.engine = self._utility.async_engine
        self.is_initialized = True
        logger.debug("DatabaseTestManager initialized (legacy compatibility)")
        
    async def setup_test_session(self):
        """Setup test database session (legacy interface)."""
        if not self.is_initialized:
            await self.initialize()
        
        # Initialize the database utility if needed
        await self._utility.initialize()
        
        # Store reference for compatibility
        self.engine = self._utility.async_engine
        logger.debug("DatabaseTestManager test session setup completed (legacy compatibility)")
        
    async def create_session(self) -> AsyncSession:
        """Create a database session (legacy interface)."""
        if not self.is_initialized:
            await self.initialize()
        
        session = await self._utility.get_test_session()
        self.session = session  # Store for compatibility
        return session
        
    async def close_session(self, session: Optional[AsyncSession] = None):
        """Close a database session (legacy interface)."""
        if session:
            await session.close()
            if session in self._utility.active_sessions:
                self._utility.active_sessions.remove(session)
        elif self.session:
            await self.session.close()
            if self.session in self._utility.active_sessions:
                self._utility.active_sessions.remove(self.session)
            
    async def execute_query(self, query: str, params: Optional[Dict] = None):
        """Execute a database query (legacy interface)."""
        if not self.session:
            self.session = await self.create_session()
        
        return await self._utility.execute_query(self.session, query, params)
        
    async def cleanup(self):
        """Clean up database resources (legacy interface)."""
        await self._utility.cleanup()
        self.is_initialized = False
        self.engine = None
        self.session = None
        logger.debug("DatabaseTestManager cleanup completed (legacy compatibility)")
        
    def get_connection_string(self) -> str:
        """Get database connection string (legacy interface)."""
        return self._utility._get_test_database_url()
        
    @property
    def health_check(self):
        """Health check method (legacy interface)."""
        async def _health_check():
            status = await self._utility.get_connection_status()
            return {"status": "healthy" if status["can_connect"] else "unhealthy"}
        
        return _health_check
        
    # Delegate additional methods to utility
    async def create_test_user(self, session: Optional[AsyncSession] = None, **kwargs):
        """Create test user (enhanced legacy interface)."""
        if not session:
            session = self.session or await self.create_session()
        return await self._utility.create_test_user(session, **kwargs)
        
    async def create_test_thread(self, user_id: str, session: Optional[AsyncSession] = None, **kwargs):
        """Create test thread (enhanced legacy interface)."""
        if not session:
            session = self.session or await self.create_session()
        return await self._utility.create_test_thread(session, user_id, **kwargs)
        
    async def create_test_message(self, thread_id: str, session: Optional[AsyncSession] = None, **kwargs):
        """Create test message (enhanced legacy interface)."""
        if not session:
            session = self.session or await self.create_session()
        return await self._utility.create_test_message(session, thread_id, **kwargs)


# Legacy alias for backward compatibility
DatabaseTestHelper = DatabaseTestUtility

# Export SSOT database utilities
__all__ = [
    'DatabaseTestUtility',
    'DatabaseTestHelper',   # Legacy alias for DatabaseTestUtility
    'DatabaseTestManager',  # Added for legacy compatibility
    'PostgreSQLTestUtility', 
    'ClickHouseTestUtility',
    'DatabaseTestMetrics',
    'create_database_test_utility',
    'get_database_test_utility',
    'cleanup_all_database_utilities'
]