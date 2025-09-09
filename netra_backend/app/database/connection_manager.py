"""
Database Connection Manager - SSOT Implementation

This module provides centralized database connection management for the Netra platform.
Following SSOT principles, this is the canonical implementation for database connections.

Business Value: Platform/Internal - System Stability & Performance
Ensures reliable database connections and proper connection pooling across all services.

CRITICAL: This is a minimal SSOT-compliant stub to resolve import errors.
Full implementation should follow CLAUDE.md SSOT patterns.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Optional, Any, AsyncGenerator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for database connections."""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class ConnectionHealth:
    """Health status of database connections."""
    is_healthy: bool
    active_connections: int
    pool_size: int
    checked_out: int
    overflow: int
    error_message: Optional[str] = None


class DatabaseConnectionManager:
    """
    SSOT Database Connection Manager.
    
    This is the canonical implementation for all database connection management
    across the platform.
    """
    
    def __init__(self):
        """Initialize connection manager with SSOT environment."""
        self._env = get_env()
        self._engines: Dict[str, AsyncEngine] = {}
        self._session_factories: Dict[str, sessionmaker] = {}
        self._is_initialized = False
        
        # Default connection configuration
        self._default_config = self._load_default_config()
    
    def _load_default_config(self) -> ConnectionConfig:
        """Load default database configuration from environment."""
        return ConnectionConfig(
            host=self._env.get("DATABASE_HOST", "localhost"),
            port=int(self._env.get("DATABASE_PORT", "5432")),
            database=self._env.get("DATABASE_NAME", "netra"),
            username=self._env.get("DATABASE_USER", "postgres"),
            password=self._env.get("DATABASE_PASSWORD", ""),
            pool_size=int(self._env.get("DATABASE_POOL_SIZE", "10")),
            max_overflow=int(self._env.get("DATABASE_MAX_OVERFLOW", "20")),
            pool_timeout=int(self._env.get("DATABASE_POOL_TIMEOUT", "30")),
            pool_recycle=int(self._env.get("DATABASE_POOL_RECYCLE", "3600")),
            echo=self._env.get("DATABASE_ECHO", "false").lower() == "true"
        )
    
    async def initialize(self, config: Optional[ConnectionConfig] = None) -> None:
        """
        Initialize the connection manager.
        
        Args:
            config: Database configuration (uses default if not provided)
        """
        if self._is_initialized:
            logger.warning("Database connection manager already initialized")
            return
        
        config = config or self._default_config
        
        try:
            # Create primary engine
            engine = await self._create_engine(config)
            self._engines["primary"] = engine
            
            # Create session factory
            session_factory = sessionmaker(
                engine, 
                class_=AsyncSession, 
                expire_on_commit=False
            )
            self._session_factories["primary"] = session_factory
            
            self._is_initialized = True
            logger.info("Database connection manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection manager: {e}")
            raise
    
    async def _create_engine(self, config: ConnectionConfig) -> AsyncEngine:
        """Create an async database engine."""
        database_url = (
            f"postgresql+asyncpg://{config.username}:{config.password}"
            f"@{config.host}:{config.port}/{config.database}"
        )
        
        engine = create_async_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            echo=config.echo,
            future=True
        )
        
        return engine
    
    async def get_engine(self, name: str = "primary") -> AsyncEngine:
        """
        Get a database engine by name.
        
        Args:
            name: Engine name
            
        Returns:
            Database engine
        """
        if not self._is_initialized:
            await self.initialize()
        
        if name not in self._engines:
            raise ValueError(f"Engine '{name}' not found")
        
        return self._engines[name]
    
    @asynccontextmanager
    async def get_session(self, name: str = "primary") -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session context manager.
        
        Args:
            name: Session factory name
            
        Yields:
            Database session
        """
        if not self._is_initialized:
            await self.initialize()
        
        if name not in self._session_factories:
            raise ValueError(f"Session factory '{name}' not found")
        
        session_factory = self._session_factories[name]
        session = session_factory()
        
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def check_health(self, name: str = "primary") -> ConnectionHealth:
        """
        Check health of database connections.
        
        Args:
            name: Engine name to check
            
        Returns:
            Connection health status
        """
        try:
            if not self._is_initialized:
                return ConnectionHealth(
                    is_healthy=False,
                    active_connections=0,
                    pool_size=0,
                    checked_out=0,
                    overflow=0,
                    error_message="Connection manager not initialized"
                )
            
            if name not in self._engines:
                return ConnectionHealth(
                    is_healthy=False,
                    active_connections=0,
                    pool_size=0,
                    checked_out=0,
                    overflow=0,
                    error_message=f"Engine '{name}' not found"
                )
            
            engine = self._engines[name]
            pool = engine.pool
            
            # Basic health check - try to get connection info
            return ConnectionHealth(
                is_healthy=True,
                active_connections=pool.checkedout(),
                pool_size=pool.size(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Health check failed for engine '{name}': {e}")
            return ConnectionHealth(
                is_healthy=False,
                active_connections=0,
                pool_size=0,
                checked_out=0,
                overflow=0,
                error_message=str(e)
            )
    
    async def close(self, name: Optional[str] = None) -> None:
        """
        Close database connections.
        
        Args:
            name: Engine name to close (closes all if None)
        """
        if name:
            if name in self._engines:
                await self._engines[name].dispose()
                del self._engines[name]
                if name in self._session_factories:
                    del self._session_factories[name]
                logger.info(f"Closed database engine '{name}'")
        else:
            # Close all engines
            for engine_name, engine in self._engines.items():
                await engine.dispose()
                logger.info(f"Closed database engine '{engine_name}'")
            
            self._engines.clear()
            self._session_factories.clear()
            self._is_initialized = False
            logger.info("Closed all database connections")


# Global connection manager instance (SSOT)
_connection_manager: Optional[DatabaseConnectionManager] = None


def get_connection_manager() -> DatabaseConnectionManager:
    """
    Get the global database connection manager instance.
    
    Returns:
        Database connection manager
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = DatabaseConnectionManager()
    return _connection_manager


# SSOT Factory Function
def create_connection_manager() -> DatabaseConnectionManager:
    """
    SSOT factory function for creating connection manager instances.
    
    Returns:
        New connection manager instance
    """
    return DatabaseConnectionManager()


# Export SSOT interface
__all__ = [
    "DatabaseConnectionManager",
    "ConnectionConfig",
    "ConnectionHealth",
    "get_connection_manager",
    "create_connection_manager"
]