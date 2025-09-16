"""
Thread Cleanup Manager NoneType Error Tests - Issue #704

These tests comprehensively validate the fix for NoneType callable errors
in the Thread Cleanup Manager's _schedule_cleanup method.

ISSUE #704 ROOT CAUSE:
The Thread Cleanup Manager was experiencing runtime errors where NoneType objects
were being called as functions, causing TypeError exceptions during cleanup operations.

TEST STRATEGY:
- Cover all possible NoneType scenarios in asyncio event loop operations
- Test comprehensive validation logic for loop objects and methods
- Verify graceful fallback to synchronous cleanup when asyncio unavailable
- Ensure no regression in existing cleanup functionality
"""

import pytest
import asyncio
import threading
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from netra_backend.app.core.thread_cleanup_manager import (
    ThreadCleanupManager,
    ThreadInfo,
)


class TestThreadCleanupNoneTypeErrorFix:
    """Test suite validating the comprehensive NoneType error fix for Issue #704."""

    def setup_method(self):
        """Set up test environment."""
        # Create fresh manager for each test
        self.manager = ThreadCleanupManager()

        # Add some tracked threads to make cleanup meaningful
        for i in range(3):
            thread_info = ThreadInfo(
                thread_id=2000 + i,
                thread_name=f"TestThread-{i}",
                created_at=datetime.now()
            )
            self.manager._tracked_threads[2000 + i] = thread_info

        # Capture logs for diagnostic validation
        self.log_messages = []
        self.log_handler = logging.Handler()
        self.log_handler.emit = lambda record: self.log_messages.append(record.getMessage())

        # Add handler to thread cleanup manager logger
        thread_cleanup_logger = logging.getLogger('netra_backend.app.core.thread_cleanup_manager')
        thread_cleanup_logger.addHandler(self.log_handler)
        thread_cleanup_logger.setLevel(logging.DEBUG)

    def teardown_method(self):
        """Clean up after each test."""
        # Remove log handler
        thread_cleanup_logger = logging.getLogger('netra_backend.app.core.thread_cleanup_manager')
        thread_cleanup_logger.removeHandler(self.log_handler)

    def test_none_event_loop_from_get_running_loop(self):
        """
        Test NoneType error fix when asyncio.get_running_loop() returns None.

        This tests the first validation layer where the loop object itself is None.
        """
        with patch('asyncio.get_running_loop') as mock_get_running_loop:
            mock_get_running_loop.return_value = None

            # This should not raise NoneType error, should fallback gracefully
            self.manager._schedule_cleanup()

            # Verify fallback was triggered
            assert any("asyncio.get_running_loop() returned None" in msg for msg in self.log_messages)

            # Verify synchronous cleanup was scheduled
            assert any("Background cleanup scheduled in separate thread" in msg for msg in self.log_messages)

            # Wait for synchronous cleanup to start
            time.sleep(0.1)

    def test_event_loop_missing_create_task_method(self):
        """
        Test NoneType error fix when event loop object lacks create_task method.

        This tests the hasattr validation for missing methods.
        """
        # Create mock loop without create_task method
        mock_loop = Mock()
        del mock_loop.create_task  # Remove the method entirely

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # This should not raise AttributeError, should fallback gracefully
            self.manager._schedule_cleanup()

            # Verify the specific validation message
            assert any("event loop missing create_task method" in msg for msg in self.log_messages)

            # Verify synchronous cleanup was scheduled
            assert any("Background cleanup scheduled in separate thread" in msg for msg in self.log_messages)

    def test_event_loop_create_task_not_callable(self):
        """
        Test NoneType error fix when event loop's create_task attribute is not callable.

        This tests the callable() validation for method attributes.
        """
        # Create mock loop with non-callable create_task
        mock_loop = Mock()
        mock_loop.create_task = "not_callable_string"  # Set as non-callable

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # This should not raise TypeError, should fallback gracefully
            self.manager._schedule_cleanup()

            # Verify the specific validation message
            assert any("event loop create_task is not callable" in msg for msg in self.log_messages)

            # Verify synchronous cleanup was scheduled
            assert any("Background cleanup scheduled in separate thread" in msg for msg in self.log_messages)

    def test_event_loop_create_task_is_none(self):
        """
        Test NoneType error fix when event loop's create_task method is explicitly None.

        This is the core NoneType scenario that was causing the original issue.
        """
        # Create mock loop with None create_task
        mock_loop = Mock()
        mock_loop.create_task = None

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # This should not raise "NoneType object is not callable", should fallback gracefully
            self.manager._schedule_cleanup()

            # Verify the specific validation message
            assert any("event loop create_task is not callable" in msg for msg in self.log_messages)

            # Verify synchronous cleanup was scheduled
            assert any("Background cleanup scheduled in separate thread" in msg for msg in self.log_messages)

    def test_event_loop_closed_during_cleanup(self):
        """
        Test NoneType error fix when event loop is closed during cleanup scheduling.

        This tests the is_closed() validation for event loop state.
        """
        # Create mock loop that reports as closed
        mock_loop = Mock()
        mock_loop.create_task = Mock()
        mock_loop.is_closed = Mock(return_value=True)

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # This should not attempt to use closed loop, should fallback gracefully
            self.manager._schedule_cleanup()

            # Verify the closed loop validation
            mock_loop.is_closed.assert_called_once()

            # Verify the specific validation message
            assert any("event loop is closed" in msg for msg in self.log_messages)

            # Verify synchronous cleanup was scheduled
            assert any("Background cleanup scheduled in separate thread" in msg for msg in self.log_messages)

    def test_existing_event_loop_none_fallback_scenario(self):
        """
        Test the secondary fallback when get_event_loop() also returns None.

        This tests the comprehensive validation in the fallback path.
        """
        with patch('asyncio.get_running_loop', side_effect=RuntimeError("No running loop")):
            with patch('asyncio.get_event_loop', return_value=None):
                # Both loop acquisition methods fail
                self.manager._schedule_cleanup()

                # Verify both validation attempts were made
                assert any("Active event loop validation failed" in msg for msg in self.log_messages)
                assert any("asyncio.get_event_loop() returned None" in msg for msg in self.log_messages)

                # Verify synchronous cleanup was scheduled
                assert any("Background cleanup scheduled in separate thread" in msg for msg in self.log_messages)

    def test_concurrent_cleanup_with_none_conditions(self):
        """
        Test that multiple concurrent cleanup calls with None conditions don't cause crashes.

        This tests thread safety of the NoneType validation fixes.
        """
        def trigger_cleanup_with_none():
            """Simulate cleanup with None conditions."""
            return self.manager._schedule_cleanup()

        # Create multiple threads that trigger cleanup with None conditions
        with patch('asyncio.get_running_loop', return_value=None):
            threads = []
            for i in range(5):
                thread = threading.Thread(target=trigger_cleanup_with_none)
                threads.append(thread)

            # Start all threads
            for thread in threads:
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join(timeout=5)

            # Verify no threads are still hanging (no deadlock)
            for thread in threads:
                assert not thread.is_alive(), "Thread cleanup with None conditions caused hanging"

            # Verify fallback messages were logged
            assert any("asyncio.get_running_loop() returned None" in msg for msg in self.log_messages)

    def test_successful_cleanup_with_valid_event_loop(self):
        """
        Test that valid event loop still works correctly after NoneType fixes.

        This ensures no regression in the happy path scenario.
        """
        # Create a valid mock loop
        mock_loop = Mock()
        mock_task = Mock()
        mock_loop.create_task.return_value = mock_task
        mock_loop.is_closed.return_value = False

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # This should work normally
            self.manager._schedule_cleanup()

            # Verify create_task was called (happy path)
            mock_loop.create_task.assert_called_once()

            # Verify success message
            assert any("comprehensive validation passed" in msg for msg in self.log_messages)

    def test_graceful_degradation_preserves_cleanup_functionality(self):
        """
        Test that even with NoneType conditions, cleanup functionality is preserved.

        This verifies that the business value (thread cleanup) is maintained.
        """
        # Force all asyncio approaches to fail
        with patch('asyncio.get_running_loop', return_value=None):
            with patch('asyncio.get_event_loop', return_value=None):
                # Trigger cleanup
                self.manager._schedule_cleanup()

                # Wait for synchronous cleanup to execute
                time.sleep(6)  # Wait longer than the 5-second delay

                # Verify cleanup was marked as not scheduled (completion)
                assert not self.manager._cleanup_scheduled

                # Verify synchronous cleanup messages
                assert any("Background cleanup scheduled in separate thread" in msg for msg in self.log_messages)


