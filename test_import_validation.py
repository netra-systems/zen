#!/usr/bin/env python3
"""Quick validation test for Issue #1176 fix - WebSocket bridge factory imports"""

def test_imports():
    """Test that all three import paths work correctly"""
    results = []

    # Test 1: factories import
    try:
        from netra_backend.app.factories.websocket_bridge_factory import StandardWebSocketBridge
        results.append("✅ factories.websocket_bridge_factory import successful")
    except Exception as e:
        results.append(f"❌ factories import failed: {e}")

    # Test 2: services import
    try:
        from netra_backend.app.services.websocket_bridge_factory import StandardWebSocketBridge
        results.append("✅ services.websocket_bridge_factory import successful")
    except Exception as e:
        results.append(f"❌ services import failed: {e}")

    # Test 3: websocket_core import
    try:
        from netra_backend.app.websocket_core.websocket_bridge_factory import StandardWebSocketBridge
        results.append("✅ websocket_core.websocket_bridge_factory import successful")
    except Exception as e:
        results.append(f"❌ websocket_core import failed: {e}")

    return results

if __name__ == "__main__":
    print("Issue #1176 Fix Validation - WebSocket Bridge Factory Imports")
    print("=" * 60)

    results = test_imports()
    for result in results:
        print(result)

    # Check if all imports succeeded
    success_count = sum(1 for r in results if r.startswith("✅"))
    total_count = len(results)

    print(f"\nSummary: {success_count}/{total_count} imports successful")

    if success_count == total_count:
        print("🎉 All imports working - Issue #1176 fix successful!")
        exit(0)
    else:
        print("⚠️  Some imports failed - Issue #1176 fix incomplete")
        exit(1)