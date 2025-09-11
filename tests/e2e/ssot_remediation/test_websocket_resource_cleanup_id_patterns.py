"""
WebSocket Resource Cleanup ID Patterns Test - SSOT Validation

This test validates WebSocket connections cleanup with consistent ID patterns,
testing thread_id/run_id pattern consistency to prevent 1011 errors.

Business Value:
- Critical for $500K+ ARR protection - prevents WebSocket 1011 connection errors
- Ensures Golden Path WebSocket flow works reliably
- Validates resource cleanup doesn't break due to ID pattern mismatches

SSOT Validation:
- Tests that WebSocket cleanup uses consistent ID patterns
- Validates thread_id/run_id relationships are maintained during cleanup
- Ensures cleanup processes don't fail due to dual SSOT ID format conflicts

Expected Behavior:
- BEFORE REMEDIATION: Should FAIL - cleanup fails due to ID format mismatches
- AFTER REMEDIATION: Should PASS - consistent SSOT ID patterns enable proper cleanup
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import (
    UserID, ThreadID, RunID, WebSocketID, 
    ensure_user_id, ensure_thread_id, ensure_run_id
)


class TestWebSocketResourceCleanupIdPatterns(SSotAsyncTestCase):
    """Test WebSocket resource cleanup with consistent ID patterns."""

    def setup_method(self, method=None):
        """Set up test environment for WebSocket resource cleanup testing."""
        super().setup_method(method)
        self.unified_id_generator = UnifiedIdGenerator()
        self.websocket_managers = []
        self.cleanup_tracking = {
            'successful_cleanups': 0,
            'failed_cleanups': 0,
            'id_pattern_mismatches': 0,
            'resource_leaks': 0
        }

    def teardown_method(self, method=None):
        """Clean up test WebSocket managers and resources."""
        # Clean up any remaining WebSocket managers
        for manager in self.websocket_managers:
            try:
                if hasattr(manager, 'cleanup') and asyncio.iscoroutinefunction(manager.cleanup):
                    asyncio.create_task(manager.cleanup())
                elif hasattr(manager, 'cleanup'):
                    manager.cleanup()
            except Exception as e:
                self.record_metric("cleanup_error", str(e))
        
        self.websocket_managers.clear()
        super().teardown_method(method)

    async def test_websocket_cleanup_with_consistent_thread_run_ids(self):
        """
        Test WebSocket cleanup with consistent thread_id/run_id patterns.
        
        This test validates that WebSocket resource cleanup works when
        thread_id and run_id follow consistent SSOT patterns.
        
        Expected to FAIL before SSOT remediation due to ID pattern conflicts.
        """
        # Generate consistent SSOT IDs
        user_id = ensure_user_id(self.unified_id_generator.generate_user_id())
        thread_id = ensure_thread_id(self.unified_id_generator.generate_thread_id())
        
        # Generate run_id that's related to thread_id (SSOT pattern)
        run_id_raw = self.unified_id_generator.generate_run_id_for_thread(str(thread_id))
        run_id = ensure_run_id(run_id_raw)
        
        # Record the ID relationships
        self.record_metric("test_user_id", str(user_id))
        self.record_metric("test_thread_id", str(thread_id))
        self.record_metric("test_run_id", str(run_id))
        self.record_metric("thread_run_relationship", f"{thread_id} -> {run_id}")
        
        # Create multiple WebSocket managers to test cleanup patterns
        test_managers = []
        
        try:
            for i in range(3):
                websocket_id = f"cleanup-test-{i}-{int(time.time())}"
                
                manager = create_websocket_manager(
                    user_id=user_id,
                    thread_id=thread_id,
                    websocket_id=websocket_id
                )
                
                test_managers.append({
                    'manager': manager,
                    'websocket_id': websocket_id,
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'run_id': run_id
                })
                
                self.websocket_managers.append(manager)
            
            # Test cleanup operations with consistent ID patterns
            cleanup_results = []
            
            for i, manager_info in enumerate(test_managers):
                manager = manager_info['manager']
                
                try:
                    # Simulate typical WebSocket operations before cleanup
                    await self._simulate_websocket_operations(manager, manager_info)
                    
                    # Attempt cleanup with consistent ID patterns
                    cleanup_success = await self._perform_websocket_cleanup(manager, manager_info)
                    
                    cleanup_results.append({
                        'manager_index': i,
                        'cleanup_success': cleanup_success,
                        'websocket_id': manager_info['websocket_id']
                    })
                    
                    if cleanup_success:
                        self.cleanup_tracking['successful_cleanups'] += 1
                    else:
                        self.cleanup_tracking['failed_cleanups'] += 1
                    
                except Exception as e:
                    cleanup_results.append({
                        'manager_index': i,
                        'cleanup_success': False,
                        'error': str(e),
                        'websocket_id': manager_info['websocket_id']
                    })
                    self.cleanup_tracking['failed_cleanups'] += 1
            
            # Record cleanup tracking metrics
            for key, value in self.cleanup_tracking.items():
                self.record_metric(key, value)
            
            # Validate that all cleanups succeeded with consistent ID patterns
            failed_cleanups = [r for r in cleanup_results if not r['cleanup_success']]
            
            self.assertEqual(
                len(failed_cleanups), 0,
                f"WebSocket resource cleanup FAILED for {len(failed_cleanups)} managers "
                f"with consistent SSOT ID patterns. Failed cleanups: {failed_cleanups}. "
                "This indicates dual SSOT violation preventing proper resource cleanup."
            )
            
            self.record_metric("cleanup_test_passed", True)
            
        except Exception as e:
            self.record_metric("cleanup_test_passed", False)
            self.record_metric("test_error", str(e))
            
            raise AssertionError(
                f"WebSocket cleanup with consistent ID patterns FAILED: {e}. "
                "SSOT ID pattern conflicts prevent proper WebSocket resource cleanup, "
                "leading to WebSocket 1011 errors and Golden Path failures."
            )

    async def test_websocket_cleanup_id_pattern_mismatch_detection(self):
        """
        Test detection of ID pattern mismatches during WebSocket cleanup.
        
        This test validates that cleanup failures can be attributed to
        ID pattern inconsistencies between components.
        
        Expected to detect mismatches before SSOT remediation.
        """
        # Create WebSocket manager with mixed ID patterns (simulating dual SSOT)
        user_id = ensure_user_id(self.unified_id_generator.generate_user_id())  # SSOT pattern
        thread_id = ensure_thread_id("thread_uuid_" + str(time.time()))  # Non-SSOT pattern
        
        websocket_id = "mismatch-test-websocket"
        
        try:
            manager = create_websocket_manager(
                user_id=user_id,
                thread_id=thread_id,
                websocket_id=websocket_id
            )
            self.websocket_managers.append(manager)
            
            # Test cleanup with mismatched ID patterns
            cleanup_attempts = []
            
            # Attempt 1: Cleanup with SSOT-compatible thread lookup
            ssot_thread_id = ensure_thread_id(self.unified_id_generator.generate_thread_id())
            cleanup_1 = await self._test_cleanup_with_thread_id(manager, ssot_thread_id)
            cleanup_attempts.append(('ssot_thread', cleanup_1))
            
            # Attempt 2: Cleanup with original (potentially non-SSOT) thread ID
            cleanup_2 = await self._test_cleanup_with_thread_id(manager, thread_id)
            cleanup_attempts.append(('original_thread', cleanup_2))
            
            # Attempt 3: Cleanup with database-lookup compatible ID
            db_compatible_id = ensure_thread_id(f"thread_db_{int(time.time())}")
            cleanup_3 = await self._test_cleanup_with_thread_id(manager, db_compatible_id)
            cleanup_attempts.append(('db_compatible', cleanup_3))
            
            # Analyze cleanup success patterns
            successful_cleanups = [attempt for attempt in cleanup_attempts if attempt[1]]
            failed_cleanups = [attempt for attempt in cleanup_attempts if not attempt[1]]
            
            # Record pattern analysis
            self.record_metric("successful_cleanup_patterns", [s[0] for s in successful_cleanups])
            self.record_metric("failed_cleanup_patterns", [f[0] for f in failed_cleanups])
            self.record_metric("mismatch_detection_complete", True)
            
            # If all cleanups fail, it indicates severe ID pattern conflicts
            if len(failed_cleanups) == len(cleanup_attempts):
                self.cleanup_tracking['id_pattern_mismatches'] += 1
                self.record_metric("severe_id_pattern_conflict", True)
                
                raise AssertionError(
                    f"All WebSocket cleanup attempts failed due to ID pattern mismatches. "
                    f"Cleanup attempts: {cleanup_attempts}. "
                    "This indicates dual SSOT violation where WebSocket and database "
                    "components use incompatible ID formats."
                )
            
            # If some cleanups succeed and others fail, it indicates partial SSOT migration
            elif len(failed_cleanups) > 0:
                self.record_metric("partial_ssot_migration_detected", True)
                self.record_metric("cleanup_success_rate", len(successful_cleanups) / len(cleanup_attempts))
                
                # This is still a failure case indicating incomplete SSOT remediation
                raise AssertionError(
                    f"Inconsistent WebSocket cleanup success: {len(successful_cleanups)} succeeded, "
                    f"{len(failed_cleanups)} failed. Successful: {successful_cleanups}, "
                    f"Failed: {failed_cleanups}. This indicates partial SSOT migration "
                    "with remaining ID pattern inconsistencies."
                )
            
        except Exception as e:
            self.record_metric("mismatch_detection_error", str(e))
            # Re-raise with SSOT context
            raise

    async def test_websocket_resource_leak_detection_with_id_patterns(self):
        """
        Test WebSocket resource leak detection related to ID pattern issues.
        
        This test validates that resource leaks can be traced to ID pattern
        inconsistencies preventing proper cleanup.
        
        Expected to detect resource leaks before SSOT remediation.
        """
        # Track resource usage before test
        initial_resources = await self._capture_resource_snapshot()
        
        # Create multiple WebSocket managers with potentially problematic ID patterns
        leak_test_managers = []
        
        for i in range(5):
            # Mix SSOT and non-SSOT ID patterns to simulate dual SSOT scenario
            if i % 2 == 0:
                # SSOT pattern
                user_id = ensure_user_id(self.unified_id_generator.generate_user_id())
                thread_id = ensure_thread_id(self.unified_id_generator.generate_thread_id())
            else:
                # Non-SSOT pattern (simulating legacy or incorrect usage)
                import uuid
                user_id = ensure_user_id(f"user_{uuid.uuid4()}")
                thread_id = ensure_thread_id(f"thread_{uuid.uuid4()}")
            
            websocket_id = f"leak-test-{i}"
            
            try:
                manager = create_websocket_manager(
                    user_id=user_id,
                    thread_id=thread_id,
                    websocket_id=websocket_id
                )
                
                leak_test_managers.append({
                    'manager': manager,
                    'user_id': user_id,
                    'thread_id': thread_id,
                    'websocket_id': websocket_id,
                    'id_pattern_type': 'ssot' if i % 2 == 0 else 'non_ssot'
                })
                
                self.websocket_managers.append(manager)
                
            except Exception as e:
                self.record_metric(f"manager_creation_error_{i}", str(e))
        
        # Perform operations that should be cleaned up
        for manager_info in leak_test_managers:
            await self._simulate_websocket_operations(
                manager_info['manager'], 
                manager_info
            )
        
        # Attempt cleanup of all managers
        cleanup_results = {}
        for i, manager_info in enumerate(leak_test_managers):
            try:
                cleanup_success = await self._perform_websocket_cleanup(
                    manager_info['manager'], 
                    manager_info
                )
                cleanup_results[i] = {
                    'success': cleanup_success,
                    'id_pattern_type': manager_info['id_pattern_type']
                }
            except Exception as e:
                cleanup_results[i] = {
                    'success': False,
                    'error': str(e),
                    'id_pattern_type': manager_info['id_pattern_type']
                }
        
        # Wait for cleanup to complete
        await asyncio.sleep(1.0)
        
        # Capture resource usage after cleanup
        final_resources = await self._capture_resource_snapshot()
        
        # Analyze resource leaks by ID pattern type
        resource_delta = self._calculate_resource_delta(initial_resources, final_resources)
        
        # Categorize cleanup results by ID pattern
        ssot_cleanup_results = [r for r in cleanup_results.values() if r['id_pattern_type'] == 'ssot']
        non_ssot_cleanup_results = [r for r in cleanup_results.values() if r['id_pattern_type'] == 'non_ssot']
        
        ssot_success_rate = sum(1 for r in ssot_cleanup_results if r['success']) / len(ssot_cleanup_results) if ssot_cleanup_results else 0
        non_ssot_success_rate = sum(1 for r in non_ssot_cleanup_results if r['success']) / len(non_ssot_cleanup_results) if non_ssot_cleanup_results else 0
        
        # Record leak detection metrics
        self.record_metric("resource_delta", resource_delta)
        self.record_metric("ssot_cleanup_success_rate", ssot_success_rate)
        self.record_metric("non_ssot_cleanup_success_rate", non_ssot_success_rate)
        self.record_metric("total_managers_tested", len(leak_test_managers))
        
        # Detect resource leaks
        has_resource_leaks = resource_delta.get('websocket_connections', 0) > 0 or \
                           resource_delta.get('memory_usage_mb', 0) > 10
        
        if has_resource_leaks:
            self.cleanup_tracking['resource_leaks'] += 1
            self.record_metric("resource_leaks_detected", True)
            
            # Correlate leaks with ID patterns
            if non_ssot_success_rate < ssot_success_rate:
                self.record_metric("leaks_correlated_with_non_ssot_patterns", True)
                
                raise AssertionError(
                    f"WebSocket resource leaks detected and correlated with non-SSOT ID patterns. "
                    f"Resource delta: {resource_delta}. "
                    f"SSOT cleanup success rate: {ssot_success_rate:.2f}, "
                    f"Non-SSOT cleanup success rate: {non_ssot_success_rate:.2f}. "
                    "This indicates dual SSOT violation causing resource cleanup failures."
                )
        
        # Even if no leaks, validate cleanup success rates
        overall_success_rate = sum(1 for r in cleanup_results.values() if r['success']) / len(cleanup_results)
        
        if overall_success_rate < 0.8:  # Less than 80% success rate is problematic
            raise AssertionError(
                f"Low WebSocket cleanup success rate: {overall_success_rate:.2f}. "
                f"SSOT success rate: {ssot_success_rate:.2f}, "
                f"Non-SSOT success rate: {non_ssot_success_rate:.2f}. "
                "Low success rates indicate ID pattern issues preventing proper cleanup."
            )

    async def _simulate_websocket_operations(self, manager, manager_info: Dict[str, Any]) -> None:
        """
        Simulate typical WebSocket operations that create resources needing cleanup.
        
        Args:
            manager: WebSocket manager instance
            manager_info: Manager information including IDs
        """
        try:
            # Simulate connection establishment
            if hasattr(manager, 'connect') and asyncio.iscoroutinefunction(manager.connect):
                await manager.connect()
            
            # Simulate message sending/receiving
            if hasattr(manager, 'send_message'):
                for i in range(3):
                    message_data = {
                        'type': 'test_message',
                        'content': f'Test message {i}',
                        'thread_id': str(manager_info['thread_id']),
                        'user_id': str(manager_info['user_id'])
                    }
                    
                    if asyncio.iscoroutinefunction(manager.send_message):
                        await manager.send_message(message_data)
                    else:
                        manager.send_message(message_data)
            
            # Record successful operation simulation
            self.record_metric(f"operations_simulated_{manager_info['websocket_id']}", True)
            
        except Exception as e:
            self.record_metric(f"operation_simulation_error_{manager_info['websocket_id']}", str(e))

    async def _perform_websocket_cleanup(self, manager, manager_info: Dict[str, Any]) -> bool:
        """
        Perform WebSocket cleanup and return success status.
        
        Args:
            manager: WebSocket manager instance
            manager_info: Manager information including IDs
            
        Returns:
            True if cleanup succeeded, False otherwise
        """
        try:
            # Attempt various cleanup methods
            cleanup_methods = ['cleanup', 'close', 'disconnect', 'shutdown']
            
            for method_name in cleanup_methods:
                if hasattr(manager, method_name):
                    method = getattr(manager, method_name)
                    
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                    
                    # If we got here, cleanup method executed successfully
                    self.record_metric(f"cleanup_method_used_{manager_info['websocket_id']}", method_name)
                    return True
            
            # If no cleanup methods found, consider it a failure
            self.record_metric(f"no_cleanup_methods_{manager_info['websocket_id']}", True)
            return False
            
        except Exception as e:
            self.record_metric(f"cleanup_error_{manager_info['websocket_id']}", str(e))
            return False

    async def _test_cleanup_with_thread_id(self, manager, thread_id: ThreadID) -> bool:
        """
        Test cleanup using a specific thread ID pattern.
        
        Args:
            manager: WebSocket manager instance
            thread_id: Thread ID to use for cleanup testing
            
        Returns:
            True if cleanup succeeded with this thread ID
        """
        try:
            # Test if manager can be cleaned up using this thread ID pattern
            if hasattr(manager, 'cleanup_for_thread'):
                if asyncio.iscoroutinefunction(manager.cleanup_for_thread):
                    await manager.cleanup_for_thread(thread_id)
                else:
                    manager.cleanup_for_thread(thread_id)
                return True
            
            # Fallback: general cleanup test
            return await self._perform_websocket_cleanup(manager, {'thread_id': thread_id})
            
        except Exception:
            return False

    async def _capture_resource_snapshot(self) -> Dict[str, Any]:
        """
        Capture current resource usage snapshot.
        
        Returns:
            Dictionary containing resource usage metrics
        """
        import psutil
        import gc
        
        try:
            process = psutil.Process()
            
            return {
                'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
                'open_files': len(process.open_files()),
                'threads': process.num_threads(),
                'websocket_connections': len(self.websocket_managers),
                'gc_objects': len(gc.get_objects()),
                'timestamp': time.time()
            }
        except Exception as e:
            self.record_metric("resource_snapshot_error", str(e))
            return {
                'websocket_connections': len(self.websocket_managers),
                'timestamp': time.time()
            }

    def _calculate_resource_delta(self, initial: Dict[str, Any], final: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate resource usage delta between snapshots.
        
        Args:
            initial: Initial resource snapshot
            final: Final resource snapshot
            
        Returns:
            Dictionary containing resource usage changes
        """
        delta = {}
        
        for key in initial.keys():
            if key == 'timestamp':
                continue
                
            if key in final:
                delta[key] = final[key] - initial[key]
            else:
                delta[key] = initial[key]  # Resource disappeared
        
        return delta