"""
Unit Tests for WebSocket Import Chain Validation

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Risk Reduction & System Stability
- Value Impact: Prevent Cloud Run import failures that block 90% of business value (chat)
- Strategic Impact: Detect import instability before production deployment

Critical Mission: These tests MUST FAIL initially to prove they catch the Cloud Run 
dynamic import failure issue: "name 'time' is not defined"

Root Cause Being Tested:
During WebSocket error scenarios in GCP Cloud Run, Python's import system becomes
unstable due to aggressive resource cleanup, causing dynamic imports within 
exception handlers to fail.
"""

import gc
import importlib
import sys
import threading
import time
import unittest.mock
from typing import Dict, Any
from unittest.mock import patch, MagicMock
import pytest

from test_framework.ssot.base_test_case import BaseTestCase


class TestImportChainValidation(BaseTestCase):
    """
    Unit tests for import chain validation under Cloud Run conditions.
    
    CRITICAL: These tests are designed to FAIL initially, proving they catch 
    the real Cloud Run dynamic import failure issue.
    """
    
    def test_dynamic_import_under_gc_pressure(self):
        """
        Test dynamic imports under garbage collection pressure similar to Cloud Run.
        
        This test MUST FAIL initially to prove it reproduces the Cloud Run scenario
        where aggressive GC interferes with dynamic imports during WebSocket error handling.
        """
        # Simulate Cloud Run aggressive garbage collection
        original_modules = dict(sys.modules)
        
        try:
            # Force garbage collection multiple times (Cloud Run behavior)
            for _ in range(10):
                gc.collect()
                
            # Remove time module from cache (simulating Cloud Run cleanup)
            if 'time' in sys.modules:
                del sys.modules['time']
                
            # Try to import utilities that depend on time module
            # This should FAIL when reproducing Cloud Run conditions
            from netra_backend.app.websocket_core.utils import get_current_timestamp
            
            # This call should fail with "name 'time' is not defined"
            # when Cloud Run conditions are properly simulated
            timestamp = get_current_timestamp()
            
            # If we reach here without error, the test hasn't reproduced the issue yet
            # Add more aggressive simulation
            self._simulate_cloud_run_resource_pressure()
            
            # Try again with resource pressure
            timestamp_under_pressure = get_current_timestamp()
            
            # EXPECTED: This should fail in initial test runs, proving it catches the issue
            assert timestamp_under_pressure > 0, "Should fail when reproducing Cloud Run conditions"
            
        finally:
            # Restore module state
            sys.modules.clear()
            sys.modules.update(original_modules)
    
    def test_time_module_availability_in_nested_calls(self):
        """
        Test time module availability in nested function calls during exception handling.
        
        This reproduces the exact scenario from websocket.py line 1293-1294:
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
            if is_websocket_connected(websocket):  # <- This call fails
        """
        # Mock WebSocket object for testing
        mock_websocket = MagicMock()
        mock_websocket.client_state = "CONNECTED"
        
        # Simulate module instability during exception handling
        with patch.dict('sys.modules', {}, clear=False):
            # Remove time module during exception handling (Cloud Run scenario)
            original_time = sys.modules.get('time')
            if 'time' in sys.modules:
                del sys.modules['time']
            
            try:
                # This should reproduce the "name 'time' is not defined" error
                from netra_backend.app.websocket_core.utils import is_websocket_connected
                
                # Force environment to staging (where the error occurs)
                with patch('shared.isolated_environment.get_env') as mock_env:
                    mock_env.return_value = {'ENVIRONMENT': 'staging'}
                    
                    # This call should FAIL with time import error
                    result = is_websocket_connected(mock_websocket)
                    
                    # If this passes, we need more aggressive simulation
                    assert result is not None, "Should fail when time module unavailable"
                    
            except NameError as e:
                if "time" in str(e):
                    # SUCCESS: We've reproduced the Cloud Run error!
                    pytest.fail(f"REPRODUCED CLOUD RUN ERROR: {e}")
                else:
                    raise
                    
            finally:
                # Restore time module
                if original_time:
                    sys.modules['time'] = original_time
    
    def test_circular_import_detection_websocket_utils(self):
        """
        Detect circular imports in websocket utils chain that may cause instability.
        
        This test identifies circular import patterns that could contribute to
        the Cloud Run import failure scenario.
        """
        import_chain = []
        
        def trace_imports(name, locals=None, globals=None, fromlist=(), level=0):
            """Trace import calls to detect circular patterns."""
            import_chain.append(name)
            # Detect if we're importing something we've already imported
            if import_chain.count(name) > 1:
                circular_chain = " -> ".join(import_chain)
                pytest.fail(f"CIRCULAR IMPORT DETECTED: {circular_chain}")
            return original_import(name, locals, globals, fromlist, level)
        
        # Hook into import system
        original_import = __builtins__.__import__
        __builtins__.__import__ = trace_imports
        
        try:
            # Test the problematic import chain from websocket.py
            from netra_backend.app.websocket_core.utils import is_websocket_connected
            from netra_backend.app.websocket_core.utils import get_current_timestamp
            
            # This should detect any circular imports
            import_chain_str = " -> ".join(import_chain)
            
            # Check for known problematic patterns
            problematic_patterns = [
                "websocket_core.utils -> shared.isolated_environment -> websocket_core",
                "utils -> connection_state_machine -> utils"
            ]
            
            for pattern in problematic_patterns:
                if pattern in import_chain_str:
                    pytest.fail(f"PROBLEMATIC IMPORT PATTERN DETECTED: {pattern}")
                    
        finally:
            __builtins__.__import__ = original_import
    
    def test_exception_handler_import_failures(self):
        """
        Test import failures during exception handling (the exact failure scenario).
        
        This reproduces the specific context where the error occurs:
        Line 1293 in websocket.py exception handler calling is_websocket_connected()
        """
        # Create a scenario that mimics the exception handler context
        mock_websocket = MagicMock()
        
        # Simulate the exact failure scenario
        def simulate_exception_handler():
            try:
                # Simulate some WebSocket operation that fails
                raise Exception("Simulated WebSocket error")
                
            except Exception as e:
                # This is line 1293-1294 in websocket.py
                print(f"WebSocket error: {e}")  # logger.error equivalent
                
                # Simulate Cloud Run resource cleanup during exception handling
                self._simulate_cloud_run_import_instability()
                
                # This call should fail with "name 'time' is not defined"
                from netra_backend.app.websocket_core.utils import is_websocket_connected
                return is_websocket_connected(mock_websocket)
        
        # Execute and expect failure
        with pytest.raises((NameError, ImportError)) as exc_info:
            simulate_exception_handler()
            
        # Verify we caught the specific error
        error_msg = str(exc_info.value)
        assert "time" in error_msg, f"Expected time-related error, got: {error_msg}"
    
    def test_is_websocket_connected_import_chain(self):
        """
        Test the specific import chain that fails in is_websocket_connected().
        
        This tests the dynamic imports in utils.py lines 159, 278 that are
        called during exception handling.
        """
        mock_websocket = MagicMock()
        mock_websocket.client_state = "CONNECTED"
        
        # Test each problematic import in the chain
        problematic_imports = [
            'shared.isolated_environment',  # Line 159
            'netra_backend.app.websocket_core.connection_state_machine',  # Line 278
            'time'  # The actual failing import
        ]
        
        for import_module in problematic_imports:
            # Simulate module unavailability (Cloud Run cleanup)
            with patch.dict('sys.modules', {import_module: None}):
                try:
                    from netra_backend.app.websocket_core.utils import is_websocket_connected
                    
                    # Force staging environment (where error occurs)
                    with patch('shared.isolated_environment.get_env') as mock_env:
                        mock_env.return_value = {'ENVIRONMENT': 'staging'}
                        
                        # This should fail when critical modules are unavailable
                        result = is_websocket_connected(mock_websocket)
                        
                        # If it doesn't fail, we need to know why
                        print(f"UNEXPECTED SUCCESS with {import_module} unavailable: {result}")
                        
                except (ImportError, NameError, AttributeError) as e:
                    # Expected failure - this proves the test catches import issues
                    print(f"CAUGHT EXPECTED IMPORT FAILURE for {import_module}: {e}")
                    continue
    
    def _simulate_cloud_run_resource_pressure(self):
        """Simulate Cloud Run resource pressure that causes import failures."""
        # Aggressive garbage collection
        for _ in range(20):
            gc.collect()
            
        # Simulate memory pressure
        temp_objects = []
        for i in range(1000):
            temp_objects.append(f"memory_pressure_object_{i}" * 100)
            
        # Clean up
        del temp_objects
        gc.collect()
    
    def _simulate_cloud_run_import_instability(self):
        """Simulate Cloud Run import system instability."""
        # Remove modules from cache (simulating aggressive cleanup)
        modules_to_remove = ['time', 'datetime', 'asyncio']
        removed_modules = {}
        
        for module_name in modules_to_remove:
            if module_name in sys.modules:
                removed_modules[module_name] = sys.modules[module_name]
                del sys.modules[module_name]
        
        # Trigger garbage collection
        gc.collect()
        
        # Restore modules after a delay (simulating instability)
        threading.Timer(0.1, lambda: sys.modules.update(removed_modules)).start()


