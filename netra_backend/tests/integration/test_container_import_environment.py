"""
Container environment tests for ServiceError import issues.

This test suite focuses on reproducing the specific Docker container startup
conditions that lead to ImportError issues, including cold start scenarios,
multi-worker environments, and container resource constraints.

Business Value:
- Ensures production container deployments are stable
- Prevents service outages due to import timing issues
- Validates container startup reliability under various conditions
"""

import pytest
import subprocess
import time
import os
import tempfile
import json
from typing import Dict, List, Any, Optional
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil

from test_framework.base_integration_test import BaseIntegrationTest


class TestContainerImportEnvironment(BaseIntegrationTest):
    """Tests for ServiceError imports under various container conditions."""
    
    @classmethod
    def setUpClass(cls):
        """Set up container testing environment."""
        super().setUpClass()
        
        cls.container_results = {
            'cold_start_tests': [],
            'resource_constraint_tests': [],
            'multi_worker_tests': [],
            'timing_analysis': []
        }
        
        cls.docker_available = cls._check_docker_availability()
        
    def setUp(self):
        """Set up individual test."""
        super().setUp()
        
        if not self.docker_available:
            self.skipTest("Docker not available - skipping container environment tests")
    
    @classmethod
    def _check_docker_availability(cls) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(['docker', 'info'], 
                                  capture_output=True, check=True, timeout=10)
            return result.returncode == 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _create_container_test_script(self, test_name: str, test_code: str) -> str:
        """Create a containerized test script."""
        full_script = f"""
#!/usr/bin/env python3

import sys
import time
import json
import traceback
import threading
import os
from typing import Dict, Any

def log_message(level: str, message: str):
    '''Unified logging for container tests.'''
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{{timestamp}}] {{level}}: {{message}}", flush=True)

def create_test_result(test_name: str, success: bool = False, **kwargs) -> Dict[str, Any]:
    '''Create standardized test result.'''
    return {{
        'test_name': test_name,
        'success': success,
        'timestamp': time.time(),
        'container_id': os.environ.get('HOSTNAME', 'unknown'),
        'python_version': sys.version,
        **kwargs
    }}

# Test implementation
{test_code}

if __name__ == "__main__":
    log_message("INFO", f"Starting container test: {test_name}")
    
    try:
        result = run_test()
        log_message("INFO", f"Test completed: {result.get('success', False)}")
        print(f"CONTAINER_TEST_RESULT_{test_name.upper()}:", json.dumps(result))
        sys.exit(0 if result.get('success', False) else 1)
    except Exception as e:
        error_result = create_test_result("{test_name}", False, 
                                        error=str(e), 
                                        traceback=traceback.format_exc())
        log_message("ERROR", f"Test failed with exception: {{e}}")
        print(f"CONTAINER_TEST_RESULT_{test_name.upper()}:", json.dumps(error_result))
        sys.exit(1)
"""
        return full_script
    
    def test_cold_start_import_timing(self):
        """Test ServiceError import during cold container startup.
        
        This reproduces the exact timing conditions where ImportError occurs:
        - Fresh container with no warm Python interpreter
        - No pre-cached imports
        - Cold file system access
        """
        
        test_code = """
def run_test():
    '''Test cold start import timing.'''
    log_message("INFO", "Starting cold start import test")
    
    # Clear any existing imports to simulate cold start
    modules_to_clear = [k for k in sys.modules.keys() if 'netra_backend' in k]
    for module in modules_to_clear:
        del sys.modules[module]
    
    cold_start_results = {
        'import_attempts': [],
        'successful_imports': 0,
        'failed_imports': 0,
        'average_import_time': 0,
        'max_import_time': 0,
        'min_import_time': float('inf')
    }
    
    # Perform multiple cold imports to detect timing issues
    for attempt in range(10):
        log_message("DEBUG", f"Cold start attempt {attempt + 1}/10")
        
        start_time = time.time()
        attempt_result = {
            'attempt': attempt,
            'success': False,
            'duration': 0,
            'error': None
        }
        
        try:
            # Force fresh import
            if 'netra_backend.app.core.exceptions_service' in sys.modules:
                del sys.modules['netra_backend.app.core.exceptions_service']
            
            from netra_backend.app.core.exceptions_service import ServiceError
            
            # Verify import worked
            test_error = ServiceError("Cold start test")
            
            attempt_result['success'] = True
            cold_start_results['successful_imports'] += 1
            
        except ImportError as e:
            attempt_result['error'] = {
                'type': 'ImportError',
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            cold_start_results['failed_imports'] += 1
            log_message("ERROR", f"Cold start import failed: {e}")
            
        except Exception as e:
            attempt_result['error'] = {
                'type': type(e).__name__,
                'message': str(e)
            }
            cold_start_results['failed_imports'] += 1
        
        attempt_result['duration'] = time.time() - start_time
        cold_start_results['import_attempts'].append(attempt_result)
        
        # Update timing statistics
        duration = attempt_result['duration']
        cold_start_results['max_import_time'] = max(cold_start_results['max_import_time'], duration)
        cold_start_results['min_import_time'] = min(cold_start_results['min_import_time'], duration)
    
    # Calculate average timing
    total_time = sum(attempt['duration'] for attempt in cold_start_results['import_attempts'])
    cold_start_results['average_import_time'] = total_time / len(cold_start_results['import_attempts'])
    
    # Determine overall success
    success = cold_start_results['failed_imports'] == 0
    
    log_message("INFO", f"Cold start test completed: {cold_start_results['successful_imports']}/10 successful")
    
    return create_test_result("cold_start_import_timing", success, **cold_start_results)
"""
        
        self._run_containerized_test("cold_start_import_timing", test_code)
    
    def test_resource_constrained_import(self):
        """Test ServiceError import under memory and CPU constraints.
        
        This simulates container resource constraints that may affect import timing.
        """
        
        test_code = """
def run_test():
    '''Test import under resource constraints.'''
    log_message("INFO", "Starting resource constrained import test")
    
    import psutil
    import gc
    
    # Get initial system state
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    constraint_results = {
        'initial_memory_mb': initial_memory / 1024 / 1024,
        'memory_tests': [],
        'cpu_stress_tests': [],
        'concurrent_import_tests': []
    }
    
    # Test 1: Memory pressure simulation
    log_message("INFO", "Testing import under memory pressure")
    
    # Create memory pressure
    memory_hogs = []
    try:
        # Allocate memory to create pressure (50MB chunks)
        for i in range(10):
            memory_hogs.append(bytearray(50 * 1024 * 1024))  # 50MB each
        
        start_time = time.time()
        
        from netra_backend.app.core.exceptions_service import ServiceError
        test_error = ServiceError("Memory pressure test")
        
        memory_test_result = {
            'success': True,
            'duration': time.time() - start_time,
            'memory_used_mb': process.memory_info().rss / 1024 / 1024
        }
        
    except Exception as e:
        memory_test_result = {
            'success': False,
            'error': str(e),
            'duration': time.time() - start_time,
            'memory_used_mb': process.memory_info().rss / 1024 / 1024
        }
    
    finally:
        # Clean up memory
        memory_hogs.clear()
        gc.collect()
    
    constraint_results['memory_tests'].append(memory_test_result)
    
    # Test 2: CPU stress during import
    log_message("INFO", "Testing import under CPU stress")
    
    def cpu_stress():
        '''CPU intensive task to create load.'''
        for _ in range(1000000):
            _ = sum(range(1000))
    
    # Start CPU stress in background
    stress_threads = []
    for _ in range(4):  # 4 CPU stress threads
        thread = threading.Thread(target=cpu_stress)
        thread.daemon = True
        thread.start()
        stress_threads.append(thread)
    
    try:
        start_time = time.time()
        
        # Clear import cache to force fresh import
        if 'netra_backend.app.core.exceptions_service' in sys.modules:
            del sys.modules['netra_backend.app.core.exceptions_service']
        
        from netra_backend.app.core.exceptions_service import ServiceError
        test_error = ServiceError("CPU stress test")
        
        cpu_test_result = {
            'success': True,
            'duration': time.time() - start_time
        }
        
    except Exception as e:
        cpu_test_result = {
            'success': False,
            'error': str(e),
            'duration': time.time() - start_time
        }
    
    constraint_results['cpu_stress_tests'].append(cpu_test_result)
    
    # Test 3: Concurrent imports under resource pressure
    log_message("INFO", "Testing concurrent imports under pressure")
    
    def concurrent_import_worker(worker_id):
        '''Worker for concurrent import testing.'''
        try:
            from netra_backend.app.core.exceptions_service import ServiceError
            return {'worker_id': worker_id, 'success': True}
        except Exception as e:
            return {'worker_id': worker_id, 'success': False, 'error': str(e)}
    
    # Run concurrent imports
    concurrent_results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(concurrent_import_worker, i) for i in range(20)]
        for future in futures:
            try:
                result = future.result(timeout=5)
                concurrent_results.append(result)
            except Exception as e:
                concurrent_results.append({'success': False, 'error': str(e)})
    
    successful_concurrent = sum(1 for r in concurrent_results if r.get('success'))
    constraint_results['concurrent_import_tests'] = {
        'total_workers': len(concurrent_results),
        'successful': successful_concurrent,
        'failed': len(concurrent_results) - successful_concurrent,
        'results': concurrent_results
    }
    
    # Overall success if all tests passed
    overall_success = (
        all(test['success'] for test in constraint_results['memory_tests']) and
        all(test['success'] for test in constraint_results['cpu_stress_tests']) and
        constraint_results['concurrent_import_tests']['failed'] == 0
    )
    
    log_message("INFO", f"Resource constraint test completed: {overall_success}")
    
    return create_test_result("resource_constrained_import", overall_success, **constraint_results)
"""
        
        self._run_containerized_test("resource_constrained_import", test_code)
    
    def test_multi_worker_startup_simulation(self):
        """Test ServiceError import in multi-worker container startup scenario.
        
        This simulates the conditions in production containers with multiple
        worker processes starting simultaneously (e.g., gunicorn workers).
        """
        
        test_code = """
import multiprocessing
from multiprocessing import Process, Queue
import time

def run_test():
    '''Test multi-worker startup simulation.'''
    log_message("INFO", "Starting multi-worker startup simulation")
    
    def worker_startup_simulation(worker_id, result_queue, startup_delay=0):
        '''Simulate a worker process startup with ServiceError import.'''
        time.sleep(startup_delay)  # Simulate staggered startup
        
        worker_result = {
            'worker_id': worker_id,
            'success': False,
            'startup_delay': startup_delay,
            'import_duration': 0,
            'error': None,
            'attempt_results': []
        }
        
        # Simulate multiple import attempts during worker startup
        for attempt in range(5):
            start_time = time.time()
            
            try:
                from netra_backend.app.core.exceptions_service import ServiceError
                
                # Test instantiation
                test_error = ServiceError(f"Worker {worker_id} attempt {attempt}")
                
                attempt_result = {
                    'attempt': attempt,
                    'success': True,
                    'duration': time.time() - start_time
                }
                
                worker_result['success'] = True  # At least one success
                worker_result['import_duration'] = time.time() - start_time
                
            except Exception as e:
                attempt_result = {
                    'attempt': attempt,
                    'success': False,
                    'duration': time.time() - start_time,
                    'error': {
                        'type': type(e).__name__,
                        'message': str(e)
                    }
                }
                
                if worker_result['error'] is None:
                    worker_result['error'] = attempt_result['error']
            
            worker_result['attempt_results'].append(attempt_result)
            
            # Short delay between attempts
            time.sleep(0.1)
        
        result_queue.put(worker_result)
    
    # Simulate startup of multiple workers with different timing
    num_workers = 8
    startup_delays = [i * 0.1 for i in range(num_workers)]  # Stagger startups
    
    result_queue = Queue()
    processes = []
    
    # Start all worker processes
    for worker_id in range(num_workers):
        delay = startup_delays[worker_id]
        p = Process(target=worker_startup_simulation, 
                   args=(worker_id, result_queue, delay))
        p.start()
        processes.append(p)
    
    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=30)  # 30 second timeout per worker
    
    # Collect results
    worker_results = []
    while not result_queue.empty():
        try:
            worker_result = result_queue.get_nowait()
            worker_results.append(worker_result)
        except:
            break
    
    # Analyze multi-worker results
    successful_workers = sum(1 for r in worker_results if r['success'])
    failed_workers = len(worker_results) - successful_workers
    
    multi_worker_results = {
        'total_workers': num_workers,
        'successful_workers': successful_workers,
        'failed_workers': failed_workers,
        'worker_details': worker_results,
        'startup_delays_used': startup_delays,
        'average_import_duration': 0
    }
    
    # Calculate average import duration for successful workers
    successful_durations = [r['import_duration'] for r in worker_results if r['success']]
    if successful_durations:
        multi_worker_results['average_import_duration'] = sum(successful_durations) / len(successful_durations)
    
    # Overall success if all workers succeeded
    overall_success = failed_workers == 0
    
    log_message("INFO", f"Multi-worker test: {successful_workers}/{num_workers} workers successful")
    
    return create_test_result("multi_worker_startup_simulation", overall_success, **multi_worker_results)
"""
        
        self._run_containerized_test("multi_worker_startup_simulation", test_code)
    
    def test_filesystem_timing_sensitivity(self):
        """Test import sensitivity to filesystem timing in containers."""
        
        test_code = """
def run_test():
    '''Test filesystem timing sensitivity.'''
    log_message("INFO", "Starting filesystem timing sensitivity test")
    
    import os
    import stat
    
    filesystem_results = {
        'file_access_tests': [],
        'import_timing_analysis': [],
        'filesystem_stats': {}
    }
    
    # Get filesystem statistics
    try:
        netra_path = None
        for path in sys.path:
            potential_path = os.path.join(path, 'netra_backend')
            if os.path.exists(potential_path):
                netra_path = potential_path
                break
        
        if netra_path:
            stat_info = os.stat(netra_path)
            filesystem_results['filesystem_stats'] = {
                'netra_path': netra_path,
                'access_time': stat_info.st_atime,
                'modify_time': stat_info.st_mtime,
                'change_time': stat_info.st_ctime,
                'mode': stat.filemode(stat_info.st_mode)
            }
    except Exception as e:
        filesystem_results['filesystem_stats']['error'] = str(e)
    
    # Test 1: File access timing before import
    test_files = [
        'netra_backend/app/core/exceptions_service.py',
        'netra_backend/app/core/exceptions_agent.py',
        'netra_backend/app/core/exceptions/__init__.py'
    ]
    
    for test_file in test_files:
        file_test = {'file': test_file, 'access_results': []}
        
        for attempt in range(5):
            start_time = time.time()
            
            try:
                # Try to find and access the file
                found_file = None
                for path in sys.path:
                    full_path = os.path.join(path, test_file)
                    if os.path.exists(full_path):
                        found_file = full_path
                        break
                
                if found_file:
                    with open(found_file, 'r') as f:
                        _ = f.read(100)  # Read first 100 chars
                    
                    access_result = {
                        'attempt': attempt,
                        'success': True,
                        'duration': time.time() - start_time,
                        'file_path': found_file
                    }
                else:
                    access_result = {
                        'attempt': attempt,
                        'success': False,
                        'duration': time.time() - start_time,
                        'error': 'File not found'
                    }
                
            except Exception as e:
                access_result = {
                    'attempt': attempt,
                    'success': False,
                    'duration': time.time() - start_time,
                    'error': str(e)
                }
            
            file_test['access_results'].append(access_result)
            time.sleep(0.05)  # Small delay between accesses
        
        filesystem_results['file_access_tests'].append(file_test)
    
    # Test 2: Import timing correlation with file access
    for timing_attempt in range(10):
        timing_test = {
            'attempt': timing_attempt,
            'file_access_duration': 0,
            'import_duration': 0,
            'total_duration': 0,
            'success': False
        }
        
        overall_start = time.time()
        
        # First, access the file directly
        file_start = time.time()
        try:
            import_file = None
            for path in sys.path:
                test_path = os.path.join(path, 'netra_backend/app/core/exceptions_service.py')
                if os.path.exists(test_path):
                    with open(test_path, 'r') as f:
                        _ = f.read(1)  # Minimal read
                    import_file = test_path
                    break
            
            timing_test['file_access_duration'] = time.time() - file_start
            
            # Now import
            import_start = time.time()
            
            # Clear module to force fresh import
            if 'netra_backend.app.core.exceptions_service' in sys.modules:
                del sys.modules['netra_backend.app.core.exceptions_service']
            
            from netra_backend.app.core.exceptions_service import ServiceError
            test_error = ServiceError(f"Filesystem timing test {timing_attempt}")
            
            timing_test['import_duration'] = time.time() - import_start
            timing_test['success'] = True
            
        except Exception as e:
            timing_test['error'] = str(e)
        
        timing_test['total_duration'] = time.time() - overall_start
        filesystem_results['import_timing_analysis'].append(timing_test)
    
    # Analyze timing correlation
    successful_timings = [t for t in filesystem_results['import_timing_analysis'] if t['success']]
    
    overall_success = len(successful_timings) == len(filesystem_results['import_timing_analysis'])
    
    if successful_timings:
        avg_file_access = sum(t['file_access_duration'] for t in successful_timings) / len(successful_timings)
        avg_import = sum(t['import_duration'] for t in successful_timings) / len(successful_timings)
        
        filesystem_results['timing_analysis_summary'] = {
            'average_file_access_duration': avg_file_access,
            'average_import_duration': avg_import,
            'successful_attempts': len(successful_timings),
            'total_attempts': len(filesystem_results['import_timing_analysis'])
        }
    
    log_message("INFO", f"Filesystem timing test: {len(successful_timings)}/10 successful")
    
    return create_test_result("filesystem_timing_sensitivity", overall_success, **filesystem_results)
"""
        
        self._run_containerized_test("filesystem_timing_sensitivity", test_code)
    
    def _run_containerized_test(self, test_name: str, test_code: str):
        """Execute a test in a Docker container and collect results."""
        
        # Create test script
        script_content = self._create_container_test_script(test_name, test_code)
        
        # Create temporary Docker context
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Write test script
            script_path = os.path.join(temp_dir, 'container_test.py')
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Create Dockerfile
            dockerfile_content = f"""
FROM python:3.11-slim

# Install system dependencies  
RUN apt-get update && apt-get install -y \\
    gcc \\
    procps \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-test.txt /app/requirements-test.txt
WORKDIR /app
RUN pip install -r requirements-test.txt

# Copy application code
COPY . /app/

# Set environment
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Copy and run test script
COPY container_test.py /app/container_test.py
RUN chmod +x /app/container_test.py

CMD ["python", "/app/container_test.py"]
"""
            
            dockerfile_path = os.path.join(temp_dir, 'Dockerfile')
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            # Build container
            build_result = subprocess.run([
                'docker', 'build', '-t', f'netra-container-test-{test_name}', temp_dir
            ], capture_output=True, text=True, timeout=120)
            
            if build_result.returncode != 0:
                self.logger.error(f"Docker build failed for {test_name}: {build_result.stderr}")
                self.fail(f"Container build failed: {build_result.stderr}")
            
            # Run container test
            run_result = subprocess.run([
                'docker', 'run', '--rm',
                '--name', f'netra-test-{test_name}-{int(time.time())}',
                # Resource constraints to simulate production
                '--memory=512m',
                '--cpus=2',
                f'netra-container-test-{test_name}'
            ], capture_output=True, text=True, timeout=120)
            
            # Parse and analyze results
            self._analyze_container_test_results(test_name, run_result)
            
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Remove test image
            try:
                subprocess.run(['docker', 'rmi', f'netra-container-test-{test_name}'], 
                             capture_output=True, check=False)
            except:
                pass
    
    def _analyze_container_test_results(self, test_name: str, run_result: subprocess.CompletedProcess):
        """Analyze and store container test results."""
        
        self.logger.info(f"Container test {test_name} - Exit code: {run_result.returncode}")
        
        if run_result.stdout:
            self.logger.info(f"Container stdout: {run_result.stdout}")
        
        if run_result.stderr:
            self.logger.error(f"Container stderr: {run_result.stderr}")
        
        # Extract test results from output
        result_marker = f"CONTAINER_TEST_RESULT_{test_name.upper()}:"
        test_results = None
        
        for line in run_result.stdout.split('\n'):
            if result_marker in line:
                try:
                    results_json = line.split(result_marker)[1].strip()
                    test_results = json.loads(results_json)
                    break
                except (json.JSONDecodeError, IndexError) as e:
                    self.logger.error(f"Failed to parse test results: {e}")
        
        if test_results is None:
            self.logger.error(f"No test results found for {test_name}")
            self.fail(f"No test results found in container output for {test_name}")
        
        # Store results based on test type
        result_category = None
        if 'cold_start' in test_name:
            result_category = 'cold_start_tests'
        elif 'resource' in test_name:
            result_category = 'resource_constraint_tests'
        elif 'multi_worker' in test_name:
            result_category = 'multi_worker_tests'
        elif 'filesystem' in test_name:
            result_category = 'timing_analysis'
        
        if result_category:
            self.container_results[result_category].append({
                'test_name': test_name,
                'container_exit_code': run_result.returncode,
                'test_results': test_results,
                'stdout': run_result.stdout,
                'stderr': run_result.stderr
            })
        
        # Fail the test if the container test failed
        if not test_results.get('success', False):
            error_details = test_results.get('error', 'Unknown error')
            self.logger.error(f"Container test {test_name} failed: {error_details}")
            
            # This should FAIL if we successfully reproduce the ImportError
            self.fail(f"Container environment test '{test_name}' reproduced ImportError: {error_details}")
        
        # Log success details
        self.logger.info(f"Container test {test_name} completed successfully")
        for key, value in test_results.items():
            if key not in ['test_name', 'success', 'timestamp']:
                self.logger.debug(f"  {key}: {value}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up and provide comprehensive test summary."""
        
        cls.logger.info("Container import environment test summary:")
        
        total_tests = sum(len(tests) for tests in cls.container_results.values())
        cls.logger.info(f"Total container tests executed: {total_tests}")
        
        for category, tests in cls.container_results.items():
            if tests:
                cls.logger.info(f"\n{category.replace('_', ' ').title()}:")
                for test in tests:
                    success = test['test_results'].get('success', False)
                    status = "✓ PASSED" if success else "✗ FAILED"
                    cls.logger.info(f"  {test['test_name']}: {status}")
        
        super().tearDownClass()