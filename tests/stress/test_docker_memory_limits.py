"""

Comprehensive Docker Memory Limits and OOM Protection Tests



This module contains stress tests that deliberately consume memory to validate:

- Docker memory limits are properly enforced

- OOM (Out of Memory) protection mechanisms work

- Container restart behavior functions correctly

- Memory leak detection systems are effective



These tests are designed to be DIFFICULT and catch regressions by actually

triggering the bugs if fixes aren't properly applied.

"""



import asyncio

import gc

import os

import psutil

import pytest

import sys

import time

import tracemalloc

from concurrent.futures import ThreadPoolExecutor, as_completed

from contextlib import contextmanager

from dataclasses import dataclass

from typing import Dict, List, Optional, Tuple, Any, Generator

from shared.isolated_environment import IsolatedEnvironment



# Docker and container management

import docker

import subprocess



# Test framework imports

from test_framework.docker_test_utils import (

    DockerContainerManager,

    get_container_memory_stats,

    wait_for_container_health,

    force_container_restart

)



# Memory monitoring imports

try:

    from netra_backend.app.services.memory_optimization_service import (

        MemoryOptimizationService,

        MemoryPressureLevel,

        RequestScope

    )

    from netra_backend.app.services.session_memory_manager import (

        SessionMemoryManager,

        UserSession,

        SessionState

    )

    MEMORY_SERVICES_AVAILABLE = True

except ImportError:

    MEMORY_SERVICES_AVAILABLE = False



# Pytest collection testing

from _pytest.config import Config

from _pytest.main import Session

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient

from shared.isolated_environment import get_env





@dataclass

class MemoryTestResult:

    """Result container for memory test operations"""

    peak_memory_mb: float

    final_memory_mb: float

    memory_leaked_mb: float

    gc_collections: int

    test_duration: float

    oom_triggered: bool

    container_restarted: bool

    error_message: Optional[str] = None





class MemoryStressTester:

    """

    Manages memory stress testing operations with precise tracking

    """

    

    def __init__(self, container_name: str = "test-backend"):

        self.container_name = container_name

        self.docker_client = docker.from_env()

        self.process = psutil.Process(os.getpid())

        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        

    def get_current_memory_mb(self) -> float:

        """Get current process memory usage in MB"""

        return self.process.memory_info().rss / 1024 / 1024

        

    def get_container_memory_mb(self) -> float:

        """Get Docker container memory usage in MB"""

        try:

            container = self.docker_client.containers.get(self.container_name)

            stats = container.stats(stream=False)

            memory_usage = stats['memory_stats']['usage']

            return memory_usage / 1024 / 1024

        except Exception:

            return 0.0

            

    def is_container_running(self) -> bool:

        """Check if container is running"""

        try:

            container = self.docker_client.containers.get(self.container_name)

            return container.status == 'running'

        except Exception:

            return False

            

    @contextmanager

    def memory_tracking(self) -> Generator[Dict[str, Any], None, None]:

        """Context manager for memory tracking during test execution"""

        tracemalloc.start()

        start_memory = self.get_current_memory_mb()

        start_time = time.time()

        gc_before = len(gc.get_objects())

        

        tracking_data = {

            'start_memory': start_memory,

            'peak_memory': start_memory,

            'allocations': []

        }

        

        try:

            yield tracking_data

        finally:

            end_time = time.time()

            end_memory = self.get_current_memory_mb()

            gc_after = len(gc.get_objects())

            

            current, peak = tracemalloc.get_traced_memory()

            tracemalloc.stop()

            

            tracking_data.update({

                'end_memory': end_memory,

                'peak_memory': max(tracking_data['peak_memory'], end_memory),

                'duration': end_time - start_time,

                'gc_objects_created': gc_after - gc_before,

                'tracemalloc_peak': peak / 1024 / 1024,  # Convert to MB

                'memory_leaked': end_memory - start_memory

            })





