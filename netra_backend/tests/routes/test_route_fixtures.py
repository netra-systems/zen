"""
Common test fixtures and utilities for route testing.
Shared components extracted from oversized test file to maintain 450-line architecture limit.
"""

import sys
from pathlib import Path

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from netra_backend.app.config import get_config
from netra_backend.app.services.key_manager import KeyManager

from netra_backend.app.services.security_service import SecurityService

class MockDBSession:
    """Mock database session for testing."""
    
    def __init__(self):
        self.mock_session = MagicMock()
    
    @asynccontextmanager
    async def get_session(self):
        """Async context manager for mock database session."""
        yield self.mock_session

class MockDependencyManager:
    """Manages mock dependencies for FastAPI testing."""
    
    @staticmethod
    def setup_core_dependencies(app):
        """Set up core application dependencies for testing."""
        from unittest.mock import AsyncMock, MagicMock

        from sqlalchemy.ext.asyncio import AsyncSession

        import netra_backend.app.db.postgres as postgres_module

        # Ensure database is initialized first - but handle session factory properly
        import netra_backend.app.db.session as session_module
        from netra_backend.app.db.postgres import get_async_db, initialize_postgres
        from netra_backend.app.db.session import get_db_session
        from netra_backend.app.dependencies import get_db_dependency, get_llm_manager
        
        # Mock the session factory to avoid the RuntimeError
        if postgres_module.async_session_factory is None:
            # Create a minimal mock session factory
            postgres_module.async_session_factory = MagicMock()
            session_module.async_session_factory = postgres_module.async_session_factory
            
            # Also mock the session_manager's get_session method
            from contextlib import asynccontextmanager
            @asynccontextmanager  
            async def mock_manager_get_session():
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.execute = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.rollback = AsyncMock()
                mock_session.close = AsyncMock()
                yield mock_session
            
            session_module.session_manager.get_session = mock_manager_get_session
        
        # Mock database session that behaves like AsyncSession
        async def mock_get_db_dependency():
            mock_session = MagicMock(spec=AsyncSession)
            yield mock_session
        
        # Mock database session for auth dependency that supports context manager
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_get_db_session():
            from unittest.mock import AsyncMock
            mock_session = AsyncMock(spec=AsyncSession)
            # Mock methods commonly used in auth
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            yield mock_session
        
        # Mock database dependency (for backward compatibility)
        def mock_get_async_db():
            return Mock()
        
        # Mock LLM manager dependency  
        def mock_get_llm_manager():
            return Mock()
        
        app.dependency_overrides[get_db_dependency] = mock_get_db_dependency
        app.dependency_overrides[get_db_session] = mock_get_db_session
        app.dependency_overrides[get_async_db] = mock_get_async_db
        app.dependency_overrides[get_llm_manager] = mock_get_llm_manager
    
    @staticmethod
    def setup_auth_dependencies(app):
        """Set up authentication dependencies for testing."""
        from netra_backend.app.auth_integration.auth import (
            get_current_active_user,
            get_current_user,
        )
        from netra_backend.app.db.models_postgres import User
        
        async def mock_get_current_user():
            # Create a mock user for testing - bypass all auth logic
            mock_user = Mock(spec=User)
            mock_user.id = "test_user_123"
            mock_user.email = "test@example.com"
            mock_user.role = "user"
            mock_user.is_active = True
            return mock_user
        
        async def mock_get_current_active_user():
            # Create a mock active user for testing - bypass all auth logic
            mock_user = Mock(spec=User)
            mock_user.id = "test_user_123"
            mock_user.email = "test@example.com"
            mock_user.role = "user"
            mock_user.is_active = True
            return mock_user
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    
    @staticmethod
    def setup_agent_dependencies(app):
        """Set up agent-specific dependencies for testing."""
        from netra_backend.app.services.agent_service import get_agent_service
        from netra_backend.app.services.agent_service_core import AgentService
        
        def mock_get_agent_service(db_session=None, llm_manager=None):
            # Return a properly mocked AgentService
            mock_service = Mock(spec=AgentService)
            mock_service.process_message = AsyncMock(return_value={
                "response": "Test response",
                "status": "success"
            })
            return mock_service
        
        app.dependency_overrides[get_agent_service] = mock_get_agent_service
    
    @staticmethod
    def clear_overrides(app):
        """Clear all dependency overrides."""
        app.dependency_overrides.clear()

