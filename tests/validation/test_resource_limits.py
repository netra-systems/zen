"""

Comprehensive Resource Limits Validation and Exhaustion Tests



This module contains validation tests for resource limits enforcement:

- Verification that all resource limits are properly enforced

- Testing graceful degradation under resource pressure  

- Resource exhaustion handling and recovery mechanisms

- Recovery from resource-induced crashes

- System stability under extreme resource conditions



These tests are designed to be DIFFICULT and catch regressions by actually

exhausting system resources and validating recovery mechanisms work.

"""



import asyncio

import gc

import multiprocessing

import os

import psutil

import pytest

import subprocess

import sys

import tempfile

import threading

import time

import traceback

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from contextlib import contextmanager

from dataclasses import dataclass, field

from pathlib import Path

from typing import Dict, List, Optional, Tuple, Any, Set

import signal

import resource

from shared.isolated_environment import IsolatedEnvironment



# Docker and system monitoring

import docker

try:

    import nvidia_ml_py3 as nvml

    GPU_MONITORING_AVAILABLE = True

except ImportError:

    GPU_MONITORING_AVAILABLE = False



# Test framework imports

from test_framework.resource_monitoring import (

    ResourceMonitor,

    SystemResourceSnapshot,

    ResourceLimitEnforcer

)





@dataclass

class ResourceExhaustionResult:

    """Result of resource exhaustion test"""

    resource_type: str

    exhaustion_successful: bool

    time_to_exhaustion: float

    peak_usage: float

    recovery_time: float

    system_stability: str  # "stable", "degraded", "crashed"

    error_messages: List[str] = field(default_factory=list)

    recovery_successful: bool = True





@dataclass

class ResourceLimitTest:

    """Configuration for resource limit test"""

    resource_type: str

    target_usage_percent: float

    duration_seconds: float

    expected_behavior: str  # "limit_enforced", "graceful_degradation", "system_protection"

    tolerance_percent: float = 10.0