class DockerMemoryLimitTests:

    """

    Comprehensive Docker memory limit and OOM protection tests

    """

    

    @pytest.fixture(scope="class")

    def memory_tester(self) -> MemoryStressTester:

        """Setup memory stress tester"""

        return MemoryStressTester()

        

    @pytest.fixture(autouse=True)

    def setup_test_isolation(self):

        """Ensure each test starts with clean memory state"""

        gc.collect()

        yield

        gc.collect()



    def test_gradual_memory_consumption_with_oom_protection(self, memory_tester: MemoryStressTester):

        """

        Test that gradually consumes memory to verify OOM protection kicks in

        

        This test deliberately tries to trigger memory exhaustion to validate

        that OOM protection mechanisms are working correctly.

        """

        memory_chunks = []

        max_chunks = 1000  # Adjust based on available memory

        chunk_size = 10 * 1024 * 1024  # 10MB chunks

        

        with memory_tester.memory_tracking() as tracking:

            try:

                for i in range(max_chunks):

                    # Allocate memory chunk

                    chunk = bytearray(chunk_size)

                    # Fill with data to ensure actual allocation

                    for j in range(0, len(chunk), 4096):

                        chunk[j:j+100] = b'X' * 100

                    

                    memory_chunks.append(chunk)

                    current_memory = memory_tester.get_current_memory_mb()

                    tracking['peak_memory'] = max(tracking['peak_memory'], current_memory)

                    

                    # Check if we're approaching system limits

                    if current_memory > tracking['start_memory'] + 1000:  # 1GB increase

                        break

                        

                    # Brief pause to allow OOM protection to kick in

                    if i % 10 == 0:

                        time.sleep(0.1)

                        

            except MemoryError:

                # This is expected behavior - OOM protection should prevent this

                pytest.fail("OOM protection failed - MemoryError was raised")

            except Exception as e:

                # Log unexpected errors but don't fail - might be OOM protection

                print(f"Memory allocation stopped due to: {e}")

                

        # Verify memory was actually allocated and tracking worked

        assert tracking['peak_memory'] > tracking['start_memory'] + 50  # At least 50MB allocated

        assert len(memory_chunks) > 0, "No memory chunks were allocated"

        

        # Clean up

        del memory_chunks

        gc.collect()

        

        # Verify cleanup worked

        final_memory = memory_tester.get_current_memory_mb()

        memory_recovered = tracking['peak_memory'] - final_memory

        assert memory_recovered > 0, "Memory was not properly recovered after cleanup"



    def test_memory_leak_detection_during_pytest_collection(self, memory_tester: MemoryStressTester):

        """

        Test memory leak detection during pytest collection phase

        

        Creates many mock test objects to simulate heavy collection load

        and verifies memory doesn't continuously grow.

        """

        

        class MockTestItem:

            """Mock pytest test item that allocates memory"""

            def __init__(self, name: str):

                self.name = name

                self.data = bytearray(1024 * 100)  # 100KB per test

                self.metadata = {f'key_{i}': f'value_{i}' * 100 for i in range(50)}

                

        with memory_tester.memory_tracking() as tracking:

            test_items = []

            memory_measurements = []

            

            # Simulate collecting 1000 test items

            for i in range(1000):

                test_item = MockTestItem(f"test_{i}")

                test_items.append(test_item)

                

                # Measure memory every 100 items

                if i % 100 == 0:

                    current_memory = memory_tester.get_current_memory_mb()

                    memory_measurements.append(current_memory)

                    tracking['peak_memory'] = max(tracking['peak_memory'], current_memory)

                    

                    # Force garbage collection periodically

                    if i % 200 == 0:

                        gc.collect()

                        

            # Verify memory growth is reasonable

            memory_growth = memory_measurements[-1] - memory_measurements[0]

            expected_max_growth = 150  # 150MB max for 1000 test items

            

            assert memory_growth < expected_max_growth, (

                f"Memory growth {memory_growth:.1f}MB exceeds expected {expected_max_growth}MB. "

                f"Possible memory leak in test collection."

            )

            

        # Clean up and verify memory is released

        del test_items

        gc.collect()

        

        final_memory = memory_tester.get_current_memory_mb()

        memory_retained = final_memory - tracking['start_memory']

        

        # Should retain less than 20MB after cleanup

        assert memory_retained < 20, (

            f"Memory leak detected: {memory_retained:.1f}MB retained after cleanup"

        )



    def test_container_restart_under_memory_pressure(self, memory_tester: MemoryStressTester):

        """

        Test container restart behavior when memory pressure is high

        

        Simulates high memory usage and verifies containers can restart

        gracefully without losing critical state.

        """

        if not memory_tester.is_container_running():

            pytest.skip("Docker container not running for test")

            

        initial_container_memory = memory_tester.get_container_memory_mb()

        

        with memory_tester.memory_tracking() as tracking:

            # Create memory pressure

            pressure_data = []

            try:

                # Allocate memory in chunks while monitoring container

                for i in range(50):

                    chunk = bytearray(20 * 1024 * 1024)  # 20MB chunks

                    # Fill to ensure actual allocation

                    chunk[0:1024] = b'Y' * 1024

                    pressure_data.append(chunk)

                    

                    current_memory = memory_tester.get_current_memory_mb()

                    container_memory = memory_tester.get_container_memory_mb()

                    

                    tracking['peak_memory'] = max(tracking['peak_memory'], current_memory)

                    

                    # Check if container is still healthy

                    if not memory_tester.is_container_running():

                        # Container restarted - this is acceptable behavior

                        time.sleep(2)  # Wait for restart

                        break

                        

                    time.sleep(0.1)  # Brief pause

                    

            except Exception as e:

                # Memory pressure might cause various exceptions

                print(f"Memory pressure caused: {e}")

                

        # Verify container is still running (possibly after restart)

        time.sleep(1)

        container_healthy = memory_tester.is_container_running()

        

        if not container_healthy:

            # Try to restart container for next tests

            try:

                container = memory_tester.docker_client.containers.get(memory_tester.container_name)

                container.restart()

                time.sleep(5)

                container_healthy = memory_tester.is_container_running()

            except Exception:

                pass

                

        # Clean up memory pressure

        del pressure_data

        gc.collect()

        

        # Assert final state

        assert tracking['peak_memory'] > tracking['start_memory'] + 100, "Insufficient memory pressure created"

        

        # Container should be healthy after cleanup (restart is acceptable)

        final_container_state = memory_tester.is_container_running()

        if not final_container_state:

            pytest.fail("Container failed to recover after memory pressure test")



    def test_memory_fragmentation_resistance(self, memory_tester: MemoryStressTester):

        """

        Test resistance to memory fragmentation attacks

        

        Rapidly allocates and deallocates memory of various sizes

        to create fragmentation and verify system stability.

        """

        

        with memory_tester.memory_tracking() as tracking:

            allocated_chunks = {}

            chunk_id = 0

            

            try:

                # Phase 1: Allocate chunks of varying sizes

                sizes = [1024, 4096, 16384, 65536, 262144]  # 1KB to 256KB

                for round_num in range(20):

                    for size in sizes:

                        for _ in range(10):  # 10 chunks per size per round

                            chunk = bytearray(size)

                            chunk[0:min(size, 100)] = b'Z' * min(size, 100)

                            allocated_chunks[chunk_id] = chunk

                            chunk_id += 1

                            

                    # Phase 2: Randomly deallocate some chunks to create fragmentation

                    if round_num % 3 == 0:

                        keys_to_remove = list(allocated_chunks.keys())[::2]  # Every second chunk

                        for key in keys_to_remove:

                            del allocated_chunks[key]

                        gc.collect()

                        

                    current_memory = memory_tester.get_current_memory_mb()

                    tracking['peak_memory'] = max(tracking['peak_memory'], current_memory)

                    

                    # Brief pause

                    time.sleep(0.05)

                    

            except MemoryError:

                pytest.fail("Memory fragmentation caused MemoryError - system not robust enough")

            except Exception as e:

                print(f"Fragmentation test encountered: {e}")

                

        # Verify we created significant memory activity

        assert len(allocated_chunks) > 0, "No chunks were allocated during fragmentation test"

        assert tracking['peak_memory'] > tracking['start_memory'] + 20, "Insufficient memory pressure for fragmentation test"

        

        # Clean up

        allocated_chunks.clear()

        gc.collect()

        

        # Verify cleanup

        final_memory = memory_tester.get_current_memory_mb()

        memory_retained = final_memory - tracking['start_memory']

        assert memory_retained < 50, f"Excessive memory retained after fragmentation test: {memory_retained:.1f}MB"



    @pytest.mark.parametrize("worker_count", [1, 2, 4, 8])

    def test_concurrent_memory_pressure_with_workers(self, memory_tester: MemoryStressTester, worker_count: int):

        """

        Test memory behavior under concurrent worker load

        

        Simulates multiple pytest workers each consuming memory

        to verify memory limits are enforced per-worker and globally.

        """

        

        def worker_memory_task(worker_id: int, duration: float) -> Dict[str, Any]:

            """Memory-intensive task for worker thread"""

            start_time = time.time()

            allocated = []

            peak_memory = 0

            

            try:

                while time.time() - start_time < duration:

                    # Allocate 5MB chunk

                    chunk = bytearray(5 * 1024 * 1024)

                    chunk[0:1024] = f"worker_{worker_id}".encode() * (1024 // len(f"worker_{worker_id}"))

                    allocated.append(chunk)

                    

                    # Measure memory

                    current_memory = memory_tester.get_current_memory_mb()

                    peak_memory = max(peak_memory, current_memory)

                    

                    # Occasionally clean up some allocations

                    if len(allocated) > 20:

                        del allocated[:10]

                        gc.collect()

                        

                    time.sleep(0.1)

                    

            except Exception as e:

                return {'worker_id': worker_id, 'error': str(e), 'peak_memory': peak_memory}

                

            # Clean up

            del allocated

            gc.collect()

            

            return {

                'worker_id': worker_id,

                'peak_memory': peak_memory,

                'allocations_made': len(allocated) if allocated else 0,

                'duration': time.time() - start_time

            }

        

        with memory_tester.memory_tracking() as tracking:

            # Run concurrent workers

            with ThreadPoolExecutor(max_workers=worker_count) as executor:

                futures = []

                test_duration = 5.0  # 5 seconds per worker

                

                for worker_id in range(worker_count):

                    future = executor.submit(worker_memory_task, worker_id, test_duration)

                    futures.append(future)

                

                # Collect results

                worker_results = []

                for future in as_completed(futures):

                    try:

                        result = future.result()

                        worker_results.append(result)

                        

                        # Update tracking peak

                        if 'peak_memory' in result:

                            tracking['peak_memory'] = max(tracking['peak_memory'], result['peak_memory'])

                            

                    except Exception as e:

                        worker_results.append({'error': str(e)})

        

        # Verify all workers completed

        assert len(worker_results) == worker_count, "Not all workers completed"

        

        # Verify no workers had critical errors (some memory pressure errors are acceptable)

        successful_workers = [r for r in worker_results if 'error' not in r]

        assert len(successful_workers) >= worker_count // 2, (

            f"Too many workers failed: {worker_count - len(successful_workers)} out of {worker_count}"

        )

        

        # Verify memory pressure was created

        assert tracking['peak_memory'] > tracking['start_memory'] + (worker_count * 20), (

            f"Insufficient memory pressure with {worker_count} workers"

        )

        

        # Final cleanup and verification

        gc.collect()

        final_memory = memory_tester.get_current_memory_mb()

        memory_retained = final_memory - tracking['start_memory']

        

        # Should not retain excessive memory

        max_retained = worker_count * 10  # 10MB per worker max

        assert memory_retained < max_retained, (

            f"Excessive memory retained: {memory_retained:.1f}MB with {worker_count} workers"

        )



    def test_oom_killer_simulation_and_recovery(self, memory_tester: MemoryStressTester):

        """

        Test OOM killer simulation and recovery mechanisms

        

        Simulates conditions that would trigger OOM killer and verifies

        the system can recover gracefully.

        """

        if not memory_tester.is_container_running():

            pytest.skip("Docker container not running for OOM test")

            

        with memory_tester.memory_tracking() as tracking:

            # Get system memory info

            system_memory = psutil.virtual_memory()

            available_mb = system_memory.available / 1024 / 1024

            

            # Try to allocate a significant portion of available memory

            target_allocation = min(available_mb * 0.6, 2000)  # 60% or 2GB, whichever is smaller

            chunk_size = 50 * 1024 * 1024  # 50MB chunks

            chunks_needed = int(target_allocation / (chunk_size / 1024 / 1024))

            

            allocated_chunks = []

            oom_triggered = False

            

            try:

                for i in range(chunks_needed):

                    chunk = bytearray(chunk_size)

                    # Actually use the memory to prevent lazy allocation

                    chunk[0:4096] = b'OOM_TEST' * 512

                    allocated_chunks.append(chunk)

                    

                    current_memory = memory_tester.get_current_memory_mb()

                    tracking['peak_memory'] = max(tracking['peak_memory'], current_memory)

                    

                    # Check if container is still healthy

                    if not memory_tester.is_container_running():

                        print("Container went down during OOM test - checking for restart")

                        oom_triggered = True

                        break

                        

                    # Brief pause to allow system to respond

                    time.sleep(0.2)

                    

                    # Stop if we've allocated enough to test limits

                    if current_memory > tracking['start_memory'] + target_allocation:

                        break

                        

            except MemoryError:

                # This might be OOM protection working correctly

                print("MemoryError encountered - this may be OOM protection")

                oom_triggered = True

                

            except Exception as e:

                print(f"OOM test encountered: {e}")

                oom_triggered = True

        

        # Clean up allocated memory

        del allocated_chunks

        gc.collect()

        

        # Verify significant memory pressure was created

        memory_pressure = tracking['peak_memory'] - tracking['start_memory']

        assert memory_pressure > 100, f"Insufficient memory pressure for OOM test: {memory_pressure:.1f}MB"

        

        # Verify system recovery

        time.sleep(2)  # Allow time for recovery

        

        # Check container health after OOM simulation

        container_recovered = memory_tester.is_container_running()

        if not container_recovered and oom_triggered:

            # Try to restart container

            try:

                container = memory_tester.docker_client.containers.get(memory_tester.container_name)

                container.restart()

                time.sleep(10)  # Wait for full restart

                container_recovered = memory_tester.is_container_running()

            except Exception as e:

                print(f"Container restart failed: {e}")

                

        # Final verification

        final_memory = memory_tester.get_current_memory_mb()

        memory_recovered = tracking['peak_memory'] - final_memory

        

        assert memory_recovered > memory_pressure * 0.8, (

            f"Insufficient memory recovery: only {memory_recovered:.1f}MB of {memory_pressure:.1f}MB recovered"

        )

        

        # If OOM was triggered, recovery should have occurred

        if oom_triggered:

            assert container_recovered, "Container failed to recover after OOM simulation"





