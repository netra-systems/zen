"""
Enhanced Cleanup Configuration for Mission Critical WebSocket Tests

This conftest provides enhanced cleanup for session-scoped fixtures to prevent:
- Resource leaks between tests
- Hanging connections
- Memory accumulation
- Event loop pollution
"""

import asyncio
import gc
import logging
import pytest
import weakref
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock

logger = logging.getLogger(__name__)

# Global resource tracking for cleanup
_session_resources: Dict[str, List[Any]] = {
    'websocket_managers': [],
    'database_connections': [],
    'redis_clients': [],
    'mock_resources': [],
    'async_tasks': [],
    'event_loops': []
}

# Track cleanup callbacks
_cleanup_callbacks: List[callable] = []


class SessionResourceTracker:
    """Tracks and manages session-level resources for proper cleanup."""
    
    def __init__(self):
        self.tracked_resources: Set[Any] = set()
        self.weak_refs: List[weakref.ref] = []
        self.cleanup_funcs: List[callable] = []
    
    def track_resource(self, resource: Any, cleanup_func: Optional[callable] = None):
        """Track a resource for cleanup."""
        self.tracked_resources.add(resource)
        
        # Create weak reference to detect when resource is garbage collected
        weak_ref = weakref.ref(resource, self._resource_cleanup_callback)
        self.weak_refs.append(weak_ref)
        
        if cleanup_func:
            self.cleanup_funcs.append(cleanup_func)
    
    def _resource_cleanup_callback(self, weak_ref):
        """Called when a tracked resource is garbage collected."""
        if weak_ref in self.weak_refs:
            self.weak_refs.remove(weak_ref)
    
    async def cleanup_all(self):
        """Clean up all tracked resources."""
        cleanup_errors = []
        
        # Run custom cleanup functions
        for cleanup_func in self.cleanup_funcs:
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()
            except Exception as e:
                cleanup_errors.append(f"Custom cleanup function error: {e}")
        
        # Clean up tracked resources
        for resource in list(self.tracked_resources):
            try:
                await self._cleanup_resource(resource)
            except Exception as e:
                cleanup_errors.append(f"Resource cleanup error: {e}")
        
        # Clear tracking
        self.tracked_resources.clear()
        self.cleanup_funcs.clear()
        self.weak_refs.clear()
        
        # Force garbage collection
        gc.collect()
        
        if cleanup_errors:
            logger.warning(f"Session cleanup completed with {len(cleanup_errors)} errors")
    
    async def _cleanup_resource(self, resource: Any):
        """Clean up a specific resource."""
        resource_type = type(resource).__name__
        
        try:
            # Try common async cleanup methods
            if hasattr(resource, 'aclose'):
                await resource.aclose()
            elif hasattr(resource, 'close') and asyncio.iscoroutinefunction(resource.close):
                await resource.close()
            elif hasattr(resource, 'shutdown') and asyncio.iscoroutinefunction(resource.shutdown):
                await resource.shutdown()
            elif hasattr(resource, 'cleanup') and asyncio.iscoroutinefunction(resource.cleanup):
                await resource.cleanup()
            elif hasattr(resource, 'stop') and asyncio.iscoroutinefunction(resource.stop):
                await resource.stop()
            
            # Try sync cleanup methods
            elif hasattr(resource, 'close') and callable(resource.close):
                resource.close()
            elif hasattr(resource, 'cleanup') and callable(resource.cleanup):
                resource.cleanup()
            elif hasattr(resource, 'reset_mock') and callable(resource.reset_mock):
                resource.reset_mock()
                
        except Exception as e:
            logger.debug(f"Error cleaning up {resource_type}: {e}")


# Global session tracker
_session_tracker = SessionResourceTracker()


@pytest.fixture(scope="function", autouse=False)
async def enhanced_session_cleanup():
    """Enhanced session cleanup fixture.
    
    FIXED: Changed from session scope with autouse=True to function scope with autouse=False
    to resolve fixture conflicts. Tests that need this functionality should explicitly request it.
    """
    global _session_tracker
    logger.info("Starting enhanced session cleanup tracking")
    
    try:
        yield _session_tracker
    finally:
        logger.info("Running enhanced session cleanup...")
        await _session_tracker.cleanup_all()
        logger.info("Enhanced session cleanup completed")


