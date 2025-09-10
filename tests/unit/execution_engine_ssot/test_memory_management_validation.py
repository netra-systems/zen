#!/usr/bin/env python
"""
UNIT TEST 4: Memory Management Validation for UserExecutionEngine SSOT

PURPOSE: Test that UserExecutionEngine properly cleans up resources and manages memory.
This validates the SSOT requirement that execution engines don't cause memory leaks or resource exhaustion.

Expected to FAIL before SSOT consolidation (proves memory management issues in multiple engines)
Expected to PASS after SSOT consolidation (proves UserExecutionEngine manages memory properly)

Business Impact: $500K+ ARR Golden Path protection - memory leaks cause system instability
"""

import asyncio
import gc
import psutil
import sys
import os
import threading
import time
import tracemalloc
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MemoryTracker:
    """Tracks memory usage and resource allocation for testing"""
    
    def __init__(self, name: str):
        self.name = name
        self.initial_memory = None
        self.peak_memory = 0
        self.final_memory = None
        self.process = psutil.Process()
        self.tracemalloc_started = False
        
    def start_tracking(self):
        """Start memory tracking"""
        try:
            tracemalloc.start()
            self.tracemalloc_started = True
            self.initial_memory = tracemalloc.get_traced_memory()[0]
        except RuntimeError:
            # Tracemalloc already started
            self.initial_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        
        # Also track process memory
        self.initial_process_memory = self.process.memory_info().rss
        
    def update_peak(self):
        """Update peak memory usage"""
        if tracemalloc.is_tracing():
            current_memory = tracemalloc.get_traced_memory()[0]
            self.peak_memory = max(self.peak_memory, current_memory)
    
    def stop_tracking(self):
        """Stop memory tracking and return stats"""
        if tracemalloc.is_tracing():
            self.final_memory = tracemalloc.get_traced_memory()[0]
            if self.tracemalloc_started:
                tracemalloc.stop()
        
        final_process_memory = self.process.memory_info().rss
        
        return {
            'name': self.name,
            'initial_memory': self.initial_memory or 0,
            'peak_memory': self.peak_memory,
            'final_memory': self.final_memory or 0,
            'memory_growth': (self.final_memory or 0) - (self.initial_memory or 0),
            'initial_process_memory': getattr(self, 'initial_process_memory', 0),
            'final_process_memory': final_process_memory,
            'process_memory_growth': final_process_memory - getattr(self, 'initial_process_memory', 0)
        }


