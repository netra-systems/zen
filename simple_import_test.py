#!/usr/bin/env python3
"""
Simple Import Test for Issue #1176 Validation
Tests basic imports to ensure no breaking changes were introduced.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def test_unified_test_runner_import():
    """Test that unified test runner can be imported."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "tests"))
        from unified_test_runner import UnifiedTestRunner
        print("✅ UnifiedTestRunner imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import UnifiedTestRunner: {e}")
        return False

def test_validation_method_exists():
    """Test that validation method exists and has correct signature."""
    try:
        from unified_test_runner import UnifiedTestRunner
        runner = UnifiedTestRunner()

        # Check if validation method exists
        if hasattr(runner, '_validate_test_execution_success'):
            print("✅ _validate_test_execution_success method exists")

            # Try to call with dummy parameters
            result = runner._validate_test_execution_success(
                initial_success=True,
                stdout="test output",
                stderr="",
                service="test",
                category_name="test"
            )
            print(f"✅ Validation method callable, returned: {result}")
            return True
        else:
            print("❌ _validate_test_execution_success method missing")
            return False
    except Exception as e:
        print(f"❌ Error testing validation method: {e}")
        return False

def test_base_test_case_import():
    """Test that base test case can be imported."""
    try:
        from test_framework.ssot.base_test_case import SSotBaseTestCase
        print("✅ SSotBaseTestCase imported successfully")

        # Try to instantiate
        test_case = SSotBaseTestCase()
        print("✅ SSotBaseTestCase instantiated successfully")
        return True
    except Exception as e:
        print(f"❌ Failed with base test case: {e}")
        return False

def test_isolated_environment_integration():
    """Test that isolated environment integration works."""
    try:
        from test_framework.ssot.base_test_case import SSotBaseTestCase
        test_case = SSotBaseTestCase()

        # Check if env property works
        if hasattr(test_case, 'env'):
            env = test_case.env
            print(f"✅ Environment integration works: {type(env)}")
            return True
        else:
            print("❌ Environment property not available")
            return False
    except Exception as e:
        print(f"❌ Environment integration failed: {e}")
        return False

def main():
    print("=" * 60)
    print("SIMPLE IMPORT VALIDATION TEST")
    print("=" * 60)

    tests = [
        ("Unified Test Runner Import", test_unified_test_runner_import),
        ("Validation Method Exists", test_validation_method_exists),
        ("Base Test Case Import", test_base_test_case_import),
        ("Environment Integration", test_isolated_environment_integration)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 40)
        try:
            success = test_func()
            results.append(success)
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)

    passed = sum(results)
    total = len(results)

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 ALL IMPORTS SUCCESSFUL - No breaking changes detected!")
    else:
        print("⚠️ IMPORT ISSUES DETECTED - May need investigation")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)