class TestNoneTypeValidationEdgeCases:
    """Additional edge case tests for comprehensive NoneType validation."""

    def setup_method(self):
        """Set up test environment."""
        self.manager = ThreadCleanupManager()

    def test_getattr_returns_none_for_create_task(self):
        """
        Test when getattr(loop, 'create_task', None) explicitly returns None.

        This tests the specific getattr pattern used in the validation.
        """
        mock_loop = Mock()
        mock_loop.create_task = None  # Explicitly set to None

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # Should handle None gracefully without recursion
            self.manager._schedule_cleanup()

    def test_is_closed_method_missing(self):
        """
        Test when event loop doesn't have is_closed method.

        This ensures the hasattr check for is_closed works correctly.
        """
        mock_loop = Mock()
        mock_loop.create_task = Mock()
        del mock_loop.is_closed  # Remove is_closed method

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # Should skip is_closed validation and succeed
            self.manager._schedule_cleanup()

            # Should call create_task since other validations pass
            mock_loop.create_task.assert_called_once()

    def test_is_closed_not_callable(self):
        """
        Test when event loop's is_closed attribute exists but is not callable.
        """
        mock_loop = Mock()
        mock_loop.create_task = Mock()
        mock_loop.is_closed = "not_callable"  # Not a callable method

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            # Should skip is_closed validation and succeed
            self.manager._schedule_cleanup()

            # Should call create_task since other validations pass
            mock_loop.create_task.assert_called_once()

    def test_is_running_method_validation_in_fallback(self):
        """
        Test is_running method validation in the existing event loop fallback.
        """
        mock_loop = Mock()
        mock_loop.create_task = Mock()
        mock_loop.is_closed.return_value = False
        mock_loop.is_running.return_value = False  # Not running

        with patch('asyncio.get_running_loop', side_effect=RuntimeError("No running loop")):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Should fail because loop is not running
                self.manager._schedule_cleanup()

                # Should not call create_task because loop is not running
                mock_loop.create_task.assert_not_called()


