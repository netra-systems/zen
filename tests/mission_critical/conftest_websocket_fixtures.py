"""
WebSocket Test Fixture Cleanup Configuration

This conftest file provides proper fixture cleanup for WebSocket-related tests
to prevent resource leaks, hanging connections, and test interference.
"""

import asyncio
import gc
import logging
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

# Configure logging for fixture cleanup
logger = logging.getLogger(__name__)

# Global test cleanup tracking
_test_resources = {
    'websocket_managers': [],
    'mock_connections': [],
    'event_loops': [],
    'monitoring_components': []
}


class WebSocketTestResourceManager:
    """Manages WebSocket test resources with proper cleanup."""
    
    def __init__(self):
        self.resources = []
        self.cleanup_callbacks = []
    
    def register_resource(self, resource: Any, cleanup_callback: Optional[callable] = None):
        """Register a resource for cleanup."""
        self.resources.append(resource)
        if cleanup_callback:
            self.cleanup_callbacks.append(cleanup_callback)
    
    async def cleanup_all(self):
        """Clean up all registered resources."""
        cleanup_errors = []
        
        # Run custom cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                cleanup_errors.append(f"Cleanup callback error: {e}")
        
        # Clear resources
        for resource in self.resources:
            try:
                # Try common cleanup methods
                if hasattr(resource, 'close') and callable(resource.close):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
                
                if hasattr(resource, 'cleanup') and callable(resource.cleanup):
                    if asyncio.iscoroutinefunction(resource.cleanup):
                        await resource.cleanup()
                    else:
                        resource.cleanup()
                
                if hasattr(resource, 'stop_monitoring') and callable(resource.stop_monitoring):
                    await resource.stop_monitoring()
                
                if hasattr(resource, 'clear_messages') and callable(resource.clear_messages):
                    resource.clear_messages()
                
                if hasattr(resource, 'connections') and hasattr(resource.connections, 'clear'):
                    resource.connections.clear()
                    
            except Exception as e:
                cleanup_errors.append(f"Resource cleanup error for {type(resource).__name__}: {e}")
        
        # Clear our tracking
        self.resources.clear()
        self.cleanup_callbacks.clear()
        
        # Log any errors but don't fail the test
        if cleanup_errors:
            logger.warning(f"WebSocket test cleanup encountered {len(cleanup_errors)} errors: {cleanup_errors}")


@pytest.fixture
def websocket_resource_manager():
    """Provides a WebSocket resource manager for test cleanup."""
    manager = WebSocketTestResourceManager()
    
    try:
        yield manager
    finally:
        # Async cleanup in sync fixture - need to handle properly
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(manager.cleanup_all())
            finally:
                loop.close()
        else:
            # Running loop exists, schedule cleanup
            try:
                loop.run_until_complete(manager.cleanup_all())
            except RuntimeError:
                # Loop might be closed, try creating task
                try:
                    task = loop.create_task(manager.cleanup_all())
                    # Don't wait for completion to avoid blocking
                except Exception as e:
                    logger.warning(f"Failed to schedule WebSocket cleanup: {e}")


@pytest.fixture
async def enhanced_mock_websocket_manager(websocket_resource_manager):
    """Enhanced mock WebSocket manager with proper cleanup tracking."""
    
    class EnhancedMockWebSocketManager:
        def __init__(self):
            self.messages: List[Dict] = []
            self.connections: Dict[str, Any] = {}
            self._closed = False
        
        async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
            if self._closed:
                return False
            self.messages.append({
                'thread_id': thread_id,
                'message': message,
                'event_type': message.get('type', 'unknown'),
                'timestamp': asyncio.get_event_loop().time()
            })
            return True
        
        async def connect_user(self, user_id: str, websocket, thread_id: str):
            if not self._closed:
                self.connections[thread_id] = {'user_id': user_id, 'connected': True}
        
        async def disconnect_user(self, user_id: str, websocket, thread_id: str):
            if thread_id in self.connections:
                self.connections[thread_id]['connected'] = False
        
        def get_events_for_thread(self, thread_id: str) -> List[Dict]:
            return [msg for msg in self.messages if msg['thread_id'] == thread_id]
        
        def get_event_types_for_thread(self, thread_id: str) -> List[str]:
            return [msg['event_type'] for msg in self.messages if msg['thread_id'] == thread_id]
        
        def clear_messages(self):
            self.messages.clear()
        
        async def close(self):
            """Proper async cleanup."""
            self._closed = True
            self.messages.clear()
            self.connections.clear()
    
    manager = EnhancedMockWebSocketManager()
    
    # Register for cleanup
    websocket_resource_manager.register_resource(manager)
    
    try:
        yield manager
    finally:
        await manager.close()


