class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Comprehensive Pytest Collection Performance and Scale Tests

        This module contains stress tests that validate pytest collection performance under load:
        - Collection time measurement with 1000+ dummy test files
        - Parallel collection stress tests
        - Memory usage during collection verification
        - Collection timeout and interruption handling
        - Performance regression detection

        These tests are designed to be DIFFICULT and catch regressions by actually
        simulating the conditions that cause pytest collection crashes.
        '''

        import asyncio
        import gc
        import os
        import psutil
        import pytest
        import sys
        import tempfile
        import time
        import threading
        import tracemalloc
        from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
        from contextlib import contextmanager
        from dataclasses import dataclass
        from pathlib import Path
        from typing import Dict, List, Optional, Tuple, Any, Generator, Set
        import shutil
        import subprocess
        import multiprocessing
        from shared.isolated_environment import IsolatedEnvironment

        # Pytest internals for collection testing
        from _pytest.config import Config, get_config
        from _pytest.main import Session
        from _pytest.python import Module, Function
        from _pytest.collection import Collector
        from _pytest.runner import CallInfo
        import _pytest.cacheprovider
        import _pytest.warnings

        # Test framework imports
        from test_framework.docker_test_utils import ( )
        DockerContainerManager,
        get_container_memory_stats
        


        @dataclass
class CollectionPerformanceResult:
        """Result container for collection performance measurements"""
        total_tests_collected: int
        collection_time_seconds: float
        peak_memory_mb: float
        memory_leaked_mb: float
        files_processed: int
        collection_rate_per_second: float
        parallel_workers_used: int
        errors_encountered: List[str]
        timeout_occurred: bool
        collection_successful: bool


class DummyTestGenerator:
        '''
        Generates realistic dummy test files for collection performance testing
        '''

    def __init__(self, base_dir: Path):
        pass
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_simple_test_file(self, file_path: Path, num_tests: int = 10) -> None:
        """Create a simple test file with specified number of tests"""
        content = '''"""Generated test file for collection performance testing"""

        import pytest
        import time
        from typing import Any, Dict, List


class TestGeneratedClass:
        """Generated test class with multiple test methods"""

        '''

    # Add test methods
        for i in range(num_tests):
        content += f'''
    def test_method_{i:03d}(self):
        """Generated test method {i}"""
        assert True, "This test always passes"

    def test_parameterized_{i:03d}(self, request):
        """Parameterized test method {i}"""
        assert hasattr(request, 'node'), "Request should have node attribute"
        '''

    # Add some parameterized tests
        content += '''
        @pytest.fixture)
        (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)
    
    def test_with_parameters(self, value: int, expected: int):
        """Test with parameters"""
        assert value == expected

        @pytest.fixture)
        {"key": "value1", "num": 1},
        {"key": "value2", "num": 2},
        {"key": "value3", "num": 3},
    
    def test_with_dict_parameters(self, data: Dict[str, Any]):
        """Test with dictionary parameters"""
        pass
        assert "key" in data
        assert "num" in data
        assert isinstance(data["num"], int)
        '''

    # Add module-level tests
        content += '''

    def test_module_level_function():
        """Module level test function"""
        assert 1 + 1 == 2

        @pytest.mark.slow
    def test_slow_marked_function():
        """Test marked as slow"""
        pass
        time.sleep(0.001)  # Brief delay to simulate slow test
        assert True

        @pytest.fixture
    def sample_data():
        """Sample fixture"""
        return {"test": "data", "numbers": [1, 2, 3]}

    def test_with_fixture(sample_data):
        """Test using fixture"""
        pass
        assert "test" in sample_data
        assert len(sample_data["numbers"]) == 3
        '''

    # Write file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')

    def create_complex_test_file(self, file_path: Path, num_classes: int = 5, methods_per_class: int = 20) -> None:
        """Create a complex test file with multiple classes and inheritance"""
        content = '''"""Complex generated test file with inheritance and fixtures"""

        import pytest
        import asyncio
        import time
        from abc import ABC, abstractmethod
        from typing import Any, Dict, List, Optional, Union


