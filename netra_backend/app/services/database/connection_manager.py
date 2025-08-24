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
    pool_size: int = 20  # Increased for production load
    max_overflow: int = 30  # Allow more overflow connections
    pool_timeout: int = 60  # Increased timeout for resilience
    pool_recycle: int = 1800  # 30 minutes - more frequent recycling
    pool_pre_ping: bool = True  # Enable pre-ping for health checking
    pool_reset_on_return: str = "rollback"  # Safe connection reset
    echo: bool = False
    # Circuit breaker settings
    max_retries: int = 3
    retry_delay: float = 0.5
    health_check_interval: int = 30  # seconds


class ConnectionMetrics(BaseModel):
    """Connection metrics and statistics."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    connection_errors: int = 0
    pool_exhaustion_count: int = 0
    circuit_breaker_trips: int = 0
    successful_recoveries: int = 0
    last_connection_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error_message: Optional[str] = None
    last_pool_exhaustion_time: Optional[datetime] = None


class DatabaseConnection:
    """Individual database connection wrapper with circuit breaker."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.metrics = ConnectionMetrics()
        self._connection_lock = asyncio.Lock()
        self._circuit_breaker_count = 0
        self._circuit_breaker_reset_time = None
        self._retry_count = 0
    
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
                
                # Create async engine with enhanced pooling
                self.engine = create_async_engine(
                    url,
                    poolclass=QueuePool,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    pool_pre_ping=self.config.pool_pre_ping,
                    pool_reset_on_return=self.config.pool_reset_on_return,
                    echo=self.config.echo,
                    # Additional resilience settings
                    connect_args={
                        "server_settings": {
                            "application_name": "netra_core",
                            "tcp_keepalives_idle": "600",  # 10 minutes
                            "tcp_keepalives_interval": "30",  # 30 seconds
                            "tcp_keepalives_count": "3",  # 3 probes
                        },
                        "command_timeout": 30,  # Query timeout
                        "prepared_statement_cache_size": 100,
                    }
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
                
                # Update circuit breaker
                self._circuit_breaker_count += 1
                if self._circuit_breaker_count >= self.config.max_retries:
                    self.metrics.circuit_breaker_trips += 1
                    self._circuit_breaker_reset_time = datetime.utcnow()
                    
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
        """Get database session with pool exhaustion handling."""
        if not self.session_factory or self.state != ConnectionState.CONNECTED:
            # Try to reconnect if disconnected
            if self.state == ConnectionState.DISCONNECTED:
                await self.connect()
            if not self.session_factory or self.state != ConnectionState.CONNECTED:
                raise RuntimeError("Database not connected")
        
        try:
            return self.session_factory()
        except Exception as e:
            # Check if this is a pool exhaustion error
            if "pool timeout" in str(e).lower() or "pool limit" in str(e).lower():
                self.metrics.pool_exhaustion_count += 1
                self.metrics.last_pool_exhaustion_time = datetime.utcnow()
            raise
    
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
        """Get connection metrics with enhanced pool information."""
        if self.engine and hasattr(self.engine.pool, 'size'):
            pool = self.engine.pool
            try:
                # Get pool status safely
                status = pool.status()
                self.metrics.active_connections = status.checked_out
                self.metrics.idle_connections = status.checked_in
            except (AttributeError, Exception):
                # Fallback for older SQLAlchemy versions
                try:
                    self.metrics.active_connections = pool.checkedin() if hasattr(pool, 'checkedin') else 0
                    self.metrics.idle_connections = pool.checkedout() if hasattr(pool, 'checkedout') else 0
                except Exception:
                    pass
        
        return self.metrics


class ConnectionManager:
    """Central database connection manager with circuit breaker support."""
    
    def __init__(self):
        self._connections: Dict[str, DatabaseConnection] = {}
        self._default_connection: Optional[str] = None
        self._health_check_interval = 30  # seconds - more frequent health checks
        self._health_check_task: Optional[asyncio.Task] = None
        self._connection_recovery_task: Optional[asyncio.Task] = None
        self._global_circuit_breaker_count = 0
        self._last_global_recovery = None
    
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
        """Health check all connections with circuit breaker support."""
        results = {}
        
        for name, connection in self._connections.items():
            healthy = await connection.health_check()
            results[name] = healthy
            
            # Attempt reconnection if unhealthy and circuit breaker allows
            if not healthy and connection.state == ConnectionState.ERROR:
                # Check circuit breaker
                if connection._circuit_breaker_reset_time:
                    # Circuit breaker is open, check if enough time has passed
                    time_since_trip = datetime.utcnow() - connection._circuit_breaker_reset_time
                    if time_since_trip.total_seconds() < 60:  # 1 minute cooldown
                        continue
                    else:
                        # Reset circuit breaker
                        connection._circuit_breaker_count = 0
                        connection._circuit_breaker_reset_time = None
                
                connection.state = ConnectionState.RECONNECTING
                success = await connection.connect()
                if success:
                    connection.metrics.successful_recoveries += 1
                    self._last_global_recovery = datetime.utcnow()
        
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


def get_connection_monitor() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager


# REMOVED: get_db_session duplicate
# Use netra_backend.app.database.get_db() for single source of truth
# Connection manager should be used directly if specific connection needed


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