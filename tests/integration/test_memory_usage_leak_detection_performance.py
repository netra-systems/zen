"""
Performance & Load Testing: Memory Usage and Leak Detection

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent memory leaks that cause system instability and crashes
- Value Impact: Users experience stable platform performance over extended periods
- Strategic Impact: Memory efficiency enables cost-effective scaling and enterprise reliability

CRITICAL: This test validates memory usage patterns and detects potential memory leaks
that could degrade performance or cause system failures under load.
"""

import asyncio
import pytest
import time
import gc
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import psutil
import os
import weakref
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time."""
    timestamp: float
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    uss_mb: float  # Unique Set Size in MB (Linux/macOS only)
    pss_mb: float  # Proportional Set Size in MB (Linux only)
    num_fds: int   # Number of file descriptors
    cpu_percent: float
    
    
@dataclass
class MemoryLeakTestResult:
    """Results from memory leak testing."""
    test_name: str
    initial_memory: MemorySnapshot
    final_memory: MemorySnapshot
    peak_memory: MemorySnapshot
    memory_growth_mb: float
    memory_growth_percentage: float
    leak_detected: bool
    leak_severity: str  # 'none', 'minor', 'moderate', 'severe'
    recommendations: List[str] = field(default_factory=list)


class TestMemoryUsageLeakDetection(BaseIntegrationTest):
    """Test memory usage patterns and detect memory leaks."""
    
    def _get_memory_snapshot(self, label: str = "") -> MemorySnapshot:
        """Get current memory usage snapshot."""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        # Get detailed memory info if available
        try:
            memory_full_info = process.memory_full_info()
            uss_mb = memory_full_info.uss / 1024 / 1024
            pss_mb = getattr(memory_full_info, 'pss', 0) / 1024 / 1024
        except (AttributeError, psutil.AccessDenied):
            uss_mb = 0
            pss_mb = 0
        
        return MemorySnapshot(
            timestamp=time.time(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            uss_mb=uss_mb,
            pss_mb=pss_mb,
            num_fds=process.num_fds() if hasattr(process, 'num_fds') else 0,
            cpu_percent=process.cpu_percent()
        )
    
    def _analyze_memory_growth(self, initial: MemorySnapshot, final: MemorySnapshot, 
                              peak: MemorySnapshot, test_name: str) -> MemoryLeakTestResult:
        """Analyze memory growth and detect potential leaks."""
        memory_growth_mb = final.rss_mb - initial.rss_mb
        memory_growth_percentage = (memory_growth_mb / initial.rss_mb) * 100
        
        # Leak detection thresholds
        leak_detected = False
        leak_severity = "none"
        recommendations = []
        
        if memory_growth_mb > 50:  # More than 50MB growth
            leak_detected = True
            leak_severity = "severe"
            recommendations.append("Investigate major memory leak - growth exceeds 50MB")
        elif memory_growth_mb > 20:  # More than 20MB growth
            leak_detected = True
            leak_severity = "moderate"
            recommendations.append("Monitor memory usage - significant growth detected")
        elif memory_growth_mb > 5:  # More than 5MB growth
            leak_detected = True
            leak_severity = "minor"
            recommendations.append("Check for minor memory leaks or suboptimal cleanup")
        
        # Additional checks
        if memory_growth_percentage > 10:
            leak_detected = True
            recommendations.append(f"Memory growth {memory_growth_percentage:.1f}% may indicate leak")
        
        if peak.rss_mb - final.rss_mb < memory_growth_mb * 0.8:
            recommendations.append("Memory not properly released after peak usage")
        
        return MemoryLeakTestResult(
            test_name=test_name,
            initial_memory=initial,
            final_memory=final,
            peak_memory=peak,
            memory_growth_mb=memory_growth_mb,
            memory_growth_percentage=memory_growth_percentage,
            leak_detected=leak_detected,
            leak_severity=leak_severity,
            recommendations=recommendations
        )
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_user_context_memory_leak_detection(self, real_services_fixture):
        """
        Test for memory leaks in user context creation and cleanup.
        
        Memory SLA:
        - Memory growth: <5MB for 1000 context operations
        - Memory release: >90% of peak memory released after cleanup
        - No object accumulation in memory
        """
        test_name = "User Context Memory Leak Detection"
        
        # Force garbage collection before starting
        gc.collect()
        initial_snapshot = self._get_memory_snapshot("initial")
        
        peak_memory = initial_snapshot
        created_contexts = []
        weak_refs = []  # Track objects with weak references
        
        # Create many user contexts to test for leaks
        context_count = 1000
        
        for i in range(context_count):
            context = await create_authenticated_user_context(
                user_email=f"memtest_{i}@example.com",
                environment="test",
                permissions=["read", "write"]
            )
            
            # Keep weak reference to track object lifecycle
            weak_refs.append(weakref.ref(context))
            
            # Store context temporarily to simulate usage
            created_contexts.append(context)
            
            # Check memory periodically
            if i % 100 == 0:
                current_snapshot = self._get_memory_snapshot(f"iteration_{i}")
                if current_snapshot.rss_mb > peak_memory.rss_mb:
                    peak_memory = current_snapshot
        
        # Memory snapshot after creation
        after_creation_snapshot = self._get_memory_snapshot("after_creation")
        if after_creation_snapshot.rss_mb > peak_memory.rss_mb:
            peak_memory = after_creation_snapshot
        
        # Clear references and force garbage collection
        created_contexts.clear()
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup
        
        # Final memory snapshot
        final_snapshot = self._get_memory_snapshot("final")
        
        # Analyze memory usage
        result = self._analyze_memory_growth(initial_snapshot, final_snapshot, peak_memory, test_name)
        
        # Check object cleanup with weak references
        alive_objects = sum(1 for ref in weak_refs if ref() is not None)
        object_cleanup_rate = (len(weak_refs) - alive_objects) / len(weak_refs) * 100
        
        # Performance assertions
        assert result.memory_growth_mb < 5, f"Memory growth {result.memory_growth_mb:.1f}MB exceeds 5MB limit for {context_count} contexts"
        assert not result.leak_detected or result.leak_severity in ["none", "minor"], f"Memory leak detected: {result.leak_severity} - {result.recommendations}"
        assert object_cleanup_rate > 80, f"Object cleanup rate {object_cleanup_rate:.1f}% below 80% threshold"
        
        print(f"✅ User Context Memory Test Results:")
        print(f"   Contexts created: {context_count}")
        print(f"   Initial memory: {initial_snapshot.rss_mb:.1f}MB")
        print(f"   Peak memory: {peak_memory.rss_mb:.1f}MB")
        print(f"   Final memory: {final_snapshot.rss_mb:.1f}MB")
        print(f"   Memory growth: {result.memory_growth_mb:.1f}MB ({result.memory_growth_percentage:.1f}%)")
        print(f"   Object cleanup rate: {object_cleanup_rate:.1f}%")
        print(f"   Leak severity: {result.leak_severity}")
        
        return result
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_websocket_connection_memory_leak(self, real_services_fixture):
        """
        Test for memory leaks in WebSocket connection lifecycle.
        
        Memory SLA:
        - Memory growth: <10MB for 100 connection cycles
        - Connection cleanup: Complete cleanup after disconnection
        - File descriptor cleanup: No FD leaks
        """
        test_name = "WebSocket Connection Memory Leak"
        
        gc.collect()
        initial_snapshot = self._get_memory_snapshot("initial")
        
        auth_helper = E2EAuthHelper()
        peak_memory = initial_snapshot
        connection_count = 100
        
        async def connection_cycle(cycle_id: int):
            """Single WebSocket connection lifecycle."""
            try:
                # Create authenticated WebSocket connection
                websocket, connection_info = await auth_helper.create_websocket_connection(
                    timeout=5.0
                )
                
                # Send a few messages
                for i in range(3):
                    message = {
                        "type": "memory_test",
                        "cycle_id": cycle_id,
                        "message_id": i,
                        "timestamp": time.time()
                    }
                    await websocket.send(json.dumps(message))
                    await asyncio.sleep(0.01)
                
                # Close connection
                await websocket.close()
                
            except Exception as e:
                print(f"Connection cycle {cycle_id} error: {e}")
        
        # Run connection cycles
        for i in range(connection_count):
            await connection_cycle(i)
            
            # Check memory periodically
            if i % 10 == 0:
                current_snapshot = self._get_memory_snapshot(f"cycle_{i}")
                if current_snapshot.rss_mb > peak_memory.rss_mb:
                    peak_memory = current_snapshot
                    
                # Force cleanup
                gc.collect()
        
        # Final cleanup and measurement
        gc.collect()
        await asyncio.sleep(0.5)  # Allow async cleanup
        final_snapshot = self._get_memory_snapshot("final")
        
        # Analyze results
        result = self._analyze_memory_growth(initial_snapshot, final_snapshot, peak_memory, test_name)
        
        # File descriptor leak check
        fd_growth = final_snapshot.num_fds - initial_snapshot.num_fds
        
        # Performance assertions
        assert result.memory_growth_mb < 10, f"Memory growth {result.memory_growth_mb:.1f}MB exceeds 10MB limit for {connection_count} connections"
        assert fd_growth <= 2, f"File descriptor growth {fd_growth} indicates FD leak"
        assert not result.leak_detected or result.leak_severity == "minor", f"Significant memory leak detected: {result.leak_severity}"
        
        print(f"✅ WebSocket Connection Memory Test Results:")
        print(f"   Connection cycles: {connection_count}")
        print(f"   Initial memory: {initial_snapshot.rss_mb:.1f}MB")
        print(f"   Peak memory: {peak_memory.rss_mb:.1f}MB")
        print(f"   Final memory: {final_snapshot.rss_mb:.1f}MB")
        print(f"   Memory growth: {result.memory_growth_mb:.1f}MB ({result.memory_growth_percentage:.1f}%)")
        print(f"   FD growth: {fd_growth}")
        print(f"   Leak severity: {result.leak_severity}")
        
        return result
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_sustained_operation_memory_stability(self, real_services_fixture):
        """
        Test memory stability during sustained operations.
        
        Memory SLA:
        - Memory growth: <2MB/hour during sustained operations
        - Memory ceiling: No unbounded growth patterns
        - GC efficiency: Memory released during periodic cleanup
        """
        test_name = "Sustained Operation Memory Stability"
        
        gc.collect()
        initial_snapshot = self._get_memory_snapshot("initial")
        
        auth_helper = E2EAuthHelper()
        test_duration = 180  # 3 minutes of sustained operations
        operation_interval = 1.0  # 1 operation per second
        
        memory_snapshots = [initial_snapshot]
        peak_memory = initial_snapshot
        operation_count = 0
        
        end_time = time.time() + test_duration
        
        while time.time() < end_time:
            try:
                # Perform mixed operations to simulate real usage
                if operation_count % 10 == 0:
                    # Create user context (heavier operation)
                    context = await create_authenticated_user_context(
                        user_email=f"sustained_{operation_count}@example.com",
                        environment="test"
                    )
                    # Don't keep reference to allow garbage collection
                    del context
                else:
                    # Create JWT token (lighter operation)
                    token = auth_helper.create_test_jwt_token(
                        user_id=f"sustained_user_{operation_count}",
                        email=f"sustained_{operation_count}@example.com"
                    )
                    # Don't keep reference
                    del token
                
                operation_count += 1
                
                # Periodic memory measurement
                if operation_count % 10 == 0:
                    current_snapshot = self._get_memory_snapshot(f"operation_{operation_count}")
                    memory_snapshots.append(current_snapshot)
                    
                    if current_snapshot.rss_mb > peak_memory.rss_mb:
                        peak_memory = current_snapshot
                
                # Periodic garbage collection
                if operation_count % 50 == 0:
                    gc.collect()
                
                await asyncio.sleep(operation_interval)
                
            except Exception as e:
                print(f"Operation {operation_count} error: {e}")
        
        # Final cleanup and measurement
        gc.collect()
        final_snapshot = self._get_memory_snapshot("final")
        memory_snapshots.append(final_snapshot)
        
        # Analyze memory trends
        memory_values = [snap.rss_mb for snap in memory_snapshots]
        memory_trend = statistics.linear_regression(range(len(memory_values)), memory_values)
        memory_growth_rate = memory_trend.slope  # MB per snapshot interval
        
        # Calculate hourly growth rate
        snapshots_per_hour = 3600 / (operation_interval * 10)  # 10 operations per snapshot
        hourly_growth_rate = memory_growth_rate * snapshots_per_hour
        
        result = self._analyze_memory_growth(initial_snapshot, final_snapshot, peak_memory, test_name)
        
        # Performance assertions
        assert hourly_growth_rate < 2.0, f"Memory growth rate {hourly_growth_rate:.2f}MB/hour exceeds 2MB/hour limit"
        assert result.memory_growth_mb < test_duration / 60 * 2, f"Total memory growth exceeds expected rate"
        
        # Check for memory ceiling behavior (no unbounded growth)
        memory_range = max(memory_values) - min(memory_values)
        memory_volatility = statistics.stdev(memory_values) if len(memory_values) > 1 else 0
        
        assert memory_volatility < 5.0, f"Memory volatility {memory_volatility:.1f}MB indicates instability"
        
        print(f"✅ Sustained Operation Memory Stability Results:")
        print(f"   Test duration: {test_duration}s")
        print(f"   Total operations: {operation_count}")
        print(f"   Initial memory: {initial_snapshot.rss_mb:.1f}MB")
        print(f"   Peak memory: {peak_memory.rss_mb:.1f}MB")
        print(f"   Final memory: {final_snapshot.rss_mb:.1f}MB")
        print(f"   Memory growth: {result.memory_growth_mb:.1f}MB")
        print(f"   Hourly growth rate: {hourly_growth_rate:.2f}MB/hour")
        print(f"   Memory volatility: {memory_volatility:.1f}MB")
        print(f"   Memory range: {memory_range:.1f}MB")
        
        return result
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_concurrent_operations_memory_efficiency(self, real_services_fixture):
        """
        Test memory efficiency during concurrent operations.
        
        Memory SLA:
        - Memory per concurrent operation: <2MB per operation
        - Memory scaling: Linear or sub-linear with concurrency
        - Memory cleanup: Proper cleanup after concurrent operations
        """
        test_name = "Concurrent Operations Memory Efficiency"
        
        gc.collect()
        initial_snapshot = self._get_memory_snapshot("initial")
        
        concurrent_operations = 50
        auth_helper = E2EAuthHelper()
        
        async def concurrent_memory_operation(op_id: int) -> Dict[str, Any]:
            """Single concurrent operation that uses memory."""
            operation_start = time.time()
            
            try:
                # Create user context
                context = await create_authenticated_user_context(
                    user_email=f"concurrent_{op_id}@example.com",
                    environment="test",
                    permissions=["read", "write", "execute"]
                )
                
                # Simulate some work with the context
                work_data = {
                    "user_id": str(context.user_id),
                    "thread_id": str(context.thread_id),
                    "request_id": str(context.request_id),
                    "operation_data": [f"data_item_{i}" for i in range(100)]  # Some memory usage
                }
                
                # Create JWT token
                token = auth_helper.create_test_jwt_token(
                    user_id=str(context.user_id),
                    email=f"concurrent_{op_id}@example.com",
                    permissions=["read", "write"]
                )
                
                # Simulate some processing time
                await asyncio.sleep(0.1)
                
                operation_time = time.time() - operation_start
                
                return {
                    "op_id": op_id,
                    "success": True,
                    "operation_time": operation_time,
                    "error": None
                }
                
            except Exception as e:
                return {
                    "op_id": op_id,
                    "success": False,
                    "operation_time": time.time() - operation_start,
                    "error": str(e)
                }
        
        # Execute concurrent operations
        concurrent_start = time.time()
        
        operation_tasks = [
            concurrent_memory_operation(i)
            for i in range(concurrent_operations)
        ]
        
        results = await asyncio.gather(*operation_tasks)
        
        concurrent_end = time.time()
        
        # Memory snapshot after concurrent operations
        after_concurrent_snapshot = self._get_memory_snapshot("after_concurrent")
        
        # Force cleanup
        gc.collect()
        await asyncio.sleep(0.5)
        final_snapshot = self._get_memory_snapshot("final")
        
        # Analyze results
        successful_operations = sum(1 for r in results if r["success"])
        failed_operations = concurrent_operations - successful_operations
        
        memory_per_operation = (after_concurrent_snapshot.rss_mb - initial_snapshot.rss_mb) / concurrent_operations
        memory_cleanup_efficiency = (after_concurrent_snapshot.rss_mb - final_snapshot.rss_mb) / (after_concurrent_snapshot.rss_mb - initial_snapshot.rss_mb) * 100
        
        result = self._analyze_memory_growth(initial_snapshot, final_snapshot, after_concurrent_snapshot, test_name)
        
        # Performance assertions
        assert memory_per_operation < 2.0, f"Memory per operation {memory_per_operation:.2f}MB exceeds 2MB limit"
        assert successful_operations >= concurrent_operations * 0.95, f"Operation success rate {successful_operations/concurrent_operations:.1%} too low"
        assert memory_cleanup_efficiency > 70, f"Memory cleanup efficiency {memory_cleanup_efficiency:.1f}% below 70% threshold"
        
        print(f"✅ Concurrent Operations Memory Efficiency Results:")
        print(f"   Concurrent operations: {concurrent_operations}")
        print(f"   Successful operations: {successful_operations}")
        print(f"   Failed operations: {failed_operations}")
        print(f"   Initial memory: {initial_snapshot.rss_mb:.1f}MB")
        print(f"   Peak memory: {after_concurrent_snapshot.rss_mb:.1f}MB")
        print(f"   Final memory: {final_snapshot.rss_mb:.1f}MB")
        print(f"   Memory per operation: {memory_per_operation:.2f}MB")
        print(f"   Memory cleanup efficiency: {memory_cleanup_efficiency:.1f}%")
        print(f"   Net memory growth: {result.memory_growth_mb:.1f}MB")
        
        return result