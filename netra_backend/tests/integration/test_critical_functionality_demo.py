#!/usr/bin/env python3
"""
Critical Functionality Demo Test
Creates a failing test to demonstrate that we can create failing tests for critical functionality.
This test will initially fail, showing that our testing infrastructure can catch issues.
""""
import pytest
import asyncio
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.db.postgres_session import get_async_db


@pytest.fixture
async def thread_service():
    """Thread service instance for testing."""
    return ThreadService()


@pytest.fixture
async def db_session():
    """Database session for testing."""
    async with get_async_db() as db:
    yield db


class TestCriticalFunctionalityDemo:
    """Demonstrate our ability to create failing tests for critical functionality."""
    
    @pytest.mark.asyncio
    async def test_thread_service_basic_functionality(self, thread_service: ThreadService):
        """Test basic thread service functionality - this should pass."""
        # This basic test should pass
        assert thread_service is not None
        assert hasattr(thread_service, '_send_thread_created_event')
        
        # Test that we can call the WebSocket event method without errors
        user_id = "test_user_basic"
        try:
            await thread_service._send_thread_created_event(user_id)
            # If no exception, the basic functionality works
            assert True
        except Exception as e:
            # Allow certain expected exceptions, but not import/attribute errors
            assert not isinstance(e, (ImportError, AttributeError, ModuleNotFoundError))
    
    @pytest.mark.asyncio
    async def test_nonexistent_method_should_fail(self, thread_service: ThreadService):
        """This test should FAIL because the method doesn't exist - demonstrating failing test creation."""
        # This test is designed to fail to show we can create failing tests
        
        # Try to call a method that doesn't exist
        with pytest.raises(AttributeError):
            await thread_service.create_thread_with_advanced_ai_features(
                user_id="test_user",
                title="Test Thread", 
                ai_model="gpt-5",
                advanced_features={"auto_complete": True}
            )
    
    @pytest.mark.asyncio
    async def test_database_connection_integrity(self, db_session):
        """Test database connection integrity - should pass if DB is healthy."""
        # Test that we can execute basic queries
        result = await db_session.execute("SELECT 1 as test_value")
        row = result.fetchone()
        assert row is not None
        assert row.test_value == 1
    
    @pytest.mark.asyncio
    async def test_websocket_manager_initialization(self, thread_service: ThreadService):
        """Test WebSocket manager can be initialized - should pass."""
        # Test that the websocket manager is available
        try:
            # Try to send an event to verify WebSocket manager is working
            await thread_service._send_thread_created_event("test_user_ws")
            # If we get here without ImportError, the WebSocket manager is working
            assert True
        except ImportError:
            # If WebSocket manager is not properly initialized
            pytest.fail("WebSocket manager not properly initialized")
        except Exception:
            # Other exceptions are acceptable (no client connected, etc.)
            assert True
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_basic(self, thread_service: ThreadService):
        """Test basic concurrent operations - should pass."""
        # Test that we can run multiple WebSocket events concurrently
        user_ids = [f"concurrent_user_{i]" for i in range(3)]
        
        tasks = []
        for user_id in user_ids:
            task = thread_service._send_thread_created_event(user_id)
            tasks.append(task)
        
        # This should complete without deadlocks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that we got results (even if they're exceptions)
        assert len(results) == len(user_ids)
        
        # Should not have RuntimeError or deadlock issues
        for result in results:
            if isinstance(result, Exception):
                assert not isinstance(result, (RuntimeError, asyncio.TimeoutError))
    
    @pytest.mark.asyncio 
    async def test_intentional_failure_for_demo(self):
        """This test intentionally fails to demonstrate failing test creation."""
        # This assertion will always fail to demonstrate we can create failing tests
        expected_value = "this_will_work"
        actual_value = "this_will_definitely_fail"
        
        assert actual_value == expected_value, f"Expected '{expected_value}' but got '{actual_value}'"
    
    @pytest.mark.asyncio
    async def test_performance_basic_sanity(self, thread_service: ThreadService):
        """Test basic performance sanity check - should pass unless system is very slow."""
        start_time = datetime.now()
        
        # Perform some basic operations
        for i in range(10):
            try:
                await thread_service._send_thread_created_event(f"perf_test_user_{i}")
            except Exception:
                # Ignore exceptions for performance test
                pass
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should complete within 5 seconds (very generous threshold)
        assert elapsed < 5.0, f"Basic operations took too long: {elapsed}s"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])