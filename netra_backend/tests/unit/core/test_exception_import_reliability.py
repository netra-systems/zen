"""
Unit tests for ServiceError import reliability and timing issues.

This test suite aims to reproduce the ImportError: cannot import name 'ServiceError' issue
that occurs during Docker container startup due to import timing/race conditions.

Business Value:
- Prevents silent failures that could impact user chat experience
- Ensures stable exception handling during container startup
- Protects business-critical error reporting functionality
"""

import pytest
import sys
import importlib
import threading
import time
from typing import List, Dict, Any
import concurrent.futures
from unittest.mock import patch, MagicMock
import logging


class TestServiceErrorImportReliability:
    """Test suite to reproduce ServiceError ImportError issues in Docker containers."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment with clean import state."""
        # Track modules to clean up after tests
        self.modules_to_cleanup = []
        
        # Store original sys.modules state
        self.original_modules = sys.modules.copy()
        
        # Import diagnostic information
        self.import_diagnostics = {
            'import_attempts': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'import_timings': [],
            'error_details': []
        }
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        
        yield
        
        # Clean up modules and restore original state
        for module_name in self.modules_to_cleanup:
            if module_name in sys.modules:
                del sys.modules[module_name]
        
        # Restore original modules state  
        for module_name in list(sys.modules.keys()):
            if module_name not in self.original_modules:
                del sys.modules[module_name]
    
    def _log_import_attempt(self, success: bool, duration: float, error: Exception = None):
        """Log import attempt for diagnostic analysis."""
        self.import_diagnostics['import_attempts'] += 1
        
        if success:
            self.import_diagnostics['successful_imports'] += 1
        else:
            self.import_diagnostics['failed_imports'] += 1
            if error:
                self.import_diagnostics['error_details'].append({
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                    'duration': duration
                })
        
        self.import_diagnostics['import_timings'].append(duration)
    
    def test_direct_service_error_import(self):
        """Test direct import of ServiceError from exceptions_service module.
        
        This test should FAIL initially if the ImportError issue exists.
        """
        start_time = time.time()
        
        try:
            # Attempt direct import that commonly fails in Docker containers
            from netra_backend.app.core.exceptions_service import ServiceError
            
            # Verify the import worked
            assert ServiceError is not None
            assert hasattr(ServiceError, '__init__')
            
            duration = time.time() - start_time
            self._log_import_attempt(True, duration)
            
            # Try to instantiate the exception
            error_instance = ServiceError("Test error message")
            assert error_instance.error_details.message == "Test error message"
            
        except ImportError as e:
            duration = time.time() - start_time
            self._log_import_attempt(False, duration, e)
            
            # Log detailed diagnostic information
            self.logger.error(f"ServiceError ImportError detected: {e}")
            self.logger.error(f"Import attempt duration: {duration:.4f}s")
            self.logger.error(f"Current sys.modules keys containing 'exception': {[k for k in sys.modules.keys() if 'exception' in k.lower()]}")
            
            # This should FAIL to reproduce the bug
            pytest.fail(f"ServiceError ImportError reproduced: {e}")
    
    def test_circular_import_chain_detection(self):
        """Test for circular import issues between exception modules.
        
        Reproduces the complex import chain: 
        exceptions/__init__.py -> exceptions_service.py -> exceptions_agent.py
        """
        start_time = time.time()
        
        try:
            # Clean slate - remove exception modules if present
            exception_modules = [k for k in sys.modules.keys() if 'exceptions' in k and 'netra_backend' in k]
            for module in exception_modules:
                if module in sys.modules:
                    del sys.modules[module]
                    self.modules_to_cleanup.append(module)
            
            # Attempt the problematic import chain
            # Step 1: Import main exceptions module (triggers cascade)
            from netra_backend.app.core.exceptions import ServiceError
            
            # Step 2: Verify all modules loaded correctly
            from netra_backend.app.core.exceptions_service import ServiceError as ServiceErrorDirect
            from netra_backend.app.core.exceptions_agent import AgentExecutionError
            
            # Verify imports are consistent
            assert ServiceError is ServiceErrorDirect
            assert AgentExecutionError is not None
            
            duration = time.time() - start_time
            self._log_import_attempt(True, duration)
            
        except ImportError as e:
            duration = time.time() - start_time
            self._log_import_attempt(False, duration, e)
            
            # Log detailed circular import diagnostics
            self.logger.error(f"Circular import detected: {e}")
            self.logger.error(f"Import chain failure duration: {duration:.4f}s")
            
            # Analyze which specific import failed
            exception_modules_after_failure = [k for k in sys.modules.keys() if 'exceptions' in k and 'netra_backend' in k]
            self.logger.error(f"Exception modules loaded after failure: {exception_modules_after_failure}")
            
            # This should FAIL to reproduce the bug
            pytest.fail(f"Circular import chain failure reproduced: {e}")
    
    def test_concurrent_import_stress(self):
        """Test concurrent imports to reproduce race conditions.
        
        This simulates multiple threads trying to import ServiceError simultaneously,
        which may happen during Docker container startup with multiple workers.
        """
        num_threads = 10
        imports_per_thread = 50
        results = []
        errors = []
        
        def import_worker(thread_id: int) -> Dict[str, Any]:
            """Worker function to perform concurrent imports."""
            thread_results = {
                'thread_id': thread_id,
                'successful_imports': 0,
                'failed_imports': 0,
                'errors': [],
                'import_times': []
            }
            
            for attempt in range(imports_per_thread):
                start_time = time.time()
                
                try:
                    # Force fresh import each time
                    module_name = 'netra_backend.app.core.exceptions_service'
                    if module_name in sys.modules:
                        # Don't actually delete - just test import
                        pass
                    
                    from netra_backend.app.core.exceptions_service import ServiceError
                    
                    # Quick validation
                    error_instance = ServiceError(f"Thread {thread_id} attempt {attempt}")
                    
                    duration = time.time() - start_time
                    thread_results['successful_imports'] += 1
                    thread_results['import_times'].append(duration)
                    
                except Exception as e:
                    duration = time.time() - start_time
                    thread_results['failed_imports'] += 1
                    thread_results['errors'].append({
                        'attempt': attempt,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'duration': duration
                    })
            
            return thread_results
        
        # Execute concurrent imports
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_thread = {
                executor.submit(import_worker, thread_id): thread_id
                for thread_id in range(num_threads)
            }
            
            for future in concurrent.futures.as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append({
                        'thread_id': thread_id,
                        'executor_error': str(e)
                    })
        
        total_duration = time.time() - start_time
        
        # Analyze results
        total_successful = sum(r['successful_imports'] for r in results)
        total_failed = sum(r['failed_imports'] for r in results)
        total_attempts = num_threads * imports_per_thread
        
        self.logger.info(f"Concurrent import stress test completed in {total_duration:.4f}s")
        self.logger.info(f"Total attempts: {total_attempts}")
        self.logger.info(f"Successful imports: {total_successful}")
        self.logger.info(f"Failed imports: {total_failed}")
        
        # Log detailed error information
        for result in results:
            if result['errors']:
                self.logger.error(f"Thread {result['thread_id']} errors: {result['errors']}")
        
        if errors:
            self.logger.error(f"Executor errors: {errors}")
        
        # This test should PASS if no race conditions exist
        # It should FAIL if race conditions cause import failures
        if total_failed > 0:
            error_details = []
            for result in results:
                error_details.extend(result['errors'])
            
            pytest.fail(f"Concurrent import failures detected: {total_failed}/{total_attempts} failed. Details: {error_details}")
        
        # Verify success rate is 100%
        success_rate = (total_successful / total_attempts) * 100
        assert success_rate == 100.0, f"Import success rate was {success_rate:.2f}%, expected 100%"
    
    def test_module_loading_order_sensitivity(self):
        """Test import sensitivity to module loading order.
        
        This tests whether the order of importing exception modules affects success.
        """
        import_orders = [
            # Order 1: Main exceptions first
            ['netra_backend.app.core.exceptions', 'netra_backend.app.core.exceptions_service', 'netra_backend.app.core.exceptions_agent'],
            # Order 2: Service exceptions first
            ['netra_backend.app.core.exceptions_service', 'netra_backend.app.core.exceptions', 'netra_backend.app.core.exceptions_agent'],
            # Order 3: Agent exceptions first
            ['netra_backend.app.core.exceptions_agent', 'netra_backend.app.core.exceptions_service', 'netra_backend.app.core.exceptions']
        ]
        
        results = []
        
        for order_index, import_order in enumerate(import_orders):
            # Clean slate
            exception_modules = [k for k in sys.modules.keys() if 'exceptions' in k and 'netra_backend' in k]
            for module in exception_modules:
                if module in sys.modules:
                    del sys.modules[module]
            
            order_result = {
                'order_index': order_index,
                'import_order': import_order,
                'successful': True,
                'errors': [],
                'duration': 0
            }
            
            start_time = time.time()
            
            try:
                # Import in specified order
                for module_name in import_order:
                    importlib.import_module(module_name)
                
                # Verify ServiceError is accessible
                from netra_backend.app.core.exceptions_service import ServiceError
                test_error = ServiceError("Order test")
                
                order_result['duration'] = time.time() - start_time
                
            except Exception as e:
                order_result['successful'] = False
                order_result['errors'].append({
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                })
                order_result['duration'] = time.time() - start_time
            
            results.append(order_result)
        
        # Analyze results
        successful_orders = [r for r in results if r['successful']]
        failed_orders = [r for r in results if not r['successful']]
        
        self.logger.info(f"Import order sensitivity test results:")
        for result in results:
            status = "SUCCESS" if result['successful'] else "FAILED"
            self.logger.info(f"Order {result['order_index']}: {status} in {result['duration']:.4f}s")
            if result['errors']:
                self.logger.error(f"  Errors: {result['errors']}")
        
        # This test should PASS if import order doesn't matter
        # It should FAIL if certain orders cause ImportError
        if failed_orders:
            pytest.fail(f"Import order sensitivity detected: {len(failed_orders)}/{len(import_orders)} orders failed")
    
    def test_import_timing_diagnostics(self):
        """Collect detailed timing diagnostics for import operations."""
        diagnostic_results = {
            'individual_module_timings': {},
            'full_chain_timing': 0,
            'memory_usage_before': 0,
            'memory_usage_after': 0
        }
        
        import psutil
        process = psutil.Process()
        diagnostic_results['memory_usage_before'] = process.memory_info().rss
        
        # Time individual module imports
        modules_to_test = [
            'netra_backend.app.core.exceptions_base',
            'netra_backend.app.core.exceptions_service', 
            'netra_backend.app.core.exceptions_agent',
            'netra_backend.app.core.exceptions'
        ]
        
        full_chain_start = time.time()
        
        for module_name in modules_to_test:
            # Clean import
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            start_time = time.time()
            try:
                importlib.import_module(module_name)
                duration = time.time() - start_time
                diagnostic_results['individual_module_timings'][module_name] = {
                    'duration': duration,
                    'success': True
                }
            except Exception as e:
                duration = time.time() - start_time
                diagnostic_results['individual_module_timings'][module_name] = {
                    'duration': duration,
                    'success': False,
                    'error': str(e)
                }
        
        diagnostic_results['full_chain_timing'] = time.time() - full_chain_start
        diagnostic_results['memory_usage_after'] = process.memory_info().rss
        diagnostic_results['memory_increase'] = diagnostic_results['memory_usage_after'] - diagnostic_results['memory_usage_before']
        
        # Log comprehensive diagnostics
        self.logger.info("Import timing diagnostics:")
        self.logger.info(f"Full import chain: {diagnostic_results['full_chain_timing']:.4f}s")
        self.logger.info(f"Memory increase: {diagnostic_results['memory_increase']} bytes")
        
        for module, timing in diagnostic_results['individual_module_timings'].items():
            status = "SUCCESS" if timing['success'] else f"FAILED ({timing.get('error', 'Unknown error')})"
            self.logger.info(f"  {module}: {timing['duration']:.4f}s - {status}")
        
        # Store diagnostics for analysis
        self.import_diagnostics.update(diagnostic_results)
        
        # Detect unusually slow imports (> 1 second indicates potential issue)
        slow_imports = {k: v for k, v in diagnostic_results['individual_module_timings'].items() 
                       if v['duration'] > 1.0}
        
        if slow_imports:
            self.logger.warning(f"Unusually slow imports detected: {slow_imports}")
        
        # The test itself doesn't fail - it's purely diagnostic
        # But log if we detect potential issues
        failed_imports = {k: v for k, v in diagnostic_results['individual_module_timings'].items() 
                         if not v['success']}
        
        if failed_imports:
            pytest.fail(f"Import failures detected during diagnostics: {failed_imports}")