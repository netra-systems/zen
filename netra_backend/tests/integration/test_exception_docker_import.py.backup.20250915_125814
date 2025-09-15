"""
Integration tests for ServiceError import reliability in Docker container environments.

This test suite reproduces the ImportError issue that occurs specifically during
Docker container startup, testing real container conditions and timing scenarios.

Business Value:
- Ensures stable exception handling during production deployments
- Prevents service degradation due to import failures
- Validates Docker container startup reliability
"""

import pytest
import subprocess
import time
import tempfile
import os
from typing import Dict, List, Any
import json

from test_framework.base_integration_test import BaseIntegrationTest


class TestExceptionDockerImport(BaseIntegrationTest):
    """Integration tests for ServiceError imports in Docker containers."""
    
    @classmethod
    def setUpClass(cls):
        """Set up Docker environment for testing."""
        super().setUpClass()
        
        # Store test results for analysis
        cls.test_results = {
            'container_tests': [],
            'import_scenarios': [],
            'timing_data': []
        }
        
        # Docker test configuration
        cls.docker_config = {
            'image_name': 'netra-backend-test',
            'container_name': 'netra-exception-test',
            'test_timeout': 30
        }
    
    def setUp(self):
        """Set up individual test environment."""
        super().setUp()
        
        # Ensure clean Docker state
        self._cleanup_test_containers()
    
    def tearDown(self):
        """Clean up test containers."""
        self._cleanup_test_containers()
        super().tearDown()
    
    def _cleanup_test_containers(self):
        """Remove any existing test containers."""
        try:
            subprocess.run([
                'docker', 'rm', '-f', self.docker_config['container_name']
            ], capture_output=True, check=False)
        except Exception as e:
            self.logger.debug(f"Container cleanup error (expected): {e}")
    
    def _create_test_dockerfile(self, test_script_content: str) -> str:
        """Create a temporary Dockerfile for testing imports."""
        dockerfile_content = f"""
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-test.txt /app/requirements-test.txt
WORKDIR /app
RUN pip install -r requirements-test.txt

# Copy application code
COPY . /app/

# Set Python path
ENV PYTHONPATH="/app"

# Create test script
RUN echo '{test_script_content}' > /app/test_import_script.py

# Run the test script
CMD ["python", "/app/test_import_script.py"]
"""
        
        temp_dir = tempfile.mkdtemp()
        dockerfile_path = os.path.join(temp_dir, 'Dockerfile')
        
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        return temp_dir
    
    def test_fresh_container_service_error_import(self):
        """Test ServiceError import in a fresh Docker container.
        
        This simulates the exact conditions where ImportError occurs:
        - Fresh container startup
        - Cold Python interpreter
        - No pre-loaded modules
        """
        test_script = """
import sys
import time
import traceback
import json

def test_service_error_import():
    results = {
        'test_name': 'fresh_container_service_error_import',
        'success': False,
        'error_details': None,
        'import_duration': 0,
        'python_path': sys.path,
        'loaded_modules': list(sys.modules.keys()),
        'timestamp': time.time()
    }
    
    start_time = time.time()
    
    try:
        # This is the exact import that fails in Docker containers
        from netra_backend.app.core.exceptions_service import ServiceError
        
        # Verify the import worked
        if ServiceError is None:
            raise ImportError("ServiceError imported as None")
        
        # Try to instantiate
        test_error = ServiceError("Container test error")
        
        results['success'] = True
        results['import_duration'] = time.time() - start_time
        results['service_error_class'] = str(ServiceError)
        results['test_instance'] = str(test_error)
        
    except Exception as e:
        results['success'] = False
        results['error_details'] = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        results['import_duration'] = time.time() - start_time
    
    print("CONTAINER_TEST_RESULTS:", json.dumps(results))
    return results

if __name__ == "__main__":
    results = test_service_error_import()
    # Exit with non-zero if failed to ensure container failure detection
    sys.exit(0 if results['success'] else 1)
"""
        
        # Skip if Docker not available
        if not self._is_docker_available():
            self.skipTest("Docker not available for container testing")
        
        # Create temporary Docker context
        temp_dir = self._create_test_dockerfile(test_script.replace("'", "\\'"))
        
        try:
            # Build test image
            build_result = subprocess.run([
                'docker', 'build', '-t', self.docker_config['image_name'], temp_dir
            ], capture_output=True, text=True, timeout=120)
            
            if build_result.returncode != 0:
                self.skipTest(f"Docker build failed: {build_result.stderr}")
            
            # Run test container
            run_result = subprocess.run([
                'docker', 'run', '--rm',
                '--name', self.docker_config['container_name'],
                self.docker_config['image_name']
            ], capture_output=True, text=True, timeout=self.docker_config['test_timeout'])
            
            # Parse results from container output
            container_output = run_result.stdout
            container_error = run_result.stderr
            
            self.logger.info(f"Container exit code: {run_result.returncode}")
            self.logger.info(f"Container output: {container_output}")
            if container_error:
                self.logger.error(f"Container stderr: {container_error}")
            
            # Extract test results
            results = None
            for line in container_output.split('\\n'):
                if line.startswith('CONTAINER_TEST_RESULTS:'):
                    try:
                        results_json = line.replace('CONTAINER_TEST_RESULTS:', '').strip()
                        results = json.loads(results_json)
                        break
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse container results: {e}")
            
            # Store results for analysis
            self.test_results['container_tests'].append({
                'test_name': 'fresh_container_service_error_import',
                'container_exit_code': run_result.returncode,
                'container_output': container_output,
                'container_error': container_error,
                'parsed_results': results
            })
            
            # Analyze results
            if results is None:
                self.fail("No test results found in container output")
            
            if not results['success']:
                error_details = results['error_details']
                
                # Log detailed failure information
                self.logger.error(f"Container import test failed:")
                self.logger.error(f"  Error type: {error_details['error_type']}")
                self.logger.error(f"  Error message: {error_details['error_message']}")
                self.logger.error(f"  Import duration: {results['import_duration']:.4f}s")
                self.logger.error(f"  Traceback: {error_details['traceback']}")
                
                # This should FAIL if the ImportError is reproduced
                self.fail(f"ServiceError ImportError reproduced in fresh container: {error_details['error_message']}")
            
            # Test passed - log success details
            self.logger.info(f"Container import test succeeded:")
            self.logger.info(f"  Import duration: {results['import_duration']:.4f}s")
            self.logger.info(f"  ServiceError class: {results.get('service_error_class')}")
            
        finally:
            # Cleanup temporary directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_container_startup_race_condition(self):
        """Test for race conditions during container startup with multiple processes."""
        
        # Skip if Docker not available
        if not self._is_docker_available():
            self.skipTest("Docker not available for race condition testing")
        
        test_script = """
import sys
import time
import traceback
import json
import multiprocessing
import concurrent.futures
from multiprocessing import Process, Queue

def import_worker(worker_id, result_queue):
    '''Worker process to test concurrent imports.'''
    worker_result = {
        'worker_id': worker_id,
        'success': False,
        'error_details': None,
        'import_duration': 0,
        'attempts': 5
    }
    
    for attempt in range(worker_result['attempts']):
        start_time = time.time()
        
        try:
            from netra_backend.app.core.exceptions_service import ServiceError
            test_error = ServiceError(f"Worker {worker_id} attempt {attempt}")
            
            worker_result['success'] = True
            worker_result['import_duration'] = time.time() - start_time
            break
            
        except Exception as e:
            worker_result['error_details'] = {
                'attempt': attempt,
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            worker_result['import_duration'] = time.time() - start_time
    
    result_queue.put(worker_result)

def test_startup_race_conditions():
    results = {
        'test_name': 'container_startup_race_condition',
        'success': False,
        'workers': 4,
        'worker_results': [],
        'total_successful': 0,
        'total_failed': 0
    }
    
    # Use multiprocessing to simulate startup race conditions
    result_queue = Queue()
    processes = []
    
    # Start worker processes
    for worker_id in range(results['workers']):
        p = Process(target=import_worker, args=(worker_id, result_queue))
        p.start()
        processes.append(p)
    
    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)  # 10 second timeout per process
    
    # Collect results
    while not result_queue.empty():
        worker_result = result_queue.get()
        results['worker_results'].append(worker_result)
        if worker_result['success']:
            results['total_successful'] += 1
        else:
            results['total_failed'] += 1
    
    results['success'] = results['total_failed'] == 0
    
    print("CONTAINER_RACE_TEST_RESULTS:", json.dumps(results))
    return results

if __name__ == "__main__":
    results = test_startup_race_conditions()
    sys.exit(0 if results['success'] else 1)
"""
        
        # Create temporary Docker context
        temp_dir = self._create_test_dockerfile(test_script.replace("'", "\\'"))
        
        try:
            # Build test image
            build_result = subprocess.run([
                'docker', 'build', '-t', f"{self.docker_config['image_name']}-race", temp_dir
            ], capture_output=True, text=True, timeout=120)
            
            if build_result.returncode != 0:
                self.skipTest(f"Docker build failed: {build_result.stderr}")
            
            # Run race condition test
            run_result = subprocess.run([
                'docker', 'run', '--rm',
                '--name', f"{self.docker_config['container_name']}-race",
                f"{self.docker_config['image_name']}-race"
            ], capture_output=True, text=True, timeout=60)
            
            # Parse results
            results = None
            for line in run_result.stdout.split('\\n'):
                if line.startswith('CONTAINER_RACE_TEST_RESULTS:'):
                    try:
                        results_json = line.replace('CONTAINER_RACE_TEST_RESULTS:', '').strip()
                        results = json.loads(results_json)
                        break
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse race test results: {e}")
            
            # Store results
            self.test_results['container_tests'].append({
                'test_name': 'container_startup_race_condition',
                'results': results
            })
            
            if results is None:
                self.fail("No race condition test results found in container output")
            
            # Analyze race condition results
            self.logger.info(f"Race condition test results:")
            self.logger.info(f"  Total workers: {results['workers']}")
            self.logger.info(f"  Successful: {results['total_successful']}")
            self.logger.info(f"  Failed: {results['total_failed']}")
            
            # Log individual worker failures
            for worker_result in results['worker_results']:
                if not worker_result['success']:
                    self.logger.error(f"Worker {worker_result['worker_id']} failed: {worker_result['error_details']}")
            
            # Test should FAIL if race conditions cause import failures
            if results['total_failed'] > 0:
                self.fail(f"Race condition detected: {results['total_failed']}/{results['workers']} workers failed")
        
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_container_python_path_diagnostics(self):
        """Test Python path and module loading diagnostics in container environment."""
        
        if not self._is_docker_available():
            self.skipTest("Docker not available for path diagnostics")
        
        diagnostics_script = """
import sys
import os
import json
import traceback

def collect_diagnostics():
    results = {
        'test_name': 'container_python_path_diagnostics',
        'python_version': sys.version,
        'python_path': sys.path,
        'working_directory': os.getcwd(),
        'environment_variables': dict(os.environ),
        'loaded_modules': {k: str(v) for k, v in sys.modules.items() if 'netra' in k.lower()},
        'netra_backend_location': None,
        'import_test_results': []
    }
    
    # Test different import paths
    import_tests = [
        'netra_backend',
        'netra_backend.app',
        'netra_backend.app.core',
        'netra_backend.app.core.exceptions_base',
        'netra_backend.app.core.exceptions_service',
        'netra_backend.app.core.exceptions'
    ]
    
    for module_name in import_tests:
        test_result = {
            'module': module_name,
            'success': False,
            'error': None,
            'location': None
        }
        
        try:
            imported_module = __import__(module_name, fromlist=[''])
            test_result['success'] = True
            test_result['location'] = getattr(imported_module, '__file__', 'No __file__ attribute')
        except Exception as e:
            test_result['error'] = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
        
        results['import_test_results'].append(test_result)
    
    # Try to locate netra_backend
    for path in sys.path:
        potential_path = os.path.join(path, 'netra_backend')
        if os.path.exists(potential_path):
            results['netra_backend_location'] = potential_path
            break
    
    print("CONTAINER_DIAGNOSTICS_RESULTS:", json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    collect_diagnostics()
"""
        
        temp_dir = self._create_test_dockerfile(diagnostics_script.replace("'", "\\'"))
        
        try:
            # Build and run diagnostics
            build_result = subprocess.run([
                'docker', 'build', '-t', f"{self.docker_config['image_name']}-diag", temp_dir
            ], capture_output=True, text=True, timeout=120)
            
            if build_result.returncode != 0:
                self.skipTest(f"Docker build failed: {build_result.stderr}")
            
            run_result = subprocess.run([
                'docker', 'run', '--rm',
                f"{self.docker_config['image_name']}-diag"
            ], capture_output=True, text=True, timeout=30)
            
            # Extract and log diagnostics
            for line in run_result.stdout.split('\\n'):
                if line.startswith('CONTAINER_DIAGNOSTICS_RESULTS:'):
                    try:
                        results_json = line.replace('CONTAINER_DIAGNOSTICS_RESULTS:', '').strip()
                        results = json.loads(results_json)
                        
                        self.logger.info("Container Python environment diagnostics:")
                        self.logger.info(f"  Python version: {results['python_version']}")
                        self.logger.info(f"  Working directory: {results['working_directory']}")
                        self.logger.info(f"  Netra backend location: {results['netra_backend_location']}")
                        
                        # Log import test results
                        for import_result in results['import_test_results']:
                            status = "SUCCESS" if import_result['success'] else f"FAILED ({import_result['error']['type']})"
                            self.logger.info(f"  Import {import_result['module']}: {status}")
                        
                        # Store for further analysis
                        self.test_results['import_scenarios'].append(results)
                        break
                        
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse diagnostics: {e}")
        
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _is_docker_available(self) -> bool:
        """Check if Docker is available for testing."""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, check=True, timeout=10)
            return result.returncode == 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @classmethod
    def tearDownClass(cls):
        """Clean up and report test results."""
        # Log comprehensive test results
        if cls.test_results['container_tests']:
            cls.logger.info("Docker container test summary:")
            for test in cls.test_results['container_tests']:
                cls.logger.info(f"  {test['test_name']}: {test}")
        
        super().tearDownClass()