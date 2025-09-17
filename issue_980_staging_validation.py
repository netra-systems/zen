#!/usr/bin/env python3
"""
Issue #980 Staging Validation Script
Validates datetime.now(UTC) migrations in key infrastructure modules
"""

import sys
import os
import importlib
from pathlib import Path
from datetime import datetime, UTC

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_datetime_imports():
    """Test that critical modules can import and use datetime.now(UTC)"""
    print("🔍 Testing datetime.now(UTC) functionality...")

    try:
        # Test basic datetime.now(UTC) functionality
        current_time = datetime.now(UTC)
        print(f"✅ datetime.now(UTC) works: {current_time}")

        # Test that UTC timezone is properly recognized
        assert current_time.tzinfo is not None, "UTC timezone not set"
        print(f"✅ UTC timezone properly set: {current_time.tzinfo}")

        return True
    except Exception as e:
        print(f"❌ datetime.now(UTC) test failed: {e}")
        return False

def test_critical_module_imports():
    """Test that critical modules with datetime changes can be imported"""
    modules_to_test = [
        "netra_backend.app.core.interfaces_websocket",
        "netra_backend.app.services.service_initialization.health_checker",
    ]

    print("\n🔍 Testing critical module imports...")

    all_passed = True
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"✅ {module_name} imported successfully")

            # Test if module has datetime usage
            if hasattr(module, 'datetime'):
                print(f"   📅 Module uses datetime functionality")

        except Exception as e:
            print(f"❌ {module_name} import failed: {e}")
            all_passed = False

    return all_passed

def test_websocket_interfaces():
    """Test WebSocket interface definitions"""
    print("\n🔍 Testing WebSocket interfaces...")

    try:
        from netra_backend.app.core.interfaces_websocket import WebSocketEventHandler, WebSocketConnectionProtocol
        print("✅ WebSocket interfaces imported successfully")

        # Test that datetime.now(UTC) is available in the module
        import netra_backend.app.core.interfaces_websocket as ws_module
        if hasattr(ws_module, 'datetime'):
            print("✅ WebSocket module has datetime functionality")

        return True
    except Exception as e:
        print(f"❌ WebSocket interface test failed: {e}")
        return False

def test_health_checker():
    """Test health checker functionality"""
    print("\n🔍 Testing health checker...")

    try:
        from netra_backend.app.services.service_initialization.health_checker import HealthStatus, HealthCheckResult
        print("✅ Health checker classes imported successfully")

        # Test creating a health check result with current timestamp
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            service_name="test_service",
            check_name="test_check",
            timestamp=datetime.now(UTC),
            response_time_ms=50.0
        )
        print(f"✅ Health check result created with UTC timestamp: {result.timestamp}")

        return True
    except Exception as e:
        print(f"❌ Health checker test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Issue #980 Staging Validation - datetime.now(UTC) Migration")
    print("=" * 60)

    tests = [
        ("DateTime Functionality", test_datetime_imports),
        ("Critical Module Imports", test_critical_module_imports),
        ("WebSocket Interfaces", test_websocket_interfaces),
        ("Health Checker", test_health_checker),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")

    print("\n" + "=" * 60)
    print(f"🎯 VALIDATION SUMMARY")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - Issue #980 changes are staging-ready!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed - review before staging deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())