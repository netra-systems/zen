"""
Performance/Stability SSOT Tests - Issue #186 WebSocket Manager Fragmentation

Tests that FAIL initially to prove performance inconsistencies exist due to manager fragmentation.
After SSOT consolidation, these tests should PASS, proving consistent performance and stability.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Stability - Ensure consistent WebSocket performance across all users
- Value Impact: Reliable WebSocket performance prevents chat disruptions
- Revenue Impact: Performance consistency protects $500K+ ARR from degraded user experience

SSOT Violations This Module Proves:
1. Manager creation performance varies significantly between implementations
2. Concurrent usage causes race conditions between different factory patterns
3. Memory usage inconsistency between different manager types
4. WebSocket connection stability varies by manager implementation
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import time
import threading
import unittest
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
import psutil
import os

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""
    operation: str
    manager_type: str
    execution_times: List[float]
    memory_usage_before: float
    memory_usage_after: float
    success_count: int
    error_count: int
    errors: List[str]
    
    @property
    def avg_time(self) -> float:
        return statistics.mean(self.execution_times) if self.execution_times else 0.0
    
    @property
    def max_time(self) -> float:
        return max(self.execution_times) if self.execution_times else 0.0
    
    @property
    def min_time(self) -> float:
        return min(self.execution_times) if self.execution_times else 0.0
    
    @property
    def memory_delta(self) -> float:
        return self.memory_usage_after - self.memory_usage_before


class TestWebSocketManagerPerformanceStability(SSotAsyncTestCase):
    """
    Tests to prove WebSocket manager performance and stability violations exist.
    
    These tests are designed to FAIL initially, proving performance inconsistencies.
    After proper SSOT consolidation, they should PASS.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.process = psutil.Process(os.getpid())
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
        
    def _measure_operation(self, operation_name: str, manager_type: str, 
                          operation_func: callable, iterations: int = 10) -> PerformanceMetrics:
        """Measure performance of an operation with multiple iterations."""
        execution_times = []
        errors = []
        success_count = 0
        error_count = 0
        
        memory_before = self._get_memory_usage()
        
        for i in range(iterations):
            try:
                start_time = time.time()
                result = operation_func()
                end_time = time.time()
                
                execution_times.append(end_time - start_time)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Iteration {i}: {str(e)[:100]}")
                error_count += 1
        
        memory_after = self._get_memory_usage()
        
        return PerformanceMetrics(
            operation=operation_name,
            manager_type=manager_type,
            execution_times=execution_times,
            memory_usage_before=memory_before,
            memory_usage_after=memory_after,
            success_count=success_count,
            error_count=error_count,
            errors=errors
        )

    def test_manager_creation_performance_consistency(self):
        """
        Test all factory methods create managers within performance bounds.
        
        EXPECTED INITIAL STATE: FAIL - Different managers have different creation times
        EXPECTED POST-SSOT STATE: PASS - All managers have consistent creation performance
        
        VIOLATION BEING PROVED: Manager creation performance inconsistency
        """
        performance_violations = []
        performance_results = {}
        
        # Performance thresholds
        MAX_AVERAGE_CREATION_TIME = 0.01  # 10ms average
        MAX_SINGLE_CREATION_TIME = 0.05   # 50ms max
        MAX_VARIANCE_RATIO = 2.0          # Creation times shouldn't vary by more than 2x
        
        # Test different manager creation patterns
        manager_creation_tests = []
        
        # Test 1: Factory-based creation
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            def create_via_factory():
                factory = WebSocketManagerFactory()
                return factory.create_isolated_manager(
                    user_id=f"perf_user_{time.time()}",
                    connection_id=f"perf_conn_{time.time()}"
                )
            
            manager_creation_tests.append(('Factory-based', create_via_factory))
            
        except ImportError:
            performance_violations.append("WebSocketManagerFactory not available for performance testing")
        except Exception as e:
            performance_violations.append(f"Factory setup failed: {e}")

        # Test 2: Direct manager creation
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            def create_direct():
                return UnifiedWebSocketManager()
            
            manager_creation_tests.append(('Direct-creation', create_direct))
            
        except ImportError:
            performance_violations.append("UnifiedWebSocketManager not available for performance testing")
        except Exception as e:
            performance_violations.append(f"Direct manager setup failed: {e}")

        # Run performance tests
        for manager_type, creation_func in manager_creation_tests:
            try:
                metrics = self._measure_operation(
                    operation_name="manager_creation",
                    manager_type=manager_type,
                    operation_func=creation_func,
                    iterations=20  # More iterations for better statistics
                )
                
                performance_results[manager_type] = metrics
                
                # Check individual performance criteria
                if metrics.avg_time > MAX_AVERAGE_CREATION_TIME:
                    performance_violations.append(
                        f"{manager_type}: Average creation time {metrics.avg_time:.3f}s > {MAX_AVERAGE_CREATION_TIME}s"
                    )
                
                if metrics.max_time > MAX_SINGLE_CREATION_TIME:
                    performance_violations.append(
                        f"{manager_type}: Max creation time {metrics.max_time:.3f}s > {MAX_SINGLE_CREATION_TIME}s"
                    )
                
                if metrics.error_count > 0:
                    performance_violations.append(
                        f"{manager_type}: {metrics.error_count} creation failures out of 20 attempts. "
                        f"First error: {metrics.errors[0] if metrics.errors else 'unknown'}"
                    )
                
            except Exception as e:
                performance_violations.append(f"{manager_type} performance test failed: {e}")

        # Compare performance consistency between managers
        if len(performance_results) >= 2:
            manager_names = list(performance_results.keys())
            avg_times = [performance_results[name].avg_time for name in manager_names]
            
            if min(avg_times) > 0:
                variance_ratio = max(avg_times) / min(avg_times)
                if variance_ratio > MAX_VARIANCE_RATIO:
                    performance_violations.append(
                        f"Manager creation time variance too high: {variance_ratio:.1f}x > {MAX_VARIANCE_RATIO}x. "
                        f"Times: {dict(zip(manager_names, avg_times))}"
                    )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Manager creation performance should be consistent
        self.assertEqual(
            len(performance_violations), 0,
            f"SSOT VIOLATION: Manager creation performance issues: {performance_violations}. "
            f"Performance results: {[(name, f'{m.avg_time:.3f}s avg, {m.error_count} errors') for name, m in performance_results.items()]}. "
            f"This proves manager creation performance is inconsistent across implementations."
        )

    def test_concurrent_manager_creation_stability(self):
        """
        Test factory handles concurrent manager creation.
        
        EXPECTED INITIAL STATE: FAIL - Race conditions between different factory patterns
        EXPECTED POST-SSOT STATE: PASS - Thread-safe concurrent manager creation
        
        VIOLATION BEING PROVED: Concurrent usage causes race conditions and instability
        """
        concurrency_violations = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            factory = WebSocketManagerFactory()
            
            def create_manager_worker(worker_id: int) -> Tuple[int, bool, str]:
                """Worker function for concurrent manager creation."""
                try:
                    manager = factory.create_isolated_manager(
                        user_id=f"concurrent_user_{worker_id}",
                        connection_id=f"concurrent_conn_{worker_id}"
                    )
                    return (worker_id, True, "success")
                except Exception as e:
                    return (worker_id, False, str(e))
            
            # Test concurrent manager creation
            num_workers = 10
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all tasks
                futures = {executor.submit(create_manager_worker, i): i for i in range(num_workers)}
                
                # Collect results
                results = []
                for future in as_completed(futures):
                    try:
                        worker_id, success, message = future.result(timeout=5.0)
                        results.append((worker_id, success, message))
                    except Exception as e:
                        concurrency_violations.append(f"Worker future failed: {e}")

            # Analyze concurrent creation results
            successful_creations = [r for r in results if r[1]]
            failed_creations = [r for r in results if not r[1]]
            
            success_rate = len(successful_creations) / len(results) if results else 0
            
            # Check for race condition indicators
            if success_rate < 0.9:  # Less than 90% success rate indicates problems
                concurrency_violations.append(
                    f"Low concurrent creation success rate: {success_rate:.1%} ({len(successful_creations)}/{len(results)})"
                )
            
            # Analyze failure patterns
            if failed_creations:
                error_patterns = {}
                for worker_id, success, error_msg in failed_creations:
                    error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg[:50]
                    error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
                
                concurrency_violations.append(
                    f"Concurrent creation failures: {error_patterns}. "
                    f"First failure: {failed_creations[0][2][:100]}"
                )

        except ImportError:
            concurrency_violations.append("WebSocketManagerFactory not available for concurrency testing")
        except Exception as e:
            concurrency_violations.append(f"Concurrent creation test setup failed: {e}")

        # Test concurrent access to existing managers
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # Create a single manager and test concurrent access
            try:
                shared_manager = UnifiedWebSocketManager()
                
                def concurrent_operation_worker(worker_id: int) -> Tuple[int, bool, str]:
                    """Worker function for concurrent operations on shared manager."""
                    try:
                        # Test concurrent method calls
                        if hasattr(shared_manager, 'get_connection_count'):
                            count = shared_manager.get_connection_count()
                        elif hasattr(shared_manager, 'get_user_connections'):
                            connections = shared_manager.get_user_connections(f"user_{worker_id}")
                        else:
                            # Just test that manager can be accessed concurrently
                            str(shared_manager)
                        
                        return (worker_id, True, "success")
                    except Exception as e:
                        return (worker_id, False, str(e))
                
                # Test concurrent operations
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {executor.submit(concurrent_operation_worker, i): i for i in range(10)}
                    
                    operation_results = []
                    for future in as_completed(futures):
                        try:
                            result = future.result(timeout=3.0)
                            operation_results.append(result)
                        except Exception as e:
                            concurrency_violations.append(f"Concurrent operation failed: {e}")
                
                # Check concurrent operation results
                successful_ops = [r for r in operation_results if r[1]]
                failed_ops = [r for r in operation_results if not r[1]]
                
                if failed_ops:
                    concurrency_violations.append(
                        f"Concurrent operations failed: {len(failed_ops)}/{len(operation_results)}. "
                        f"First failure: {failed_ops[0][2][:100]}"
                    )
                    
            except Exception as e:
                concurrency_violations.append(f"Shared manager concurrent access test failed: {e}")
                
        except ImportError:
            pass  # Direct manager not available
        except Exception as e:
            concurrency_violations.append(f"Direct manager concurrency test setup failed: {e}")

        # ASSERTION THAT SHOULD FAIL INITIALLY: Concurrent access should be stable
        self.assertEqual(
            len(concurrency_violations), 0,
            f"SSOT VIOLATION: Concurrent manager usage issues: {concurrency_violations}. "
            f"This proves manager implementations are not thread-safe and cause race conditions."
        )

    def test_memory_usage_consistency(self):
        """
        Test all managers have consistent memory footprint.
        
        EXPECTED INITIAL STATE: FAIL - Different managers use different amounts of memory
        EXPECTED POST-SSOT STATE: PASS - All managers have similar memory usage patterns
        
        VIOLATION BEING PROVED: Memory usage inconsistency indicates architectural problems
        """
        memory_violations = []
        memory_results = {}
        
        # Memory thresholds
        MAX_MEMORY_PER_MANAGER = 5.0    # 5MB per manager instance
        MAX_MEMORY_VARIANCE_RATIO = 3.0  # Memory usage shouldn't vary by more than 3x
        MAX_MEMORY_LEAK_PER_OPERATION = 0.5  # 0.5MB max leak per operation
        
        # Test memory usage of different managers
        manager_memory_tests = []
        
        # Test 1: Factory-created managers
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            def create_multiple_factory_managers():
                factory = WebSocketManagerFactory()
                managers = []
                for i in range(5):
                    try:
                        manager = factory.create_isolated_manager(
                            user_id=f"memory_user_{i}",
                            connection_id=f"memory_conn_{i}"
                        )
                        managers.append(manager)
                    except Exception:
                        pass  # Expected failures due to constructor issues
                return managers
            
            manager_memory_tests.append(('Factory-managers', create_multiple_factory_managers))
            
        except ImportError:
            memory_violations.append("WebSocketManagerFactory not available for memory testing")
        except Exception as e:
            memory_violations.append(f"Factory memory test setup failed: {e}")

        # Test 2: Direct managers
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            def create_multiple_direct_managers():
                managers = []
                for i in range(5):
                    try:
                        manager = UnifiedWebSocketManager()
                        managers.append(manager)
                    except Exception as e:
                        pass  # Some failures expected
                return managers
            
            manager_memory_tests.append(('Direct-managers', create_multiple_direct_managers))
            
        except ImportError:
            memory_violations.append("UnifiedWebSocketManager not available for memory testing")
        except Exception as e:
            memory_violations.append(f"Direct manager memory test setup failed: {e}")

        # Run memory tests
        for manager_type, creation_func in manager_memory_tests:
            try:
                metrics = self._measure_operation(
                    operation_name="manager_memory_usage",
                    manager_type=manager_type,
                    operation_func=creation_func,
                    iterations=3  # Fewer iterations for memory testing
                )
                
                memory_results[manager_type] = metrics
                
                # Check memory usage criteria
                if metrics.memory_delta > MAX_MEMORY_PER_MANAGER:
                    memory_violations.append(
                        f"{manager_type}: Memory usage {metrics.memory_delta:.1f}MB > {MAX_MEMORY_PER_MANAGER}MB"
                    )
                
                # Check for memory leaks (consistent memory growth)
                if len(metrics.execution_times) > 1:
                    memory_leak_per_op = metrics.memory_delta / len(metrics.execution_times)
                    if memory_leak_per_op > MAX_MEMORY_LEAK_PER_OPERATION:
                        memory_violations.append(
                            f"{manager_type}: Potential memory leak {memory_leak_per_op:.2f}MB per operation"
                        )
                
            except Exception as e:
                memory_violations.append(f"{manager_type} memory test failed: {e}")

        # Compare memory usage consistency between managers
        if len(memory_results) >= 2:
            manager_names = list(memory_results.keys())
            memory_deltas = [memory_results[name].memory_delta for name in manager_names]
            
            positive_deltas = [delta for delta in memory_deltas if delta > 0]
            if positive_deltas and min(positive_deltas) > 0:
                variance_ratio = max(positive_deltas) / min(positive_deltas)
                if variance_ratio > MAX_MEMORY_VARIANCE_RATIO:
                    memory_violations.append(
                        f"Manager memory usage variance too high: {variance_ratio:.1f}x > {MAX_MEMORY_VARIANCE_RATIO}x. "
                        f"Memory usage: {dict(zip(manager_names, memory_deltas))}"
                    )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Memory usage should be consistent
        self.assertEqual(
            len(memory_violations), 0,
            f"SSOT VIOLATION: Manager memory usage inconsistencies: {memory_violations}. "
            f"Memory results: {[(name, f'{m.memory_delta:.1f}MB delta') for name, m in memory_results.items()]}. "
            f"This proves managers have inconsistent memory usage patterns indicating architectural issues."
        )

    def test_websocket_connection_stability_across_managers(self):
        """
        Test WebSocket stability regardless of manager type.
        
        EXPECTED INITIAL STATE: FAIL - Different connection handling patterns
        EXPECTED POST-SSOT STATE: PASS - Consistent connection handling across all managers
        
        VIOLATION BEING PROVED: Connection stability varies by manager implementation
        """
        stability_violations = []
        
        # Mock WebSocket connections for testing
        class MockWebSocket:
            def __init__(self, connection_id: str):
                self.connection_id = connection_id
                self.messages_sent = []
                self.is_closed = False
                
            async def send_json(self, data: Dict[str, Any]) -> None:
                if not self.is_closed:
                    self.messages_sent.append(data)
                    
            def close(self) -> None:
                self.is_closed = True
        
        # Test connection stability with different managers
        managers_to_test = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory = WebSocketManagerFactory()
            managers_to_test.append(('Factory', factory, True))
        except ImportError:
            pass
        except Exception as e:
            stability_violations.append(f"Factory manager unavailable: {e}")
            
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            direct_manager = UnifiedWebSocketManager()
            managers_to_test.append(('Direct', direct_manager, False))
        except Exception as e:
            stability_violations.append(f"Direct manager unavailable: {e}")

        # Test connection handling for each manager
        connection_test_results = {}
        
        for manager_name, manager, is_factory in managers_to_test:
            try:
                test_results = {
                    'connections_added': 0,
                    'connections_failed': 0,
                    'messages_sent': 0,
                    'message_failures': 0,
                    'errors': []
                }
                
                # Get actual manager instance
                if is_factory:
                    try:
                        actual_manager = manager.create_isolated_manager(
                            user_id="stability_user",
                            connection_id="stability_conn"
                        )
                    except Exception as e:
                        stability_violations.append(f"{manager_name} manager creation failed: {e}")
                        continue
                else:
                    actual_manager = manager
                
                # Test connection addition stability
                mock_websockets = []
                for i in range(5):
                    mock_ws = MockWebSocket(f"ws_{i}")
                    mock_websockets.append(mock_ws)
                    
                    try:
                        # Try different connection signatures
                        if hasattr(actual_manager, 'add_connection'):
                            try:
                                # New signature (connection object)
                                result = actual_manager.add_connection(mock_ws)
                                test_results['connections_added'] += 1
                            except TypeError:
                                # Old signature (user_id, websocket)
                                result = actual_manager.add_connection(f"user_{i}", mock_ws)
                                test_results['connections_added'] += 1
                        else:
                            test_results['errors'].append("add_connection method missing")
                            
                    except Exception as e:
                        test_results['connections_failed'] += 1
                        test_results['errors'].append(f"Connection {i} failed: {str(e)[:50]}")
                
                # Test message sending stability
                for i, mock_ws in enumerate(mock_websockets):
                    try:
                        if hasattr(actual_manager, 'send_message'):
                            result = actual_manager.send_message(
                                f"user_{i}", 
                                {"type": "test", "content": f"message_{i}"}
                            )
                            test_results['messages_sent'] += 1
                        elif hasattr(actual_manager, 'send_to_user'):
                            result = actual_manager.send_to_user(
                                f"user_{i}",
                                {"type": "test", "content": f"message_{i}"}
                            )
                            test_results['messages_sent'] += 1
                        else:
                            test_results['errors'].append("No message sending method found")
                            
                    except Exception as e:
                        test_results['message_failures'] += 1
                        test_results['errors'].append(f"Message {i} failed: {str(e)[:50]}")
                
                connection_test_results[manager_name] = test_results
                
            except Exception as e:
                stability_violations.append(f"{manager_name} connection stability test failed: {e}")

        # Analyze connection stability results
        if connection_test_results:
            # Check for consistent connection handling
            connection_success_rates = {}
            message_success_rates = {}
            
            for manager_name, results in connection_test_results.items():
                total_connections = results['connections_added'] + results['connections_failed']
                total_messages = results['messages_sent'] + results['message_failures']
                
                if total_connections > 0:
                    connection_success_rates[manager_name] = results['connections_added'] / total_connections
                if total_messages > 0:
                    message_success_rates[manager_name] = results['messages_sent'] / total_messages
            
            # Check for significant differences in success rates
            if len(connection_success_rates) > 1:
                rates = list(connection_success_rates.values())
                if max(rates) - min(rates) > 0.3:  # More than 30% difference
                    stability_violations.append(
                        f"Connection success rate variance: {connection_success_rates}"
                    )
            
            if len(message_success_rates) > 1:
                rates = list(message_success_rates.values())
                if max(rates) - min(rates) > 0.3:  # More than 30% difference
                    stability_violations.append(
                        f"Message success rate variance: {message_success_rates}"
                    )
            
            # Check for common failure patterns
            all_errors = []
            for results in connection_test_results.values():
                all_errors.extend(results['errors'])
            
            if all_errors:
                stability_violations.append(
                    f"Connection stability errors found: {len(all_errors)} total errors. "
                    f"Sample errors: {all_errors[:3]}"
                )

        # ASSERTION THAT SHOULD FAIL INITIALLY: Connection stability should be consistent
        self.assertEqual(
            len(stability_violations), 0,
            f"SSOT VIOLATION: WebSocket connection stability issues: {stability_violations}. "
            f"Connection test results: {connection_test_results}. "
            f"This proves connection handling is not consistent across manager implementations."
        )


if __name__ == '__main__':
    import unittest
    unittest.main()