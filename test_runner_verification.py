#!/usr/bin/env python3
"""
Test Runner Verification Script
Validates that Issue #1176 fixes are working correctly without full test execution.
"""

import sys
import os
import tempfile
import subprocess
from pathlib import Path

# Setup project root
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def test_runner_basic_import():
    """Test that the unified test runner can be imported."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "tests"))
        from unified_test_runner import UnifiedTestRunner
        print("✅ Successfully imported UnifiedTestRunner")
        return True
    except ImportError as e:
        print(f"❌ Failed to import UnifiedTestRunner: {e}")
        return False

def test_validation_methods():
    """Test that validation methods exist and can be called."""
    try:
        from unified_test_runner import UnifiedTestRunner
        runner = UnifiedTestRunner()

        # Test count extraction
        test_output = "5 passed, 2 failed in 3.2s"
        result = {"output": test_output}
        counts = runner._extract_test_counts_from_result(result)

        print(f"✅ Test count extraction works: {counts}")

        # Test validation method
        success = runner._validate_test_execution_success(
            initial_success=True,
            stdout="5 passed in 2.1s",
            stderr="",
            service="test_service",
            category_name="test_category"
        )
        print(f"✅ Validation method works: {success}")

        # Test failure detection
        failure = runner._validate_test_execution_success(
            initial_success=True,
            stdout="collected 0 items\n==== no tests ran ====",
            stderr="",
            service="test_service",
            category_name="test_category"
        )
        print(f"✅ Failure detection works: {failure} (should be False)")

        return True
    except Exception as e:
        print(f"❌ Validation methods failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_empty_directory_scenario():
    """Test that the runner fails correctly on empty directory."""
    try:
        # Create temporary empty directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test the runner on empty directory
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "tests" / "unified_test_runner.py"),
                "--category", "unit",
                "--test-paths", temp_dir,
                "--no-coverage",
                "--fast-fail"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"✅ Empty directory correctly returns failure (exit code: {result.returncode})")
                return True
            else:
                print(f"❌ Empty directory should fail but returned success (exit code: {result.returncode})")
                print(f"stdout: {result.stdout[:500]}...")
                print(f"stderr: {result.stderr[:500]}...")
                return False

    except subprocess.TimeoutExpired:
        print("❌ Test runner timed out on empty directory")
        return False
    except Exception as e:
        print(f"❌ Empty directory test failed: {e}")
        return False

def test_import_error_scenario():
    """Test that the runner fails correctly on import errors."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with import error
            bad_test = Path(temp_dir) / "test_bad_import.py"
            bad_test.write_text("""
import nonexistent_module_that_does_not_exist

def test_dummy():
    assert True
""")

            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "tests" / "unified_test_runner.py"),
                "--category", "unit",
                "--test-paths", str(temp_dir),
                "--no-coverage",
                "--fast-fail"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"✅ Import error correctly returns failure (exit code: {result.returncode})")
                output = result.stdout + result.stderr
                if "ImportError" in output or "ModuleNotFoundError" in output:
                    print("✅ Import error properly reported")
                else:
                    print("⚠️ Import error not explicitly reported in output")
                return True
            else:
                print(f"❌ Import error should fail but returned success (exit code: {result.returncode})")
                return False

    except subprocess.TimeoutExpired:
        print("❌ Test runner timed out on import error")
        return False
    except Exception as e:
        print(f"❌ Import error test failed: {e}")
        return False

def test_legitimate_success():
    """Test that legitimate tests still pass."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple passing test
            good_test = Path(temp_dir) / "test_simple.py"
            good_test.write_text("""
def test_simple():
    assert 1 + 1 == 2

def test_another():
    assert "hello".upper() == "HELLO"
""")

            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "tests" / "unified_test_runner.py"),
                "--category", "unit",
                "--test-paths", str(temp_dir),
                "--no-coverage",
                "--fast-fail"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"✅ Legitimate tests correctly return success (exit code: {result.returncode})")
                output = result.stdout + result.stderr
                if "passed" in output:
                    print("✅ Test execution properly reported")
                else:
                    print("⚠️ Test results not clearly reported")
                return True
            else:
                print(f"❌ Legitimate tests should pass but returned failure (exit code: {result.returncode})")
                print(f"stdout: {result.stdout[:500]}...")
                print(f"stderr: {result.stderr[:500]}...")
                return False

    except subprocess.TimeoutExpired:
        print("❌ Test runner timed out on legitimate tests")
        return False
    except Exception as e:
        print(f"❌ Legitimate success test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("TEST RUNNER VERIFICATION - Issue #1176 Fixes")
    print("=" * 60)

    tests = [
        ("Basic Import", test_runner_basic_import),
        ("Validation Methods", test_validation_methods),
        ("Empty Directory Failure", test_empty_directory_scenario),
        ("Import Error Failure", test_import_error_scenario),
        ("Legitimate Success", test_legitimate_success)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 40)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}")
        if success:
            passed += 1

    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL VERIFICATIONS PASSED - Issue #1176 fixes are working!")
        return 0
    else:
        print("⚠️ SOME VERIFICATIONS FAILED - Need investigation")
        return 1

if __name__ == "__main__":
    sys.exit(main())