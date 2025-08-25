"""
Test suite for critical event loop conflicts in dev launcher.

This test suite creates failing tests that replicate the exact event loop
conflicts that occur when checking backend and auth service readiness.

Key issues tested:
1. Event loop conflict in _wait_for_backend_readiness() (lines 1556-1558)
2. Event loop conflict in _verify_auth_system() auth readiness check
3. Database URL normalization issues in auth service
4. Async context conflicts when multiple async operations run concurrently
"""

import asyncio
import logging
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, List, Optional

from dev_launcher.config import LauncherConfig
from dev_launcher.launcher import DevLauncher
from dev_launcher.isolated_environment import get_env
from dev_launcher.network_resilience import NetworkResilientClient, RetryPolicy


class TestEventLoopConflict(unittest.TestCase):
    """Test suite for event loop conflicts in dev launcher readiness checks."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temp directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create expected directory structure
        (self.test_path / 'netra_backend' / 'app').mkdir(parents=True)
        (self.test_path / 'frontend').mkdir(parents=True)
        (self.test_path / 'auth_service').mkdir(parents=True)
        
        # Save original environment
        self.original_env = dict(os.environ)
        
        # Clear test-specific env vars
        for key in list(os.environ.keys()):
            if key.startswith(('NETRA_', 'DATABASE_', 'POSTGRES_')):
                del os.environ[key]
        
        # Set minimal test configuration
        os.environ['NETRA_PROJECT_ROOT'] = str(self.test_path)
        os.environ['NETRA_ENVIRONMENT'] = 'test'
        os.environ['DATABASE_URL'] = 'postgres://user:pass@localhost:5432/test'
        
        # Create minimal launcher config
        self.config = LauncherConfig(
            project_root=Path(str(self.test_path)),
            backend_port=8000,
            frontend_port=3000,
            verbose=False,
            no_cache=True
        )
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('dev_launcher.launcher.asyncio.new_event_loop')
    @patch('dev_launcher.launcher.asyncio.set_event_loop')
    @patch('dev_launcher.launcher.asyncio.get_running_loop')
    def test_backend_readiness_event_loop_conflict_when_loop_exists(self, mock_get_running, mock_set_loop, mock_new_loop):
        """
        FAILING TEST: Event loop conflict in _wait_for_backend_readiness().
        
        This test replicates the exact issue where _wait_for_backend_readiness()
        tries to create a new event loop when one is already running.
        
        The issue occurs at lines 1556-1558 in launcher.py:
        - loop = asyncio.new_event_loop()
        - asyncio.set_event_loop(loop) 
        - ready = loop.run_until_complete(check_readiness())
        
        Expected behavior: Should detect existing loop and handle gracefully
        Actual behavior: RuntimeError when trying to create new loop
        """
        # Mock that an event loop is already running
        mock_running_loop = AsyncMock()
        mock_get_running.return_value = mock_running_loop
        
        # Mock the new event loop
        mock_loop = Mock()
        mock_loop.run_until_complete = Mock()
        mock_loop.close = Mock()
        mock_new_loop.return_value = mock_loop
        
        # Create launcher with mocked network client
        launcher = DevLauncher(self.config)
        launcher.network_client = Mock(spec=NetworkResilientClient)
        
        # Mock the resilient_http_request to return success
        async def mock_http_request(*args, **kwargs):
            return True, {"status": "ready"}
        
        launcher.network_client.resilient_http_request = AsyncMock(side_effect=mock_http_request)
        
        # The current implementation will fail because it doesn't check for existing loop
        # This should raise RuntimeError: There is already a running event loop
        with self.assertRaises(RuntimeError) as context:
            # Simulate the scenario where we're already in an async context
            async def run_in_existing_loop():
                # This is what happens when launcher._wait_for_backend_readiness() 
                # is called from within an async context
                result = launcher._wait_for_backend_readiness(timeout=5)
                return result
            
            # This will fail because the current implementation tries to create
            # a new event loop without checking if one exists
            asyncio.run(run_in_existing_loop())
        
        # The error should mention event loop conflict
        self.assertIn("event loop", str(context.exception).lower())
    
    def test_auth_system_verification_event_loop_conflict(self):
        """
        FAILING TEST: Event loop conflict in _verify_auth_system().
        
        This test replicates the event loop conflict that occurs in auth system
        verification when multiple async operations try to manage event loops.
        
        The _verify_auth_system method has complex event loop handling logic
        that can fail in certain race conditions.
        """
        launcher = DevLauncher(self.config)
        launcher.network_client = Mock(spec=NetworkResilientClient)
        launcher.service_startup = Mock()
        launcher.service_startup.allocated_ports = {'auth': 8081}
        launcher.health_monitor = Mock()
        launcher.health_monitor.mark_service_ready = Mock()
        
        # Mock the resilient_http_request to simulate auth service response
        async def mock_auth_request(*args, **kwargs):
            return True, {"auth_configured": True}
        
        launcher.network_client.resilient_http_request = AsyncMock(side_effect=mock_auth_request)
        
        def run_in_thread():
            """Run auth verification in a separate thread to simulate real conditions."""
            return launcher._verify_auth_system(timeout=5)
        
        # Start multiple threads that try to verify auth system simultaneously
        # This will expose the event loop conflict issue
        threads = []
        results = []
        exceptions = []
        
        def thread_worker():
            try:
                result = run_in_thread()
                results.append(result)
            except Exception as e:
                exceptions.append(e)
        
        # Start multiple threads simultaneously to create race condition
        for i in range(3):
            thread = threading.Thread(target=thread_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # The current implementation should fail with event loop conflicts
        # At least one thread should encounter the RuntimeError
        self.assertTrue(len(exceptions) > 0, 
                       "Expected at least one RuntimeError from event loop conflict")
        
        # Check if any exception is related to event loop
        event_loop_errors = [e for e in exceptions 
                           if "event loop" in str(e).lower() or 
                              "asyncio" in str(e).lower()]
        self.assertTrue(len(event_loop_errors) > 0,
                       f"Expected event loop related errors, got: {exceptions}")
    
    def test_database_url_normalization_import_error(self):
        """
        FAILING TEST: Database URL normalization fails with ImportError.
        
        This test replicates the issue where auth service database URL 
        normalization fails when shared modules are not available.
        
        The _normalize_database_url method tries to import shared modules
        but falls back to potentially incompatible normalization.
        """
        # Mock import error for shared database modules
        with patch('builtins.__import__', side_effect=ImportError("Shared module not found")):
            try:
                # This would be the problematic import in auth service
                from shared.database.core_database_manager import CoreDatabaseManager
                self.fail("Expected ImportError for shared database manager")
            except ImportError:
                pass  # This is expected
        
        # Test the fallback normalization behavior 
        test_urls = [
            "postgres://user:pass@localhost:5432/test",
            "postgresql://user:pass@localhost:5432/test", 
            "postgres://user:pass@localhost:5432/test?sslmode=require",
            "postgresql://user:pass@localhost:5432/test?sslmode=disable"
        ]
        
        # The fallback normalization is incomplete and will cause issues
        for url in test_urls:
            # Simulate the fallback behavior from auth service
            if url.startswith("postgres://"):
                normalized = url.replace("postgres://", "postgresql://")
            else:
                normalized = url
            
            # This normalization is insufficient - it doesn't handle SSL parameters
            # or other asyncpg-specific requirements that would cause connection failures
            if "sslmode=" in url and "sslmode=" in normalized:
                # The fallback doesn't properly handle SSL parameter conflicts
                # This demonstrates the issue: the normalization is incomplete
                self.assertIn("sslmode=", normalized,
                             "Fallback normalization doesn't handle SSL parameters properly")
                
                # This is the actual problem - the fallback keeps SSL parameters
                # that can conflict with asyncpg driver expectations
                if "sslmode=require" in normalized:
                    self.fail(f"SSL parameter conflict not resolved in fallback: {normalized}")
                    
        # This test demonstrates that the fallback normalization is insufficient
        # and will cause actual database connection failures in auth service
    
    def test_concurrent_readiness_checks_create_event_loop_race(self):
        """
        FAILING TEST: Concurrent readiness checks create event loop race conditions.
        
        This test replicates the race condition that occurs when multiple
        readiness checks (backend, auth, frontend) run concurrently and
        all try to manage their own event loops.
        """
        launcher = DevLauncher(self.config)
        launcher.network_client = Mock(spec=NetworkResilientClient)
        launcher.service_startup = Mock()
        launcher.service_startup.allocated_ports = {'auth': 8081}
        launcher.health_monitor = Mock()
        launcher.health_monitor.mark_service_ready = Mock()
        
        # Mock network requests to simulate slow responses
        async def slow_backend_request(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
            return True, {"status": "ready"}
        
        async def slow_auth_request(*args, **kwargs):
            await asyncio.sleep(0.15)  # Simulate different timing
            return True, {"auth_configured": True}
        
        # Set up different responses based on URL
        def mock_request(url, *args, **kwargs):
            if "health/ready" in url:
                return slow_backend_request(*args, **kwargs)
            elif "auth/config" in url:
                return slow_auth_request(*args, **kwargs)
            else:
                return AsyncMock(return_value=(False, {}))(*args, **kwargs)
        
        launcher.network_client.resilient_http_request = mock_request
        
        # Run multiple readiness checks concurrently
        # This will expose the event loop management issues
        def run_concurrent_checks():
            results = []
            exceptions = []
            
            def check_backend():
                try:
                    result = launcher._wait_for_backend_readiness(timeout=5)
                    results.append(("backend", result))
                except Exception as e:
                    exceptions.append(("backend", e))
            
            def check_auth():
                try:
                    result = launcher._verify_auth_system(timeout=5)
                    results.append(("auth", result))
                except Exception as e:
                    exceptions.append(("auth", e))
            
            # Start both checks simultaneously
            backend_thread = threading.Thread(target=check_backend)
            auth_thread = threading.Thread(target=check_auth)
            
            backend_thread.start()
            auth_thread.start()
            
            backend_thread.join()
            auth_thread.join()
            
            return results, exceptions
        
        results, exceptions = run_concurrent_checks()
        
        # The current implementation should have race conditions
        # where both threads try to create/manage event loops
        self.assertTrue(len(exceptions) > 0,
                       f"Expected race condition exceptions, got results: {results}")
        
        # Check for event loop related errors
        loop_errors = [e for name, e in exceptions
                      if "event loop" in str(e).lower() or
                         "asyncio" in str(e).lower()]
        
        self.assertTrue(len(loop_errors) > 0,
                       f"Expected event loop race condition errors, got: {exceptions}")
    
    def test_nested_async_context_event_loop_creation_fails(self):
        """
        FAILING TEST: Creating event loops within existing async contexts fails.
        
        This test replicates the specific scenario where launcher methods are
        called from within an async context and demonstrates that the current
        implementation fails gracefully but logs the event loop conflict.
        
        Expected: Should handle async context properly
        Actual: Logs "Cannot run the event loop while another loop is running"
        """
        launcher = DevLauncher(self.config)
        launcher.network_client = Mock(spec=NetworkResilientClient)
        
        # Mock successful network response
        async def mock_success(*args, **kwargs):
            return True, {"status": "ready"}
        
        launcher.network_client.resilient_http_request = AsyncMock(side_effect=mock_success)
        
        async def async_launcher_simulation():
            """
            Simulate calling launcher from an async context.
            
            The current implementation catches the RuntimeError but returns False
            instead of handling the async context properly.
            """
            # This will fail internally but not raise - it will return False
            result = launcher._wait_for_backend_readiness(timeout=5)
            return result
        
        # The current implementation doesn't raise but fails internally
        result = asyncio.run(async_launcher_simulation())
        
        # The test should demonstrate that the check failed due to event loop conflict
        # The current implementation returns False when it should handle async properly
        self.assertFalse(result, 
                        "Backend readiness check should fail due to event loop conflict")
        
        # This test demonstrates the issue: the method fails silently instead of
        # properly handling the async context
    
    def test_direct_event_loop_conflict_reproduction(self):
        """
        FAILING TEST: Direct reproduction of the exact event loop conflict.
        
        This test directly replicates the problematic code pattern from lines 1556-1558:
        - loop = asyncio.new_event_loop()
        - asyncio.set_event_loop(loop)
        - ready = loop.run_until_complete(check_readiness())
        
        Expected: Should detect existing loop and handle gracefully
        Actual: RuntimeError when called from async context
        """
        async def simulate_problematic_pattern():
            """Simulate the exact problematic pattern from the launcher."""
            
            # This is the problematic pattern from launcher.py lines 1556-1558
            try:
                # The issue: this tries to create a new loop without checking
                # if we're already in an async context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # This will fail because we're already in an async context
                async def dummy_check():
                    return True
                
                ready = loop.run_until_complete(dummy_check())
                loop.close()
                return ready
                
            except RuntimeError as e:
                # This is the error we expect to catch
                if "event loop" in str(e).lower():
                    return False
                raise
        
        # Run this from an async context to trigger the issue
        result = asyncio.run(simulate_problematic_pattern())
        
        # The test should demonstrate the failure
        self.assertFalse(result, 
                        "Event loop conflict should cause the check to fail")
    
    def test_event_loop_cleanup_on_exception_leaks_resources(self):
        """
        FAILING TEST: Event loop cleanup fails on exceptions, causing resource leaks.
        
        This test replicates the issue where event loops are not properly
        cleaned up when exceptions occur during readiness checks.
        """
        launcher = DevLauncher(self.config)
        launcher.network_client = Mock(spec=NetworkResilientClient)
        
        # Mock network request that will raise an exception
        async def failing_request(*args, **kwargs):
            raise ConnectionError("Network failure")
        
        launcher.network_client.resilient_http_request = AsyncMock(side_effect=failing_request)
        
        # Track event loop creation and cleanup
        created_loops = []
        closed_loops = []
        
        original_new_loop = asyncio.new_event_loop
        original_loop_close = None
        
        def track_new_loop():
            loop = original_new_loop()
            created_loops.append(loop)
            
            # Track when this loop is closed
            original_close = loop.close
            def track_close():
                closed_loops.append(loop)
                return original_close()
            loop.close = track_close
            
            return loop
        
        with patch('asyncio.new_event_loop', side_effect=track_new_loop):
            # This should handle the exception gracefully and clean up the event loop
            # But the current implementation may not do this properly
            try:
                result = launcher._wait_for_backend_readiness(timeout=5)
                self.assertFalse(result, "Expected readiness check to fail")
            except Exception:
                pass  # Expected due to network error
        
        # Check if all created event loops were properly closed
        self.assertEqual(len(created_loops), len(closed_loops),
                        f"Event loop resource leak detected. Created: {len(created_loops)}, "
                        f"Closed: {len(closed_loops)}")
        
        # Verify the specific loops that were created were also closed
        for created_loop in created_loops:
            self.assertIn(created_loop, closed_loops,
                         "Event loop was created but not properly closed")


if __name__ == '__main__':
    # Run the failing tests to demonstrate the issues
    unittest.main(verbosity=2)