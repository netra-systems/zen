"""
Database Connection Manager: Centralized database connection management.

This module manages database connections, connection pooling, health monitoring,
and connection lifecycle across PostgreSQL and ClickHouse databases.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure (supports all tiers)
- Business Goal: 99.9% uptime, zero connection-related downtime
- Value Impact: Reliable data access enables all platform features
- Revenue Impact: Prevents $50K+ loss from database-related outages
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool


class DatabaseType(str, Enum):
    """Database type enumeration."""
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    REDIS = "redis"


class ConnectionState(str, Enum):
    """Database connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class DatabaseConfig(BaseModel):
    """Database configuration model."""
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: DatabaseType
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


class ConnectionMetrics(BaseModel):
    """Connection metrics and statistics."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    connection_errors: int = 0
    last_connection_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error_message: Optional[str] = None


class DatabaseConnection:
    """Individual database connection wrapper."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.metrics = ConnectionMetrics()
        self._connection_lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """Establish database connection."""
        async with self._connection_lock:
            try:
                self.state = ConnectionState.CONNECTING
                
                # Build connection URL
                if self.config.db_type == DatabaseType.POSTGRESQL:
                    url = (f"postgresql+asyncpg://{self.config.username}:{self.config.password}@"
                          f"{self.config.host}:{self.config.port}/{self.config.database}")
                elif self.config.db_type == DatabaseType.CLICKHOUSE:
                    url = (f"clickhouse+asynch://{self.config.username}:{self.config.password}@"
                          f"{self.config.host}:{self.config.port}/{self.config.database}")
                else:
                    raise ValueError(f"Unsupported database type: {self.config.db_type}")
                
                # Create async engine
                self.engine = create_async_engine(
                    url,
                    poolclass=QueuePool,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    echo=self.config.echo
                )
                
                # Create session factory
                self.session_factory = sessionmaker(
                    bind=self.engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
                
                # Test connection
                async with self.engine.begin() as conn:
                    await conn.execute("SELECT 1")
                
                self.state = ConnectionState.CONNECTED
                self.metrics.total_connections += 1
                self.metrics.last_connection_time = datetime.utcnow()
                return True
                
            except Exception as e:
                self.state = ConnectionState.ERROR
                self.metrics.connection_errors += 1
                self.metrics.last_error_time = datetime.utcnow()
                self.metrics.last_error_message = str(e)
                return False
    
    async def disconnect(self) -> None:
        """Close database connection."""
        async with self._connection_lock:
            if self.engine:
                await self.engine.dispose()
                self.engine = None
                self.session_factory = None
            
            self.state = ConnectionState.DISCONNECTED
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self.session_factory or self.state != ConnectionState.CONNECTED:
            raise RuntimeError("Database not connected")
        
        return self.session_factory()
    
    async def health_check(self) -> bool:
        """Check connection health."""
        try:
            if not self.engine:
                return False
            
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            return True
        except Exception:
            self.state = ConnectionState.ERROR
            return False
    
    def get_metrics(self) -> ConnectionMetrics:
        """Get connection metrics."""
        if self.engine and hasattr(self.engine.pool, 'size'):
            pool = self.engine.pool
            self.metrics.active_connections = pool.checkedin()
            self.metrics.idle_connections = pool.checkedout()
        
        return self.metrics


class ConnectionManager:
    """Central database connection manager."""
    
    def __init__(self):
        self._connections: Dict[str, DatabaseConnection] = {}
        self._default_connection: Optional[str] = None
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
    
    def add_connection(self, name: str, config: DatabaseConfig, is_default: bool = False) -> None:
        """Add database connection configuration."""
        connection = DatabaseConnection(config)
        self._connections[name] = connection
        
        if is_default or self._default_connection is None:
            self._default_connection = name
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all configured databases."""
        results = {}
        
        for name, connection in self._connections.items():
            success = await connection.connect()
            results[name] = success
        
        # Start health monitoring
        await self._start_health_monitoring()
        
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect from all databases."""
        # Stop health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all connections
        for connection in self._connections.values():
            await connection.disconnect()
    
    def get_connection(self, name: Optional[str] = None) -> Optional[DatabaseConnection]:
        """Get database connection by name or default."""
        if name:
            return self._connections.get(name)
        elif self._default_connection:
            return self._connections.get(self._default_connection)
        return None
    
    @asynccontextmanager
    async def get_session(self, connection_name: Optional[str] = None):
        """Get database session context manager."""
        connection = self.get_connection(connection_name)
        if not connection:
            raise RuntimeError(f"Connection not found: {connection_name or 'default'}")
        
        session = await connection.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Health check all connections."""
        results = {}
        
        for name, connection in self._connections.items():
            healthy = await connection.health_check()
            results[name] = healthy
            
            # Attempt reconnection if unhealthy
            if not healthy and connection.state == ConnectionState.ERROR:
                connection.state = ConnectionState.RECONNECTING
                await connection.connect()
        
        return results
    
    def get_metrics(self) -> Dict[str, ConnectionMetrics]:
        """Get metrics for all connections."""
        return {name: conn.get_metrics() for name, conn in self._connections.items()}
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        if self._health_check_task:
            return
        
        async def monitor():
            while True:
                try:
                    await asyncio.sleep(self._health_check_interval)
                    await self.health_check_all()
                except asyncio.CancelledError:
                    break
                except Exception:
                    # Continue monitoring despite errors
                    pass
        
        self._health_check_task = asyncio.create_task(monitor())
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """List all connections with their status."""
        return [
            {
                "name": name,
                "type": conn.config.db_type.value,
                "host": conn.config.host,
                "port": conn.config.port,
                "database": conn.config.database,
                "state": conn.state.value,
                "metrics": conn.get_metrics()
            }
            for name, conn in self._connections.items()
        ]


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager


async def get_db_session(connection_name: Optional[str] = None):
    """Convenience function to get database session."""
    async with connection_manager.get_session(connection_name) as session:
        yield session


# Common database configurations for easy setup
class DatabaseConfigs:
    """Common database configuration templates."""
    
    @staticmethod
    def postgresql(host: str = "localhost", port: int = 5432, 
                  database: str = "netra", username: str = "postgres", 
                  password: str = "password") -> DatabaseConfig:
        """Create PostgreSQL configuration."""
        return DatabaseConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            db_type=DatabaseType.POSTGRESQL
        )
    
    @staticmethod
    def clickhouse(host: str = "localhost", port: int = 9000,
                  database: str = "netra", username: str = "default",
                  password: str = "") -> DatabaseConfig:
        """Create ClickHouse configuration."""
        return DatabaseConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            db_type=DatabaseType.CLICKHOUSE
        )