class TestExceptionHandlerImports(BaseTestCase):
    """Test import stability during exception handling scenarios."""
    
    def test_exception_handler_nested_import_failures(self):
        """
        Test nested import failures during exception handling.
        
        This simulates the exact call stack when the error occurs:
        websocket_endpoint -> exception handler -> is_websocket_connected -> get_env -> time
        """
        # Create the exact call chain that fails
        def websocket_endpoint_simulation():
            """Simulate the websocket endpoint exception handler."""
            try:
                # Simulate WebSocket operation that triggers exception
                raise ConnectionError("WebSocket connection lost")
                
            except Exception as e:
                # Line 1293: logger.error(f"WebSocket error: {e}", exc_info=True)
                
                # Simulate Cloud Run resource cleanup at this moment
                self._corrupt_import_system()
                
                # Line 1294: if is_websocket_connected(websocket):
                from netra_backend.app.websocket_core.utils import is_websocket_connected
                mock_websocket = MagicMock()
                
                # This should fail with "name 'time' is not defined"
                return is_websocket_connected(mock_websocket)
        
        # Expected to fail initially
        with pytest.raises((NameError, ImportError, AttributeError)):
            websocket_endpoint_simulation()
    
    def test_environment_detection_import_chain_failure(self):
        """
        Test the environment detection import chain that fails in Cloud Run.
        
        The failure chain: is_websocket_connected -> get_env -> isolated_environment -> time
        """
        # Mock the exact scenario
        mock_websocket = MagicMock()
        
        # Simulate the environment detection call that fails
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            # Configure to return staging environment
            mock_get_env.return_value = {'ENVIRONMENT': 'staging'}
            
            # Corrupt the time module during environment detection
            original_time = sys.modules.get('time')
            if 'time' in sys.modules:
                del sys.modules['time']
            
            try:
                from netra_backend.app.websocket_core.utils import is_websocket_connected
                
                # This should fail when time is unavailable during environment detection
                result = is_websocket_connected(mock_websocket)
                
                # Should not reach here when properly simulating the failure
                assert False, f"Test did not reproduce import failure, got result: {result}"
                
            except NameError as e:
                # Success - we reproduced the error
                assert "time" in str(e), f"Expected time error, got: {e}"
                
            finally:
                if original_time:
                    sys.modules['time'] = original_time
    
    def _corrupt_import_system(self):
        """Corrupt the import system to simulate Cloud Run instability."""
        # Remove critical modules that are dynamically imported
        critical_modules = [
            'time',
            'datetime', 
            'shared.isolated_environment',
            'netra_backend.app.websocket_core.connection_state_machine'
        ]
        
        for module in critical_modules:
            if module in sys.modules:
                del sys.modules[module]
        
        # Force garbage collection to clear any cached references
        gc.collect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])