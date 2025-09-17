#!/usr/bin/env python3
"""
Simple startup test to verify our Issue #1177 fixes don't break imports or basic functionality.
This tests imports and basic initialization without requiring Docker or full services.
"""

import sys
import traceback

def test_critical_imports():
    """Test that critical imports still work after our changes."""
    try:
        # Test Redis manager imports
        from netra_backend.app.redis_manager import RedisManager, get_redis_manager
        print("✅ Redis manager imports successful")

        # Test backend environment imports
        from netra_backend.app.core.backend_environment import BackendEnvironment
        print("✅ Backend environment imports successful")

        # Test isolation environment imports
        from shared.isolated_environment import get_env
        print("✅ Isolated environment imports successful")

        # Test SSOT test framework imports
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        print("✅ SSOT test framework imports successful")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        traceback.print_exc()
        return False

def test_basic_initialization():
    """Test basic initialization of core components."""
    try:
        # Test backend environment initialization
        from netra_backend.app.core.backend_environment import BackendEnvironment
        backend_env = BackendEnvironment()
        redis_url = backend_env.get_redis_url()
        print(f"✅ Backend environment initialization successful: {redis_url}")

        # Test Redis manager initialization (without connecting)
        from netra_backend.app.redis_manager import RedisManager
        redis_manager = RedisManager()
        status = redis_manager.get_status()
        print(f"✅ Redis manager initialization successful: {status['connected']}")

        return True

    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        traceback.print_exc()
        return False

def test_configuration_access():
    """Test that configuration access patterns work."""
    try:
        # Test environment access
        from shared.isolated_environment import get_env
        env = get_env()
        print(f"✅ Environment access successful: {len(env)} variables available")

        # Test configuration loading
        from netra_backend.app.config import get_config
        config = get_config()
        print(f"✅ Configuration loading successful: {type(config)}")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all startup tests."""
    print("🚀 Running Issue #1177 startup validation tests...")

    tests = [
        ("Critical Imports", test_critical_imports),
        ("Basic Initialization", test_basic_initialization),
        ("Configuration Access", test_configuration_access)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        success = test_func()
        results.append((test_name, success))

    print(f"\n📊 Test Results Summary:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(success for _, success in results)

    if all_passed:
        print("\n🎉 All startup tests passed! Issue #1177 fixes do not break existing functionality.")
        return 0
    else:
        print("\n❌ Some startup tests failed! Issue #1177 fixes may have introduced problems.")
        return 1

if __name__ == "__main__":
    sys.exit(main())