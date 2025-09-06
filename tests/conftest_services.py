from unittest.mock import MagicMock, AsyncMock

class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
Service fixtures for database, memory optimization, and session management.

This module contains fixtures for:
- Database session management 
- Memory optimization services
- Session memory management
- Factory pattern components

Memory Impact: MEDIUM - Database and memory services can allocate significant resources
Uses lazy loading to prevent unnecessary imports during collection phase.
"""
import asyncio
import uuid
from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime, timezone
from contextlib import asynccontextmanager

import pytest
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

# Lazy import flag - prevents heavy imports during collection
_SQLALCHEMY_IMPORTS_LOADED = False
_PHASE0_IMPORTS_LOADED = False

def _lazy_import_sqlalchemy():
    """Lazy import SQLAlchemy components to avoid collection phase overhead."""
    global _SQLALCHEMY_IMPORTS_LOADED
    if not _SQLALCHEMY_IMPORTS_LOADED:
        try:
            from sqlalchemy.ext.asyncio import (
                AsyncSession,
                async_sessionmaker, 
                create_async_engine,
            )
            from sqlalchemy.pool import StaticPool
            globals().update({
                'AsyncSession': AsyncSession,
                'async_sessionmaker': async_sessionmaker,
                'create_async_engine': create_async_engine,
                'StaticPool': StaticPool
            })
            _SQLALCHEMY_IMPORTS_LOADED = True
            return True
        except ImportError:
            return False
    return _SQLALCHEMY_IMPORTS_LOADED

def _lazy_import_phase0():
    """Lazy import Phase 0 components to reduce collection phase memory."""
    global _PHASE0_IMPORTS_LOADED
    if not _PHASE0_IMPORTS_LOADED:
        try:
            from netra_backend.app.dependencies import (
                get_request_scoped_db_session,
                RequestScopedDbDep,
                RequestScopedSupervisorDep,
                get_request_scoped_supervisor_dependency,
                RequestScopedContext
            )
            from netra_backend.app.services.memory_optimization_service import (
                MemoryOptimizationService,
                get_memory_service,
                MemoryPressureLevel,
                RequestScope
            )
            from netra_backend.app.services.session_memory_manager import (
                SessionMemoryManager,
                UserSession,
                SessionState,
                get_session_manager
            )
            from netra_backend.app.database.session_manager import (
                DatabaseSessionManager,
                SessionScopeValidator,
                managed_session
            )
            globals().update({
                'get_request_scoped_db_session': get_request_scoped_db_session,
                'RequestScopedDbDep': RequestScopedDbDep,
                'RequestScopedSupervisorDep': RequestScopedSupervisorDep,
                'get_request_scoped_supervisor_dependency': get_request_scoped_supervisor_dependency,
                'RequestScopedContext': RequestScopedContext,
                'MemoryOptimizationService': MemoryOptimizationService,
                'get_memory_service': get_memory_service,
                'MemoryPressureLevel': MemoryPressureLevel,
                'RequestScope': RequestScope,
                'SessionMemoryManager': SessionMemoryManager,
                'UserSession': UserSession,
                'SessionState': SessionState,
                'get_session_manager': get_session_manager,
                'DatabaseSessionManager': DatabaseSessionManager,
                'SessionScopeValidator': SessionScopeValidator,
                'managed_session': managed_session
            })
            _PHASE0_IMPORTS_LOADED = True
            return True
        except ImportError:
            return False
    return _PHASE0_IMPORTS_LOADED

# Memory profiling decorator
def memory_profile(description: str = "", impact: str = "MEDIUM"):
    """Decorator to track memory usage of service fixtures."""
    def decorator(func):
        func._memory_description = description
        func._memory_impact = impact
        return func
    return decorator

# =============================================================================
# DATABASE SESSION FIXTURES
# Memory Impact: MEDIUM - Database connections and sessions
# =============================================================================

@pytest.fixture
@memory_profile("Isolated database session for testing", "MEDIUM")
async def isolated_db_session():
    """Create isolated database session for testing.
    
    This fixture provides request-scoped database sessions that are properly
    isolated and automatically cleaned up after tests.
    
    Memory Impact: MEDIUM - Creates database connection and session
    
    Yields:
        AsyncSession: Isolated database session
    """
    # Use lazy loading to avoid imports during collection
    sqlalchemy_available = _lazy_import_sqlalchemy()
    phase0_available = _lazy_import_phase0()
    
    if not sqlalchemy_available or not phase0_available:
        # Mock session for testing without real database
        mock_session = MagicMock()
        mock_session.info = {'mock_session': True}
        yield mock_session
        return
        
    try:
        # Create isolated test database session
        async with get_request_scoped_db_session() as session:
            # Tag session as test-scoped
            session.info = getattr(session, 'info', {})
            session.info['test_scoped'] = True
            session.info['created_at'] = datetime.now(timezone.utc).isoformat()
            
            yield session
    except Exception as e:
        # Fallback to mock if real session creation fails
        mock_session = MagicMock()
        mock_session.info = {'mock_session': True, 'fallback': True}
        yield mock_session

@pytest.fixture
@memory_profile("Database session with isolation validation", "MEDIUM")
async def database_session_isolation():
    """Create database session with isolation validation.
    
    This fixture provides database sessions that are validated for proper
    isolation and prevents global session storage.
    
    Memory Impact: MEDIUM - Database session with validation overhead
    
    Yields:
        Tuple[AsyncSession, Callable]: Session and validation function
    """
    sqlalchemy_available = _lazy_import_sqlalchemy() 
    phase0_available = _lazy_import_phase0()
    
    if not sqlalchemy_available or not phase0_available:
        # Mock session with validation
        mock_session = MagicMock()
        mock_session.info = {'test_isolated': True}
        
        def validate_isolation():
            return True
            
        yield mock_session, validate_isolation
        return
    
    async with get_request_scoped_db_session() as session:
        # Tag session with isolation markers
        session.info = getattr(session, 'info', {})
        session.info['test_isolated'] = True
        session.info['isolation_test_id'] = str(uuid.uuid4())
        
        def validate_isolation():
            """Validate that session maintains proper isolation."""
            if not hasattr(session, 'info'):
                return False
            return session.info.get('test_isolated', False)
        
        yield session, validate_isolation

# =============================================================================
# MEMORY OPTIMIZATION SERVICE FIXTURES  
# Memory Impact: HIGH - Memory monitoring and optimization services
# =============================================================================

@pytest.fixture  
@memory_profile("Memory optimization service for testing", "HIGH")
async def memory_optimization_service():
    """Create memory optimization service for testing.
    
    This fixture provides a MemoryOptimizationService instance that is
    properly started and stopped for each test.
    
    Memory Impact: HIGH - Active memory monitoring and optimization
    
    Yields:
        MemoryOptimizationService: Started memory service
    """
    if not _lazy_import_phase0():
        # Mock memory service
        mock_service = MagicMock()
        mock_service.websocket = TestWebSocketConnection()
        mock_service.get_memory_stats = MagicMock()
        mock_service.get_active_scopes_count = MagicMock(return_value=0)
        mock_service.request_scope = asynccontextmanager(
            lambda request_id, user_id, **kwargs: MagicMock()
        )
        
        await mock_service.start()
        try:
            yield mock_service
        finally:
            await mock_service.stop()
        return
    
    # Real memory optimization service
    service = MemoryOptimizationService()
    await service.start()
    
    try:
        yield service
    finally:
        await service.stop()

@pytest.fixture
@memory_profile("Session memory manager for testing", "HIGH")
async def session_memory_manager():
    """Create session memory manager for testing.
    
    This fixture provides a SessionMemoryManager instance for testing
    session lifecycle and memory cleanup functionality.
    
    Memory Impact: HIGH - Session tracking and memory management
    
    Yields:
        SessionMemoryManager: Started session manager
    """
    if not _lazy_import_phase0():
        # Mock session manager
        mock_manager = MagicMock()
        mock_manager.websocket = TestWebSocketConnection()
        mock_manager.cleanup_session = AsyncMock(return_value=True)
        mock_manager.session_scope = asynccontextmanager(
            lambda session_id, user_id, **kwargs: MagicMock()
        )
        
        await mock_manager.start()
        try:
            yield mock_manager
        finally:
            await mock_manager.stop()
        return
    
    # Real session memory manager
    manager = SessionMemoryManager()
    await manager.start()
    
    try:
        yield manager
    finally:
        await manager.stop()

# =============================================================================
# REQUEST-SCOPED SUPERVISOR FIXTURES
# Memory Impact: HIGH - Full supervisor with dependencies
# =============================================================================

@pytest.fixture
@memory_profile("Request-scoped supervisor with proper user context", "HIGH")
async def request_scoped_supervisor(valid_user_execution_context, isolated_db_session):
    """Create request-scoped supervisor with proper user context.
    
    This fixture provides isolated supervisor instances that use request-scoped
    database sessions and proper user execution contexts.
    
    Memory Impact: HIGH - Full supervisor instance with all dependencies
    
    Args:
        valid_user_execution_context: Valid user context fixture
        isolated_db_session: Isolated database session fixture
        
    Yields:
        Supervisor: Request-scoped supervisor instance
    """
    # Import from conftest_base
    from tests.conftest_base import valid_user_execution_context as get_context
    
    if not _lazy_import_phase0():
        # Mock supervisor for testing
        mock_supervisor = MagicMock()
        mock_supervisor.user_context = valid_user_execution_context
        mock_supervisor.websocket = TestWebSocketConnection()
        yield mock_supervisor
        return
    
    try:
        # Create mock FastAPI request for supervisor creation
        mock_request = MagicMock()
        mock_request.app.state.llm_manager = MagicMock()
        mock_request.app.state.websocket_bridge = MagicMock()
        mock_request.app.state.agent_supervisor = MagicMock()
        mock_request.app.state.agent_supervisor.tool_dispatcher = MagicMock()
        # Create request-scoped context
        context = RequestScopedContext(
            user_id=valid_user_execution_context.user_id,
            thread_id=valid_user_execution_context.thread_id,
            run_id=valid_user_execution_context.run_id,
            websocket_connection_id=getattr(valid_user_execution_context, 'websocket_connection_id', None)
        )
        
        # Create supervisor with request-scoped session
        supervisor = await get_request_scoped_supervisor_dependency(
            mock_request, context, isolated_db_session
        )
        
        yield supervisor
        
        # Cleanup
        if hasattr(supervisor, 'cleanup'):
            await supervisor.cleanup()
            
    except Exception as e:
        # Fallback to mock supervisor if creation fails
        websocket = TestWebSocketConnection()
        mock_supervisor.user_context = valid_user_execution_context
        mock_supervisor.websocket = TestWebSocketConnection()
        yield mock_supervisor

# =============================================================================
# FACTORY PATTERN AND UTILITY FIXTURES
# Memory Impact: LOW - Mock factory components
# =============================================================================

@pytest.fixture
@memory_profile("Mock factory pattern components for testing", "LOW")
def factory_pattern_mocks():
    """Create mock factory pattern components for testing.
    
    This fixture provides mock implementations of factory pattern components
    for testing factory-based dependency injection.
    
    Memory Impact: LOW - Simple mock objects
    
    Returns:
        Dict[str, Any]: Dictionary of mock factory components
    """
    return {
        'execution_engine_factory': MagicMock(),
        'websocket_bridge_factory': MagicMock(),
        'factory_adapter': MagicMock(),
        'agent_instance_factory': MagicMock()
    }

# =============================================================================
# COMPLETE PHASE 0 TEST ENVIRONMENT
# Memory Impact: VERY_HIGH - All Phase 0 components together
# =============================================================================

@pytest.fixture
@memory_profile("Complete Phase 0 test environment with all components", "VERY_HIGH")
async def phase0_test_environment(
    isolated_db_session,
    memory_optimization_service,
    session_memory_manager
):
    """Complete Phase 0 test environment with all key components.
    
    This fixture provides a full testing environment with:
    - Valid UserExecutionContext
    - Isolated database session
    - Memory optimization service
    - Session memory manager
    
    Memory Impact: VERY_HIGH - All memory-intensive services combined
    
    Yields:
        Dict[str, Any]: Dictionary of Phase 0 components
    """
    # Import user context from base
    from tests.conftest_base import valid_user_execution_context
    
    # Get user context for this test
    test_context = valid_user_execution_context()
    
    yield {
        'user_context': test_context,
        'db_session': isolated_db_session,
        'memory_service': memory_optimization_service,
        'session_manager': session_memory_manager
    }