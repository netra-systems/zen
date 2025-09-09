#!/usr/bin/env python3
"""
Comprehensive validation script for ServiceError ImportError fix stability.

This script performs thorough validation that all exception classes work correctly
after the circular import fixes and SSOT consolidation.
"""

import sys
import time
import traceback
import importlib
from typing import Dict, List, Any, Type


def test_direct_exception_imports() -> Dict[str, Any]:
    """Test direct imports of all exception classes."""
    print("[IMPORTS] Testing direct exception imports...")
    
    exception_modules = [
        'netra_backend.app.core.exceptions_base',
        'netra_backend.app.core.exceptions_service', 
        'netra_backend.app.core.exceptions_agent',
        'netra_backend.app.core.exceptions_database',
        'netra_backend.app.core.exceptions'
    ]
    
    results = {
        'success': True,
        'module_results': [],
        'total_modules': len(exception_modules),
        'successful_imports': 0,
        'failed_imports': 0
    }
    
    for module_name in exception_modules:
        module_result = {
            'module': module_name,
            'success': False,
            'duration': 0,
            'error': None,
            'classes_found': []
        }
        
        start_time = time.time()
        try:
            # Fresh import to ensure no caching effects
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            module = importlib.import_module(module_name)
            
            # Find exception classes in the module
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, Exception):
                    module_result['classes_found'].append(name)
            
            module_result['success'] = True
            module_result['duration'] = time.time() - start_time
            results['successful_imports'] += 1
            print(f"  [OK] {module_name}: {len(module_result['classes_found'])} exception classes")
            
        except Exception as e:
            module_result['success'] = False
            module_result['error'] = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            module_result['duration'] = time.time() - start_time
            results['failed_imports'] += 1
            results['success'] = False
            print(f"  ❌ {module_name}: {type(e).__name__}: {e}")
        
        results['module_results'].append(module_result)
    
    return results


def test_exception_class_instantiation() -> Dict[str, Any]:
    """Test that all exception classes can be instantiated correctly."""
    print("\n🔧 Testing exception class instantiation...")
    
    # Key exception classes to test
    exception_tests = [
        ('netra_backend.app.core.exceptions_service', 'ServiceError'),
        ('netra_backend.app.core.exceptions_service', 'ServiceUnavailableError'),
        ('netra_backend.app.core.exceptions_service', 'ServiceTimeoutError'),
        ('netra_backend.app.core.exceptions_agent', 'AgentError'),
        ('netra_backend.app.core.exceptions_agent', 'AgentExecutionError'),
        ('netra_backend.app.core.exceptions_agent', 'AgentTimeoutError'),
        ('netra_backend.app.core.exceptions_agent', 'LLMError'),
        ('netra_backend.app.core.exceptions_database', 'DatabaseError'),
        ('netra_backend.app.core.exceptions_database', 'RecordNotFoundError'),
    ]
    
    results = {
        'success': True,
        'class_results': [],
        'total_classes': len(exception_tests),
        'successful_instantiations': 0,
        'failed_instantiations': 0
    }
    
    for module_name, class_name in exception_tests:
        class_result = {
            'module': module_name,
            'class': class_name,
            'success': False,
            'duration': 0,
            'error': None,
            'instance_created': False,
            'properties_validated': False
        }
        
        start_time = time.time()
        try:
            # Import the class
            module = importlib.import_module(module_name)
            exception_class = getattr(module, class_name)
            
            # Create an instance
            instance = exception_class("Test error message")
            class_result['instance_created'] = True
            
            # Validate basic properties
            assert hasattr(instance, 'error_details'), f"{class_name} missing error_details"
            assert instance.error_details.message == "Test error message", f"{class_name} message mismatch"
            class_result['properties_validated'] = True
            
            class_result['success'] = True
            class_result['duration'] = time.time() - start_time
            results['successful_instantiations'] += 1
            print(f"  ✅ {class_name}: instantiated and validated")
            
        except Exception as e:
            class_result['success'] = False
            class_result['error'] = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            class_result['duration'] = time.time() - start_time
            results['failed_instantiations'] += 1
            results['success'] = False
            print(f"  ❌ {class_name}: {type(e).__name__}: {e}")
        
        results['class_results'].append(class_result)
    
    return results


