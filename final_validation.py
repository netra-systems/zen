#!/usr/bin/env python3
"""Final validation that test framework imports are fixed."""

import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=== FINAL VALIDATION ===")

def test_critical_imports():
    """Test the most critical imports needed by unified test runner."""

    tests = [
        ("test_framework", lambda: __import__('test_framework')),
        ("test_framework.ssot", lambda: __import__('test_framework.ssot', fromlist=[''])),
        ("BaseTestCase from ssot", lambda: getattr(__import__('test_framework.ssot', fromlist=['BaseTestCase']), 'BaseTestCase')),
        ("UnifiedDockerManager", lambda: getattr(__import__('test_framework.unified_docker_manager', fromlist=['UnifiedDockerManager']), 'UnifiedDockerManager')),
        ("test_config", lambda: __import__('test_framework.test_config', fromlist=[''])),
        ("CategoryConfigLoader", lambda: getattr(__import__('test_framework.config.category_config', fromlist=['CategoryConfigLoader']), 'CategoryConfigLoader')),
    ]

    all_passed = True

    for description, test_func in tests:
        try:
            result = test_func()
            print(f"✅ {description}")
        except Exception as e:
            print(f"❌ {description}: {e}")
            all_passed = False

    return all_passed

def test_unified_test_runner():
    """Test if unified test runner can be imported."""
    try:
        import tests.unified_test_runner
        print("✅ unified_test_runner import")
        return True
    except Exception as e:
        print(f"❌ unified_test_runner import: {e}")
        return False

if __name__ == "__main__":
    critical_passed = test_critical_imports()
    runner_passed = test_unified_test_runner()

    print(f"\n=== RESULTS ===")
    print(f"Critical imports: {'✅ PASS' if critical_passed else '❌ FAIL'}")
    print(f"Unified test runner: {'✅ PASS' if runner_passed else '❌ FAIL'}")

    if critical_passed and runner_passed:
        print("\n🎉 SUCCESS! Test framework imports are now working!")
        print("You can now run: python tests/unified_test_runner.py --help")
    else:
        print("\n⚠️  Some issues remain. Check the failures above.")

    sys.exit(0 if critical_passed and runner_passed else 1)