"""Tests for router configuration and Pydantic models - split from test_threads_route.py"""

import pytest
from netra_backend.app.routes.threads_route import router, ThreadCreate, ThreadUpdate, ThreadResponse

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestRouterConfiguration:
    """Test router configuration"""
    
    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/threads"
    
    def test_router_tags(self):
        """Test router has correct tags"""
        assert "threads" in router.tags
    
    def test_router_redirect_slashes(self):
        """Test router has redirect_slashes disabled"""
        assert router.redirect_slashes == False


class TestPydanticModels:
    """Test Pydantic model configurations"""
    
    def test_thread_create_model(self):
        """Test ThreadCreate model"""
        thread = ThreadCreate(title="Test", metadata={"key": "value"})
        assert thread.title == "Test"
        assert thread.metadata == {"key": "value"}
        
        thread = ThreadCreate()
        assert thread.title == None
        assert thread.metadata == None
    
    def test_thread_update_model(self):
        """Test ThreadUpdate model"""
        update = ThreadUpdate(title="Updated", metadata={"new": "data"})
        assert update.title == "Updated"
        assert update.metadata == {"new": "data"}
        
        update = ThreadUpdate()
        assert update.title == None
        assert update.metadata == None
    
    def test_thread_response_model(self):
        """Test ThreadResponse model"""
        response = ThreadResponse(
            id="thread_123",
            title="Test Thread",
            created_at=1234567890,
            updated_at=1234567900,
            metadata={"key": "value"},
            message_count=10
        )
        assert response.id == "thread_123"
        assert response.object == "thread"
        assert response.title == "Test Thread"
        assert response.created_at == 1234567890
        assert response.updated_at == 1234567900
        assert response.metadata == {"key": "value"}
        assert response.message_count == 10
    
    def test_thread_response_defaults(self):
        """Test ThreadResponse model defaults"""
        response = ThreadResponse(id="thread_456", created_at=1234567890)
        assert response.object == "thread"
        assert response.title == None
        assert response.updated_at == None
        assert response.metadata == None
        assert response.message_count == 0