@pytest.fixture(autouse=True, scope="function")
async def function_level_cleanup():
    """Function-level cleanup to prevent resource accumulation."""
    # Pre-test setup
    initial_tasks = len(asyncio.all_tasks()) if asyncio._get_running_loop() else 0
    
    try:
        yield
    finally:
        # Post-test cleanup
        try:
            # Cancel any lingering tasks created during test
            current_loop = asyncio.get_running_loop()
            current_tasks = asyncio.all_tasks(current_loop)
            
            if len(current_tasks) > initial_tasks:
                # Cancel extra tasks
                extra_tasks = list(current_tasks)[-len(current_tasks) + initial_tasks:]
                for task in extra_tasks:
                    if not task.done() and not task.cancelled():
                        task.cancel()
                
                # Give tasks time to clean up
                try:
                    await asyncio.sleep(0.01)
                except Exception:
                    pass
        
        except RuntimeError:
            # No event loop, which is fine
            pass
        
        # Force garbage collection
        gc.collect()


@pytest.fixture
async def enhanced_websocket_manager(enhanced_session_cleanup):
    """WebSocket manager with enhanced cleanup tracking."""
    from netra_backend.app.websocket_core.manager import WebSocketManager
    
    manager = WebSocketManager()
    
    # Track for cleanup
    enhanced_session_cleanup.track_resource(manager)
    
    try:
        yield manager
    finally:
        # Immediate cleanup
        try:
            if hasattr(manager, 'close_all_connections'):
                await manager.close_all_connections()
            if hasattr(manager, 'shutdown'):
                await manager.shutdown()
        except Exception as e:
            logger.debug(f"WebSocket manager cleanup error: {e}")


@pytest.fixture
async def enhanced_mock_websocket_manager(enhanced_session_cleanup):
    """Enhanced mock WebSocket manager with proper cleanup."""
    
    class TrackedMockWebSocketManager:
        def __init__(self):
            self.messages = []
            self.connections = {}
            self.closed = False
            self._cleanup_callbacks = []
        
        def add_cleanup_callback(self, callback):
            self._cleanup_callbacks.append(callback)
        
        async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
            if self.closed:
                return False
            self.messages.append({
                'thread_id': thread_id,
                'message': message,
                'event_type': message.get('type', 'unknown'),
                'timestamp': asyncio.get_event_loop().time()
            })
            return True
        
        def get_events_for_thread(self, thread_id: str) -> List[Dict]:
            return [msg for msg in self.messages if msg['thread_id'] == thread_id]
        
        def clear_messages(self):
            self.messages.clear()
        
        async def cleanup(self):
            """Enhanced cleanup with callbacks."""
            self.closed = True
            
            # Run cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.debug(f"Mock WebSocket cleanup callback error: {e}")
            
            # Clear data
            self.messages.clear()
            self.connections.clear()
            self._cleanup_callbacks.clear()
    
    manager = TrackedMockWebSocketManager()
    
    # Track for cleanup
    enhanced_session_cleanup.track_resource(manager, manager.cleanup)
    
    try:
        yield manager
    finally:
        await manager.cleanup()


@pytest.fixture
async def database_session_with_cleanup(enhanced_session_cleanup):
    """Database session with enhanced cleanup tracking."""
    session = None
    
    try:
        # Create database session (would normally import from app)
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from shared.isolated_environment import get_env
        
        env = get_env()
        database_url = env.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5433/netra_test')
        
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        
        async with engine.begin() as conn:
            session = AsyncSession(bind=conn)
            
            # Track for cleanup
            enhanced_session_cleanup.track_resource(session)
            enhanced_session_cleanup.track_resource(engine)
            
            yield session
    
    except Exception as e:
        logger.debug(f"Database session creation failed: {e}")
        # Yield None if database not available
        yield None
    
    finally:
        # Cleanup
        if session:
            try:
                await session.close()
            except Exception:
                pass


@pytest.fixture
def test_resource_tracker(enhanced_session_cleanup):
    """Provides access to the resource tracker for tests."""
    return enhanced_session_cleanup


def pytest_runtest_setup(item):
    """Pytest hook for test setup."""
    # Log test start for debugging resource leaks
    if 'websocket' in item.name.lower():
        logger.debug(f"Starting WebSocket test: {item.name}")


def pytest_runtest_teardown(item, nextitem):
    """Pytest hook for test teardown."""
    # Enhanced teardown for WebSocket tests
    if 'websocket' in item.name.lower():
        # Force garbage collection
        gc.collect()
        
        # Log completion
        logger.debug(f"Completed WebSocket test: {item.name}")


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    logger.info("Starting enhanced cleanup session")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    logger.info("Enhanced cleanup session finished")
    
    # Final cleanup check
    gc.collect()
    
    # Report any lingering tasks
    try:
        loop = asyncio.get_running_loop()
        remaining_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if remaining_tasks:
            logger.warning(f"Session finished with {len(remaining_tasks)} remaining async tasks")
    except RuntimeError:
        # No loop, which is fine
        pass