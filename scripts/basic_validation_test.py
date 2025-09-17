#!/usr/bin/env python3
"""Basic validation test for Issue #1176 implementation."""

import sys
import traceback

def test_basic_imports():
    """Test basic imports are working."""
    try:
        # Test basic WebSocket imports
        from netra_backend.app.websocket_core.types import WebSocketManagerMode
        print("✅ WebSocket types import successful")

        # Test protocols import
        from netra_backend.app.websocket_core.protocols import WebSocketProtocol
        print("✅ WebSocket protocols import successful")

        # Test standardized factory interface
        from netra_backend.app.websocket_core.standardized_factory_interface import (
            StandardizedWebSocketManagerFactory,
            get_standardized_websocket_manager_factory
        )
        print("✅ Standardized factory interface import successful")

        # Test agent bridge
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        print("✅ Agent WebSocket bridge import successful")

        return True

    except Exception as e:
        print(f"❌ Basic imports failed: {e}")
        traceback.print_exc()
        return False

def test_factory_creation():
    """Test factory creation without dependencies."""
    try:
        from netra_backend.app.websocket_core.standardized_factory_interface import (
            get_standardized_websocket_manager_factory
        )

        factory = get_standardized_websocket_manager_factory(require_user_context=False)
        print("✅ Factory creation successful")

        # Test factory interface
        if hasattr(factory, 'create_manager'):
            print("✅ Factory has create_manager method")
        else:
            print("❌ Factory missing create_manager method")
            return False

        if hasattr(factory, 'supports_user_isolation'):
            print("✅ Factory has supports_user_isolation method")
        else:
            print("❌ Factory missing supports_user_isolation method")
            return False

        return True

    except Exception as e:
        print(f"❌ Factory creation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run basic validation tests."""
    print("🚀 Running basic Issue #1176 validation tests...")
    print("=" * 50)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Factory Creation", test_factory_creation),
    ]

    passed = 0
    for name, test_func in tests:
        print(f"\n📋 Testing: {name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {name} PASSED")
            else:
                print(f"❌ {name} FAILED")
        except Exception as e:
            print(f"❌ {name} failed with exception: {e}")

    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)