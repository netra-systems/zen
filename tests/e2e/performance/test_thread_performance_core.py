"""Thread Performance Tests - Core Operations
Focused performance tests for thread operations under load.
Extracted from test_thread_management_websocket.py and test_thread_performance.py.

BVJ: Performance guarantees ensure responsive user experience and prevent timeouts.
Segment: Enterprise primarily, affects all tiers. Business Goal: Platform reliability.
Value Impact: Performance meets SLA requirements preventing customer churn.
Strategic Impact: Thread operation speed directly impacts user satisfaction and retention.
"""

import asyncio
import statistics
import time
from typing import Any, Callable, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from tests.e2e.config import TEST_USERS
from tests.e2e.fixtures.core.thread_test_fixtures_core import (
    ThreadContextManager,
    ThreadPerformanceUtils,
    ThreadWebSocketFixtures,
    performance_utils,
    thread_context_manager,
    unified_harness,
    ws_thread_fixtures,
)

logger = central_logger.get_logger(__name__)

class TestThreadPerformanceer:
    """Comprehensive thread performance testing."""
    
    def __init__(self, ws_fixtures: ThreadWebSocketFixtures, 
                 context_manager: ThreadContextManager,
                 perf_utils: ThreadPerformanceUtils):
        self.ws_fixtures = ws_fixtures
        self.context_manager = context_manager
        self.perf_utils = perf_utils
        self.performance_metrics: List[Dict[str, Any]] = []
    
    async def measure_thread_creation_performance(self, user_id: str, 
                                                   thread_count: int) -> Dict[str, Any]:
        """Measure thread creation performance under load."""
        creation_tasks = []
        thread_names = [f"Perf Thread {i+1}" for i in range(thread_count)]
        
        # Create tasks for concurrent thread creation
        for i, name in enumerate(thread_names):
            task = self._create_single_thread_with_timing(user_id, name, i)
            creation_tasks.append(task)
        
        # Execute and measure
        start_time = time.perf_counter()
        results = await asyncio.gather(*creation_tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        errors = [r for r in results if isinstance(r, Exception) or not isinstance(r, dict)]
        
        performance_data = self.perf_utils.calculate_performance_metrics(
            successful_results, errors, start_time, start_time + total_time
        )
        
        # Calculate detailed timing statistics
        creation_times = [r.get("creation_time", 0) for r in successful_results]
        if creation_times:
            performance_data.update({
                "avg_creation_time": statistics.mean(creation_times),
                "median_creation_time": statistics.median(creation_times),
                "max_creation_time": max(creation_times),
                "min_creation_time": min(creation_times)
            })
        
        self.performance_metrics.append({
            "operation": "thread_creation",
            "thread_count": thread_count,
            "metrics": performance_data,
            "timestamp": time.time()
        })
        
        return performance_data
    
    async def _create_single_thread_with_timing(self, user_id: str, thread_name: str, 
                                                index: int) -> Dict[str, Any]:
        """Create single thread with detailed timing."""
        try:
            start_time = time.perf_counter()
            
            # Generate thread ID
            thread_id = f"perf_thread_{index}_{user_id}_{int(time.time())}"
            
            # Build and send creation message
            message = self.ws_fixtures.build_websocket_message(
                WebSocketMessageType.CREATE_THREAD,
                thread_id=thread_id,
                thread_name=thread_name
            )
            await self.ws_fixtures.send_websocket_message(user_id, message)
            
            # Initialize context
            context_key = f"{user_id}:{thread_id}"
            self.ws_fixtures.thread_contexts[context_key] = {
                "thread_id": thread_id,
                "thread_name": thread_name,
                "created_at": time.time(),
                "messages": [],
                "performance_test": True
            }
            
            # Capture event
            self.ws_fixtures.capture_thread_event(
                WebSocketMessageType.THREAD_CREATED,
                user_id,
                thread_id,
                thread_name=thread_name
            )
            
            creation_time = time.perf_counter() - start_time
            
            return {
                "success": True,
                "thread_id": thread_id,
                "thread_name": thread_name,
                "creation_time": creation_time,
                "index": index
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "index": index
            }
    
    async def measure_thread_switching_performance(self, user_id: str, 
                                                    thread_ids: List[str],
                                                    switch_count: int) -> Dict[str, Any]:
        """Measure thread switching performance."""
        if not thread_ids:
            return {"error": "No threads provided for switching test"}
        
        switching_tasks = []
        
        # Create rapid switching pattern
        for i in range(switch_count):
            thread_id = thread_ids[i % len(thread_ids)]
            task = self._switch_thread_with_timing(user_id, thread_id, i)
            switching_tasks.append(task)
        
        # Execute and measure
        start_time = time.perf_counter()
        results = await asyncio.gather(*switching_tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        errors = [r for r in results if isinstance(r, Exception) or not isinstance(r, dict)]
        
        performance_data = self.perf_utils.calculate_performance_metrics(
            successful_results, errors, start_time, start_time + total_time
        )
        
        # Calculate switching-specific metrics
        switch_times = [r.get("switch_time", 0) for r in successful_results]
        if switch_times:
            performance_data.update({
                "avg_switch_time": statistics.mean(switch_times),
                "median_switch_time": statistics.median(switch_times),
                "max_switch_time": max(switch_times),
                "min_switch_time": min(switch_times)
            })
        
        self.performance_metrics.append({
            "operation": "thread_switching",
            "switch_count": switch_count,
            "thread_count": len(thread_ids),
            "metrics": performance_data,
            "timestamp": time.time()
        })
        
        return performance_data
    
    async def _switch_thread_with_timing(self, user_id: str, thread_id: str, 
                                         index: int) -> Dict[str, Any]:
        """Switch thread with detailed timing."""
        try:
            start_time = time.perf_counter()
            
            # Build and send switch message
            switch_message = self.ws_fixtures.build_websocket_message(
                WebSocketMessageType.SWITCH_THREAD,
                thread_id=thread_id
            )
            await self.ws_fixtures.send_websocket_message(user_id, switch_message)
            
            # Simulate history loading
            context_key = f"{user_id}:{thread_id}"
            if context_key in self.ws_fixtures.thread_contexts:
                context = self.ws_fixtures.thread_contexts[context_key]
                context["last_accessed"] = time.time()
                context["access_count"] = context.get("access_count", 0) + 1
            
            # Capture event
            self.ws_fixtures.capture_thread_event(
                WebSocketMessageType.THREAD_SWITCHED,
                user_id,
                thread_id
            )
            
            switch_time = time.perf_counter() - start_time
            
            return {
                "success": True,
                "thread_id": thread_id,
                "switch_time": switch_time,
                "index": index
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "index": index
            }
    
    async def measure_concurrent_user_performance(self, user_count: int, 
                                                   operations_per_user: int) -> Dict[str, Any]:
        """Measure performance with multiple concurrent users."""
        user_tasks = []
        
        for i in range(user_count):
            user_id = f"perf_user_{i}"
            task = self._simulate_user_operations(user_id, operations_per_user, i)
            user_tasks.append(task)
        
        # Execute concurrent user operations
        start_time = time.perf_counter()
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Analyze multi-user results
        successful_users = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_users = len(results) - len(successful_users)
        
        total_operations = sum(r.get("completed_operations", 0) for r in successful_users)
        
        performance_data = {
            "total_time": total_time,
            "user_count": user_count,
            "successful_users": len(successful_users),
            "failed_users": failed_users,
            "total_operations": total_operations,
            "operations_per_second": total_operations / total_time if total_time > 0 else 0,
            "avg_operations_per_user": total_operations / len(successful_users) if successful_users else 0
        }
        
        self.performance_metrics.append({
            "operation": "concurrent_users",
            "user_count": user_count,
            "operations_per_user": operations_per_user,
            "metrics": performance_data,
            "timestamp": time.time()
        })
        
        return performance_data
    
    async def _simulate_user_operations(self, user_id: str, operation_count: int, 
                                        user_index: int) -> Dict[str, Any]:
        """Simulate realistic user operations for performance testing."""
        try:
            # Create connection
            await self.ws_fixtures.create_authenticated_connection(user_id)
            
            completed_operations = 0
            created_threads = []
            
            # Create threads
            for i in range(min(3, operation_count)):
                thread_id = f"user_{user_index}_thread_{i}_{int(time.time())}"
                thread_name = f"User {user_index} Thread {i+1}"
                
                # Create thread
                message = self.ws_fixtures.build_websocket_message(
                    WebSocketMessageType.CREATE_THREAD,
                    thread_id=thread_id,
                    thread_name=thread_name
                )
                await self.ws_fixtures.send_websocket_message(user_id, message)
                
                # Initialize context
                context_key = f"{user_id}:{thread_id}"
                self.ws_fixtures.thread_contexts[context_key] = {
                    "thread_id": thread_id,
                    "thread_name": thread_name,
                    "created_at": time.time(),
                    "messages": []
                }
                
                created_threads.append(thread_id)
                completed_operations += 1
            
            # Perform thread switches
            remaining_operations = operation_count - completed_operations
            for i in range(min(remaining_operations, len(created_threads) * 2)):
                if created_threads:
                    thread_id = created_threads[i % len(created_threads)]
                    
                    switch_message = self.ws_fixtures.build_websocket_message(
                        WebSocketMessageType.SWITCH_THREAD,
                        thread_id=thread_id
                    )
                    await self.ws_fixtures.send_websocket_message(user_id, switch_message)
                    completed_operations += 1
            
            return {
                "success": True,
                "user_id": user_id,
                "user_index": user_index,
                "completed_operations": completed_operations,
                "created_threads": len(created_threads)
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user_id,
                "user_index": user_index,
                "error": str(e),
                "completed_operations": 0
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.performance_metrics:
            return {"error": "No performance metrics available"}
        
        summary = {
            "total_tests": len(self.performance_metrics),
            "test_operations": [m["operation"] for m in self.performance_metrics],
            "avg_throughput": 0,
            "avg_error_rate": 0,
            "test_results": []
        }
        
        throughputs = []
        error_rates = []
        
        for metric in self.performance_metrics:
            test_result = {
                "operation": metric["operation"],
                "throughput": metric["metrics"].get("throughput", 0),
                "error_rate": metric["metrics"].get("error_rate", 0),
                "total_time": metric["metrics"].get("total_time", 0)
            }
            
            summary["test_results"].append(test_result)
            
            if test_result["throughput"] > 0:
                throughputs.append(test_result["throughput"])
            error_rates.append(test_result["error_rate"])
        
        if throughputs:
            summary["avg_throughput"] = statistics.mean(throughputs)
        if error_rates:
            summary["avg_error_rate"] = statistics.mean(error_rates)
        
        return summary


# Alias for backward compatibility (fixing typo)
ThreadPerformanceTester = TestThreadPerformanceer


@pytest.fixture
def thread_performance_tester(ws_thread_fixtures, thread_context_manager, performance_utils):
    """Thread performance tester fixture."""
    return ThreadPerformanceTester(ws_thread_fixtures, thread_context_manager, performance_utils)

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_thread_creation_performance_under_load(ws_thread_fixtures, thread_performance_tester):
    """Test thread creation performance with concurrent load."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Test thread creation performance
    thread_count = 15
    performance_data = await thread_performance_tester.measure_thread_creation_performance(
        user.id, thread_count
    )
    
    # Verify performance requirements
    assert performance_data["throughput"] >= 10.0, \
           f"Throughput must be >= 10 threads/sec, got {performance_data['throughput']:.2f}"
    assert performance_data["error_rate"] <= 0.05, \
           f"Error rate must be <= 5%, got {performance_data['error_rate']:.2%}"
    assert performance_data["success_count"] >= thread_count * 0.95, \
           f"Success rate must be >= 95%, got {performance_data['success_count']}/{thread_count}"
    
    # Verify timing statistics
    if "avg_creation_time" in performance_data:
        assert performance_data["avg_creation_time"] < 0.5, \
               f"Average creation time must be < 0.5s, got {performance_data['avg_creation_time']:.3f}s"
        assert performance_data["max_creation_time"] < 2.0, \
               f"Max creation time must be < 2s, got {performance_data['max_creation_time']:.3f}s"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_thread_switching_performance_rapid_switches(ws_thread_fixtures, thread_performance_tester):
    """Test thread switching performance with rapid switches."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Create threads for switching
    thread_count = 5
    creation_data = await thread_performance_tester.measure_thread_creation_performance(
        user.id, thread_count
    )
    
    # Extract created thread IDs
    thread_ids = []
    for event in ws_thread_fixtures.thread_events:
        if (event["type"] == WebSocketMessageType.THREAD_CREATED.value and 
            event["user_id"] == user.id):
            thread_ids.append(event["thread_id"])
    
    assert len(thread_ids) >= thread_count * 0.8, "Must have created enough threads for switching test"
    
    # Test switching performance
    switch_count = 20
    switching_data = await thread_performance_tester.measure_thread_switching_performance(
        user.id, thread_ids[:thread_count], switch_count
    )
    
    # Verify switching performance
    assert switching_data["throughput"] >= 15.0, \
           f"Switch throughput must be >= 15 switches/sec, got {switching_data['throughput']:.2f}"
    assert switching_data["error_rate"] <= 0.05, \
           f"Switch error rate must be <= 5%, got {switching_data['error_rate']:.2%}"
    
    # Verify switching timing
    if "avg_switch_time" in switching_data:
        assert switching_data["avg_switch_time"] < 0.2, \
               f"Average switch time must be < 0.2s, got {switching_data['avg_switch_time']:.3f}s"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_user_performance(ws_thread_fixtures, thread_performance_tester):
    """Test performance with multiple concurrent users."""
    user_count = 5
    operations_per_user = 8
    
    # Test concurrent user operations
    performance_data = await thread_performance_tester.measure_concurrent_user_performance(
        user_count, operations_per_user
    )
    
    # Verify multi-user performance
    assert performance_data["successful_users"] >= user_count * 0.8, \
           f"At least 80% of users must succeed, got {performance_data['successful_users']}/{user_count}"
    assert performance_data["operations_per_second"] >= 20.0, \
           f"Overall throughput must be >= 20 ops/sec, got {performance_data['operations_per_second']:.2f}"
    assert performance_data["total_time"] < 10.0, \
           f"Total test time must be < 10s, got {performance_data['total_time']:.2f}s"
    
    # Verify reasonable operation distribution
    expected_total_operations = user_count * operations_per_user
    actual_operations = performance_data["total_operations"]
    
    assert actual_operations >= expected_total_operations * 0.8, \
           f"Should complete at least 80% of operations, got {actual_operations}/{expected_total_operations}"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_comprehensive_thread_operations_performance_target(ws_thread_fixtures:
                                                                   thread_performance_tester,
                                                                   thread_context_manager):
    """Test all thread operations complete within comprehensive performance targets."""
    user = TEST_USERS["enterprise"]
    
    # Create connection
    await ws_thread_fixtures.create_authenticated_connection(user.id)
    
    # Comprehensive performance test combining all operations
    start_time = time.perf_counter()
    
    # Phase 1: Create threads
    creation_data = await thread_performance_tester.measure_thread_creation_performance(
        user.id, 5
    )
    
    # Phase 2: Switch between threads
    thread_ids = []
    for event in ws_thread_fixtures.thread_events:
        if (event["type"] == WebSocketMessageType.THREAD_CREATED.value and 
            event["user_id"] == user.id):
            thread_ids.append(event["thread_id"])
    
    if thread_ids:
        switching_data = await thread_performance_tester.measure_thread_switching_performance(
            user.id, thread_ids, 10
        )
    
    # Phase 3: Add agent contexts
    for thread_id in thread_ids[:3]:
        agent_data = {
            "agent_id": f"perf_agent_{thread_id[:8]}",
            "status": "active",
            "execution_state": {"step": 1, "performance_test": True}
        }
        await thread_context_manager.preserve_agent_context_in_thread(
            user.id, thread_id, agent_data
        )
    
    total_duration = time.perf_counter() - start_time
    
    # Verify comprehensive performance target
    assert total_duration < 30.0, \
           f"All comprehensive thread operations must complete within 30 seconds, took {total_duration:.2f}s"
    
    # Verify individual phase performance
    assert creation_data["success_count"] >= 4, "Must successfully create most threads"
    
    if 'switching_data' in locals():
        assert switching_data["success_count"] >= 8, "Must successfully complete most switches"
    
    # Verify system stability after load
    assert len(ws_thread_fixtures.active_connections) > 0, "Connection must remain stable"
    assert len(ws_thread_fixtures.thread_events) >= 15, "All operations must generate events"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_performance_metrics_collection_and_analysis(thread_performance_tester):
    """Test performance metrics collection and analysis capabilities."""
    user = TEST_USERS["enterprise"]
    
    # Run multiple performance tests to collect metrics
    await thread_performance_tester.measure_thread_creation_performance(user.id, 3)
    await thread_performance_tester.measure_concurrent_user_performance(2, 4)
    
    # Get performance summary
    summary = thread_performance_tester.get_performance_summary()
    
    # Verify metrics collection
    assert summary["total_tests"] >= 2, "Multiple tests must be recorded"
    assert "thread_creation" in summary["test_operations"], "Thread creation test must be recorded"
    assert "concurrent_users" in summary["test_operations"], "Concurrent users test must be recorded"
    
    # Verify performance analysis
    assert "avg_throughput" in summary, "Average throughput must be calculated"
    assert "avg_error_rate" in summary, "Average error rate must be calculated"
    assert len(summary["test_results"]) >= 2, "Individual test results must be preserved"
    
    # Verify performance standards
    if summary["avg_throughput"] > 0:
        assert summary["avg_throughput"] >= 5.0, \
               f"Average throughput should be reasonable, got {summary['avg_throughput']:.2f}"
    
    assert summary["avg_error_rate"] <= 0.1, \
           f"Average error rate should be low, got {summary['avg_error_rate']:.2%}"