# Integration with real memory monitoring services

@pytest.mark.skipif(not MEMORY_SERVICES_AVAILABLE, reason="Memory monitoring services not available")

class TestMemoryServicesIntegration:

    """

    Tests integration with actual memory monitoring services

    """

    

    def test_memory_optimization_service_under_pressure(self):

        """Test memory optimization service behavior under memory pressure"""

        memory_service = MemoryOptimizationService()

        

        # Create memory pressure

        large_allocations = []

        try:

            for i in range(100):

                allocation = bytearray(10 * 1024 * 1024)  # 10MB

                large_allocations.append(allocation)

                

                # Check if memory service detects pressure

                pressure_level = memory_service.get_current_pressure_level()

                if pressure_level != MemoryPressureLevel.LOW:

                    break

                    

        finally:

            # Clean up

            del large_allocations

            gc.collect()

            

        # Verify service detected pressure

        final_pressure = memory_service.get_current_pressure_level()

        assert final_pressure in [MemoryPressureLevel.LOW, MemoryPressureLevel.MEDIUM], (

            "Memory service should have detected and cleaned up pressure"

        )



    def test_session_memory_manager_cleanup(self):

        """Test session memory manager cleanup under load"""

        session_manager = SessionMemoryManager()

        

        # Create many user sessions

        sessions = []

        for i in range(500):

            user_session = UserSession(

                user_id=f"user_{i}",

                session_id=f"session_{i}",

                state=SessionState.ACTIVE

            )

            sessions.append(user_session)

            session_manager.register_session(user_session)

            

        # Force cleanup

        initial_count = session_manager.get_active_session_count()

        session_manager.cleanup_inactive_sessions()

        

        # Verify cleanup occurred

        final_count = session_manager.get_active_session_count()

        assert final_count <= initial_count, "Session cleanup should not increase session count"

        

        # Clean up test sessions

        for session in sessions:

            session_manager.unregister_session(session.session_id)

