"""
Thread Cleanup Deadlock Reproduction Tests - Issue #601

These tests reproduce the exact deadlock condition identified in the ThreadCleanupManager
where nested lock acquisition in force_cleanup_all() causes deadlocks.

CRITICAL DEADLOCK PATTERN:
1. force_cleanup_all() acquires _cleanup_lock (line 306)
2. force_cleanup_all() calls cleanup_thread_locals() (line 313)
3. cleanup_thread_locals() tries to acquire _cleanup_lock again (line 129)
4. Result: Deadlock when multiple threads call force_cleanup_all() concurrently

Test Strategy:
- Simulate concurrent force_cleanup_all() calls
- Test nested lock acquisition patterns
- Use reasonable timeouts to avoid infinite CI hangs
- Clearly demonstrate deadlock before fixes are applied
"""

import pytest
import threading
import time
import concurrent.futures
from unittest.mock import patch, MagicMock
from datetime import datetime

from netra_backend.app.core.thread_cleanup_manager import (
    ThreadCleanupManager,
    ThreadInfo,
    get_thread_cleanup_manager,
    force_cleanup_all_threads
)


class TestThreadCleanupDeadlockReproduction:
    """Test suite to reproduce the thread cleanup deadlock issue."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create fresh manager for each test
        self.manager = ThreadCleanupManager()
        
        # Add some tracked threads to make cleanup meaningful
        for i in range(5):
            thread_info = ThreadInfo(
                thread_id=1000 + i,
                thread_name=f"TestThread-{i}",
                created_at=datetime.now()
            )
            self.manager._tracked_threads[1000 + i] = thread_info
    
    def test_deadlock_concurrent_force_cleanup_calls(self):
        """
        Test that reproduces deadlock when multiple threads call force_cleanup_all() concurrently.
        
        This is the primary deadlock scenario:
        1. Thread A calls force_cleanup_all() and acquires _cleanup_lock
        2. Thread B calls force_cleanup_all() and waits for _cleanup_lock
        3. Thread A calls cleanup_thread_locals() which tries to acquire _cleanup_lock again
        4. Thread A deadlocks waiting for itself
        """
        deadlock_occurred = threading.Event()
        completion_times = []
        
        def concurrent_force_cleanup(thread_id):
            """Simulate concurrent force_cleanup_all() calls."""
            start_time = time.time()
            
            try:
                # This should deadlock due to nested lock acquisition
                stats = self.manager.force_cleanup_all()
                completion_times.append(time.time() - start_time)
                return stats
            except Exception as e:
                # If we get here, something went wrong during execution
                deadlock_occurred.set()
                raise e
        
        # Use ThreadPoolExecutor to create concurrent calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit multiple concurrent force_cleanup_all() calls
            futures = [
                executor.submit(concurrent_force_cleanup, i) 
                for i in range(3)
            ]
            
            # Wait for completion with a reasonable timeout
            # If deadlock occurs, this will timeout
            timeout_seconds = 10
            start_time = time.time()
            
            completed_futures = 0
            for future in concurrent.futures.as_completed(futures, timeout=timeout_seconds):
                try:
                    result = future.result()
                    completed_futures += 1
                except concurrent.futures.TimeoutError:
                    # Expected behavior: deadlock causes timeout
                    pass
                except Exception as e:
                    # Unexpected error
                    pytest.fail(f"Unexpected error in concurrent cleanup: {e}")
            
            elapsed_time = time.time() - start_time
            
            # If we completed all operations quickly, no deadlock occurred
            # If we hit timeout or took too long, deadlock likely occurred
            if elapsed_time >= timeout_seconds * 0.9 or completed_futures < len(futures):
                # This indicates a deadlock occurred (expected behavior before fix)
                pytest.fail(
                    f"DEADLOCK REPRODUCED: Only {completed_futures}/{len(futures)} operations completed "
                    f"in {elapsed_time:.2f}s. This confirms the deadlock issue exists."
                )
    
    def test_nested_lock_acquisition_pattern(self):
        """
        Test the specific nested lock acquisition pattern that causes deadlock.
        
        This test directly verifies the problematic code path:
        1. Acquire _cleanup_lock
        2. Call cleanup_thread_locals() which tries to acquire the same lock
        """
        
        def simulate_nested_lock_scenario():
            """Simulate the exact nested lock pattern from force_cleanup_all()."""
            with self.manager._cleanup_lock:
                # This is what happens in force_cleanup_all() line 306-313
                thread_ids = list(self.manager._tracked_threads.keys())
                
                # This call will deadlock because cleanup_thread_locals() 
                # tries to acquire _cleanup_lock again (line 129)
                for thread_id in thread_ids[:1]:  # Just test one to avoid infinite wait
                    return self.manager.cleanup_thread_locals(thread_id)
        
        # Use a timeout to detect deadlock
        start_time = time.time()
        
        # This should deadlock and timeout
        with pytest.raises((TimeoutError, RuntimeError)):
            # Run in a separate thread with timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Nested lock acquisition deadlock detected")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # 5 second timeout
            
            try:
                simulate_nested_lock_scenario()
                # If we get here without timeout, the deadlock wasn't reproduced
                pytest.fail("Expected deadlock did not occur - nested lock acquisition succeeded")
            finally:
                signal.alarm(0)  # Cancel the alarm
    
    def test_cleanup_thread_locals_lock_contention(self):
        """
        Test lock contention when cleanup_thread_locals() is called multiple times.
        
        This verifies that the lock acquisition in cleanup_thread_locals() can
        cause contention when called from within force_cleanup_all().
        """
        results = []
        lock_acquisition_times = []
        
        def measure_cleanup_time(thread_id):
            """Measure how long it takes to acquire lock and cleanup."""
            start_time = time.time()
            
            # This should be fast if no deadlock
            result = self.manager.cleanup_thread_locals(thread_id)
            
            elapsed = time.time() - start_time
            lock_acquisition_times.append(elapsed)
            results.append(result)
            return result
        
        # Create multiple threads that all try to cleanup different thread IDs
        threads = []
        thread_ids = list(self.manager._tracked_threads.keys())
        
        for i, thread_id in enumerate(thread_ids):
            thread = threading.Thread(
                target=measure_cleanup_time,
                args=(thread_id,),
                name=f"CleanupThread-{i}"
            )
            threads.append(thread)
        
        # Start all threads nearly simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for completion with timeout
        timeout_per_thread = 3
        for thread in threads:
            thread.join(timeout=timeout_per_thread)
            
            if thread.is_alive():
                pytest.fail(
                    f"Thread {thread.name} did not complete within {timeout_per_thread}s - "
                    "likely deadlock in cleanup_thread_locals()"
                )
        
        # Analyze results
        if not results:
            pytest.fail("No cleanup operations completed - likely deadlock occurred")
        
        # If any cleanup took too long, it suggests lock contention/deadlock
        max_time = max(lock_acquisition_times) if lock_acquisition_times else 0
        if max_time > 2.0:  # 2 seconds is too long for simple cleanup
            pytest.fail(
                f"Cleanup operation took {max_time:.2f}s - indicates lock contention or deadlock"
            )
    
    def test_force_cleanup_all_timeout_detection(self):
        """
        Test that force_cleanup_all() times out due to internal deadlock.
        
        This test calls force_cleanup_all() and monitors for timeout,
        which indicates the deadlock condition.
        """
        
        def timed_force_cleanup():
            """Call force_cleanup_all() and measure execution time."""
            start_time = time.time()
            try:
                result = self.manager.force_cleanup_all()
                return result, time.time() - start_time
            except Exception as e:
                return None, time.time() - start_time
        
        # Use a thread to call force_cleanup_all() with timeout monitoring
        result_container = []
        
        def run_with_timeout():
            result, elapsed = timed_force_cleanup()
            result_container.append((result, elapsed))
        
        thread = threading.Thread(target=run_with_timeout)
        thread.start()
        
        # Wait for completion with timeout
        timeout_seconds = 8
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            # Thread is still running - likely deadlocked
            pytest.fail(
                f"force_cleanup_all() did not complete within {timeout_seconds}s - "
                "deadlock in nested lock acquisition detected"
            )
        
        if not result_container:
            pytest.fail("force_cleanup_all() did not return any result - execution failed")
        
        result, elapsed = result_container[0]
        
        # Even successful completion should be fast for small thread count
        if elapsed > 5.0:
            pytest.fail(
                f"force_cleanup_all() took {elapsed:.2f}s - too slow, indicates lock contention"
            )
    
    def test_global_manager_deadlock_reproduction(self):
        """
        Test deadlock using the global manager instance.
        
        This tests the real-world scenario where force_cleanup_all_threads()
        is called concurrently from different parts of the application.
        """
        
        def concurrent_global_cleanup(iteration):
            """Call the global force_cleanup_all_threads() function."""
            try:
                return force_cleanup_all_threads()
            except Exception as e:
                return {"error": str(e), "iteration": iteration}
        
        # Use concurrent.futures to simulate real concurrent access
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit multiple concurrent calls to global cleanup
            futures = [
                executor.submit(concurrent_global_cleanup, i)
                for i in range(4)
            ]
            
            completed_count = 0
            errors = []
            
            # Wait for completion with timeout
            try:
                for future in concurrent.futures.as_completed(futures, timeout=12):
                    try:
                        result = future.result()
                        if "error" in result:
                            errors.append(result)
                        else:
                            completed_count += 1
                    except Exception as e:
                        errors.append({"error": str(e)})
            except concurrent.futures.TimeoutError:
                # Timeout indicates deadlock
                active_futures = [f for f in futures if not f.done()]
                pytest.fail(
                    f"DEADLOCK DETECTED: {len(active_futures)} global cleanup operations "
                    f"timed out after 12s. This confirms the deadlock issue in the global manager."
                )
            
            # If we have errors or incomplete operations, report them
            if errors or completed_count < len(futures):
                pytest.fail(
                    f"Global cleanup deadlock: Only {completed_count}/{len(futures)} completed. "
                    f"Errors: {errors}"
                )
    
    def test_mock_based_deadlock_simulation(self):
        """
        Use mocking to simulate the exact deadlock condition without actual hanging.
        
        This test verifies the deadlock logic without relying on timeouts.
        """
        
        # Track lock acquisition attempts
        lock_attempts = []
        original_lock = self.manager._cleanup_lock
        
        class MockLock:
            def __init__(self):
                self.locked = False
                self.lock_count = 0
            
            def __enter__(self):
                current_thread = threading.current_thread().name
                lock_attempts.append(f"{current_thread}: attempting lock (count: {self.lock_count})")
                
                if self.locked:
                    # Simulate deadlock - second attempt on same thread
                    lock_attempts.append(f"{current_thread}: DEADLOCK - lock already held")
                    raise RuntimeError("Deadlock detected: nested lock acquisition")
                
                self.locked = True
                self.lock_count += 1
                lock_attempts.append(f"{current_thread}: acquired lock")
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                current_thread = threading.current_thread().name
                self.locked = False
                lock_attempts.append(f"{current_thread}: released lock")
        
        # Replace the lock with our mock
        mock_lock = MockLock()
        self.manager._cleanup_lock = mock_lock
        
        try:
            # This should trigger the deadlock detection in our mock
            with pytest.raises(RuntimeError, match="Deadlock detected"):
                self.manager.force_cleanup_all()
            
            # Verify we detected the nested lock pattern
            assert any("DEADLOCK" in attempt for attempt in lock_attempts), \
                f"Deadlock pattern not detected in lock attempts: {lock_attempts}"
            
        finally:
            # Restore original lock
            self.manager._cleanup_lock = original_lock


class TestSpecificDeadlockScenarios:
    """Additional tests for specific deadlock scenarios identified in Issue #601."""
    
    def test_startup_deadlock_scenario(self):
        """
        Reproduce deadlock during startup when multiple services initialize concurrently.
        
        This simulates the real-world scenario where multiple services
        register threads and trigger cleanup simultaneously during startup.
        """
        manager = ThreadCleanupManager()
        
        # Simulate startup scenario with multiple services
        def simulate_service_startup(service_name, thread_count):
            """Simulate a service starting up and registering threads."""
            threads = []
            
            # Register multiple threads for this service
            for i in range(thread_count):
                thread = threading.Thread(
                    target=lambda: time.sleep(0.1),
                    name=f"{service_name}-Thread-{i}"
                )
                thread.start()
                manager.register_thread(thread)
                threads.append(thread)
            
            # Wait for threads to complete
            for thread in threads:
                thread.join()
            
            # Trigger cleanup (this is where deadlock occurs)
            return manager.force_cleanup_all()
        
        # Start multiple services concurrently
        services = ["auth", "websocket", "database", "agent"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(services)) as executor:
            futures = [
                executor.submit(simulate_service_startup, service, 3)
                for service in services
            ]
            
            timeout_occurred = False
            try:
                # Wait for all services to complete startup
                results = []
                for future in concurrent.futures.as_completed(futures, timeout=15):
                    result = future.result()
                    results.append(result)
                
                # If we get here, no deadlock occurred (unexpected before fix)
                pytest.fail(
                    f"Expected startup deadlock did not occur. All {len(results)} services "
                    "completed initialization without deadlock."
                )
                
            except concurrent.futures.TimeoutError:
                timeout_occurred = True
                pytest.fail(
                    "STARTUP DEADLOCK REPRODUCED: Multiple services timed out during "
                    "concurrent startup and cleanup operations."
                )
    
    def test_exit_cleanup_deadlock(self):
        """
        Test deadlock during application exit cleanup.
        
        This reproduces the scenario where atexit handlers trigger
        force_cleanup_all() while other threads are also cleaning up.
        """
        from netra_backend.app.core.thread_cleanup_manager import install_thread_cleanup_hooks
        
        manager = ThreadCleanupManager()
        
        # Register some threads
        for i in range(3):
            thread_info = ThreadInfo(
                thread_id=2000 + i,
                thread_name=f"ExitTestThread-{i}",
                created_at=datetime.now()
            )
            manager._tracked_threads[2000 + i] = thread_info
        
        # Simulate exit scenario with concurrent cleanup calls
        def simulate_exit_cleanup():
            """Simulate cleanup during application exit."""
            return manager.force_cleanup_all()
        
        def simulate_manual_cleanup():
            """Simulate manual cleanup call."""
            return manager.cleanup_stale_threads()
        
        # Run both cleanup operations concurrently (simulates exit race condition)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(simulate_exit_cleanup)
            future2 = executor.submit(simulate_manual_cleanup)
            
            try:
                # Both should complete quickly if no deadlock
                result1 = future1.result(timeout=8)
                result2 = future2.result(timeout=8)
                
                # If we get here without timeout, no deadlock occurred
                pytest.fail(
                    "Expected exit cleanup deadlock did not occur. "
                    f"Exit cleanup: {result1}, Manual cleanup: {result2}"
                )
                
            except concurrent.futures.TimeoutError:
                pytest.fail(
                    "EXIT CLEANUP DEADLOCK REPRODUCED: Concurrent cleanup operations "
                    "during exit scenario caused deadlock."
                )


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "--tb=short"])