def test_comprehensive_validation_logging():
    """
    Test that all validation steps produce appropriate diagnostic logs.

    This ensures enhanced diagnostic logging is working as described in the fix.
    """
    manager = ThreadCleanupManager()
    log_messages = []

    # Create a proper logging handler
    class TestLogHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())

    log_handler = TestLogHandler()
    logger = logging.getLogger('netra_backend.app.core.thread_cleanup_manager')
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)

    try:
        # Test with None loop scenario
        log_messages.clear()
        with patch('asyncio.get_running_loop', return_value=None):
            manager._schedule_cleanup()

        # Verify diagnostic logging
        assert len(log_messages) > 0, "No diagnostic logs for None loop scenario"
        assert any("fallback" in msg.lower() for msg in log_messages), \
            "No fallback message for None loop scenario"

        # Test with closed loop scenario - use fresh manager to avoid state issues
        manager_2 = ThreadCleanupManager()
        log_messages.clear()
        mock_loop = Mock()
        mock_loop.create_task = Mock()
        mock_loop.is_closed.return_value = True

        with patch('asyncio.get_running_loop', return_value=mock_loop):
            manager_2._schedule_cleanup()

        # Verify closed loop logging
        assert any("closed" in msg.lower() for msg in log_messages), \
            f"No closed loop message found in: {log_messages}"

    finally:
        logger.removeHandler(log_handler)


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "--tb=short"])