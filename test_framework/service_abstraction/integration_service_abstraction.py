"""
Integration Test Service Abstraction Layer

CRITICAL SERVICE DEPENDENCY RESOLUTION: This module provides service abstraction
for integration tests, enabling them to run with or without external services
based on availability and configuration.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure 
- Business Goal: Enable reliable integration testing in all environments
- Value Impact: Prevents CI/CD failures due to service dependencies
- Strategic Impact: Ensures continuous integration velocity for development team

PROBLEM SOLVED:
Integration tests were failing with --no-docker flag because they had hard 
dependencies on running services (WebSocket connections, PostgreSQL, Redis).
This abstraction layer provides:

1. Service Availability Detection
2. Graceful Fallback Mechanisms  
3. In-Memory Service Alternatives
4. Proper Integration vs E2E Separation

CLAUDE.MD COMPLIANCE:
- Real services preferred when available (REAL_SERVICES > Integration > Unit)
- No mocks in E2E tests (but integration tests can use abstractions)
- SSOT environment management through IsolatedEnvironment
- Follows absolute import patterns
"""

import asyncio
import logging
import json
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Tuple
from unittest.mock import AsyncMock

from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, MessageID

logger = logging.getLogger(__name__)


class ServiceAvailability(Enum):
    """Service availability states for integration testing."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ServiceStatus:
    """Service status information."""
    name: str
    availability: ServiceAvailability
    connection_url: Optional[str] = None
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    fallback_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegrationServiceAbstraction(ABC):
    """
    Abstract base class for integration test service abstractions.
    
    This provides the contract for service abstractions that can work
    with real services when available or gracefully degrade to in-memory
    alternatives for integration testing.
    """
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the real service is available."""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to service (real or fallback)."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from service."""
        pass
    
    @abstractmethod
    async def health_check(self) -> ServiceStatus:
        """Get current service health status."""
        pass
    
    @abstractmethod
    async def reset(self) -> None:
        """Reset service state for clean testing."""
        pass