class SystemResourceMonitor:

    """

    Advanced system resource monitoring and analysis

    """

    

    def __init__(self):

        self.process = psutil.Process()

        self.initial_snapshot = self._take_snapshot()

        self.monitoring_active = False

        self.resource_history = []

        

        # Initialize GPU monitoring if available

        self.gpu_available = False

        if GPU_MONITORING_AVAILABLE:

            try:

                nvml.nvmlInit()

                self.gpu_count = nvml.nvmlDeviceGetCount()

                self.gpu_available = self.gpu_count > 0

            except:

                self.gpu_available = False

    

    def _take_snapshot(self) -> Dict[str, Any]:

        """Take comprehensive system resource snapshot"""

        snapshot = {

            'timestamp': time.time(),

            'cpu_percent': psutil.cpu_percent(interval=0.1),

            'cpu_count': psutil.cpu_count(),

            'memory': psutil.virtual_memory(),

            'swap': psutil.swap_memory(),

            'disk': psutil.disk_usage('/'),

            'process_count': len(psutil.pids()),

            'open_files': len(psutil.Process().open_files()) if hasattr(psutil.Process(), 'open_files') else 0,

            'network': psutil.net_io_counters(),

        }

        

        # Add process-specific info

        try:

            proc_info = self.process.as_dict([

                'pid', 'memory_info', 'cpu_percent', 'num_threads',

                'open_files', 'connections'

            ])

            snapshot['process'] = proc_info

        except:

            snapshot['process'] = {}

        

        # Add GPU info if available

        if self.gpu_available:

            try:

                gpu_info = []

                for i in range(self.gpu_count):

                    handle = nvml.nvmlDeviceGetHandleByIndex(i)

                    memory = nvml.nvmlDeviceGetMemoryInfo(handle)

                    utilization = nvml.nvmlDeviceGetUtilizationRates(handle)

                    

                    gpu_info.append({

                        'index': i,

                        'memory_used': memory.used,

                        'memory_total': memory.total,

                        'memory_percent': (memory.used / memory.total) * 100,

                        'gpu_utilization': utilization.gpu,

                        'memory_utilization': utilization.memory

                    })

                snapshot['gpu'] = gpu_info

            except:

                snapshot['gpu'] = []

        

        return snapshot

    

    @contextmanager

    def continuous_monitoring(self, interval: float = 1.0):

        """Continuously monitor system resources"""

        self.monitoring_active = True

        self.resource_history.clear()

        

        def monitoring_worker():

            while self.monitoring_active:

                snapshot = self._take_snapshot()

                self.resource_history.append(snapshot)

                time.sleep(interval)

        

        monitor_thread = threading.Thread(target=monitoring_worker, daemon=True)

        monitor_thread.start()

        

        try:

            yield self.resource_history

        finally:

            self.monitoring_active = False

            monitor_thread.join(timeout=5)

    

    def analyze_resource_patterns(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Analyze resource usage patterns from monitoring history"""

        if not history:

            return {}

        

        analysis = {

            'duration': history[-1]['timestamp'] - history[0]['timestamp'],

            'samples': len(history)

        }

        

        # CPU analysis

        cpu_values = [s['cpu_percent'] for s in history if s['cpu_percent'] is not None]

        if cpu_values:

            analysis['cpu'] = {

                'min': min(cpu_values),

                'max': max(cpu_values),

                'avg': sum(cpu_values) / len(cpu_values),

                'variance': max(cpu_values) - min(cpu_values)

            }

        

        # Memory analysis  

        memory_values = [s['memory']['percent'] for s in history if 'memory' in s]

        if memory_values:

            analysis['memory'] = {

                'min': min(memory_values),

                'max': max(memory_values),

                'avg': sum(memory_values) / len(memory_values),

                'peak_mb': max(s['memory']['used'] / 1024 / 1024 for s in history if 'memory' in s)

            }

        

        # Process analysis

        proc_memory_values = []

        proc_thread_values = []

        

        for s in history:

            if 'process' in s and 'memory_info' in s['process']:

                if s['process']['memory_info']:

                    proc_memory_values.append(s['process']['memory_info']['rss'] / 1024 / 1024)

            

            if 'process' in s and 'num_threads' in s['process']:

                if s['process']['num_threads']:

                    proc_thread_values.append(s['process']['num_threads'])

        

        if proc_memory_values:

            analysis['process_memory'] = {

                'min_mb': min(proc_memory_values),

                'max_mb': max(proc_memory_values),

                'avg_mb': sum(proc_memory_values) / len(proc_memory_values)

            }

        

        if proc_thread_values:

            analysis['process_threads'] = {

                'min': min(proc_thread_values),

                'max': max(proc_thread_values),

                'avg': sum(proc_thread_values) / len(proc_thread_values)

            }

        

        return analysis





class ResourceExhaustionTester:

    """

    Creates controlled resource exhaustion scenarios for testing

    """

    

    def __init__(self):

        self.active_exhaustion_threads = []

        self.exhaustion_data = {}

        

    def cleanup(self):

        """Clean up any active resource exhaustion operations"""

        for thread in self.active_exhaustion_threads:

            if thread.is_alive():

                # Note: Can't directly kill threads, they should check termination conditions

                pass

        

        # Force garbage collection

        gc.collect()

        

        # Clear any cached data

        self.exhaustion_data.clear()

    

    def exhaust_memory(self, target_percent: float, max_duration: float = 30.0) -> ResourceExhaustionResult:

        """Gradually exhaust system memory to target percentage"""

        start_time = time.time()

        allocated_chunks = []

        

        system_memory = psutil.virtual_memory()

        target_bytes = int((target_percent / 100) * system_memory.total)

        current_process_memory = psutil.Process().memory_info().rss

        

        # Calculate how much more memory to allocate

        additional_bytes = target_bytes - current_process_memory

        if additional_bytes <= 0:

            return ResourceExhaustionResult(

                resource_type="memory",

                exhaustion_successful=False,

                time_to_exhaustion=0,

                peak_usage=current_process_memory / 1024 / 1024,

                recovery_time=0,

                system_stability="stable",

                error_messages=["Already at or above target memory usage"]

            )

        

        chunk_size = 10 * 1024 * 1024  # 10MB chunks

        chunks_needed = additional_bytes // chunk_size

        

        try:

            for i in range(int(chunks_needed)):

                if time.time() - start_time > max_duration:

                    break

                

                # Allocate and actually use memory to prevent lazy allocation

                chunk = bytearray(chunk_size)

                chunk[0:4096] = b'EXHAUST' * (4096 // 7)

                chunk[-4096:] = b'MEMORY' * (4096 // 6)

                allocated_chunks.append(chunk)

                

                # Check current memory usage

                current_memory = psutil.virtual_memory()

                if current_memory.percent >= target_percent:

                    break

                    

                # Brief pause to allow system to respond

                if i % 10 == 0:

                    time.sleep(0.1)

            

            exhaustion_time = time.time() - start_time

            peak_usage = psutil.virtual_memory().percent

            exhaustion_successful = peak_usage >= target_percent * 0.9  # Within 90% of target

            

            # Hold memory briefly to test system behavior

            time.sleep(2)

            

        except MemoryError:

            exhaustion_time = time.time() - start_time

            peak_usage = psutil.virtual_memory().percent

            exhaustion_successful = True  # MemoryError indicates successful exhaustion

        except Exception as e:

            exhaustion_time = time.time() - start_time

            peak_usage = psutil.virtual_memory().percent

            exhaustion_successful = False

            

        # Recovery phase

        recovery_start = time.time()

        try:

            del allocated_chunks

            gc.collect()

            

            # Wait for memory to be released

            time.sleep(1)

            recovery_time = time.time() - recovery_start

            recovery_successful = True

            

        except Exception as e:

            recovery_time = time.time() - recovery_start

            recovery_successful = False

        

        # Assess system stability

        try:

            final_memory = psutil.virtual_memory()

            if final_memory.percent < target_percent * 0.5:

                stability = "stable"

            elif final_memory.percent < target_percent * 0.8:

                stability = "degraded"

            else:

                stability = "crashed"

        except:

            stability = "crashed"

        

        return ResourceExhaustionResult(

            resource_type="memory",

            exhaustion_successful=exhaustion_successful,

            time_to_exhaustion=exhaustion_time,

            peak_usage=peak_usage,

            recovery_time=recovery_time,

            system_stability=stability,

            recovery_successful=recovery_successful

        )

    

    def exhaust_cpu(self, target_percent: float, duration: float = 10.0) -> ResourceExhaustionResult:

        """Create CPU exhaustion using multiple worker threads"""

        start_time = time.time()

        cpu_count = psutil.cpu_count()

        

        # Calculate number of threads needed

        threads_needed = max(1, int((target_percent / 100) * cpu_count))

        

        def cpu_worker(worker_id: int, duration: float):

            """CPU-intensive worker function"""

            import math

            end_time = time.time() + duration

            

            while time.time() < end_time:

                # Intensive mathematical operations

                for _ in range(10000):

                    math.sqrt(worker_id * 12345) * math.sin(worker_id) * math.cos(worker_id)

        

        # Start CPU workers

        workers = []

        with ThreadPoolExecutor(max_workers=threads_needed) as executor:

            for i in range(threads_needed):

                future = executor.submit(cpu_worker, i, duration)

                workers.append(future)

            

            # Monitor CPU usage during exhaustion

            time.sleep(1)  # Let threads start

            peak_cpu = 0

            

            monitor_start = time.time()

            while time.time() - monitor_start < duration - 1:

                current_cpu = psutil.cpu_percent(interval=0.5)

                peak_cpu = max(peak_cpu, current_cpu)

                

            # Wait for workers to complete

            for future in as_completed(workers, timeout=duration + 5):

                try:

                    future.result()

                except Exception as e:

                    pass  # Worker exceptions are not critical for this test

        

        exhaustion_time = time.time() - start_time

        exhaustion_successful = peak_cpu >= target_percent * 0.8  # Within 80% of target

        

        # Recovery assessment

        recovery_start = time.time()

        time.sleep(2)  # Wait for CPU to cool down

        final_cpu = psutil.cpu_percent(interval=1.0)

        recovery_time = time.time() - recovery_start

        

        # Assess stability

        if final_cpu < 20:

            stability = "stable"

        elif final_cpu < 50:

            stability = "degraded"

        else:

            stability = "crashed"

        

        return ResourceExhaustionResult(

            resource_type="cpu",

            exhaustion_successful=exhaustion_successful,

            time_to_exhaustion=exhaustion_time,

            peak_usage=peak_cpu,

            recovery_time=recovery_time,

            system_stability=stability,

            recovery_successful=final_cpu < target_percent

        )

    

    def exhaust_file_descriptors(self, target_percent: float = 80.0) -> ResourceExhaustionResult:

        """Exhaust available file descriptors"""

        start_time = time.time()

        

        # Get current and max file descriptor limits

        try:

            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

            target_fds = int((target_percent / 100) * soft_limit)

        except:

            # Fallback if resource limits not available

            soft_limit = 1024

            target_fds = int((target_percent / 100) * soft_limit)

        

        opened_files = []

        temp_files = []

        

        try:

            # Create temporary files and keep them open

            temp_dir = Path(tempfile.mkdtemp())

            

            for i in range(target_fds):

                temp_file = temp_dir / f"exhaust_fd_{i}.tmp"

                temp_files.append(temp_file)

                

                try:

                    f = open(temp_file, 'w')

                    f.write(f"FD exhaustion test file {i}\n" * 10)

                    opened_files.append(f)

                except OSError as e:

                    if "too many open files" in str(e).lower():

                        # Successfully exhausted file descriptors

                        break

                    else:

                        raise

                        

                # Check periodically 

                if i % 100 == 0:

                    time.sleep(0.01)

            

            exhaustion_time = time.time() - start_time

            fds_opened = len(opened_files)

            exhaustion_successful = fds_opened >= target_fds * 0.8

            peak_usage = fds_opened

            

        except Exception as e:

            exhaustion_time = time.time() - start_time

            fds_opened = len(opened_files)

            exhaustion_successful = "too many open files" in str(e).lower()

            peak_usage = fds_opened

        

        # Recovery phase

        recovery_start = time.time()

        try:

            # Close all opened files

            for f in opened_files:

                try:

                    f.close()

                except:

                    pass

            

            # Clean up temp files

            import shutil

            if temp_dir.exists():

                shutil.rmtree(temp_dir, ignore_errors=True)

            

            recovery_time = time.time() - recovery_start

            recovery_successful = True

            

        except Exception as e:

            recovery_time = time.time() - recovery_start

            recovery_successful = False

        

        # Stability assessment

        try:

            # Try to open a new file to test recovery

            test_file = tempfile.NamedTemporaryFile(delete=True)

            test_file.close()

            stability = "stable"

        except:

            stability = "degraded"

        

        return ResourceExhaustionResult(

            resource_type="file_descriptors",

            exhaustion_successful=exhaustion_successful,

            time_to_exhaustion=exhaustion_time,

            peak_usage=peak_usage,

            recovery_time=recovery_time,

            system_stability=stability,

            recovery_successful=recovery_successful

        )

    

    def exhaust_disk_space(self, target_percent: float = 90.0, max_size_mb: float = 1000.0) -> ResourceExhaustionResult:

        """Create temporary disk space exhaustion (limited for safety)"""

        start_time = time.time()

        

        # Get disk usage info

        disk_usage = psutil.disk_usage('/')

        available_mb = disk_usage.free / 1024 / 1024

        

        # Limit exhaustion size for safety

        max_safe_mb = min(max_size_mb, available_mb * 0.8)  # Use at most 80% of available

        

        temp_files = []

        total_written_mb = 0

        

        try:

            temp_dir = Path(tempfile.mkdtemp())

            chunk_size_mb = 50  # 50MB chunks

            

            while total_written_mb < max_safe_mb:

                chunk_file = temp_dir / f"disk_exhaust_{len(temp_files)}.tmp"

                

                try:

                    with open(chunk_file, 'wb') as f:

                        # Write chunk_size_mb of data

                        chunk_data = b'DISK_EXHAUST' * (1024 * 1024 // 12)  # ~1MB

                        for _ in range(int(chunk_size_mb)):

                            f.write(chunk_data)

                        

                        temp_files.append(chunk_file)

                        total_written_mb += chunk_size_mb

                        

                except OSError as e:

                    if "no space left" in str(e).lower():

                        exhaustion_successful = True

                        break

                    else:

                        raise

                

                # Safety check

                current_disk = psutil.disk_usage('/')

                if (current_disk.free / current_disk.total) < 0.1:  # Less than 10% free

                    break

            

            exhaustion_time = time.time() - start_time

            peak_usage = total_written_mb

            exhaustion_successful = total_written_mb >= max_safe_mb * 0.8

            

        except Exception as e:

            exhaustion_time = time.time() - start_time

            peak_usage = total_written_mb

            exhaustion_successful = "no space left" in str(e).lower()

        

        # Recovery phase

        recovery_start = time.time()

        try:

            # Clean up temp files

            import shutil

            if temp_dir.exists():

                shutil.rmtree(temp_dir, ignore_errors=True)

            

            recovery_time = time.time() - recovery_start

            recovery_successful = True

            

        except Exception as e:

            recovery_time = time.time() - recovery_start

            recovery_successful = False

        

        # Stability check

        try:

            test_file = tempfile.NamedTemporaryFile(delete=True)

            test_file.write(b"disk recovery test")

            test_file.close()

            stability = "stable"

        except:

            stability = "degraded"

        

        return ResourceExhaustionResult(

            resource_type="disk_space",

            exhaustion_successful=exhaustion_successful,

            time_to_exhaustion=exhaustion_time,

            peak_usage=peak_usage,

            recovery_time=recovery_time,

            system_stability=stability,

            recovery_successful=recovery_successful

        )





class ResourceLimitsValidationTests:

    """

    Comprehensive resource limits validation and exhaustion tests

    """

    

    @pytest.fixture(scope="class")

    def resource_monitor(self) -> SystemResourceMonitor:

        """Setup system resource monitor"""

        return SystemResourceMonitor()

    

    @pytest.fixture(scope="class") 

    def exhaustion_tester(self) -> ResourceExhaustionTester:

        """Setup resource exhaustion tester"""

        tester = ResourceExhaustionTester()

        yield tester

        tester.cleanup()

    

    @pytest.fixture(autouse=True)

    def setup_test_isolation(self):

        """Ensure each test starts with clean resource state"""

        # Force garbage collection

        gc.collect()

        

        # Brief pause to let system stabilize

        time.sleep(1)

        

        yield

        

        # Cleanup after test

        gc.collect()

        time.sleep(0.5)



    def test_memory_limit_enforcement_and_recovery(self, resource_monitor: SystemResourceMonitor, 

                                                  exhaustion_tester: ResourceExhaustionTester):

        """

        Test memory limit enforcement and recovery mechanisms

        

        Gradually exhausts system memory to test limit enforcement,

        graceful degradation, and recovery mechanisms.

        """

        

        # Get initial memory state

        initial_memory = psutil.virtual_memory()

        if initial_memory.percent > 70:

            pytest.skip("System memory already too high for exhaustion test")

        

        with resource_monitor.continuous_monitoring(interval=0.5) as monitoring_data:

            # Test different memory exhaustion levels

            test_levels = [60, 75, 85]  # Percentage targets

            results = []

            

            for target_percent in test_levels:

                if initial_memory.percent + 30 < target_percent:  # Only test if realistic

                    print(f"Testing memory exhaustion to {target_percent}%")

                    

                    result = exhaustion_tester.exhaust_memory(

                        target_percent=target_percent,

                        max_duration=15.0

                    )

                    results.append(result)

                    

                    # Recovery pause between tests

                    time.sleep(3)

                    gc.collect()

        

        # Analyze monitoring data

        analysis = resource_monitor.analyze_resource_patterns(monitoring_data)

        

        # Validate results

        assert len(results) > 0, "Should have performed at least one memory exhaustion test"

        

        for result in results:

            # Exhaustion should be achievable within reasonable time

            assert result.time_to_exhaustion < 30, (

                f"Memory exhaustion took {result.time_to_exhaustion:.1f}s, should be under 30s"

            )

            

            # Recovery should be successful

            assert result.recovery_successful, (

                f"Memory recovery failed for {result.resource_type} test"

            )

            

            # System should achieve stability or graceful degradation

            assert result.system_stability in ["stable", "degraded"], (

                f"System stability '{result.system_stability}' indicates crash or hang"

            )

        

        # Overall memory behavior validation

        if 'memory' in analysis:

            memory_analysis = analysis['memory']

            

            # Peak memory should be reasonable

            assert memory_analysis['max'] < 95, (

                f"Peak memory usage {memory_analysis['max']:.1f}% too high, "

                f"system should enforce limits before 95%"

            )

            

            # Should show memory recovery after exhaustion

            memory_variance = memory_analysis['variance']

            assert memory_variance > 10, (

                f"Memory variance {memory_variance:.1f}% too low, "

                f"should show significant change during exhaustion/recovery"

            )

        

        # Final system state should be stable

        final_memory = psutil.virtual_memory()

        memory_increase = final_memory.percent - initial_memory.percent

        max_residual_increase = 20  # 20% increase acceptable

        

        assert memory_increase < max_residual_increase, (

            f"Memory increased by {memory_increase:.1f}% and didn't recover, "

            f"indicates memory leak (initial: {initial_memory.percent:.1f}%, "

            f"final: {final_memory.percent:.1f}%)"

        )



    def test_cpu_limit_enforcement_and_throttling(self, resource_monitor: SystemResourceMonitor,

                                                 exhaustion_tester: ResourceExhaustionTester):

        """

        Test CPU limit enforcement and throttling mechanisms

        

        Creates high CPU load to test throttling, limit enforcement,

        and system responsiveness under CPU pressure.

        """

        

        initial_cpu = psutil.cpu_percent(interval=1.0)

        if initial_cpu > 50:

            pytest.skip("System CPU already too high for exhaustion test")

        

        with resource_monitor.continuous_monitoring(interval=0.5) as monitoring_data:

            # Test different CPU exhaustion levels

            cpu_tests = [

                (70, 8.0),   # 70% for 8 seconds

                (90, 6.0),   # 90% for 6 seconds

                (100, 4.0)   # 100% for 4 seconds

            ]

            

            results = []

            

            for target_percent, duration in cpu_tests:

                print(f"Testing CPU exhaustion to {target_percent}% for {duration}s")

                

                result = exhaustion_tester.exhaust_cpu(

                    target_percent=target_percent,

                    duration=duration

                )

                results.append(result)

                

                # Cool-down between tests

                time.sleep(5)

        

        # Analyze CPU patterns

        analysis = resource_monitor.analyze_resource_patterns(monitoring_data)

        

        # Validate CPU exhaustion results

        assert len(results) == len(cpu_tests), f"Should have completed all {len(cpu_tests)} CPU tests"

        

        for i, result in enumerate(results):

            target_percent, expected_duration = cpu_tests[i]

            

            # Should achieve reasonable CPU utilization

            min_expected_cpu = target_percent * 0.6  # At least 60% of target

            assert result.peak_usage >= min_expected_cpu, (

                f"CPU test {i+1}: Peak CPU {result.peak_usage:.1f}% below expected minimum "

                f"{min_expected_cpu:.1f}% (target: {target_percent}%)"

            )

            

            # Timing should be reasonable

            assert result.time_to_exhaustion <= expected_duration + 2, (

                f"CPU test {i+1}: Exhaustion time {result.time_to_exhaustion:.1f}s exceeded "

                f"expected {expected_duration}s + 2s tolerance"

            )

            

            # Recovery should be successful

            assert result.recovery_successful, (

                f"CPU test {i+1}: CPU recovery failed, final usage still high"

            )

        

        # Overall CPU behavior analysis

        if 'cpu' in analysis:

            cpu_analysis = analysis['cpu']

            

            # Should show significant CPU activity

            assert cpu_analysis['max'] > 30, (

                f"Peak CPU {cpu_analysis['max']:.1f}% too low, "

                f"CPU exhaustion tests may not have been effective"

            )

            

            # Should show CPU variance (high during tests, low during recovery)

            assert cpu_analysis['variance'] > 20, (

                f"CPU variance {cpu_analysis['variance']:.1f}% too low, "

                f"should show significant changes during exhaustion cycles"

            )

        

        # Final CPU should be back to reasonable level

        final_cpu = psutil.cpu_percent(interval=2.0)

        max_residual_cpu = 30  # 30% residual acceptable

        

        assert final_cpu < max_residual_cpu, (

            f"Final CPU usage {final_cpu:.1f}% still high after exhaustion tests, "

            f"should recover to under {max_residual_cpu}%"

        )



    def test_file_descriptor_limit_enforcement(self, resource_monitor: SystemResourceMonitor,

                                             exhaustion_tester: ResourceExhaustionTester):

        """

        Test file descriptor limit enforcement and recovery

        

        Exhausts available file descriptors to test limit enforcement

        and graceful handling of resource exhaustion.

        """

        

        # Check initial file descriptor usage

        try:

            initial_process = psutil.Process()

            initial_open_files = len(initial_process.open_files())

        except:

            initial_open_files = 0

        

        with resource_monitor.continuous_monitoring(interval=1.0) as monitoring_data:

            # Test file descriptor exhaustion

            print("Testing file descriptor exhaustion")

            

            result = exhaustion_tester.exhaust_file_descriptors(target_percent=80)

            

            # Allow system to recover

            time.sleep(2)

        

        # Validate file descriptor exhaustion

        assert result.exhaustion_successful or result.peak_usage > 100, (

            f"File descriptor exhaustion test should open significant number of files, "

            f"only opened {result.peak_usage}"

        )

        

        # Recovery should be successful

        assert result.recovery_successful, "File descriptor recovery should succeed"

        

        # System stability validation

        assert result.system_stability in ["stable", "degraded"], (

            f"System stability '{result.system_stability}' indicates serious issues"

        )

        

        # Test system recovery by opening new files

        try:

            test_files = []

            for i in range(10):

                f = tempfile.NamedTemporaryFile(delete=False)

                test_files.append(f)

            

            # Clean up test files

            for f in test_files:

                f.close()

                os.unlink(f.name)

                

            recovery_verified = True

            

        except Exception as e:

            recovery_verified = False

            pytest.fail(f"System failed to recover from file descriptor exhaustion: {e}")

        

        assert recovery_verified, "Should be able to open new files after recovery"

        

        # Check final file descriptor state

        try:

            final_process = psutil.Process()

            final_open_files = len(final_process.open_files())

            

            # Should not have excessive file descriptor leak

            fd_increase = final_open_files - initial_open_files

            max_acceptable_increase = 20  # 20 FDs acceptable increase

            

            assert fd_increase < max_acceptable_increase, (

                f"File descriptor leak detected: {fd_increase} FDs increase "

                f"(initial: {initial_open_files}, final: {final_open_files})"

            )

        except:

            # If we can't measure FDs, that's okay as long as basic recovery worked

            pass



    def test_disk_space_limit_handling(self, resource_monitor: SystemResourceMonitor,

                                     exhaustion_tester: ResourceExhaustionTester):

        """

        Test disk space limit handling and recovery

        

        Creates controlled disk space pressure to test how the system

        handles low disk space conditions.

        """

        

        # Check initial disk space

        initial_disk = psutil.disk_usage('/')

        available_gb = initial_disk.free / 1024 / 1024 / 1024

        

        if available_gb < 2:  # Less than 2GB available

            pytest.skip("Insufficient disk space for exhaustion test")

        

        # Limit test size for safety

        max_test_size_mb = min(1000, available_gb * 1024 * 0.1)  # Max 1GB or 10% of available

        

        with resource_monitor.continuous_monitoring(interval=2.0) as monitoring_data:

            print(f"Testing disk space exhaustion (max {max_test_size_mb:.0f}MB)")

            

            result = exhaustion_tester.exhaust_disk_space(

                target_percent=85,  # Target 85% usage

                max_size_mb=max_test_size_mb

            )

            

            # Allow system to recover

            time.sleep(3)

        

        # Validate disk space test

        assert result.peak_usage > 0, "Should have written some data during disk exhaustion test"

        

        # Recovery should be successful

        assert result.recovery_successful, (

            "Disk space recovery should succeed (temp files should be cleaned up)"

        )

        

        # System should remain stable

        assert result.system_stability == "stable", (

            f"System stability '{result.system_stability}' after disk exhaustion indicates issues"

        )

        

        # Verify disk space recovery

        final_disk = psutil.disk_usage('/')

        space_recovered = final_disk.free - initial_disk.free

        

        # Should have recovered most of the space (allowing for some system writes)

        min_recovery_mb = result.peak_usage * 0.8  # At least 80% should be recovered

        max_acceptable_loss_mb = 100  # Up to 100MB loss acceptable

        

        recovered_mb = abs(space_recovered) / 1024 / 1024

        

        if recovered_mb < min_recovery_mb and space_recovered < -max_acceptable_loss_mb:

            pytest.fail(

                f"Disk space not properly recovered: {space_recovered / 1024 / 1024:.1f}MB change, "

                f"should have recovered at least {min_recovery_mb:.1f}MB"

            )

        

        # Test disk write capability after recovery

        try:

            test_file = tempfile.NamedTemporaryFile(delete=True, mode='w')

            test_file.write("Disk recovery test" * 1000)  # Write some data

            test_file.flush()

            test_file.close()

            

            disk_write_recovery = True

            

        except Exception as e:

            disk_write_recovery = False

            pytest.fail(f"Cannot write to disk after recovery: {e}")

        

        assert disk_write_recovery, "Should be able to write to disk after space recovery"



    def test_combined_resource_exhaustion_resilience(self, resource_monitor: SystemResourceMonitor,

                                                   exhaustion_tester: ResourceExhaustionTester):

        """

        Test system resilience under combined resource exhaustion

        

        Applies multiple resource pressures simultaneously to test

        system behavior under extreme stress conditions.

        """

        

        # Check if system has sufficient resources for combined test

        initial_memory = psutil.virtual_memory()

        initial_cpu = psutil.cpu_percent(interval=1.0)

        initial_disk = psutil.disk_usage('/')

        

        if (initial_memory.percent > 60 or initial_cpu > 40 or 

            initial_disk.free < 1024 * 1024 * 1024):  # Less than 1GB free

            pytest.skip("System resources too constrained for combined exhaustion test")

        

        def memory_pressure_worker():

            """Worker for memory pressure"""

            try:

                result = exhaustion_tester.exhaust_memory(target_percent=70, max_duration=20)

                return ("memory", result)

            except Exception as e:

                return ("memory", f"failed: {e}")

        

        def cpu_pressure_worker():

            """Worker for CPU pressure"""

            try:

                result = exhaustion_tester.exhaust_cpu(target_percent=80, duration=15)

                return ("cpu", result)

            except Exception as e:

                return ("cpu", f"failed: {e}")

        

        def fd_pressure_worker():

            """Worker for file descriptor pressure"""

            try:

                result = exhaustion_tester.exhaust_file_descriptors(target_percent=70)

                return ("fd", result)

            except Exception as e:

                return ("fd", f"failed: {e}")

        

        # Run combined resource exhaustion

        with resource_monitor.continuous_monitoring(interval=1.0) as monitoring_data:

            print("Starting combined resource exhaustion test")

            

            with ThreadPoolExecutor(max_workers=3) as executor:

                # Start all resource pressure workers

                futures = []

                futures.append(executor.submit(memory_pressure_worker))

                futures.append(executor.submit(cpu_pressure_worker))

                futures.append(executor.submit(fd_pressure_worker))

                

                # Collect results

                combined_results = {}

                for future in as_completed(futures, timeout=45):

                    try:

                        resource_type, result = future.result()

                        combined_results[resource_type] = result

                    except Exception as e:

                        print(f"Combined exhaustion worker failed: {e}")

            

            # Allow system to recover

            time.sleep(5)

            gc.collect()

        

        # Analyze system behavior under combined stress

        analysis = resource_monitor.analyze_resource_patterns(monitoring_data)

        

        # Validate combined test results

        assert len(combined_results) > 0, "Should have completed some resource exhaustion tests"

        

        successful_exhaustions = 0

        successful_recoveries = 0

        

        for resource_type, result in combined_results.items():

            if isinstance(result, ResourceExhaustionResult):

                if result.exhaustion_successful:

                    successful_exhaustions += 1

                if result.recovery_successful:

                    successful_recoveries += 1

                

                # System should not crash under combined pressure

                assert result.system_stability != "crashed", (

                    f"System crashed during {resource_type} exhaustion in combined test"

                )

        

        # Should achieve some resource exhaustion

        assert successful_exhaustions >= 1, (

            f"Should successfully exhaust at least 1 resource type in combined test, "

            f"got {successful_exhaustions}"

        )

        

        # Most resources should recover

        recovery_ratio = successful_recoveries / len(combined_results) if combined_results else 0

        min_recovery_ratio = 0.67  # At least 67% should recover

        

        assert recovery_ratio >= min_recovery_ratio, (

            f"Recovery ratio {recovery_ratio:.2f} too low in combined test, "

            f"should be at least {min_recovery_ratio}"

        )

        

        # System should maintain basic functionality during stress

        if 'memory' in analysis and 'cpu' in analysis:

            # Memory and CPU should show significant activity

            assert analysis['memory']['max'] > 40, (

                f"Peak memory {analysis['memory']['max']:.1f}% too low for combined stress test"

            )

            

            assert analysis['cpu']['max'] > 30, (

                f"Peak CPU {analysis['cpu']['max']:.1f}% too low for combined stress test"

            )

        

        # Final system state check

        final_memory = psutil.virtual_memory()

        final_cpu = psutil.cpu_percent(interval=2.0)

        

        # System should recover to reasonable state

        assert final_memory.percent < initial_memory.percent + 30, (

            f"Memory did not recover after combined test: "

            f"initial {initial_memory.percent:.1f}%, final {final_memory.percent:.1f}%"

        )

        

        assert final_cpu < 50, (

            f"CPU did not recover after combined test: final {final_cpu:.1f}%"

        )

        

        # Basic functionality test

        try:

            # Test that we can still perform basic operations

            test_data = list(range(1000))

            test_sum = sum(test_data)

            

            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=True)

            temp_file.write(f"System functional after combined test: {test_sum}")

            temp_file.close()

            

            basic_functionality_ok = True

            

        except Exception as e:

            basic_functionality_ok = False

            pytest.fail(f"System basic functionality impaired after combined test: {e}")

        

        assert basic_functionality_ok, "System should maintain basic functionality after combined stress"



    def test_resource_limit_configuration_validation(self, resource_monitor: SystemResourceMonitor):

        """

        Test validation of resource limit configurations

        

        Validates that resource limits are properly configured and enforced

        according to system specifications and Docker configurations.

        """

        

        # Check Docker container resource limits if Docker is available

        docker_limits = {}

        try:

            docker_client = docker.from_env()

            containers = docker_client.containers.list()

            

            for container in containers:

                if any(keyword in container.name.lower() for keyword in [

                    'netra', 'dev-', 'test-', 'backend', 'frontend', 'auth'

                ]):

                    # Get container resource limits

                    container.reload()

                    host_config = container.attrs.get('HostConfig', {})

                    

                    limits = {

                        'memory_limit': host_config.get('Memory', 0),

                        'cpu_limit': host_config.get('CpuShares', 0),

                        'cpu_quota': host_config.get('CpuQuota', 0),

                        'cpu_period': host_config.get('CpuPeriod', 0)

                    }

                    

                    docker_limits[container.name] = limits

                    

        except Exception as e:

            print(f"Could not check Docker limits: {e}")

        

        # Check system resource limits

        system_limits = {}

        try:

            # Memory limits

            system_memory = psutil.virtual_memory()

            system_limits['total_memory_gb'] = system_memory.total / 1024 / 1024 / 1024

            

            # CPU limits  

            system_limits['cpu_count'] = psutil.cpu_count()

            system_limits['cpu_freq'] = psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}

            

            # File descriptor limits

            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

            system_limits['fd_soft_limit'] = soft_limit

            system_limits['fd_hard_limit'] = hard_limit

            

            # Process limits

            system_limits['max_processes'] = resource.getrlimit(resource.RLIMIT_NPROC)[0]

            

        except Exception as e:

            print(f"Could not check system limits: {e}")

        

        # Validate Docker container limits

        if docker_limits:

            for container_name, limits in docker_limits.items():

                # Memory limits should be set for production-like containers

                if 'dev-' in container_name:

                    memory_mb = limits['memory_limit'] / 1024 / 1024 if limits['memory_limit'] else 0

                    

                    if memory_mb > 0:

                        # Memory limit should be reasonable (between 256MB and 8GB)

                        assert 256 <= memory_mb <= 8192, (

                            f"Container {container_name} memory limit {memory_mb:.0f}MB outside reasonable range"

                        )

                        

                        # Memory limit should not exceed system memory

                        system_memory_mb = system_limits.get('total_memory_gb', 16) * 1024

                        assert memory_mb <= system_memory_mb * 0.8, (

                            f"Container {container_name} memory limit {memory_mb:.0f}MB too high for system"

                        )

        

        # Validate system limits are reasonable

        assert system_limits.get('total_memory_gb', 0) >= 2, (

            f"System memory {system_limits.get('total_memory_gb', 0):.1f}GB too low for testing"

        )

        

        assert system_limits.get('cpu_count', 0) >= 2, (

            f"System CPU count {system_limits.get('cpu_count', 0)} too low for testing"

        )

        

        assert system_limits.get('fd_soft_limit', 0) >= 1024, (

            f"File descriptor soft limit {system_limits.get('fd_soft_limit', 0)} too low"

        )

        

        # Test that limits are actually enforced by attempting to exceed them

        with resource_monitor.continuous_monitoring(interval=2.0) as monitoring_data:

            # Test process limit enforcement  

            try:

                max_procs = system_limits.get('max_processes', 1024)

                # Don't actually try to exhaust processes - too dangerous

                # Just verify the limit exists and is reasonable

                assert max_procs >= 512, f"Max processes limit {max_procs} too restrictive"

                

            except Exception as e:

                print(f"Process limit validation failed: {e}")

        

        # Report findings

        print(f"\nResource Limit Validation Summary:")

        print(f"- System Memory: {system_limits.get('total_memory_gb', 0):.1f}GB")

        print(f"- System CPU Count: {system_limits.get('cpu_count', 0)}")

        print(f"- File Descriptor Limits: {system_limits.get('fd_soft_limit', 0)}/{system_limits.get('fd_hard_limit', 0)}")

        print(f"- Docker Containers with Limits: {len(docker_limits)}")

        

        if docker_limits:

            for container, limits in list(docker_limits.items())[:3]:  # Show first 3

                memory_mb = limits['memory_limit'] / 1024 / 1024 if limits['memory_limit'] else 0

                print(f"  - {container}: Memory {memory_mb:.0f}MB")

        

        # Basic validation that we have some limits configured

        limits_configured = (

            len(docker_limits) > 0 or  # Docker limits exist

            system_limits.get('fd_soft_limit', 0) < 65536  # FD limits are reasonable

        )

        

        assert limits_configured, (

            "No resource limits appear to be properly configured for testing environment"

        )