def test_unified_exceptions_import() -> Dict[str, Any]:
    """Test the unified exceptions module imports."""
    print("\n🎯 Testing unified exceptions module...")
    
    results = {
        'success': False,
        'duration': 0,
        'error': None,
        'classes_available': [],
        'missing_classes': []
    }
    
    expected_classes = [
        'ServiceError', 'ServiceUnavailableError', 'ServiceTimeoutError',
        'AgentError', 'AgentExecutionError', 'AgentTimeoutError', 'LLMError',
        'DatabaseError', 'RecordNotFoundError',
        'NetraException', 'ValidationError'
    ]
    
    start_time = time.time()
    try:
        # Test unified import
        from netra_backend.app.core.exceptions import (
            ServiceError, ServiceUnavailableError, ServiceTimeoutError,
            AgentError, AgentExecutionError, AgentTimeoutError, LLMError,
            DatabaseError, RecordNotFoundError,
            NetraException, ValidationError
        )
        
        # Validate each class is available
        local_vars = locals()
        for class_name in expected_classes:
            if class_name in local_vars and local_vars[class_name] is not None:
                results['classes_available'].append(class_name)
            else:
                results['missing_classes'].append(class_name)
        
        # Test that ServiceError still works as expected (the original issue)
        service_error = ServiceError("Unified import test")
        assert service_error.error_details.message == "Unified import test"
        
        results['success'] = len(results['missing_classes']) == 0
        results['duration'] = time.time() - start_time
        
        print(f"  ✅ Unified import: {len(results['classes_available'])}/{len(expected_classes)} classes available")
        if results['missing_classes']:
            print(f"  ⚠️ Missing classes: {results['missing_classes']}")
            
    except Exception as e:
        results['success'] = False
        results['error'] = {
            'type': type(e).__name__,
            'message': str(e),
            'traceback': traceback.format_exc()
        }
        results['duration'] = time.time() - start_time
        print(f"  ❌ Unified import failed: {type(e).__name__}: {e}")
    
    return results


def test_circular_import_resistance() -> Dict[str, Any]:
    """Test resistance to circular import patterns."""
    print("\n🔄 Testing circular import resistance...")
    
    results = {
        'success': True,
        'import_scenarios': [],
        'total_scenarios': 0,
        'successful_scenarios': 0
    }
    
    # Test different import orders that previously caused issues
    import_scenarios = [
        # Scenario 1: exceptions_service first
        ['netra_backend.app.core.exceptions_service', 'netra_backend.app.core.exceptions_agent', 'netra_backend.app.core.exceptions'],
        # Scenario 2: exceptions_agent first  
        ['netra_backend.app.core.exceptions_agent', 'netra_backend.app.core.exceptions_service', 'netra_backend.app.core.exceptions'],
        # Scenario 3: unified exceptions first
        ['netra_backend.app.core.exceptions', 'netra_backend.app.core.exceptions_service', 'netra_backend.app.core.exceptions_agent'],
    ]
    
    results['total_scenarios'] = len(import_scenarios)
    
    for i, scenario_modules in enumerate(import_scenarios):
        scenario_result = {
            'scenario': i + 1,
            'modules': scenario_modules,
            'success': False,
            'duration': 0,
            'error': None
        }
        
        start_time = time.time()
        try:
            # Clean slate - remove all exception modules
            modules_to_clean = [m for m in sys.modules.keys() if 'exceptions' in m and 'netra_backend' in m]
            for module in modules_to_clean:
                del sys.modules[module]
            
            # Import in specified order
            for module_name in scenario_modules:
                importlib.import_module(module_name)
            
            # Test that ServiceError is accessible
            from netra_backend.app.core.exceptions_service import ServiceError
            test_error = ServiceError(f"Scenario {i+1} test")
            
            scenario_result['success'] = True
            scenario_result['duration'] = time.time() - start_time
            results['successful_scenarios'] += 1
            print(f"  ✅ Scenario {i+1}: import order successful")
            
        except Exception as e:
            scenario_result['success'] = False
            scenario_result['error'] = {
                'type': type(e).__name__,
                'message': str(e)
            }
            scenario_result['duration'] = time.time() - start_time
            results['success'] = False
            print(f"  ❌ Scenario {i+1}: {type(e).__name__}: {e}")
        
        results['import_scenarios'].append(scenario_result)
    
    return results


