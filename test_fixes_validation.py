#!/usr/bin/env python3
"""
Test script to validate the BaseTestCase and async fixture fixes.
This script tests the specific issues that were causing failures.
"""

import asyncio
import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_base_test_case_import():
    """Test 1: BaseTestCase import fix"""
    print("=== Test 1: BaseTestCase Import ===")
    try:
        from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
        print("✅ PASS: BaseTestCase imports successful")
        return True
    except Exception as e:
        print(f"❌ FAIL: BaseTestCase import failed: {e}")
        traceback.print_exc()
        return False

def test_async_test_case_instantiation():
    """Test 2: AsyncTestCase instantiation fix"""
    print("\n=== Test 2: AsyncTestCase Instantiation ===")
    try:
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        
        # This should work without __init__ issues
        test_instance = SSotAsyncTestCase()
        print("✅ PASS: AsyncTestCase instantiation successful")
        return True
    except Exception as e:
        print(f"❌ FAIL: AsyncTestCase instantiation failed: {e}")
        traceback.print_exc()
        return False

def test_setup_method_execution():
    """Test 3: setup_method execution"""
    print("\n=== Test 3: setup_method Execution ===")
    try:
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        
        test_instance = SSotAsyncTestCase()
        
        # Mock method object
        class MockMethod:
            def __init__(self, name):
                self.__name__ = name
        
        # This should work without crashing
        test_instance.setup_method(MockMethod("test_mock"))
        
        # Verify environment was set up
        if hasattr(test_instance, '_env') and hasattr(test_instance, '_metrics'):
            print("✅ PASS: setup_method execution successful")
            return True
        else:
            print("❌ FAIL: setup_method did not initialize properly")
            return False
    except Exception as e:
        print(f"❌ FAIL: setup_method execution failed: {e}")
        traceback.print_exc()
        return False

def test_async_fixture_compatibility():
    """Test 4: Async fixture compatibility"""
    print("\n=== Test 4: Async Fixture Compatibility ===")
    try:
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        
        test_instance = SSotAsyncTestCase()
        
        # Test the event_loop fixture method
        if hasattr(test_instance, 'event_loop'):
            print("✅ PASS: event_loop fixture method available")
        else:
            print("⚠️  INFO: event_loop fixture not found (this is acceptable)")
        
        # Test async execution helper
        async def dummy_coro():
            return "test_result"
        
        # This should work without nested event loop issues
        result = test_instance.safe_run_async(dummy_coro())
        
        if result == "test_result":
            print("✅ PASS: safe_run_async works correctly")
            return True
        else:
            print(f"❌ FAIL: safe_run_async returned unexpected result: {result}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Async fixture compatibility failed: {e}")
        traceback.print_exc()
        return False

def test_unittest_compatibility():
    """Test 5: unittest compatibility layer"""
    print("\n=== Test 5: unittest Compatibility ===")
    try:
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        
        test_instance = SSotAsyncTestCase()
        
        # Test unittest-style methods are available
        required_methods = [
            'setUp', 'tearDown', 'assertEqual', 'assertIsNone', 
            'assertIsNotNone', 'assertTrue', 'assertFalse'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(test_instance, method):
                missing_methods.append(method)
        
        if not missing_methods:
            print("✅ PASS: All unittest compatibility methods available")
            return True
        else:
            print(f"❌ FAIL: Missing unittest methods: {missing_methods}")
            return False
    except Exception as e:
        print(f"❌ FAIL: unittest compatibility test failed: {e}")
        traceback.print_exc()
        return False

def test_unified_test_runner_import():
    """Test 6: unified test runner import"""
    print("\n=== Test 6: Unified Test Runner Import ===")
    try:
        # Try to import the unified test runner
        sys.path.append('tests')
        from unified_test_runner import TestRunner
        print("✅ PASS: Unified test runner import successful")
        return True
    except Exception as e:
        print(f"❌ FAIL: Unified test runner import failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests"""
    print("🔬 Testing BaseTestCase and Async Fixture Fixes")
    print("=" * 60)
    
    tests = [
        test_base_test_case_import,
        test_async_test_case_instantiation,
        test_setup_method_execution,
        test_async_fixture_compatibility,
        test_unittest_compatibility,
        test_unified_test_runner_import
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ CRITICAL: Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Fixes are working!")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Review the errors above")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)