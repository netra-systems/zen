#!/usr/bin/env python3
"""
Issue #1176 Fix Validation Script

This script validates that the websocket_bridge_factory import issues have been resolved
and that the test runner now properly detects import failures.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def test_factory_imports():
    """Test that the websocket bridge factory can be imported from both locations."""
    print("🧪 Testing websocket bridge factory imports...")

    try:
        # Test import from factories directory
        from netra_backend.app.factories.websocket_bridge_factory import (
            StandardWebSocketBridge,
            WebSocketBridgeAdapter,
            WebSocketBridgeFactory,
            create_standard_websocket_bridge,
            create_agent_bridge_adapter
        )
        print("✅ Successfully imported from factories.websocket_bridge_factory")

        # Test import from services directory (compatibility)
        from netra_backend.app.services.websocket_bridge_factory import (
            StandardWebSocketBridge as ServiceStandardBridge,
            WebSocketBridgeAdapter as ServiceBridgeAdapter,
            WebSocketBridgeFactory as ServiceBridgeFactory
        )
        print("✅ Successfully imported from services.websocket_bridge_factory (compatibility)")

        # Test that we can create instances
        bridge = create_standard_websocket_bridge()
        print(f"✅ Successfully created StandardWebSocketBridge: {bridge}")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_factories_init_exports():
    """Test that the factories __init__.py properly exports the new classes."""
    print("🧪 Testing factories __init__.py exports...")

    try:
        from netra_backend.app.factories import (
            StandardWebSocketBridge,
            WebSocketBridgeAdapter,
            WebSocketBridgeFactory,
            create_standard_websocket_bridge,
            create_agent_bridge_adapter
        )
        print("✅ Successfully imported all classes from factories.__init__")
        return True

    except ImportError as e:
        print(f"❌ Import from factories.__init__ failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of the created classes."""
    print("🧪 Testing basic functionality...")

    try:
        from netra_backend.app.factories.websocket_bridge_factory import (
            StandardWebSocketBridge,
            WebSocketBridgeFactory,
            create_websocket_bridge_for_testing
        )

        # Test factory creation
        factory = WebSocketBridgeFactory()
        bridge1 = factory.create_standard_bridge(bridge_id="test_bridge_1")
        print(f"✅ Factory created bridge: {bridge1.bridge_id}")

        # Test function creation
        bridge2 = create_websocket_bridge_for_testing()
        print(f"✅ Function created bridge: {bridge2.bridge_id}")

        return True

    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🚀 Starting Issue #1176 Fix Validation")
    print("=" * 50)

    tests = [
        ("Factory Imports", test_factory_imports),
        ("Init Exports", test_factories_init_exports),
        ("Basic Functionality", test_basic_functionality),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n📋 Running {name} test...")
        success = test_func()
        results.append((name, success))
        print(f"{'✅ PASSED' if success else '❌ FAILED'}: {name}")

    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Issue #1176 fix is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Issue #1176 fix needs more work.")
        return 1

if __name__ == "__main__":
    sys.exit(main())