@pytest.fixture
def websocket_event_validator(websocket_resource_manager):
    """WebSocket event validator with cleanup tracking."""
    from tests.mission_critical.test_websocket_agent_events_suite import MissionCriticalEventValidator
    
    validator = MissionCriticalEventValidator()
    
    # Register cleanup callback
    def cleanup_validator():
        validator.events.clear()
        validator.event_timeline.clear()
        validator.event_counts.clear()
        validator.errors.clear()
        validator.warnings.clear()
    
    websocket_resource_manager.register_resource(validator, cleanup_validator)
    
    try:
        yield validator
    finally:
        cleanup_validator()


@pytest.fixture(autouse=True, scope="session")
async def websocket_test_session_cleanup():
    """Session-level cleanup for WebSocket tests."""
    # Setup
    global _test_resources
    _test_resources = {
        'websocket_managers': [],
        'mock_connections': [],
        'event_loops': [],
        'monitoring_components': []
    }
    
    try:
        yield
    finally:
        # Session cleanup
        cleanup_errors = []
        
        # Clean up monitoring components
        for component in _test_resources['monitoring_components']:
            try:
                if hasattr(component, 'stop_monitoring'):
                    await component.stop_monitoring()
            except Exception as e:
                cleanup_errors.append(f"Monitoring cleanup error: {e}")
        
        # Clean up WebSocket managers
        for manager in _test_resources['websocket_managers']:
            try:
                if hasattr(manager, 'close_all_connections'):
                    await manager.close_all_connections()
                if hasattr(manager, 'shutdown'):
                    await manager.shutdown()
            except Exception as e:
                cleanup_errors.append(f"WebSocket manager cleanup error: {e}")
        
        # Clean up mock connections
        for connection in _test_resources['mock_connections']:
            try:
                if hasattr(connection, 'close'):
                    if asyncio.iscoroutinefunction(connection.close):
                        await connection.close()
                    else:
                        connection.close()
            except Exception as e:
                cleanup_errors.append(f"Mock connection cleanup error: {e}")
        
        # Clear all tracking
        for resource_type in _test_resources:
            _test_resources[resource_type].clear()
        
        # Force garbage collection
        gc.collect()
        
        # Log cleanup summary
        if cleanup_errors:
            logger.warning(f"WebSocket session cleanup completed with {len(cleanup_errors)} errors")
        else:
            logger.info("WebSocket session cleanup completed successfully")


@pytest.fixture(autouse=True)
def websocket_test_isolation():
    """Ensure test isolation for WebSocket tests."""
    # Setup - ensure clean state before each test
    
    # Clear any lingering asyncio tasks
    try:
        loop = asyncio.get_running_loop()
        # Cancel any pending tasks that might be from previous tests
        pending_tasks = [task for task in asyncio.all_tasks(loop) 
                        if not task.done() and 'websocket' in str(task).lower()]
        for task in pending_tasks:
            if not task.done():
                task.cancel()
    except RuntimeError:
        # No running loop, which is fine
        pass
    
    yield
    
    # Teardown - ensure clean state after each test
    try:
        loop = asyncio.get_running_loop()
        # Cancel any tasks created during this test
        pending_tasks = [task for task in asyncio.all_tasks(loop) 
                        if not task.done() and 'websocket' in str(task).lower()]
        for task in pending_tasks:
            if not task.done():
                task.cancel()
        
        # Give cancelled tasks a chance to clean up
        if pending_tasks:
            try:
                # Wait briefly for cancelled tasks to finish
                await asyncio.sleep(0.01)
            except Exception:
                pass
    except RuntimeError:
        # No running loop, which is fine
        pass


def register_websocket_resource(resource: Any, resource_type: str = 'websocket_managers'):
    """Register a WebSocket resource for session cleanup."""
    global _test_resources
    if resource_type in _test_resources:
        _test_resources[resource_type].append(resource)


def pytest_runtest_teardown(item, nextitem):
    """Pytest hook for test teardown - ensure no resource leaks."""
    # Force garbage collection after each WebSocket test
    if 'websocket' in item.name.lower():
        gc.collect()