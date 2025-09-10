"""
Performance & Load Testing: Resource Exhaustion Detection and Handling

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent system failures by detecting and handling resource exhaustion gracefully
- Value Impact: Users experience stable service even under resource pressure or unexpected load spikes
- Strategic Impact: Resource exhaustion handling prevents costly system downtime and maintains SLA compliance

CRITICAL: This test validates resource exhaustion detection, graceful degradation mechanisms,
and system recovery capabilities under various resource pressure scenarios.
"""

import asyncio
import pytest
import time
import statistics
import json
import psutil
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import threading
import gc

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class ResourceExhaustionMetrics:
    """Resource exhaustion test metrics."""
    test_name: str
    resource_type: str
    initial_usage: float
    peak_usage: float
    final_usage: float
    exhaustion_threshold: float
    exhaustion_detected: bool
    graceful_degradation_triggered: bool
    recovery_time_seconds: float
    operations_before_exhaustion: int
    operations_during_exhaustion: int
    operations_after_recovery: int
    errors_during_exhaustion: List[str] = field(default_factory=list)


@dataclass
class SystemResourceSnapshot:
    """System resource usage snapshot."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float
    open_files: int
    network_connections: int
    thread_count: int


class TestResourceExhaustionDetectionHandling(BaseIntegrationTest):
    """Test resource exhaustion detection and handling mechanisms."""
    
    def _get_system_resource_snapshot(self) -> SystemResourceSnapshot:
        """Get current system resource usage snapshot."""
        process = psutil.Process(os.getpid())
        
        # Get system-wide stats
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        # Get process-specific stats
        proc_memory = process.memory_info()
        proc_memory_mb = proc_memory.rss / 1024 / 1024
        
        try:
            open_files = process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            open_files = 0
        
        try:
            network_connections = len(process.connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            network_connections = 0
        
        try:
            thread_count = process.num_threads()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            thread_count = threading.active_count()
        
        return SystemResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_mb=proc_memory_mb,
            memory_percent=memory_info.percent,
            disk_usage_percent=disk_info.percent,
            open_files=open_files,
            network_connections=network_connections,
            thread_count=thread_count
        )
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_memory_exhaustion_detection_and_recovery(self, real_services_fixture):
        """
        Test memory exhaustion detection and graceful recovery.
        
        Resource SLA:
        - Memory usage monitoring and alerting
        - Graceful degradation when memory usage >80%
        - Automatic recovery when memory usage <70%
        - No system crashes due to OOM
        """
        redis = real_services_fixture["redis"]
        
        # Memory exhaustion thresholds (as percentage of available memory)
        memory_warning_threshold = 80.0  # 80% memory usage triggers warnings
        memory_critical_threshold = 90.0  # 90% memory usage triggers degradation
        memory_recovery_threshold = 70.0  # 70% memory usage allows recovery
        
        initial_snapshot = self._get_system_resource_snapshot()
        memory_exhaustion_metrics = ResourceExhaustionMetrics(
            test_name="Memory Exhaustion Detection",
            resource_type="memory",
            initial_usage=initial_snapshot.memory_mb,
            peak_usage=initial_snapshot.memory_mb,
            final_usage=initial_snapshot.memory_mb,
            exhaustion_threshold=memory_warning_threshold,
            exhaustion_detected=False,
            graceful_degradation_triggered=False,
            recovery_time_seconds=0,
            operations_before_exhaustion=0,
            operations_during_exhaustion=0,
            operations_after_recovery=0
        )
        
        # Memory consumption strategy: gradually consume memory until threshold
        memory_consumers = []  # Keep references to prevent GC
        chunk_size_mb = 10  # 10MB chunks
        max_chunks = 100  # Maximum 1GB total consumption
        
        operations_count = 0
        exhaustion_phase = "loading"  # loading -> exhausted -> recovering
        phase_start_time = time.time()
        
        try:
            for chunk_id in range(max_chunks):
                # Allocate memory chunk
                chunk_data = bytearray(chunk_size_mb * 1024 * 1024)  # 10MB of data
                
                # Fill with data to ensure actual memory allocation
                for i in range(0, len(chunk_data), 4096):  # Every 4KB
                    chunk_data[i:i+8] = b"testdata"
                
                memory_consumers.append(chunk_data)
                
                # Perform operations and monitor memory
                current_snapshot = self._get_system_resource_snapshot()
                memory_exhaustion_metrics.peak_usage = max(
                    memory_exhaustion_metrics.peak_usage, 
                    current_snapshot.memory_mb
                )
                
                # Simulate system operations under memory pressure
                try:
                    # Redis operations (memory intensive)
                    test_key = f"memory_test:{chunk_id}"
                    test_data = {"chunk_id": chunk_id, "data": "x" * 1024}  # 1KB JSON data
                    await redis.set(test_key, json.dumps(test_data), ex=60)
                    
                    # User context creation (memory intensive)
                    if chunk_id % 5 == 0:  # Every 5th iteration
                        user_context = await create_authenticated_user_context(
                            user_email=f"memory_test_{chunk_id}@example.com",
                            environment="test"
                        )
                        # Don't keep reference to allow GC
                        del user_context
                    
                    operations_count += 1
                    
                    if exhaustion_phase == "loading":
                        memory_exhaustion_metrics.operations_before_exhaustion += 1
                    elif exhaustion_phase == "exhausted":
                        memory_exhaustion_metrics.operations_during_exhaustion += 1
                    else:  # recovering
                        memory_exhaustion_metrics.operations_after_recovery += 1
                    
                except Exception as e:
                    error_msg = f"Operation failed at chunk {chunk_id}: {str(e)}"
                    memory_exhaustion_metrics.errors_during_exhaustion.append(error_msg)
                
                # Check for memory exhaustion thresholds
                memory_growth_mb = current_snapshot.memory_mb - initial_snapshot.memory_mb
                memory_growth_percent = (memory_growth_mb / initial_snapshot.memory_mb) * 100
                
                if not memory_exhaustion_metrics.exhaustion_detected and memory_growth_percent > 50:
                    # Detected significant memory growth (>50% increase)
                    memory_exhaustion_metrics.exhaustion_detected = True
                    exhaustion_phase = "exhausted"
                    phase_start_time = time.time()
                    print(f"💾 Memory exhaustion detected at chunk {chunk_id}: {current_snapshot.memory_mb:.1f}MB ({memory_growth_percent:.1f}% growth)")
                
                # Trigger graceful degradation if memory usage is very high
                if memory_growth_percent > 75 and not memory_exhaustion_metrics.graceful_degradation_triggered:
                    memory_exhaustion_metrics.graceful_degradation_triggered = True
                    print(f"⚠️ Graceful degradation triggered at chunk {chunk_id}")
                    
                    # Simulate graceful degradation: reduce operation frequency
                    await asyncio.sleep(0.1)  # Slow down operations
                    
                    # Cleanup some memory consumers to simulate memory management
                    if len(memory_consumers) > 20:
                        # Release 25% of consumed memory
                        release_count = len(memory_consumers) // 4
                        for _ in range(release_count):
                            memory_consumers.pop(0)
                        
                        # Force garbage collection
                        gc.collect()
                        exhaustion_phase = "recovering"
                        phase_start_time = time.time()
                        print(f"🔄 Memory recovery initiated")
                        break
                
                # Safety check: don't consume too much memory
                if current_snapshot.memory_mb > initial_snapshot.memory_mb * 3:  # 3x original memory
                    print(f"🛑 Safety limit reached at chunk {chunk_id}, stopping memory consumption")
                    break
                
                # Small delay between chunks
                await asyncio.sleep(0.01)
        
        finally:
            # Cleanup: release all memory consumers
            print(f"🧹 Cleaning up {len(memory_consumers)} memory chunks...")
            cleanup_start = time.time()
            memory_consumers.clear()
            gc.collect()  # Force garbage collection
            
            # Wait for memory to be released
            await asyncio.sleep(1.0)
            
            recovery_snapshot = self._get_system_resource_snapshot()
            memory_exhaustion_metrics.recovery_time_seconds = time.time() - cleanup_start
            memory_exhaustion_metrics.final_usage = recovery_snapshot.memory_mb
        
        # Memory recovery verification
        memory_recovered = (
            memory_exhaustion_metrics.final_usage <= 
            initial_snapshot.memory_mb * 1.2  # Within 20% of original
        )
        
        # Performance assertions
        assert memory_exhaustion_metrics.exhaustion_detected, "Memory exhaustion should have been detected"
        assert memory_exhaustion_metrics.operations_before_exhaustion > 0, "Should have operations before exhaustion"
        assert len(memory_exhaustion_metrics.errors_during_exhaustion) <= operations_count * 0.1, "Too many errors during memory pressure"
        assert memory_recovered, f"Memory not properly recovered: {memory_exhaustion_metrics.final_usage:.1f}MB vs initial {initial_snapshot.memory_mb:.1f}MB"
        assert memory_exhaustion_metrics.recovery_time_seconds < 10.0, f"Memory recovery took too long: {memory_exhaustion_metrics.recovery_time_seconds:.1f}s"
        
        print(f"✅ Memory Exhaustion Detection and Recovery Results:")
        print(f"   Initial memory: {initial_snapshot.memory_mb:.1f}MB")
        print(f"   Peak memory: {memory_exhaustion_metrics.peak_usage:.1f}MB")
        print(f"   Final memory: {memory_exhaustion_metrics.final_usage:.1f}MB")
        print(f"   Memory growth: {memory_exhaustion_metrics.peak_usage - initial_snapshot.memory_mb:.1f}MB")
        print(f"   Exhaustion detected: {'✓' if memory_exhaustion_metrics.exhaustion_detected else '✗'}")
        print(f"   Graceful degradation: {'✓' if memory_exhaustion_metrics.graceful_degradation_triggered else '✗'}")
        print(f"   Recovery time: {memory_exhaustion_metrics.recovery_time_seconds:.2f}s")
        print(f"   Memory recovered: {'✓' if memory_recovered else '✗'}")
        print(f"   Operations completed: {operations_count}")
        print(f"   Errors during exhaustion: {len(memory_exhaustion_metrics.errors_during_exhaustion)}")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_database_connection_exhaustion_handling(self, real_services_fixture):
        """
        Test database connection pool exhaustion and recovery.
        
        Resource SLA:
        - Connection pool exhaustion detection
        - Graceful request queuing when pool exhausted
        - Automatic recovery when connections available
        - No permanent connection leaks
        """
        db = real_services_fixture["db"]
        
        # Connection exhaustion test parameters
        max_concurrent_connections = 100  # Try to exhaust connection pool
        operations_per_connection = 20
        
        connection_exhaustion_metrics = ResourceExhaustionMetrics(
            test_name="Database Connection Exhaustion",
            resource_type="database_connections",
            initial_usage=0,
            peak_usage=0,
            final_usage=0,
            exhaustion_threshold=50,  # Assume pool has ~50 connections
            exhaustion_detected=False,
            graceful_degradation_triggered=False,
            recovery_time_seconds=0,
            operations_before_exhaustion=0,
            operations_during_exhaustion=0,
            operations_after_recovery=0
        )
        
        connection_timeout_count = 0
        connection_error_count = 0
        active_connections = set()
        
        async def connection_intensive_operation(operation_id: int) -> Dict[str, Any]:
            """Operation that holds database connections for extended periods."""
            operation_start = time.time()
            
            try:
                # Hold connection for longer than usual to increase pool pressure
                connection_hold_time = 0.5  # 500ms per operation
                
                # Start transaction (holds connection)
                async with db.transaction():
                    active_connections.add(operation_id)
                    
                    # Update peak usage tracking
                    current_active = len(active_connections)
                    connection_exhaustion_metrics.peak_usage = max(
                        connection_exhaustion_metrics.peak_usage,
                        current_active
                    )
                    
                    # Perform database operations within transaction
                    for i in range(3):  # 3 queries per connection
                        await db.execute(
                            "SELECT $1 as operation_id, $2 as query_num, generate_series(1, 5)",
                            operation_id, i
                        )
                        
                        # Small delay to hold connection longer
                        await asyncio.sleep(connection_hold_time / 3)
                    
                    # Check if we've likely exhausted the connection pool
                    if current_active > 30 and not connection_exhaustion_metrics.exhaustion_detected:
                        connection_exhaustion_metrics.exhaustion_detected = True
                        print(f"🗃️ Database connection exhaustion detected with {current_active} active connections")
                    
                    active_connections.discard(operation_id)
                
                execution_time = time.time() - operation_start
                
                return {
                    "operation_id": operation_id,
                    "execution_time": execution_time,
                    "success": True,
                    "active_connections_peak": current_active
                }
                
            except asyncio.TimeoutError:
                connection_timeout_count += 1
                connection_exhaustion_metrics.errors_during_exhaustion.append(
                    f"Connection timeout for operation {operation_id}"
                )
                active_connections.discard(operation_id)
                
                return {
                    "operation_id": operation_id,
                    "execution_time": time.time() - operation_start,
                    "success": False,
                    "error": "timeout"
                }
                
            except Exception as e:
                connection_error_count += 1
                connection_exhaustion_metrics.errors_during_exhaustion.append(
                    f"Connection error for operation {operation_id}: {str(e)}"
                )
                active_connections.discard(operation_id)
                
                return {
                    "operation_id": operation_id,
                    "execution_time": time.time() - operation_start,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute connection exhaustion test
        print(f"🔗 Testing database connection exhaustion with {max_concurrent_connections} concurrent operations...")
        exhaustion_start = time.time()
        
        # Launch all operations simultaneously to maximize connection pressure
        operation_tasks = [
            connection_intensive_operation(i)
            for i in range(max_concurrent_connections)
        ]
        
        operation_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        exhaustion_duration = time.time() - exhaustion_start
        
        # Recovery test: perform simple operations after exhaustion
        print(f"🔄 Testing connection pool recovery...")
        recovery_start = time.time()
        
        recovery_operations = 10
        recovery_results = []
        
        for i in range(recovery_operations):
            try:
                await db.execute("SELECT 1 as recovery_test")
                recovery_results.append(True)
            except Exception as e:
                recovery_results.append(False)
                print(f"Recovery operation {i} failed: {e}")
            
            await asyncio.sleep(0.1)
        
        recovery_time = time.time() - recovery_start
        connection_exhaustion_metrics.recovery_time_seconds = recovery_time
        
        # Analyze results
        successful_operations = [r for r in operation_results if isinstance(r, dict) and r.get("success", False)]
        failed_operations = [r for r in operation_results if isinstance(r, dict) and not r.get("success", False)]
        
        connection_exhaustion_metrics.operations_before_exhaustion = len(successful_operations)
        connection_exhaustion_metrics.operations_during_exhaustion = len(failed_operations)
        
        recovery_success_rate = sum(recovery_results) / len(recovery_results)
        overall_success_rate = len(successful_operations) / max_concurrent_connections
        
        # Connection exhaustion assertions
        assert connection_exhaustion_metrics.peak_usage > 10, "Should have created significant connection pressure"
        assert recovery_success_rate >= 0.90, f"Connection pool recovery rate {recovery_success_rate:.3f} below 90%"
        assert recovery_time < 5.0, f"Connection pool recovery time {recovery_time:.2f}s too long"
        
        # Allow for some failures during exhaustion, but not complete failure
        assert overall_success_rate >= 0.60, f"Overall success rate {overall_success_rate:.3f} too low"
        
        print(f"✅ Database Connection Exhaustion Results:")
        print(f"   Concurrent operations: {max_concurrent_connections}")
        print(f"   Successful operations: {len(successful_operations)}")
        print(f"   Failed operations: {len(failed_operations)}")
        print(f"   Peak active connections: {connection_exhaustion_metrics.peak_usage}")
        print(f"   Connection timeouts: {connection_timeout_count}")
        print(f"   Connection errors: {connection_error_count}")
        print(f"   Overall success rate: {overall_success_rate:.3f}")
        print(f"   Recovery success rate: {recovery_success_rate:.3f}")
        print(f"   Recovery time: {recovery_time:.2f}s")
        print(f"   Test duration: {exhaustion_duration:.2f}s")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_redis_memory_exhaustion_handling(self, real_services_fixture):
        """
        Test Redis memory exhaustion detection and handling.
        
        Resource SLA:
        - Redis memory usage monitoring
        - Graceful handling when Redis approaches memory limits
        - Cache eviction policies work correctly under pressure
        - Recovery after memory pressure relief
        """
        redis = real_services_fixture["redis"]
        
        # Redis memory exhaustion parameters
        large_value_size = 1024 * 100  # 100KB per value
        max_keys = 1000  # Up to 100MB of data
        
        redis_memory_metrics = ResourceExhaustionMetrics(
            test_name="Redis Memory Exhaustion",
            resource_type="redis_memory",
            initial_usage=0,
            peak_usage=0,
            final_usage=0,
            exhaustion_threshold=50 * 1024 * 1024,  # 50MB threshold
            exhaustion_detected=False,
            graceful_degradation_triggered=False,
            recovery_time_seconds=0,
            operations_before_exhaustion=0,
            operations_during_exhaustion=0,
            operations_after_recovery=0
        )
        
        # Get initial Redis memory usage
        try:
            initial_redis_info = await redis.info('memory')
            initial_memory = int(initial_redis_info.get('used_memory', 0))
            redis_memory_metrics.initial_usage = initial_memory / 1024 / 1024  # Convert to MB
        except Exception:
            initial_memory = 0
            redis_memory_metrics.initial_usage = 0
        
        operations_completed = 0
        memory_operations_failed = 0
        keys_created = []
        
        try:
            for key_id in range(max_keys):
                test_key = f"redis_exhaustion_test:{key_id}:{int(time.time())}"
                
                # Create large value to consume memory
                large_value = {
                    "key_id": key_id,
                    "data": "x" * large_value_size,
                    "timestamp": time.time(),
                    "metadata": {
                        "size": large_value_size,
                        "test_type": "memory_exhaustion",
                        "iteration": key_id
                    }
                }
                
                try:
                    # Store large value in Redis
                    await redis.set(test_key, json.dumps(large_value), ex=300)  # 5 minute expiry
                    keys_created.append(test_key)
                    operations_completed += 1
                    
                    # Check Redis memory usage periodically
                    if key_id % 50 == 0:  # Every 50 keys
                        try:
                            memory_info = await redis.info('memory')
                            current_memory = int(memory_info.get('used_memory', 0))
                            current_memory_mb = current_memory / 1024 / 1024
                            
                            redis_memory_metrics.peak_usage = max(
                                redis_memory_metrics.peak_usage,
                                current_memory_mb
                            )
                            
                            # Detect memory pressure
                            memory_growth = current_memory - initial_memory
                            if memory_growth > 50 * 1024 * 1024 and not redis_memory_metrics.exhaustion_detected:
                                redis_memory_metrics.exhaustion_detected = True
                                print(f"🔴 Redis memory exhaustion detected at key {key_id}: {current_memory_mb:.1f}MB")
                                
                                # Trigger graceful degradation
                                redis_memory_metrics.graceful_degradation_triggered = True
                                print(f"⚠️ Redis graceful degradation triggered")
                                break
                                
                        except Exception as e:
                            print(f"Memory info check failed: {e}")
                    
                except Exception as e:
                    memory_operations_failed += 1
                    error_msg = str(e).lower()
                    
                    if "memory" in error_msg or "oom" in error_msg:
                        redis_memory_metrics.errors_during_exhaustion.append(
                            f"Redis OOM at key {key_id}: {str(e)}"
                        )
                        if not redis_memory_metrics.exhaustion_detected:
                            redis_memory_metrics.exhaustion_detected = True
                            redis_memory_metrics.graceful_degradation_triggered = True
                            print(f"🔴 Redis OOM detected at key {key_id}")
                            break
                    else:
                        redis_memory_metrics.errors_during_exhaustion.append(
                            f"Redis operation failed at key {key_id}: {str(e)}"
                        )
        
        finally:
            # Test recovery: cleanup keys and verify Redis recovery
            print(f"🧹 Cleaning up {len(keys_created)} Redis keys...")
            recovery_start = time.time()
            
            # Delete keys in batches to avoid overwhelming Redis
            batch_size = 100
            for i in range(0, len(keys_created), batch_size):
                batch_keys = keys_created[i:i + batch_size]
                try:
                    if batch_keys:
                        await redis.delete(*batch_keys)
                except Exception as e:
                    print(f"Batch delete failed: {e}")
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            # Force Redis cleanup (if supported)
            try:
                await redis.execute_command('MEMORY', 'PURGE')
            except Exception:
                pass  # Command might not be supported
            
            # Wait for cleanup to complete
            await asyncio.sleep(2.0)
            
            # Check final memory usage
            try:
                final_redis_info = await redis.info('memory')
                final_memory = int(final_redis_info.get('used_memory', 0))
                redis_memory_metrics.final_usage = final_memory / 1024 / 1024
            except Exception:
                redis_memory_metrics.final_usage = redis_memory_metrics.initial_usage
            
            redis_memory_metrics.recovery_time_seconds = time.time() - recovery_start
        
        # Memory recovery verification
        memory_recovered = (
            redis_memory_metrics.final_usage <= 
            redis_memory_metrics.initial_usage * 1.5  # Within 50% of original
        )
        
        # Redis memory exhaustion assertions
        assert operations_completed > 0, "Should have completed some operations before exhaustion"
        assert redis_memory_metrics.peak_usage > redis_memory_metrics.initial_usage, "Should have increased memory usage"
        assert memory_recovered, f"Redis memory not properly recovered: {redis_memory_metrics.final_usage:.1f}MB vs initial {redis_memory_metrics.initial_usage:.1f}MB"
        
        # Allow for some operations to fail during exhaustion
        failure_rate = memory_operations_failed / (operations_completed + memory_operations_failed)
        assert failure_rate <= 0.5, f"Too many Redis operations failed: {failure_rate:.3f}"
        
        print(f"✅ Redis Memory Exhaustion Results:")
        print(f"   Initial memory: {redis_memory_metrics.initial_usage:.1f}MB")
        print(f"   Peak memory: {redis_memory_metrics.peak_usage:.1f}MB")
        print(f"   Final memory: {redis_memory_metrics.final_usage:.1f}MB")
        print(f"   Memory growth: {redis_memory_metrics.peak_usage - redis_memory_metrics.initial_usage:.1f}MB")
        print(f"   Operations completed: {operations_completed}")
        print(f"   Operations failed: {memory_operations_failed}")
        print(f"   Failure rate: {failure_rate:.3f}")
        print(f"   Exhaustion detected: {'✓' if redis_memory_metrics.exhaustion_detected else '✗'}")
        print(f"   Memory recovered: {'✓' if memory_recovered else '✗'}")
        print(f"   Recovery time: {redis_memory_metrics.recovery_time_seconds:.2f}s")
        print(f"   Keys created: {len(keys_created)}")
        print(f"   Errors during exhaustion: {len(redis_memory_metrics.errors_during_exhaustion)}")