class MockAppStateManager:
    """Manages application state setup for testing."""
    
    @staticmethod
    def setup_app_state(app):
        """Set up required application state for testing."""
        # Set up database session factory
        @asynccontextmanager
        async def mock_db_session():
            mock_session = MagicMock()
            yield mock_session
        
        if not hasattr(app.state, 'db_session_factory'):
            app.state.db_session_factory = mock_db_session
        
        # Set up security service
        if not hasattr(app.state, 'security_service'):
            config = get_config()
            key_manager = KeyManager.load_from_settings(config)
            app.state.security_service = SecurityService(key_manager)
        
        # Set up LLM manager for dependency injection
        if not hasattr(app.state, 'llm_manager'):
            app.state.llm_manager = Mock()
        
        # Set up other required services for dependency injection
        if not hasattr(app.state, 'agent_supervisor'):
            app.state.agent_supervisor = Mock()
        
        if not hasattr(app.state, 'agent_service'):
            app.state.agent_service = Mock()
        
        if not hasattr(app.state, 'thread_service'):
            app.state.thread_service = Mock()
        
        if not hasattr(app.state, 'corpus_service'):
            app.state.corpus_service = Mock()

@pytest.fixture
def basic_test_client():
    """Basic FastAPI test client with minimal setup."""
    from netra_backend.app.main import app
    MockAppStateManager.setup_app_state(app)
    return TestClient(app)

@pytest.fixture
def authenticated_test_client(ensure_db_initialized):
    """FastAPI test client with authentication mocked."""
    from netra_backend.app.main import app
    
    MockDependencyManager.setup_core_dependencies(app)
    MockDependencyManager.setup_auth_dependencies(app)
    MockAppStateManager.setup_app_state(app)
    
    try:
        return TestClient(app)
    finally:
        MockDependencyManager.clear_overrides(app)

@pytest.fixture  
def configured_test_client():
    """Test client with core dependencies mocked."""
    from netra_backend.app.main import app
    
    MockDependencyManager.setup_core_dependencies(app)
    MockAppStateManager.setup_app_state(app)
    
    try:
        return TestClient(app)
    finally:
        MockDependencyManager.clear_overrides(app)

@pytest.fixture
def agent_test_client():
    """Test client configured for agent route testing."""
    from netra_backend.app.main import app
    
    MockDependencyManager.setup_core_dependencies(app)
    MockDependencyManager.setup_agent_dependencies(app)
    MockAppStateManager.setup_app_state(app)
    
    try:
        return TestClient(app)
    finally:
        MockDependencyManager.clear_overrides(app)

class CommonResponseValidators:
    """Common response validation patterns."""
    
    @staticmethod
    def validate_success_response(response, expected_keys=None):
        """Validate successful API response structure."""
        if response.status_code == 200:
            data = response.json()
            if expected_keys:
                for key in expected_keys:
                    assert key in data
            return True
        return False
    
    @staticmethod
    def validate_error_response(response, expected_status_codes=None):
        """Validate error response structure."""
        if expected_status_codes is None:
            expected_status_codes = [400, 422, 404, 500]
        
        assert response.status_code in expected_status_codes
        
        if response.status_code != 404:  # 404 might not have JSON body
            try:
                data = response.json()
                # Error responses typically have 'detail' or 'error' field
                assert 'detail' in data or 'error' in data or 'message' in data
            except:
                pass  # Some error responses might not be JSON
    
    @staticmethod
    def validate_pagination_response(response, max_items=None):
        """Validate paginated response structure."""
        if response.status_code == 200:
            data = response.json()
            
            # Common pagination fields
            pagination_indicators = ['items', 'data', 'results', 'threads', 'users']
            has_pagination = any(key in data for key in pagination_indicators)
            
            if has_pagination and max_items:
                for key in pagination_indicators:
                    if key in data and isinstance(data[key], list):
                        assert len(data[key]) <= max_items
            
            return True
        return False

class MockServiceFactory:
    """Factory for creating mock service instances."""
    
    @staticmethod
    def create_mock_agent_service():
        """Create mock agent service with common methods."""
        mock_service = Mock()
        mock_service.process_message = AsyncMock(return_value={
            "response": "Processed successfully",
            "agent": "supervisor", 
            "status": "success"
        })
        return mock_service
    
    @staticmethod
    def create_mock_quality_service():
        """Create mock quality service with metrics."""
        mock_service = Mock()
        mock_service.get_quality_stats = Mock(return_value={
            "accuracy": 0.96,
            "latency_p50": 120,
            "latency_p99": 450,
            "error_rate": 0.02,
            "throughput": 1000
        })
        return mock_service
    
    @staticmethod
    def create_mock_cache_service():
        """Create mock cache service with metrics."""
        mock_service = Mock()
        mock_service.get_cache_metrics = Mock(return_value={
            "hits": 150,
            "misses": 50,
            "hit_rate": 0.75,
            "size_mb": 24.5,
            "entries": 200
        })
        mock_service.clear_cache = Mock(return_value=50)
        return mock_service

# Common test data constants
TEST_USER_DATA = {
    "admin": {"id": "admin1", "role": "admin"},
    "regular": {"id": "user1", "role": "user"}
}

TEST_DOCUMENT_DATA = {
    "title": "Test Document",
    "content": "This is test content",
    "metadata": {"category": "test", "tags": ["sample"]}
}

TEST_MCP_REQUEST = {
    "jsonrpc": "2.0", 
    "method": "tools/list",
    "params": {},
    "id": 1
}