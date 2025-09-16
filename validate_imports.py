#!/usr/bin/env python3
"""Validate that test framework imports are working"""

import sys
from pathlib import Path

# Ensure we can import the project
sys.path.insert(0, str(Path(__file__).parent))

def test_import(description, import_func):
    try:
        result = import_func()
        print(f"✅ {description}: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ {description}: FAILED - {e}")
        return False

def test_basic_imports():
    print("=== TESTING BASIC IMPORTS ===")

    success = True

    # Test basic test_framework import
    success &= test_import(
        "test_framework module",
        lambda: __import__('test_framework')
    )

    # Test specific SSOT imports
    success &= test_import(
        "test_framework.ssot module",
        lambda: __import__('test_framework.ssot', fromlist=[''])
    )

    # Test BaseTestCase import
    success &= test_import(
        "BaseTestCase from ssot",
        lambda: getattr(__import__('test_framework.ssot', fromlist=['BaseTestCase']), 'BaseTestCase')
    )

    # Test UnifiedDockerManager
    success &= test_import(
        "UnifiedDockerManager",
        lambda: getattr(__import__('test_framework', fromlist=['UnifiedDockerManager']), 'UnifiedDockerManager')
    )

    return success

def test_unified_test_runner_imports():
    print("\n=== TESTING UNIFIED TEST RUNNER IMPORTS ===")

    success = True

    # Test imports from unified test runner
    test_imports = [
        ('test_framework.test_config', 'configure_dev_environment'),
        ('test_framework.llm_config_manager', 'configure_llm_testing'),
        ('test_framework.test_discovery', 'TestDiscovery'),
        ('test_framework.test_validation', 'TestValidation'),
        ('test_framework.category_system', 'CategorySystem'),
    ]

    for module, attr in test_imports:
        success &= test_import(
            f"{module}.{attr}",
            lambda m=module, a=attr: getattr(__import__(m, fromlist=[a]), a)
        )

    return success

if __name__ == "__main__":
    print("Testing test_framework imports...")

    basic_success = test_basic_imports()
    unified_success = test_unified_test_runner_imports()

    overall_success = basic_success and unified_success

    print(f"\n=== SUMMARY ===")
    print(f"Basic imports: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"Unified test runner imports: {'✅ PASS' if unified_success else '❌ FAIL'}")
    print(f"Overall: {'✅ ALL IMPORTS WORKING' if overall_success else '❌ IMPORTS STILL FAILING'}")

    if overall_success:
        print("\n🎉 Test framework imports are now working!")
        print("You can now run: python tests/unified_test_runner.py --help")
    else:
        print("\n⚠️  Some imports still failing. Check the errors above.")

    sys.exit(0 if overall_success else 1)