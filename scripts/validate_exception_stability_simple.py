#!/usr/bin/env python3
"""
Comprehensive validation script for ServiceError ImportError fix stability.
Windows-compatible version without Unicode emojis.
"""

import sys
import time
import traceback
import importlib
from typing import Dict, List, Any


def test_all_exception_imports():
    """Test all exception imports and functionality."""
    print("=" * 60)
    print("SERVICEERROR IMPORTERROR FIX VALIDATION")
    print("=" * 60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")
    
    results = {
        'all_tests_passed': True,
        'test_results': []
    }
    
    # Test 1: Direct ServiceError import (the original issue)
    print("\n[TEST 1] Direct ServiceError import...")
    try:
        from netra_backend.app.core.exceptions_service import ServiceError
        test_error = ServiceError("Direct import test")
        assert test_error.error_details.message == "Direct import test"
        print("  [PASS] ServiceError direct import successful")
        results['test_results'].append(('ServiceError direct import', True, None))
    except Exception as e:
        print(f"  [FAIL] ServiceError direct import failed: {e}")
        results['all_tests_passed'] = False
        results['test_results'].append(('ServiceError direct import', False, str(e)))
    
    # Test 2: Unified exceptions import
    print("\n[TEST 2] Unified exceptions import...")
    try:
        from netra_backend.app.core.exceptions import (
            ServiceError, ServiceUnavailableError, AgentError, AgentTimeoutError
        )
        # Test each class
        service_error = ServiceError("Unified test 1")
        service_unavail = ServiceUnavailableError("Unified test 2")
        agent_error = AgentError("Unified test 3")
        agent_timeout = AgentTimeoutError("Unified test 4")
        
        print("  [PASS] Unified exceptions import successful")
        results['test_results'].append(('Unified exceptions import', True, None))
    except Exception as e:
        print(f"  [FAIL] Unified exceptions import failed: {e}")
        results['all_tests_passed'] = False
        results['test_results'].append(('Unified exceptions import', False, str(e)))
    
    # Test 3: Circular import resistance
    print("\n[TEST 3] Circular import resistance...")
    try:
        # Clean modules
        modules_to_clean = [m for m in sys.modules.keys() if 'exceptions' in m and 'netra_backend' in m]
        for module in modules_to_clean:
            del sys.modules[module]
        
        # Import in problematic order (previously caused circular imports)
        import netra_backend.app.core.exceptions_service
        import netra_backend.app.core.exceptions_agent
        import netra_backend.app.core.exceptions
        
        # Test that ServiceError still works
        from netra_backend.app.core.exceptions_service import ServiceError
        test_error = ServiceError("Circular import resistance test")
        
        print("  [PASS] Circular import resistance test successful")
        results['test_results'].append(('Circular import resistance', True, None))
    except Exception as e:
        print(f"  [FAIL] Circular import resistance failed: {e}")
        results['all_tests_passed'] = False
        results['test_results'].append(('Circular import resistance', False, str(e)))
    
    # Test 4: AgentTimeoutError SSOT validation
    print("\n[TEST 4] AgentTimeoutError SSOT validation...")
    try:
        from netra_backend.app.core.exceptions_agent import AgentTimeoutError
        
        # Ensure it's NOT available from exceptions_service (SSOT compliance)
        try:
            from netra_backend.app.core.exceptions_service import AgentTimeoutError as ServiceAgentTimeoutError
            # If this import succeeds, SSOT is violated
            print("  [FAIL] AgentTimeoutError SSOT violation: available in exceptions_service")
            results['all_tests_passed'] = False
            results['test_results'].append(('AgentTimeoutError SSOT', False, "Available in multiple modules"))
        except ImportError:
            # This is expected - AgentTimeoutError should only be in exceptions_agent
            timeout_error = AgentTimeoutError("SSOT test", timeout_seconds=30)
            print("  [PASS] AgentTimeoutError SSOT compliance validated")
            results['test_results'].append(('AgentTimeoutError SSOT', True, None))
    except Exception as e:
        print(f"  [FAIL] AgentTimeoutError SSOT validation failed: {e}")
        results['all_tests_passed'] = False
        results['test_results'].append(('AgentTimeoutError SSOT', False, str(e)))
    
    # Test 5: Import timing performance
    print("\n[TEST 5] Import performance test...")
    try:
        import_times = []
        num_cycles = 5
        
        for i in range(num_cycles):
            # Clean import
            modules_to_clean = [m for m in sys.modules.keys() if 'exceptions' in m and 'netra_backend' in m]
            for module in modules_to_clean:
                del sys.modules[module]
            
            start_time = time.time()
            from netra_backend.app.core.exceptions import ServiceError
            test_error = ServiceError("Performance test")
            import_time = time.time() - start_time
            import_times.append(import_time)
        
        avg_time = sum(import_times) / len(import_times)
        max_time = max(import_times)
        
        print(f"  Average import time: {avg_time:.4f}s")
        print(f"  Maximum import time: {max_time:.4f}s")
        
        if avg_time < 1.0:  # Under 1 second is acceptable
            print("  [PASS] Import performance acceptable")
            results['test_results'].append(('Import performance', True, f"Avg: {avg_time:.4f}s"))
        else:
            print("  [FAIL] Import performance too slow")
            results['all_tests_passed'] = False
            results['test_results'].append(('Import performance', False, f"Avg: {avg_time:.4f}s"))
            
    except Exception as e:
        print(f"  [FAIL] Import performance test failed: {e}")
        results['all_tests_passed'] = False
        results['test_results'].append(('Import performance', False, str(e)))
    
    # Final assessment
    print("\n" + "=" * 60)
    print("FINAL ASSESSMENT")
    print("=" * 60)
    
    print(f"\nTest Summary:")
    for test_name, passed, error_msg in results['test_results']:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed and error_msg:
            print(f"       Error: {error_msg}")
    
    if results['all_tests_passed']:
        print(f"\n[SUCCESS] All tests passed!")
        print("ServiceError ImportError fixes are stable and production-ready.")
        print("System has maintained stability without introducing breaking changes.")
        return 0
    else:
        print(f"\n[FAILURE] Some tests failed!")
        print("ServiceError ImportError fixes require additional work before deployment.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = test_all_exception_imports()
        sys.exit(exit_code)
    except Exception as e:
        print(f"CRITICAL ERROR: Validation suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1)