class BaseTestClass(ABC):
        """Abstract base test class"""

        @pytest.fixture
    def setup_base(self):
        """Auto-used fixture for base setup"""
        self.base_data = {"initialized": True}
        yield
    # Cleanup
        self.base_data = None

        @abstractmethod
    def get_test_data(self) -> Dict[str, Any]:
        """Abstract method for test data"""
        pass
        pass

        '''

    # Generate test classes
        for class_idx in range(num_classes):
        content += f'''

class TestGenerated{class_idx:02d}(BaseTestClass):
        """Generated test class {class_idx} inheriting from BaseTestClass"""

    def get_test_data(self) -> Dict[str, Any]:
        """Implementation of abstract method"""
        return {{"class_id": {class_idx}, "methods": {methods_per_class}}}

        @pytest.fixture
    def class_fixture(self):
        """Class-scoped fixture"""
        return "formatted_string"

        @pytest.fixture
    def method_fixture(self):
        """Method-scoped fixture"""
        pass
        return {{"method_data": "test_value_{class_idx}"}}
        '''

    # Generate test methods for each class
        for method_idx in range(methods_per_class):
        content += f'''
    def test_method_{method_idx:03d}(self, class_fixture, method_fixture):
        """Generated test method {method_idx} for class {class_idx}"""
        assert self.base_data["initialized"] is True
        assert "class_{class_idx}" in class_fixture
        assert "method_data" in method_fixture

        @pytest.fixture)
        (1, 2), (2, 4), (3, 6), (4, 8)
    
    def test_parameterized_{method_idx:03d}(self, input_val: int, expected: int):
        """Parameterized test {method_idx}"""
        assert input_val * 2 == expected

    async def test_async_{method_idx:
        """Async test method {method_idx}"""
        await asyncio.sleep(0.001)  # Brief async operation
        assert True

    def test_with_mock_{method_idx:03d}(self, mock_time):
        """Test with mock {method_idx}"""
        assert time.time() == 1234567890.0
        mock_time.assert_called_once()
        '''

    # Write file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')

    def create_nested_test_structure(self, num_dirs: int = 20, files_per_dir: int = 50) -> List[Path]:
        """Create nested directory structure with test files"""
        created_files = []

        for dir_idx in range(num_dirs):
        dir_path = self.base_dir / "formatted_string"
        dir_path.mkdir(parents=True, exist_ok=True)

        for file_idx in range(files_per_dir):
        file_path = dir_path / "formatted_string"

            # Mix simple and complex files
        if file_idx % 3 == 0:
        self.create_complex_test_file(file_path, num_classes=2, methods_per_class=10)
        else:
        self.create_simple_test_file(file_path, num_tests=15)

        created_files.append(file_path)

                    # Add __init__.py files to make packages
        for dir_idx in range(num_dirs):
        init_file = self.base_dir / "formatted_string" / "__init__.py"
        init_file.write_text('"""Generated test package"""', encoding='utf-8')

        return created_files

    def create_conftest_files(self, num_conftest: int = 5) -> List[Path]:
        """Create conftest.py files with fixtures"""
        conftest_files = []

        for i in range(num_conftest):
        if i == 0:
            # Root conftest
        conftest_path = self.base_dir / "conftest.py"
        else:
                # Nested conftest files
        subdir = self.base_dir / "formatted_string"
        subdir.mkdir(parents=True, exist_ok=True)
        conftest_path = subdir / "conftest.py"

        conftest_content = f'''"""Generated conftest.py file {i}"""

        import pytest
        from typing import Any, Dict, List


        @pytest.fixture
    def session_fixture_{i}():
        """Session-scoped fixture {i}"""
        return "formatted_string"

        @pytest.fixture
    def module_fixture_{i}():
        """Module-scoped fixture {i}"""
        return {{"module_id": {i}, "data": "test_data"}}

        @pytest.fixture
    def function_fixture_{i}():
        """Function-scoped fixture {i}"""
        return list(range({i * 10}))

        @pytest.fixture
    def parametrized_fixture_{i}(request):
        """Parametrized fixture {i}"""
        return request.param * {i + 1}

    def pytest_configure(config):
        """Configure pytest for this conftest {i}"""
        config.addinivalue_line("markers", "formatted_string")

    def pytest_collection_modifyitems(config, items):
        """Modify collected items in conftest {i}"""
        pass
    # Add custom marker to tests in this scope
        for item in items:
        if "formatted_string" in str(item.fspath):
        item.add_marker(pytest.mark.custom_marker_{i})
        '''

        conftest_path.write_text(conftest_content, encoding='utf-8')
        conftest_files.append(conftest_path)

        return conftest_files


class PytestCollectionTester:
        '''
        Manages pytest collection testing operations
        '''

    def __init__(self, temp_dir: Optional[Path] = None):
        pass
        if temp_dir:
        self.temp_dir = Path(temp_dir)
        else:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pytest_collection_test_"))

        self.test_generator = DummyTestGenerator(self.temp_dir)
        self.process = psutil.Process(os.getpid())

    def cleanup(self):
        """Clean up temporary test directory"""
        if self.temp_dir.exists():
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def get_current_memory_mb(self) -> float:
        """Get current process memory usage in MB"""
        pass
        return self.process.memory_info().rss / 1024 / 1024

        @contextmanager
    def collection_tracking(self) -> Generator[Dict[str, Any], None, None]:
        """Context manager for tracking collection performance"""
        tracemalloc.start()
        start_memory = self.get_current_memory_mb()
        start_time = time.time()

        tracking_data = { )
        'start_memory': start_memory,
        'start_time': start_time,
        'peak_memory': start_memory,
        'tests_collected': 0,
        'files_processed': 0,
        'errors': []
    

        try:
        yield tracking_data
        finally:
        end_time = time.time()
        end_memory = self.get_current_memory_mb()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        tracking_data.update({ ))
        'end_time': end_time,
        'end_memory': end_memory,
        'duration': end_time - start_time,
        'tracemalloc_peak': peak / 1024 / 1024,  # Convert to MB
        'memory_leaked': end_memory - start_memory
            

        def run_pytest_collection(self, test_paths: List[Path],
extra_args: Optional[List[str]] = None,
timeout: Optional[float] = None) -> CollectionPerformanceResult:
"""Run pytest collection and measure performance"""

args = ["--collect-only", "-q"] + [str(p) for p in test_paths]
if extra_args:
args.extend(extra_args)

with self.collection_tracking() as tracking:
try:
                # Run pytest as subprocess to isolate collection
cmd = [sys.executable, "-m", "pytest"] + args

start_time = time.time()
process = subprocess.Popen( )
cmd,
stdout=subprocess.PIPE,
stderr=subprocess.PIPE,
text=True,
cwd=str(self.temp_dir)
                

try:
stdout, stderr = process.communicate(timeout=timeout)
collection_successful = process.returncode == 0
timeout_occurred = False
except subprocess.TimeoutExpired:
process.kill()
stdout, stderr = process.communicate()
collection_successful = False
timeout_occurred = True

end_time = time.time()

                        # Parse collection output to count tests
tests_collected = 0
if stdout:
for line in stdout.split(" )
"):
if 'collected' in line and 'item' in line:
                                    Extract number from lines like "collected 1500 items"
words = line.split()
for i, word in enumerate(words):
if word == 'collected' and i + 1 < len(words):
try:
tests_collected = int(words[i + 1])
break
except ValueError:
continue

                                                    # Count files processed
files_processed = len(test_paths)

                                                    # Parse errors
errors = []
if stderr:
errors = stderr.split(" )
")

if not collection_successful:
errors.append("formatted_string")

tracking['tests_collected'] = tests_collected
tracking['files_processed'] = files_processed
tracking['errors'] = errors

except Exception as e:
tracking['errors'].append("formatted_string")
tests_collected = 0
files_processed = len(test_paths)
collection_successful = False
timeout_occurred = False
end_time = start_time + (timeout or 300)  # Default timeout handling

                                                                # Calculate metrics
collection_time = tracking['duration']
collection_rate = tests_collected / collection_time if collection_time > 0 else 0

return CollectionPerformanceResult( )
total_tests_collected=tracking['tests_collected'],
collection_time_seconds=collection_time,
peak_memory_mb=tracking['peak_memory'],
memory_leaked_mb=tracking['memory_leaked'],
files_processed=tracking['files_processed'],
collection_rate_per_second=collection_rate,
parallel_workers_used=1,  # Single process collection
errors_encountered=tracking['errors'],
timeout_occurred=timeout_occurred,
collection_successful=collection_successful
                                                                


class PytestCollectionPerformanceTests:
    '''
    Comprehensive pytest collection performance and scale tests
    '''

    @pytest.fixture
    def collection_tester(self) -> PytestCollectionTester:
        """Setup collection performance tester"""
        tester = PytestCollectionTester()
        yield tester
        tester.cleanup()

        @pytest.fixture
    def setup_test_isolation(self):
        """Ensure each test starts with clean state"""
        gc.collect()
        yield
        gc.collect()

    def test_collection_performance_with_1000_simple_files(self, collection_tester: PytestCollectionTester):
        '''
        pass
        Test collection performance with 1000+ simple test files

        Creates 1000 simple test files and measures collection time and memory usage.
        This test catches regressions in basic collection scalability.
        '''

    # Create 1000 simple test files
        num_files = 1000
        test_files = []

        for i in range(num_files):
        file_path = collection_tester.temp_dir / "formatted_string"
        collection_tester.test_generator.create_simple_test_file(file_path, num_tests=10)
        test_files.append(file_path)

        # Run collection and measure performance
        result = collection_tester.run_pytest_collection( )
        test_paths=[collection_tester.temp_dir],
        timeout=300.0  # 5 minute timeout
        

        # Verify collection succeeded
        assert result.collection_successful, "formatted_string"
        assert not result.timeout_occurred, "Collection timed out"

        # Verify we collected a reasonable number of tests
        expected_min_tests = num_files * 8  # At least 8 tests per file
        assert result.total_tests_collected >= expected_min_tests, ( )
        "formatted_string"
        

        # Performance assertions
        max_collection_time = 60.0  # Should complete within 60 seconds
        assert result.collection_time_seconds < max_collection_time, ( )
        "formatted_string"
        

        # Memory usage assertions
        max_memory_mb = 500  # Should not use more than 500MB
        assert result.peak_memory_mb < max_memory_mb, ( )
        "formatted_string"
        

        # Memory leak detection
        max_leaked_mb = 50  # Should not leak more than 50MB
        assert result.memory_leaked_mb < max_leaked_mb, ( )
        "formatted_string"
        

        # Collection rate should be reasonable
        min_collection_rate = 50  # At least 50 tests/second
        assert result.collection_rate_per_second >= min_collection_rate, ( )
        "formatted_string"
        

    def test_collection_performance_with_complex_nested_structure(self, collection_tester: PytestCollectionTester):
        '''
        Test collection performance with complex nested directory structure

        Creates a deep, complex test structure to validate collection
        handles nested imports and fixtures correctly at scale.
        '''

    # Create nested structure with 50 directories, 20 files each
        num_dirs = 50
        files_per_dir = 20

    # Create the nested structure
        test_files = collection_tester.test_generator.create_nested_test_structure( )
        num_dirs=num_dirs,
        files_per_dir=files_per_dir
    

    # Create conftest files
        conftest_files = collection_tester.test_generator.create_conftest_files( )
        num_conftest=10
    

    # Run collection with extended timeout for complex structure
        result = collection_tester.run_pytest_collection( )
        test_paths=[collection_tester.temp_dir],
        timeout=600.0  # 10 minute timeout for complex structure
    

    # Verify collection succeeded
        assert result.collection_successful, "formatted_string"
        assert not result.timeout_occurred, "Collection timed out"

    # Verify comprehensive test collection
        expected_files = num_dirs * files_per_dir
        expected_min_tests = expected_files * 10  # Conservative estimate

        assert result.total_tests_collected >= expected_min_tests, ( )
        "formatted_string"
        "formatted_string"
    

    # Performance assertions for complex structure
        max_collection_time = 180.0  # 3 minutes for complex nested structure
        assert result.collection_time_seconds < max_collection_time, ( )
        "formatted_string"
        "formatted_string"
    

    # Memory usage should be reasonable even for complex structure
        max_memory_mb = 800  # Higher limit for complex structure
        assert result.peak_memory_mb < max_memory_mb, ( )
        "formatted_string"
    

    # Should not have significant errors
        critical_errors = [err for err in result.errors_encountered )
        if 'error' in err.lower() or 'failed' in err.lower()]
        assert len(critical_errors) == 0, "formatted_string"

    def test_parallel_collection_stress_with_multiple_processes(self, collection_tester: PytestCollectionTester):
        '''
        Test collection under parallel stress using multiple processes

        Simulates multiple pytest processes running collection simultaneously
        to catch concurrency and resource contention issues.
        '''

    # Create moderate number of test files for parallel processing
        num_files = 200
        test_files = []

        for i in range(num_files):
        file_path = collection_tester.temp_dir / "formatted_string"
        # Mix simple and complex files
        if i % 4 == 0:
        collection_tester.test_generator.create_complex_test_file( )
        file_path, num_classes=3, methods_per_class=15
            
        else:
        collection_tester.test_generator.create_simple_test_file(file_path, num_tests=12)
        test_files.append(file_path)

    def run_collection_worker(worker_id: int, file_subset: List[Path]) -> CollectionPerformanceResult:
        """Worker function for parallel collection"""
        try:
        # Create separate tester instance for this worker
        worker_tester = PytestCollectionTester(collection_tester.temp_dir)

        result = worker_tester.run_pytest_collection( )
        test_paths=file_subset,
        extra_args=["formatted_string"],
        timeout=120.0
        

        return result

        except Exception as e:
            # Return error result
        return CollectionPerformanceResult( )
        total_tests_collected=0,
        collection_time_seconds=120.0,
        peak_memory_mb=0,
        memory_leaked_mb=0,
        files_processed=len(file_subset),
        collection_rate_per_second=0,
        parallel_workers_used=1,
        errors_encountered=["formatted_string"],
        timeout_occurred=True,
        collection_successful=False
            

            # Split files among workers
        num_workers = min(multiprocessing.cpu_count(), 4)  # Cap at 4 workers
        files_per_worker = len(test_files) // num_workers
        worker_file_sets = []

        for worker_id in range(num_workers):
        start_idx = worker_id * files_per_worker
        if worker_id == num_workers - 1:
                    # Last worker gets remaining files
        end_idx = len(test_files)
        else:
        end_idx = start_idx + files_per_worker

        worker_files = test_files[start_idx:end_idx]
        worker_file_sets.append((worker_id, worker_files))

                        # Run parallel collection
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for worker_id, file_subset in worker_file_sets:
        future = executor.submit(run_collection_worker, worker_id, file_subset)
        futures.append(future)

                                # Collect results
        worker_results = []
        for future in as_completed(futures):
        try:
        result = future.result()
        worker_results.append(result)
        except Exception as e:
                                            # Create error result for failed worker
        error_result = CollectionPerformanceResult( )
        total_tests_collected=0,
        collection_time_seconds=120.0,
        peak_memory_mb=0,
        memory_leaked_mb=0,
        files_processed=0,
        collection_rate_per_second=0,
        parallel_workers_used=1,
        errors_encountered=["formatted_string"],
        timeout_occurred=True,
        collection_successful=False
                                            
        worker_results.append(error_result)

                                            # Verify all workers completed
        assert len(worker_results) == num_workers, "formatted_string"

                                            # Verify at least half the workers succeeded
        successful_workers = [item for item in []]
        assert len(successful_workers) >= num_workers // 2, ( )
        "formatted_string"
                                            

                                            # Aggregate results
        total_tests = sum(r.total_tests_collected for r in successful_workers)
        max_collection_time = max(r.collection_time_seconds for r in successful_workers)
        total_errors = sum(len(r.errors_encountered) for r in worker_results)

                                            # Verify reasonable collection occurred
        expected_min_tests = num_files * 8  # Conservative estimate
        assert total_tests >= expected_min_tests // 2, (  # Allow for some worker failures )
        "formatted_string"
                                            

                                            # Verify parallel collection didn't take too long
        max_parallel_time = 150.0  # Should be faster than sequential
        assert max_collection_time < max_parallel_time, ( )
        "formatted_string"
                                            

                                            # Verify not too many errors across all workers
        max_total_errors = num_workers * 2  # Allow up to 2 errors per worker
        assert total_errors <= max_total_errors, ( )
        "formatted_string"
                                            

    def test_collection_memory_growth_with_large_scale(self, collection_tester: PytestCollectionTester):
        '''
        Test memory growth behavior during large-scale collection

        Incrementally adds test files and measures memory growth to detect
        memory leaks and excessive memory usage patterns.
        '''

    # Test in incremental batches to track memory growth
        batch_sizes = [100, 200, 500, 1000]  # Incremental file counts
        memory_measurements = []

        for batch_size in batch_sizes:
        # Create test files for this batch
        current_files = []
        for i in range(batch_size):
        file_path = collection_tester.temp_dir / "formatted_string"
        collection_tester.test_generator.create_simple_test_file(file_path, num_tests=8)
        current_files.append(file_path)

            # Run collection and measure
        result = collection_tester.run_pytest_collection( )
        test_paths=[collection_tester.temp_dir],
        timeout=240.0  # 4 minute timeout
            

            # Record measurements
        measurement = { )
        'file_count': batch_size,
        'tests_collected': result.total_tests_collected,
        'peak_memory_mb': result.peak_memory_mb,
        'collection_time': result.collection_time_seconds,
        'memory_leaked': result.memory_leaked_mb,
        'successful': result.collection_successful
            
        memory_measurements.append(measurement)

            # Verify this batch succeeded
        assert result.collection_successful, ( )
        "formatted_string"
            

            # Clean up files for next batch (keep directory structure)
        for file_path in current_files:
        file_path.unlink(missing_ok=True)

                # Force garbage collection between batches
        gc.collect()

                # Analyze memory growth patterns
        for i, measurement in enumerate(memory_measurements):
        batch_size = batch_sizes[i]

                    # Memory should scale reasonably with file count
        memory_per_file = measurement['peak_memory_mb'] / batch_size
        max_memory_per_file = 0.5  # 0.5MB per file maximum

        assert memory_per_file < max_memory_per_file, ( )
        "formatted_string"
                    

                    # Collection time should scale reasonably
        time_per_file = measurement['collection_time'] / batch_size
        max_time_per_file = 0.1  # 0.1 seconds per file maximum

        assert time_per_file < max_time_per_file, ( )
        "formatted_string"
                    

                    # Memory leaks should not accumulate excessively
        max_leaked_per_file = 0.05  # 0.05MB per file
        leaked_per_file = measurement['memory_leaked'] / batch_size

        assert leaked_per_file < max_leaked_per_file, ( )
        "formatted_string"
                    

                    # Verify memory growth is sub-linear (efficiency improves with scale)
        if len(memory_measurements) >= 2:
        small_batch = memory_measurements[0]
        large_batch = memory_measurements[-1]

                        # Calculate scaling ratios
        file_ratio = large_batch['file_count'] / small_batch['file_count']
        memory_ratio = large_batch['peak_memory_mb'] / small_batch['peak_memory_mb']
        time_ratio = large_batch['collection_time'] / small_batch['collection_time']

                        # Memory growth should be sub-linear (better than O(n))
        assert memory_ratio < file_ratio * 0.8, ( )
        "formatted_string"
                        

                        # Time growth should be approximately linear or better
        assert time_ratio <= file_ratio * 1.2, ( )
        "formatted_string"
                        

    def test_collection_with_circular_import_simulation(self, collection_tester: PytestCollectionTester):
        '''
        Test collection behavior with simulated circular import scenarios

        Creates test files with complex import dependencies to verify
        collection handles import cycles gracefully without hanging.
        '''

    # Create files with potential circular imports
        num_modules = 20
        test_files = []

        for i in range(num_modules):
        module_name = "formatted_string"
        file_path = collection_tester.temp_dir / "formatted_string"

        # Create content with imports to other modules
        import_targets = []
        Each module imports from 2-3 other modules
        for j in range(2 + (i % 2)):  # 2 or 3 imports
        target_idx = (i + j + 1) % num_modules
        if target_idx != i:  # Don"t import self
        import_targets.append("formatted_string")

        content = f'''"""Test module {i} with cross-imports for circular dependency testing"""

        import pytest
        import sys
        from typing import Any, Dict
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env

        # Cross-imports that may create circular dependencies
        '''

        # Add imports
        for target in import_targets:
        content += f'''
        try:
        from {target} import shared_fixture_{target.split("_")[-1]}
        except ImportError:
                    Handle import failure gracefully
    def shared_fixture_{target.split("_")[-1]}():
        return "fallback_data_{target.split('_')[-1]}"
        '''

    # Add shared fixture that others might import
        content += f'''

        @pytest.fixture
    def shared_fixture_{i:02d}():
        """Shared fixture that other modules might import"""
        return {{"module_id": {i}, "data": "shared_data_{i:02d}"}}

class TestCrossImport{i:02d}:
        """Test class with cross-module dependencies"""

    def test_local_functionality(self):
        """Test that doesn't depend on imports"""
        assert {i} >= 0
        assert isinstance({i}, int)

        '''

    # Add tests that use imported fixtures (with fallback)
        for target in import_targets[:1]:  # Only use first import to avoid complexity
        target_num = target.split("_")[-1]
        content += f'''
    def test_with_imported_fixture(self):
        """Test using imported fixture with fallback"""
        pass
        try:
        fixture_data = shared_fixture_{target_num}()
        assert fixture_data is not None
        except Exception:
            # Fallback test
        assert True
        '''

            # Add regular tests
        content += f'''
    def test_basic_functionality_{i}(self):
        """Basic test for module {i}"""
        result = {i} * 2
        assert result == {i * 2}

        @pytest.fixture
    def test_parametrized_{i}(self, value):
        """Parametrized test for module {i}"""
        assert value + {i} > {i}
        '''

        file_path.write_text(content, encoding='utf-8')
        test_files.append(file_path)

    # Run collection with timeout to catch hangs
        result = collection_tester.run_pytest_collection( )
        test_paths=[collection_tester.temp_dir],
        timeout=180.0  # 3 minute timeout - important for circular import detection
    

    # The key assertion: collection should not timeout due to circular imports
        assert not result.timeout_occurred, ( )
        "Collection timed out - likely due to circular import hanging. "
        "This indicates the collection process is not robust against import cycles."
    

    Collection might fail due to import issues, but shouldn't hang
        if not result.collection_successful:
        # Verify errors are import-related, not hangs
        import_errors = [err for err in result.errors_encountered )
        if 'import' in err.lower() or 'modulenotfounderror' in err.lower()]

        Some import errors are acceptable, but not complete failure
        assert len(import_errors) < len(result.errors_encountered), ( )
        "All errors appear to be import-related, which suggests "
        "the test structure may be too complex"
        

        Should collect at least some tests even with import issues
        min_tests_expected = num_modules * 2  # At least 2 tests per module
        assert result.total_tests_collected >= min_tests_expected, ( )
        "formatted_string"
        "formatted_string"
        

        Collection time should be reasonable even with import complexity
        max_collection_time = 120.0  # Should not take more than 2 minutes
        assert result.collection_time_seconds < max_collection_time, ( )
        "formatted_string"
        "formatted_string"
        

    def test_collection_interruption_and_recovery(self, collection_tester: PytestCollectionTester):
        '''
        Test collection behavior under interruption and recovery scenarios

        Simulates collection interruptions (like CTRL+C) and verifies
        the system can recover gracefully without leaving corrupted state.
        '''

    # Create a large set of test files
        num_files = 300
        test_files = []

        for i in range(num_files):
        file_path = collection_tester.temp_dir / "formatted_string"
        collection_tester.test_generator.create_simple_test_file(file_path, num_tests=10)
        test_files.append(file_path)

        # Test 1: Start collection and interrupt it early
    def interrupt_collection_after_delay(delay: float, process: subprocess.Popen):
        """Helper function to interrupt collection after delay"""
        time.sleep(delay)
        try:
        process.terminate()  # Gentle termination first
        time.sleep(1)
        if process.poll() is None:
        process.kill()  # Force kill if needed
        except Exception:
        pass  # Process might have already finished

                # Run collection with planned interruption
        cmd = [sys.executable, "-m", "pytest", "--collect-only", "-v", str(collection_tester.temp_dir)]

        start_time = time.time()
        process = subprocess.Popen( )
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(collection_tester.temp_dir)
                

                # Start interruption timer
        interrupt_delay = 5.0  # Interrupt after 5 seconds
        interrupt_thread = threading.Thread( )
        target=interrupt_collection_after_delay,
        args=(interrupt_delay, process)
                
        interrupt_thread.start()

        try:
        stdout, stderr = process.communicate(timeout=15.0)
        interrupted = process.returncode != 0
        except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        interrupted = True

        interrupt_thread.join()
        interrupt_time = time.time() - start_time

                        # Verify interruption worked as expected
        assert interrupt_time <= 10.0, ( )
        "formatted_string"
                        

                        # Test 2: Verify system can recover and run collection again
        recovery_start = time.time()

        recovery_result = collection_tester.run_pytest_collection( )
        test_paths=[collection_tester.temp_dir],
        timeout=120.0
                        

        recovery_time = time.time() - recovery_start

                        # Verify recovery worked
        assert recovery_result.collection_successful, ( )
        "formatted_string"
                        

                        # Verify we can collect the expected number of tests after recovery
        expected_tests = num_files * 8  # Conservative estimate
        assert recovery_result.total_tests_collected >= expected_tests, ( )
        "formatted_string"
        "formatted_string"
                        

                        # Verify recovery didn't take excessively long
        max_recovery_time = 60.0
        assert recovery_time < max_recovery_time, ( )
        "formatted_string"
                        

                        # Test 3: Verify no corrupted cache files or state
                        # Check for any .pytest_cache or .pyc files that might indicate corruption
        cache_files = list(collection_tester.temp_dir.rglob("*.pyc"))
        cache_files.extend(list(collection_tester.temp_dir.rglob(".pytest_cache")))

                        # Should be minimal cache files after interruption and recovery
        assert len(cache_files) < 50, ( )
        "formatted_string"
                        

                        # Test 4: Run a final collection to ensure complete stability
        final_result = collection_tester.run_pytest_collection( )
        test_paths=[collection_tester.temp_dir],
        timeout=120.0
                        

        assert final_result.collection_successful, ( )
        "Final collection failed - system may not have fully recovered"
                        

                        # Results should be consistent
        test_count_difference = abs( )
        final_result.total_tests_collected - recovery_result.total_tests_collected
                        
        assert test_count_difference < 10, ( )
        "formatted_string"
        "formatted_string"
                        
        pass