def test_performance_benchmarks() -> Dict[str, Any]:
    """Test import performance to detect regressions."""
    print("\n⚡ Testing import performance...")
    
    results = {
        'success': True,
        'benchmarks': [],
        'average_import_time': 0,
        'slowest_import': None,
        'fastest_import': None
    }
    
    # Run multiple import cycles to get accurate timing
    num_cycles = 10
    import_times = []
    
    for cycle in range(num_cycles):
        # Clean imports
        modules_to_clean = [m for m in sys.modules.keys() if 'exceptions' in m and 'netra_backend' in m]
        for module in modules_to_clean:
            del sys.modules[module]
        
        start_time = time.time()
        try:
            from netra_backend.app.core.exceptions import ServiceError
            test_error = ServiceError("Performance test")
            duration = time.time() - start_time
            import_times.append(duration)
            
        except Exception as e:
            results['success'] = False
            print(f"  ❌ Performance test cycle {cycle+1} failed: {e}")
            return results
    
    if import_times:
        results['average_import_time'] = sum(import_times) / len(import_times)
        results['slowest_import'] = max(import_times)
        results['fastest_import'] = min(import_times)
        
        print(f"  📊 Import timing over {num_cycles} cycles:")
        print(f"    Average: {results['average_import_time']:.4f}s")
        print(f"    Fastest: {results['fastest_import']:.4f}s")
        print(f"    Slowest: {results['slowest_import']:.4f}s")
        
        # Flag if imports are unusually slow (> 1 second indicates potential issues)
        if results['average_import_time'] > 1.0:
            print(f"  ⚠️ Warning: Average import time is slow ({results['average_import_time']:.4f}s)")
        else:
            print(f"  ✅ Import performance is acceptable")
    
    return results


def generate_comprehensive_report(test_results: Dict[str, Any]) -> None:
    """Generate comprehensive stability assessment report."""
    print("\n" + "="*80)
    print("📋 SERVICEERROR IMPORTERROR FIX STABILITY ASSESSMENT")
    print("="*80)
    
    overall_success = all(result['success'] for result in test_results.values())
    
    print(f"\n🎯 OVERALL ASSESSMENT: {'✅ STABLE' if overall_success else '❌ UNSTABLE'}")
    
    print(f"\n📊 TEST RESULTS SUMMARY:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    # Detailed findings
    print(f"\n🔍 DETAILED FINDINGS:")
    
    # Import results
    if 'direct_imports' in test_results:
        import_result = test_results['direct_imports']
        print(f"  Direct Imports: {import_result['successful_imports']}/{import_result['total_modules']} modules successful")
    
    # Instantiation results
    if 'instantiation' in test_results:
        inst_result = test_results['instantiation']
        print(f"  Class Instantiation: {inst_result['successful_instantiations']}/{inst_result['total_classes']} classes successful")
    
    # Circular import resistance
    if 'circular_imports' in test_results:
        circular_result = test_results['circular_imports']
        print(f"  Circular Import Resistance: {circular_result['successful_scenarios']}/{circular_result['total_scenarios']} scenarios successful")
    
    # Performance
    if 'performance' in test_results:
        perf_result = test_results['performance']
        if perf_result['success']:
            print(f"  Import Performance: {perf_result['average_import_time']:.4f}s average")
    
    print(f"\n🚀 PRODUCTION READINESS ASSESSMENT:")
    
    if overall_success:
        print("  ✅ All ServiceError ImportError fixes are functioning correctly")
        print("  ✅ No circular import issues detected")
        print("  ✅ Exception classes instantiate and work properly")
        print("  ✅ System is stable for production deployment")
        
        # Performance assessment
        if 'performance' in test_results and test_results['performance']['success']:
            avg_time = test_results['performance']['average_import_time']
            if avg_time < 0.1:
                print("  ✅ Excellent import performance")
            elif avg_time < 0.5:
                print("  ✅ Good import performance")  
            else:
                print("  ⚠️ Import performance could be optimized")
        
        print(f"\n🎉 RECOMMENDATION: DEPLOY - ServiceError fixes are production-ready")
        
    else:
        print("  ❌ Critical issues detected that prevent production deployment")
        print("  ❌ ServiceError ImportError fixes require additional work")
        
        # Specific failure analysis
        for test_name, result in test_results.items():
            if not result['success']:
                print(f"  🔧 Fix required: {test_name}")
        
        print(f"\n⚠️ RECOMMENDATION: DO NOT DEPLOY - Address failures first")
    
    print("="*80)


def main():
    """Main validation execution."""
    print("[VALIDATION] Starting comprehensive ServiceError ImportError fix validation...")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")
    
    test_start_time = time.time()
    
    # Run all validation tests
    test_results = {}
    
    try:
        test_results['direct_imports'] = test_direct_exception_imports()
        test_results['instantiation'] = test_exception_class_instantiation()
        test_results['unified_import'] = test_unified_exceptions_import()
        test_results['circular_imports'] = test_circular_import_resistance()
        test_results['performance'] = test_performance_benchmarks()
        
    except Exception as e:
        print(f"\n❌ CRITICAL: Validation suite failed with exception: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Generate comprehensive report
    generate_comprehensive_report(test_results)
    
    total_duration = time.time() - test_start_time
    print(f"\n⏱️ Total validation time: {total_duration:.2f} seconds")
    
    # Exit with appropriate code
    overall_success = all(result['success'] for result in test_results.values())
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()