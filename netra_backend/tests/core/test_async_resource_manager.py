"""
Tests for AsyncResourceManager - resource lifecycle management
Split from test_async_utils.py for architectural compliance (≤300 lines, ≤8 lines per function)
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, Mock

import pytest

# Add project root to path
from netra_backend.app.core.async_resource_manager import AsyncResourceManager
from .async_utils_helpers import (
    assert_callbacks_called,
    assert_resource_manager_state,
    create_failing_callback,
    # Add project root to path
    create_mock_resources,
    register_test_resources,
)


class TestAsyncResourceManager:
    """Test AsyncResourceManager for resource lifecycle management"""
    
    @pytest.fixture
    def resource_manager(self):
        return AsyncResourceManager()
    
    def test_initialization(self, resource_manager):
        """Test resource manager initialization"""
        assert resource_manager._resources != None
        assert resource_manager._cleanup_callbacks == []
        assert resource_manager._shutting_down == False
    
    def test_register_resource_without_callback(self, resource_manager):
        """Test registering resource without cleanup callback"""
        resource = Mock()
        resource_manager.register_resource(resource)
        assert resource in resource_manager._resources
        assert len(resource_manager._cleanup_callbacks) == 0
    
    def test_register_resource_with_callback(self, resource_manager):
        """Test registering resource with cleanup callback"""
        resource = Mock()
        callback = AsyncMock()
        resource_manager.register_resource(resource, callback)
        assert resource in resource_manager._resources
        assert callback in resource_manager._cleanup_callbacks
    
    def test_register_resource_during_shutdown(self, resource_manager):
        """Test that resources cannot be registered during shutdown"""
        resource_manager._shutting_down = True
        resource = Mock()
        resource_manager.register_resource(resource)
        assert resource not in resource_manager._resources
    
    async def test_cleanup_all(self, resource_manager):
        """Test cleanup of all resources"""
        callback1, callback2, resource1, resource2 = create_mock_resources()
        register_test_resources(resource_manager, callback1, callback2, resource1, resource2)
        await resource_manager.cleanup_all()
        assert_callbacks_called(callback1, callback2)
        assert_resource_manager_state(resource_manager)
    
    async def test_cleanup_all_idempotent(self, resource_manager):
        """Test that cleanup_all is idempotent"""
        callback = AsyncMock()
        resource = Mock()
        resource_manager.register_resource(resource, callback)
        await resource_manager.cleanup_all()
        callback.assert_called_once()
        await resource_manager.cleanup_all()
        callback.assert_called_once()
    
    async def test_cleanup_handles_exceptions(self, resource_manager):
        """Test that cleanup handles exceptions gracefully"""
        failing_callback = create_failing_callback()
        success_callback = AsyncMock()
        resource_manager.register_resource(Mock(), failing_callback)
        resource_manager.register_resource(Mock(), success_callback)
        await resource_manager.cleanup_all()
        failing_callback.assert_called_once()
        success_callback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])