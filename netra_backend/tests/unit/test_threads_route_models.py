"""Tests for router configuration and Pydantic models - split from test_threads_route.py"""

import sys
from pathlib import Path

import pytest

from netra_backend.app.schemas.core_models import Thread
from netra_backend.app.routes.threads_route import (
    ThreadResponse,
    ThreadUpdate,
    router,
)

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
        """Test Thread model"""
        thread = Thread(title="Test", metadata={"key": "value"})
        assert thread.title == "Test"
        assert thread.metadata == {"key": "value"}
        
        thread = Thread()
        assert thread.title == None
        assert thread.metadata == None
    
    def test_thread_update_model(self):
        """Test ThreadUpdate model"""
        update = ThreadUpdate(title="Updated", metadata={"new": "data"})
        assert update.title == "Updated"
        assert update.metadata == {"new": "data"}
        
        update = ThreadUpdate()
        assert update.title == None

    def test_thread_validation_boundaries_iteration_15(self):
        """Test thread model validation boundaries - Iteration 15."""
        
        # Test ThreadUpdate (which allows optional fields) for validation
        update = ThreadUpdate(title="Valid Title")
        assert update.title == "Valid Title"
        
        # Test title boundary conditions
        long_title = "A" * 1000  # Very long title
        update_long = ThreadUpdate(title=long_title)
        assert len(update_long.title) == 1000
        
        # Test metadata validation boundaries
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(50)}
        update_meta = ThreadUpdate(metadata=large_metadata)
        assert len(update_meta.metadata) == 50
        
        # Test nested metadata structure
        nested_meta = {"level1": {"level2": {"data": "test"}}}
        update_nested = ThreadUpdate(metadata=nested_meta)
        assert update_nested.metadata["level1"]["level2"]["data"] == "test"
    
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
    
    def test_thread_response_validation_edge_cases(self):
        """Test ThreadResponse model validation with edge case values"""
        # Test with empty metadata
        response = ThreadResponse(
            id="thread_edge", 
            created_at=0, 
            updated_at=0, 
            metadata={}
        )
        assert response.metadata == {}
        
        # Test with maximum message count
        response_high = ThreadResponse(
            id="thread_high", 
            created_at=1234567890, 
            message_count=999999
        )
        assert response_high.message_count == 999999
        
        # Test with long title
        long_title = "A" * 500
        response_long = ThreadResponse(
            id="thread_long", 
            created_at=1234567890, 
            title=long_title
        )
        assert response_long.title == long_title