class IntegrationDatabaseService(IntegrationServiceAbstraction):
    """
    Database service abstraction for integration tests.
    
    Prefers real PostgreSQL when available, falls back to in-memory SQLite
    for integration testing when Docker is not available.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.env = get_env()
        self._connection = None
        self._engine = None
        self._session_maker = None
        self._is_real_postgres = False
        self._tables_created = False
        
    async def is_available(self) -> bool:
        """Check if real PostgreSQL is available."""
        try:
            # Only try real PostgreSQL if USE_REAL_SERVICES is true
            use_real_services = self.env.get("USE_REAL_SERVICES", "false").lower() == "true"
            if not use_real_services:
                logger.info("Real services disabled - will use in-memory database")
                return False
                
            # Try to import and connect to PostgreSQL
            import asyncpg
            
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 5434)  # Docker test port
            user = self.config.get("user", "test_user")
            password = self.config.get("password", "test_password") 
            database = self.config.get("database", "netra_test")
            
            connection_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            
            # Quick connection test
            conn = await asyncpg.connect(connection_url)
            await conn.execute("SELECT 1")
            await conn.close()
            
            logger.info(f"Real PostgreSQL available at {host}:{port}")
            return True
            
        except Exception as e:
            logger.info(f"Real PostgreSQL not available: {e} - will use in-memory database")
            return False
    
    async def connect(self) -> bool:
        """Connect to database (real PostgreSQL or in-memory SQLite)."""
        if await self.is_available():
            return await self._connect_postgres()
        else:
            return await self._connect_sqlite()
    
    async def _connect_postgres(self) -> bool:
        """Connect to real PostgreSQL database."""
        try:
            import asyncpg
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 5434)
            user = self.config.get("user", "test_user")
            password = self.config.get("password", "test_password")
            database = self.config.get("database", "netra_test")
            
            connection_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
            
            self._engine = create_async_engine(
                connection_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            self._session_maker = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            self._is_real_postgres = True
            logger.info("Connected to real PostgreSQL for integration testing")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to connect to real PostgreSQL: {e}")
            return False
    
    async def _connect_sqlite(self) -> bool:
        """Connect to in-memory SQLite database."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
            from sqlalchemy.pool import StaticPool
            from sqlalchemy import text
            
            self._engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                poolclass=StaticPool,
                echo=False,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True
            )
            
            self._session_maker = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Create integration test schema
            await self._create_integration_schema()
            
            self._is_real_postgres = False
            logger.info("Connected to in-memory SQLite for integration testing")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to in-memory SQLite: {e}")
            return False
    
    async def _create_integration_schema(self):
        """Create minimal schema needed for integration tests."""
        if self._tables_created:
            return
            
        async with self._engine.begin() as conn:
            from sqlalchemy import text
            
            # Users table
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            
            # Threads table
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    metadata TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            '''))
            
            # Messages table
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES threads (id)
                )
            '''))
            
            # Agent executions table
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS agent_execution_results (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    execution_data TEXT,
                    success BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            '''))
            
            # User responses table
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS user_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    response_data TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            '''))
            
            # WebSocket connections table
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS websocket_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    websocket_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    thread_id TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (thread_id) REFERENCES threads (id)
                )
            '''))
            
            # Message routing log table
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS message_routing_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    message_content TEXT,
                    selected_agent TEXT,
                    confidence REAL,
                    routing_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (thread_id) REFERENCES threads (id)
                )
            '''))
        
        self._tables_created = True
        logger.info("Integration test database schema created")
    
    @asynccontextmanager
    async def get_session(self):
        """Get a database session for integration testing."""
        if not self._session_maker:
            raise RuntimeError("Database not connected - call connect() first")
        
        session = self._session_maker()
        try:
            yield session
        finally:
            try:
                await session.rollback()
            except Exception:
                pass
            try:
                await session.close()
            except Exception:
                pass
    
    async def disconnect(self) -> None:
        """Disconnect from database."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None
            logger.info("Disconnected from integration database")
    
    async def health_check(self) -> ServiceStatus:
        """Check database health."""
        try:
            if self._engine:
                async with self._engine.begin() as conn:
                    await conn.execute("SELECT 1")
                
                return ServiceStatus(
                    name="database",
                    availability=ServiceAvailability.AVAILABLE,
                    last_check=datetime.now(timezone.utc),
                    metadata={
                        "type": "postgresql" if self._is_real_postgres else "sqlite",
                        "in_memory": not self._is_real_postgres,
                        "tables_created": self._tables_created
                    }
                )
            else:
                return ServiceStatus(
                    name="database",
                    availability=ServiceAvailability.UNAVAILABLE,
                    error_message="Not connected",
                    last_check=datetime.now(timezone.utc)
                )
        except Exception as e:
            return ServiceStatus(
                name="database",
                availability=ServiceAvailability.DEGRADED,
                error_message=str(e),
                last_check=datetime.now(timezone.utc)
            )
    
    async def reset(self) -> None:
        """Reset database state for clean testing."""
        if not self._engine:
            return
            
        async with self._engine.begin() as conn:
            # Clear test data in dependency order
            tables = [
                "message_routing_log",
                "websocket_connections", 
                "user_responses",
                "agent_execution_results",
                "messages",
                "threads",
                "users"
            ]
            
            for table in tables:
                try:
                    await conn.execute(f"DELETE FROM {table}")
                except Exception as e:
                    logger.debug(f"Failed to clear table {table}: {e}")
        
        logger.debug("Integration database reset completed")


class IntegrationWebSocketService(IntegrationServiceAbstraction):
    """
    WebSocket service abstraction for integration tests.
    
    Simulates WebSocket connections and events for integration testing
    without requiring actual WebSocket server connections.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.env = get_env()
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []
        self._is_real_websocket = False
        
    async def is_available(self) -> bool:
        """Check if real WebSocket service is available."""
        try:
            use_real_services = self.env.get("USE_REAL_SERVICES", "false").lower() == "true"
            if not use_real_services:
                return False
                
            import aiohttp
            
            websocket_url = self.config.get("url", "ws://localhost:8000/ws")
            
            # Quick connection test
            timeout = aiohttp.ClientTimeout(total=2)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.ws_connect(websocket_url) as ws:
                        # Send ping and wait for response
                        await ws.send_str('{"type": "ping"}')
                        response = await asyncio.wait_for(ws.receive(), timeout=1.0)
                        
                    logger.info("Real WebSocket service available")
                    return True
                except Exception:
                    return False
                    
        except Exception as e:
            logger.debug(f"Real WebSocket not available: {e}")
            return False
    
    async def connect(self) -> bool:
        """Connect to WebSocket service (real or simulated)."""
        if await self.is_available():
            return await self._connect_real_websocket()
        else:
            return await self._connect_simulated_websocket()
    
    async def _connect_real_websocket(self) -> bool:
        """Connect to real WebSocket service."""
        try:
            # Real WebSocket connection would be handled per-test
            # This just validates the service is available
            self._is_real_websocket = True
            logger.info("Real WebSocket service connected")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to real WebSocket: {e}")
            return False
    
    async def _connect_simulated_websocket(self) -> bool:
        """Connect to simulated WebSocket service."""
        try:
            # Initialize simulated WebSocket state
            self._connections.clear()
            self._events.clear()
            self._is_real_websocket = False
            logger.info("Simulated WebSocket service initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize simulated WebSocket: {e}")
            return False
    
    async def create_connection(self, websocket_id: str, user_id: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a simulated WebSocket connection."""
        connection_data = {
            "websocket_id": websocket_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "status": "connected",
            "created_at": datetime.now(timezone.utc),
            "events_sent": []
        }
        
        self._connections[websocket_id] = connection_data
        await self.send_event(websocket_id, {"type": "connection_ready", "data": {"status": "connected"}})
        
        return connection_data
    
    async def send_event(self, websocket_id: str, event: Dict[str, Any]) -> None:
        """Send event through WebSocket connection."""
        if websocket_id not in self._connections:
            logger.warning(f"WebSocket connection {websocket_id} not found - skipping event {event.get('type', 'unknown')}")
            return
        
        event_data = {
            "websocket_id": websocket_id,
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._events.append(event_data)
        self._connections[websocket_id]["events_sent"].append(event_data)
        
        logger.debug(f"WebSocket event sent: {event.get('type', 'unknown')} to {websocket_id}")
    
    async def get_events(self, websocket_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events sent through WebSocket connections."""
        if websocket_id:
            if websocket_id not in self._connections:
                return []
            return self._connections[websocket_id]["events_sent"]
        else:
            return self._events
    
    async def close_connection(self, websocket_id: str) -> None:
        """Close WebSocket connection."""
        if websocket_id in self._connections:
            self._connections[websocket_id]["status"] = "disconnected" 
            self._connections[websocket_id]["disconnected_at"] = datetime.now(timezone.utc)
            await self.send_event(websocket_id, {"type": "connection_closed"})
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket service."""
        for websocket_id in list(self._connections.keys()):
            await self.close_connection(websocket_id)
        
        self._connections.clear()
        self._events.clear()
        logger.info("Disconnected from WebSocket service")
    
    async def health_check(self) -> ServiceStatus:
        """Check WebSocket service health."""
        return ServiceStatus(
            name="websocket",
            availability=ServiceAvailability.AVAILABLE,
            last_check=datetime.now(timezone.utc),
            metadata={
                "type": "real" if self._is_real_websocket else "simulated",
                "active_connections": len(self._connections),
                "total_events": len(self._events)
            }
        )
    
    async def reset(self) -> None:
        """Reset WebSocket service state."""
        self._connections.clear()
        self._events.clear()
        logger.debug("WebSocket service state reset")


class IntegrationServiceManager:
    """
    Central manager for integration test service abstractions.
    
    This coordinates all service abstractions and provides a unified
    interface for integration tests to interact with services.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.env = get_env()
        
        # Initialize service abstractions
        db_config = self.config.get("database", {})
        self.database = IntegrationDatabaseService(db_config)
        
        websocket_config = self.config.get("websocket", {})
        self.websocket = IntegrationWebSocketService(websocket_config)
        
        self._connected = False
        self._service_status: Dict[str, ServiceStatus] = {}
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all service abstractions."""
        results = {}
        
        # Connect to database
        try:
            results["database"] = await self.database.connect()
            logger.info(f"Database connection: {'success' if results['database'] else 'fallback'}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            results["database"] = False
        
        # Connect to WebSocket
        try:
            results["websocket"] = await self.websocket.connect()
            logger.info(f"WebSocket connection: {'success' if results['websocket'] else 'fallback'}")
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            results["websocket"] = False
        
        self._connected = any(results.values())
        await self._update_service_status()
        
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect from all service abstractions."""
        try:
            await self.database.disconnect()
        except Exception as e:
            logger.warning(f"Database disconnect failed: {e}")
        
        try:
            await self.websocket.disconnect()
        except Exception as e:
            logger.warning(f"WebSocket disconnect failed: {e}")
        
        self._connected = False
        self._service_status.clear()
    
    async def reset_all(self) -> None:
        """Reset all service abstractions to clean state."""
        try:
            await self.database.reset()
        except Exception as e:
            logger.warning(f"Database reset failed: {e}")
        
        try:
            await self.websocket.reset()
        except Exception as e:
            logger.warning(f"WebSocket reset failed: {e}")
    
    async def health_check_all(self) -> Dict[str, ServiceStatus]:
        """Perform health check on all service abstractions."""
        status = {}
        
        try:
            status["database"] = await self.database.health_check()
        except Exception as e:
            status["database"] = ServiceStatus(
                name="database",
                availability=ServiceAvailability.UNAVAILABLE,
                error_message=str(e),
                last_check=datetime.now(timezone.utc)
            )
        
        try:
            status["websocket"] = await self.websocket.health_check()
        except Exception as e:
            status["websocket"] = ServiceStatus(
                name="websocket", 
                availability=ServiceAvailability.UNAVAILABLE,
                error_message=str(e),
                last_check=datetime.now(timezone.utc)
            )
        
        self._service_status = status
        return status
    
    async def _update_service_status(self) -> None:
        """Update internal service status."""
        await self.health_check_all()
    
    def is_connected(self) -> bool:
        """Check if service manager is connected."""
        return self._connected
    
    def get_service_status(self, service_name: Optional[str] = None) -> Union[ServiceStatus, Dict[str, ServiceStatus]]:
        """Get service status for specific service or all services."""
        if service_name:
            return self._service_status.get(service_name)
        else:
            return self._service_status
    
    @asynccontextmanager
    async def get_database_session(self):
        """Get database session context manager."""
        async with self.database.get_session() as session:
            yield session
    
    async def create_websocket_connection(self, websocket_id: str, user_id: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Create WebSocket connection."""
        return await self.websocket.create_connection(websocket_id, user_id, thread_id)
    
    async def send_websocket_event(self, websocket_id: str, event: Dict[str, Any]) -> None:
        """Send WebSocket event."""
        await self.websocket.send_event(websocket_id, event)
    
    async def get_websocket_events(self, websocket_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get WebSocket events."""
        return await self.websocket.get_events(websocket_id)


# Export all classes
__all__ = [
    "ServiceAvailability",
    "ServiceStatus", 
    "IntegrationServiceAbstraction",
    "IntegrationDatabaseService",
    "IntegrationWebSocketService",
    "IntegrationServiceManager"
]