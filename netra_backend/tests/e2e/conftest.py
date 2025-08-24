"""E2E test fixtures and configuration."""

import pytest
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.containers_utils import TestcontainerHelper
from dev_launcher.isolated_environment import get_env

# Basic test setup fixtures
@pytest.fixture
async def mock_agent_service():
    """Mock agent service for E2E tests."""
    mock_service = AsyncMock()
    mock_service.process_message.return_value = {
        "response": "Test response",
        "metadata": {"test": True}
    }
    yield mock_service

@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for E2E tests."""
    mock_manager = MagicMock()
    mock_manager.send_message = AsyncMock()
    mock_manager.broadcast = AsyncMock()
    return mock_manager

@pytest.fixture
def model_selection_setup():
    """Basic setup for model selection tests."""
    return {
        "mock_llm_service": AsyncMock(),
        "mock_database": AsyncMock(),
        "test_config": {"environment": "test"}
    }

# Database mocking for E2E tests
@pytest.fixture
def mock_database_factory():
    """Mock database session factory for E2E tests."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.get = AsyncMock()
    mock_session.id = "mock_session_id"  # Add session ID
    
    # Create proper async context manager mock
    class MockSessionFactory:
        def __call__(self):
            return self
            
        async def __aenter__(self):
            return mock_session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None
    
    return MockSessionFactory()

@pytest.fixture
def setup_database_mocking(mock_database_factory):
    """Auto-setup database mocking for all E2E tests."""
    # Skip during collection mode to avoid heavy imports
    import os
    if get_env().get("TEST_COLLECTION_MODE"):
        yield
        return
        
    try:
        import netra_backend.app.services.database.unit_of_work as uow_module
        import netra_backend.app.db.postgres_core as postgres_module
        from netra_backend.app.db.models_postgres import Thread, Run
    except ImportError as e:
        import warnings
        warnings.warn(f"Cannot import database modules for mocking: {e}")
        yield
        return
    
    # Mock thread and run objects with all required attributes
    mock_thread = MagicMock()
    mock_thread.id = "test_thread_123"
    mock_thread.user_id = "test_user_001"
    mock_thread.metadata_ = {"user_id": "test_user_001", "created_at": "2025-01-01T00:00:00Z"}
    mock_thread.created_at = 1640995200  # timestamp
    mock_thread.object = "thread"
    
    mock_run = MagicMock()
    mock_run.id = "test_run_123"  
    mock_run.thread_id = "test_thread_123"
    mock_run.status = "completed"
    mock_run.assistant_id = "test_assistant"
    mock_run.model = "gpt-4"
    mock_run.metadata_ = {"user_id": "test_user_001"}
    mock_run.created_at = 1640995200
    
    with patch.object(uow_module, 'async_session_factory', mock_database_factory):
        with patch.object(postgres_module, 'async_session_factory', mock_database_factory):
            # Wrap in try-except to handle missing modules gracefully
            try:
                with patch('netra_backend.app.services.thread_service.ThreadService.get_thread', new_callable=AsyncMock, return_value=mock_thread):
                    with patch('netra_backend.app.services.thread_service.ThreadService.get_or_create_thread', new_callable=AsyncMock, return_value=mock_thread):
                        with patch('netra_backend.app.services.thread_service.ThreadService.create_run', new_callable=AsyncMock, return_value=mock_run):
                            with patch('netra_backend.app.services.thread_service.ThreadService.create_message', new_callable=AsyncMock, return_value=None):
                                # Mock WebSocket manager broadcasting functionality
                                mock_broadcasting = MagicMock()
                                mock_broadcasting.join_room = AsyncMock()
                                mock_broadcasting.leave_all_rooms = AsyncMock()
                                
                                try:
                                    with patch('netra_backend.app.get_websocket_manager().broadcasting', mock_broadcasting):
                                        yield
                                except (ImportError, AttributeError):
                                    # WebSocket manager not available, yield without it
                                    yield
            except ImportError as e:
                import warnings
                warnings.warn(f"Cannot patch thread services: {e}")
                yield

# Real LLM testing configuration
@pytest.fixture
def real_llm_config():
    """Configuration for real LLM testing."""
    import os
    return {
        "enabled": get_env().get("ENABLE_REAL_LLM_TESTING") == "true",
        "timeout": float(get_env().get("LLM_TEST_TIMEOUT", "30.0")),
        "max_retries": int(get_env().get("LLM_TEST_RETRIES", "3"))
    }

# Container management for L3/L4 testing
@pytest.fixture
def container_helper():
    """Provide containerized services for L3/L4 testing."""
    helper = TestcontainerHelper()
    yield helper
    helper.stop_all_containers()
