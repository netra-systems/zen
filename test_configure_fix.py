#!/usr/bin/env python3
"""
Test script to verify that the AgentWebSocketBridge configure method fix works correctly.
This addresses Issue #1339 - AgentWebSocketBridge missing 'configure' attribute.
"""

import sys
import traceback

def test_configure_method_exists():
    """Test that the configure method exists on AgentWebSocketBridge."""
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

        bridge = AgentWebSocketBridge()

        # Test that configure method exists
        assert hasattr(bridge, 'configure'), "AgentWebSocketBridge should have a configure method"

        # Test that we can call configure with expected parameters
        bridge.configure(
            connection_pool=None,
            agent_registry=None,
            health_monitor=None
        )

        print("✓ PASS: configure method exists and can be called")
        return True

    except Exception as e:
        print(f"✗ FAIL: {e}")
        print(traceback.format_exc())
        return False

def test_factory_initialization_scenario():
    """Test the exact factory initialization scenario that was failing."""
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool

        # Create instances like the factory does
        bridge = AgentWebSocketBridge()
        connection_pool = WebSocketConnectionPool()

        # This is the exact call that was failing in dependencies.py:2086-2090
        bridge.configure(
            connection_pool=connection_pool,
            agent_registry=None,  # getattr(app.state, 'agent_registry', None) becomes None in test
            health_monitor=None   # Explicit None as in original code
        )

        print("✓ PASS: Factory initialization scenario works")
        return True

    except Exception as e:
        print(f"✗ FAIL: Factory initialization failed: {e}")
        print(traceback.format_exc())
        return False

def test_method_signature_compatibility():
    """Test that the configure method signature matches what's expected."""
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        import inspect

        bridge = AgentWebSocketBridge()
        configure_method = getattr(bridge, 'configure')

        # Get method signature
        sig = inspect.signature(configure_method)
        params = list(sig.parameters.keys())

        # Expected parameters based on dependencies.py usage
        expected_params = ['connection_pool', 'agent_registry', 'health_monitor']

        for param in expected_params:
            assert param in params, f"Expected parameter '{param}' not found in configure method"

        print("✓ PASS: Method signature is compatible")
        return True

    except Exception as e:
        print(f"✗ FAIL: Method signature test failed: {e}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Testing AgentWebSocketBridge configure method fix...")
    print("=" * 60)

    tests = [
        test_configure_method_exists,
        test_factory_initialization_scenario,
        test_method_signature_compatibility
    ]

    passed = 0
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 ALL TESTS PASSED - Issue #1339 is RESOLVED!")
        sys.exit(0)
    else:
        print("❌ Some tests failed - Issue #1339 needs more work")
        sys.exit(1)