class ResourceMonitoringWebSocket:
    """WebSocket mock that monitors resource usage"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events_sent = 0
        self.memory_at_events = []
        self.send_agent_event = AsyncMock(side_effect=self._track_event)
        
    async def _track_event(self, event_type: str, data: Dict[str, Any]):
        """Track memory usage at each event"""
        self.events_sent += 1
        if tracemalloc.is_tracing():
            current_memory = tracemalloc.get_traced_memory()[0]
            self.memory_at_events.append({
                'event_type': event_type,
                'memory': current_memory,
                'event_number': self.events_sent
            })


class TestMemoryManagementValidation(SSotAsyncTestCase):
    """Unit Test 4: Validate memory management in UserExecutionEngine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = "memory_test_user"
        self.test_session_id = "memory_test_session"
        
    def test_basic_memory_cleanup(self):
        """Test that UserExecutionEngine cleans up memory properly"""
        print("\n🔍 Testing basic memory cleanup in UserExecutionEngine...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        memory_violations = []
        tracker = MemoryTracker("basic_cleanup")
        tracker.start_tracking()
        
        # Create and use UserExecutionEngine
        engine_refs = []
        try:
            for i in range(10):
                # Create fresh WebSocket mock for each engine
                websocket_mock = ResourceMonitoringWebSocket(f"{self.test_user_id}_{i}")
                
                engine = UserExecutionEngine(
                    user_id=f"{self.test_user_id}_{i}",
                    session_id=f"{self.test_session_id}_{i}",
                    websocket_manager=websocket_mock
                )
                
                # Create weak reference to track garbage collection
                engine_refs.append(weakref.ref(engine))
                
                # Use the engine
                context = engine.get_user_context() if hasattr(engine, 'get_user_context') else {}
                
                # Test async operations
                async def use_engine():
                    await engine.send_websocket_event('test_memory', {'iteration': i})
                    if hasattr(engine, 'cleanup'):
                        engine.cleanup()
                
                asyncio.run(use_engine())
                tracker.update_peak()
                
                # Explicitly delete the engine
                del engine
                del websocket_mock
                
                # Force garbage collection every few iterations
                if i % 3 == 0:
                    gc.collect()
                
        except Exception as e:
            memory_violations.append(f"Engine creation/usage failed: {e}")
        
        # Final garbage collection
        gc.collect()
        
        # Check if engines were properly garbage collected
        alive_engines = sum(1 for ref in engine_refs if ref() is not None)
        if alive_engines > 2:  # Allow for some GC delay
            memory_violations.append(f"Memory leak: {alive_engines}/{len(engine_refs)} engines not garbage collected")
        else:
            print(f"  ✅ {len(engine_refs) - alive_engines}/{len(engine_refs)} engines properly garbage collected")
        
        # Get memory statistics
        memory_stats = tracker.stop_tracking()
        
        # Validate memory growth is reasonable
        memory_growth_mb = memory_stats['memory_growth'] / (1024 * 1024)
        process_growth_mb = memory_stats['process_memory_growth'] / (1024 * 1024)
        
        print(f"  ✅ Memory growth: {memory_growth_mb:.2f}MB (tracemalloc)")
        print(f"  ✅ Process memory growth: {process_growth_mb:.2f}MB")
        
        # Define reasonable thresholds
        if memory_growth_mb > 50:  # 50MB growth for 10 engines is excessive
            memory_violations.append(f"Excessive memory growth: {memory_growth_mb:.2f}MB")
        
        if process_growth_mb > 100:  # 100MB process growth is excessive
            memory_violations.append(f"Excessive process memory growth: {process_growth_mb:.2f}MB")
        
        # CRITICAL: Memory cleanup is essential for system stability
        if memory_violations:
            self.fail(f"Memory cleanup violations: {memory_violations}")
        
        print(f"  ✅ Basic memory cleanup validated")
    
    async def test_concurrent_memory_isolation(self):
        """Test memory isolation between concurrent UserExecutionEngine instances"""
        print("\n🔍 Testing concurrent memory isolation...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        isolation_violations = []
        tracker = MemoryTracker("concurrent_isolation")
        tracker.start_tracking()
        
        # Create concurrent engines and track their memory usage
        num_concurrent = 8
        memory_per_user = {}
        
        async def create_and_monitor_user(user_index: int):
            """Create user engine and monitor memory usage"""
            user_id = f"concurrent_user_{user_index}"
            websocket_mock = ResourceMonitoringWebSocket(user_id)
            
            try:
                # Track memory before engine creation
                pre_creation_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
                
                engine = UserExecutionEngine(
                    user_id=user_id,
                    session_id=f"concurrent_session_{user_index}",
                    websocket_manager=websocket_mock
                )
                
                # Track memory after engine creation
                post_creation_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
                
                # Perform some operations
                operations = [
                    ('agent_started', {'user_index': user_index}),
                    ('agent_thinking', {'thought': f'User {user_index} processing'}),
                    ('tool_executing', {'tool_name': f'user_tool_{user_index}'}),
                    ('tool_completed', {'tool_name': f'user_tool_{user_index}', 'result': 'success'}),
                    ('agent_completed', {'result': f'user_{user_index}_complete'})
                ]
                
                for event_type, event_data in operations:
                    await engine.send_websocket_event(event_type, event_data)
                    await asyncio.sleep(0.001)  # Small delay
                
                # Track memory after operations
                post_operations_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
                
                # Cleanup
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                
                # Track memory after cleanup
                post_cleanup_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
                
                # Store memory statistics for this user
                memory_per_user[user_id] = {
                    'pre_creation': pre_creation_memory,
                    'post_creation': post_creation_memory,
                    'post_operations': post_operations_memory,
                    'post_cleanup': post_cleanup_memory,
                    'creation_cost': post_creation_memory - pre_creation_memory,
                    'operation_cost': post_operations_memory - post_creation_memory,
                    'cleanup_recovery': post_operations_memory - post_cleanup_memory,
                    'events_sent': websocket_mock.events_sent
                }
                
                return f"success_{user_index}"
                
            except Exception as e:
                isolation_violations.append(f"User {user_index} failed: {e}")
                return f"error_{user_index}"
        
        # Run concurrent user simulations
        concurrent_tasks = [create_and_monitor_user(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Analyze memory usage patterns
        if memory_per_user:
            creation_costs = [stats['creation_cost'] for stats in memory_per_user.values()]
            operation_costs = [stats['operation_cost'] for stats in memory_per_user.values()]
            cleanup_recoveries = [stats['cleanup_recovery'] for stats in memory_per_user.values()]
            
            avg_creation_cost = sum(creation_costs) / len(creation_costs) if creation_costs else 0
            avg_operation_cost = sum(operation_costs) / len(operation_costs) if operation_costs else 0
            avg_cleanup_recovery = sum(cleanup_recoveries) / len(cleanup_recoveries) if cleanup_recoveries else 0
            
            print(f"  ✅ Average creation cost: {avg_creation_cost / 1024:.2f}KB per engine")
            print(f"  ✅ Average operation cost: {avg_operation_cost / 1024:.2f}KB per engine")
            print(f"  ✅ Average cleanup recovery: {avg_cleanup_recovery / 1024:.2f}KB per engine")
            
            # Check for memory consistency between users
            max_creation_cost = max(creation_costs) if creation_costs else 0
            min_creation_cost = min(creation_costs) if creation_costs else 0
            
            if max_creation_cost > min_creation_cost * 3:  # More than 3x difference is concerning
                isolation_violations.append(
                    f"Inconsistent memory usage between users: {min_creation_cost/1024:.2f}KB - {max_creation_cost/1024:.2f}KB"
                )
            
            # Check cleanup effectiveness
            poor_cleanup_users = [
                user_id for user_id, stats in memory_per_user.items() 
                if stats['cleanup_recovery'] < stats['operation_cost'] * 0.5  # Should recover at least 50%
            ]
            
            if poor_cleanup_users:
                isolation_violations.append(f"Poor cleanup for users: {poor_cleanup_users}")
        
        # Validate concurrent execution success
        success_count = sum(1 for result in results if isinstance(result, str) and result.startswith('success'))
        if success_count != num_concurrent:
            isolation_violations.append(f"Only {success_count}/{num_concurrent} concurrent users succeeded")
        
        print(f"  ✅ {success_count}/{num_concurrent} concurrent users completed successfully")
        
        # Get overall memory statistics
        memory_stats = tracker.stop_tracking()
        total_growth_mb = memory_stats['memory_growth'] / (1024 * 1024)
        
        print(f"  ✅ Total memory growth: {total_growth_mb:.2f}MB for {num_concurrent} concurrent users")
        
        # CRITICAL: Memory isolation prevents resource exhaustion
        if isolation_violations:
            self.fail(f"Concurrent memory isolation violations: {isolation_violations}")
        
        print(f"  ✅ Concurrent memory isolation validated")
    
    def test_resource_cleanup_validation(self):
        """Test that UserExecutionEngine properly cleans up all resources"""
        print("\n🔍 Testing resource cleanup validation...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        cleanup_violations = []
        
        # Track system resources before test
        initial_thread_count = threading.active_count()
        initial_handles = None
        
        try:
            process = psutil.Process()
            if hasattr(process, 'num_handles'):
                initial_handles = process.num_handles()
        except Exception:
            pass  # Handle count not available on all platforms
        
        # Create engines and test cleanup
        engines_created = []
        
        try:
            for i in range(15):  # Create multiple engines to test cleanup
                websocket_mock = ResourceMonitoringWebSocket(f"{self.test_user_id}_cleanup_{i}")
                
                engine = UserExecutionEngine(
                    user_id=f"{self.test_user_id}_cleanup_{i}",
                    session_id=f"{self.test_session_id}_cleanup_{i}",
                    websocket_manager=websocket_mock
                )
                
                engines_created.append(engine)
                
                # Use the engine
                context = engine.get_user_context() if hasattr(engine, 'get_user_context') else {}
                
                # Test async operations
                async def use_and_cleanup_engine():
                    await engine.send_websocket_event('cleanup_test', {'iteration': i})
                    
                    # Test cleanup method
                    if hasattr(engine, 'cleanup'):
                        engine.cleanup()
                        print(f"    ✅ Cleanup method called for engine {i}")
                    else:
                        cleanup_violations.append(f"Engine {i} missing cleanup method")
                
                asyncio.run(use_and_cleanup_engine())
                
                # Test resource state after cleanup
                if hasattr(engine, 'websocket_manager'):
                    ws_manager = engine.websocket_manager
                    if hasattr(ws_manager, 'events_sent'):
                        if ws_manager.events_sent == 0:
                            cleanup_violations.append(f"Engine {i} websocket manager not used")
        
        except Exception as e:
            cleanup_violations.append(f"Engine creation/cleanup test failed: {e}")
        
        # Clear all engine references
        engines_created.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Check thread count after cleanup
        final_thread_count = threading.active_count()
        thread_growth = final_thread_count - initial_thread_count
        
        if thread_growth > 2:  # Allow for some reasonable thread growth
            cleanup_violations.append(f"Thread leak detected: {thread_growth} extra threads")
        else:
            print(f"  ✅ Thread count stable: {initial_thread_count} -> {final_thread_count}")
        
        # Check handle count if available
        if initial_handles is not None:
            try:
                final_handles = process.num_handles()
                handle_growth = final_handles - initial_handles
                
                if handle_growth > 10:  # Allow for some handle growth
                    cleanup_violations.append(f"Handle leak detected: {handle_growth} extra handles")
                else:
                    print(f"  ✅ Handle count stable: {initial_handles} -> {final_handles}")
            except Exception:
                print(f"  ⚠️  Handle count check failed (platform limitation)")
        
        # Test cleanup method interface
        if engines_created:  # If any engines are still referenced
            test_engine = engines_created[0]
            
            # Test cleanup method exists and is callable
            if not hasattr(test_engine, 'cleanup'):
                cleanup_violations.append("UserExecutionEngine missing cleanup method")
            elif not callable(getattr(test_engine, 'cleanup')):
                cleanup_violations.append("cleanup method is not callable")
            else:
                # Test cleanup method can be called multiple times safely
                try:
                    test_engine.cleanup()
                    test_engine.cleanup()  # Should not fail on second call
                    print(f"  ✅ Cleanup method can be called multiple times safely")
                except Exception as e:
                    cleanup_violations.append(f"Cleanup method failed on repeated calls: {e}")
        
        # CRITICAL: Resource cleanup prevents system resource exhaustion
        if cleanup_violations:
            self.fail(f"Resource cleanup violations: {cleanup_violations}")
        
        print(f"  ✅ Resource cleanup validation completed")
    
    async def test_memory_stress_validation(self):
        """Test UserExecutionEngine under memory stress conditions"""
        print("\n🔍 Testing memory stress validation...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        stress_violations = []
        tracker = MemoryTracker("memory_stress")
        tracker.start_tracking()
        
        # Stress test parameters
        stress_iterations = 50
        concurrent_engines = 5
        events_per_engine = 10
        
        async def stress_test_engine(engine_index: int):
            """Stress test single engine with many operations"""
            user_id = f"stress_user_{engine_index}"
            websocket_mock = ResourceMonitoringWebSocket(user_id)
            
            try:
                engine = UserExecutionEngine(
                    user_id=user_id,
                    session_id=f"stress_session_{engine_index}",
                    websocket_manager=websocket_mock
                )
                
                # Perform many operations rapidly
                for event_num in range(events_per_engine):
                    event_type = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'][event_num % 5]
                    
                    await engine.send_websocket_event(event_type, {
                        'engine_index': engine_index,
                        'event_num': event_num,
                        'large_data': 'x' * 1000  # Add some data size
                    })
                    
                    # Update memory tracking
                    tracker.update_peak()
                
                # Cleanup
                if hasattr(engine, 'cleanup'):
                    engine.cleanup()
                
                return websocket_mock.events_sent
                
            except Exception as e:
                stress_violations.append(f"Stress test engine {engine_index} failed: {e}")
                return 0
        
        # Run stress test in batches to avoid overwhelming the system
        total_events_sent = 0
        
        for batch in range(stress_iterations // concurrent_engines):
            print(f"    Running stress batch {batch + 1}/{stress_iterations // concurrent_engines}")
            
            # Run concurrent engines
            batch_tasks = [stress_test_engine(batch * concurrent_engines + i) for i in range(concurrent_engines)]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Count successful events
            batch_events = sum(result for result in batch_results if isinstance(result, int))
            total_events_sent += batch_events
            
            # Force garbage collection between batches
            gc.collect()
            
            # Check memory growth between batches
            if tracemalloc.is_tracing():
                current_memory = tracemalloc.get_traced_memory()[0]
                memory_growth_mb = (current_memory - (tracker.initial_memory or 0)) / (1024 * 1024)
                
                # If memory grows too much, fail early
                if memory_growth_mb > 200:  # 200MB growth is excessive
                    stress_violations.append(f"Excessive memory growth during stress test: {memory_growth_mb:.2f}MB")
                    break
        
        # Get final memory statistics
        memory_stats = tracker.stop_tracking()
        
        final_growth_mb = memory_stats['memory_growth'] / (1024 * 1024)
        peak_growth_mb = (memory_stats['peak_memory'] - (memory_stats['initial_memory'] or 0)) / (1024 * 1024)
        
        print(f"  ✅ Total events sent: {total_events_sent}")
        print(f"  ✅ Final memory growth: {final_growth_mb:.2f}MB")
        print(f"  ✅ Peak memory growth: {peak_growth_mb:.2f}MB")
        
        # Validate stress test results
        expected_events = (stress_iterations // concurrent_engines) * concurrent_engines * events_per_engine
        if total_events_sent < expected_events * 0.8:  # Allow for some failures
            stress_violations.append(f"Stress test failed: only {total_events_sent}/{expected_events} events sent")
        
        # Check memory growth is reasonable
        if final_growth_mb > 100:  # 100MB final growth is excessive
            stress_violations.append(f"Excessive final memory growth: {final_growth_mb:.2f}MB")
        
        if peak_growth_mb > 150:  # 150MB peak growth is excessive
            stress_violations.append(f"Excessive peak memory growth: {peak_growth_mb:.2f}MB")
        
        # CRITICAL: Memory stress testing validates system stability
        if stress_violations:
            self.fail(f"Memory stress test violations: {stress_violations}")
        
        print(f"  ✅ Memory stress validation completed successfully")


if __name__ == '__main__':
    unittest.main(verbosity=2)