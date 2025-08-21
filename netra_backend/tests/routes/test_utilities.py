"""
Common test utilities for API route tests.
Shared fixtures and mocks for route testing.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from typing import Any, Dict
from contextlib import asynccontextmanager

from netra_backend.app.services.security_service import SecurityService, KeyManager
from config import settings

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



@pytest.fixture
def base_client():
    """Base FastAPI test client with minimal setup."""
    from netra_backend.app.routes.mcp.main import app
    return TestClient(app)


@pytest.fixture  
def secured_client():
    """Test client with security service configured."""
    from netra_backend.app.routes.mcp.main import app
    
    # Mock db session factory
    @asynccontextmanager
    async def mock_db_session():
        mock_session = MagicMock()
        yield mock_session
    
    if not hasattr(app.state, 'db_session_factory'):
        app.state.db_session_factory = mock_db_session
        
    # Set up security service
    if not hasattr(app.state, 'security_service'):
        key_manager = KeyManager.load_from_settings(settings)
        app.state.security_service = SecurityService(key_manager)
    
    return TestClient(app)


def create_mock_user(user_id: str, role: str = "user") -> Dict[str, Any]:
    """Create a mock user for testing."""
    return {"id": user_id, "role": role}


def create_admin_user(user_id: str = "admin1") -> Dict[str, Any]:
    """Create a mock admin user for testing."""
    return create_mock_user(user_id, "admin")


def setup_agent_mocks(app):
    """Set up agent service mocks for testing."""
    from netra_backend.app.services.agent_service import get_agent_service
    from netra_backend.app.dependencies import get_llm_manager
    from netra_backend.app.db.postgres import get_async_db
    
    def mock_get_async_db():
        return Mock()
        
    def mock_get_llm_manager():
        return Mock()
        
    def mock_get_agent_service():
        return Mock()
    
    # Override dependencies
    app.dependency_overrides[get_async_db] = mock_get_async_db
    app.dependency_overrides[get_llm_manager] = mock_get_llm_manager  
    app.dependency_overrides[get_agent_service] = mock_get_agent_service
    
    return app


def clear_dependency_overrides(app):
    """Clear all dependency overrides from netra_backend.app."""
    app.dependency_overrides.clear()


def assert_valid_response(response, expected_codes: list = None):
    """Assert response has valid status code."""
    if expected_codes is None:
        expected_codes = [200, 201]
    assert response.status_code in expected_codes


def assert_error_response(response, expected_codes: list = None):
    """Assert response has error status code."""
    if expected_codes is None:
        expected_codes = [400, 401, 404, 422, 500]
    assert response.status_code in expected_codes