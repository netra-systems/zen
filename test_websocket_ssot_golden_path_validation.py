#!/usr/bin/env python3
"""
Test script to validate WebSocket Manager SSOT functionality during Issue #712 remediation.
This ensures we don't break the Golden Path while fixing validation gaps.
"""

import asyncio
import sys
import traceback
from typing import Dict, Any

def test_basic_ssot_redirection():
    """Test that basic SSOT redirection works (Golden Path protection)."""
    print("Testing basic SSOT redirection...")

    try:
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, UnifiedWebSocketManager

        # Check that alias works
        same_class = WebSocketManager is UnifiedWebSocketManager
        print(f"   WebSocketManager alias: {'PASS' if same_class else 'FAIL'}")

        if same_class:
            print(f"   SSOT redirection working: {WebSocketManager}")
            return True
        else:
            print(f"   SSOT redirection broken: {WebSocketManager} != {UnifiedWebSocketManager}")
            return False

    except Exception as e:
        print(f"   Import error: {e}")
        return False

def test_factory_functionality():
    """Test that factory creates proper instances."""
    print("Testing factory functionality...")

    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager_sync
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

        # Create a test manager with proper user ID format
        manager = create_websocket_manager_sync(user_id="test_12345678")

        # Check if it's the right type
        is_correct_type = isinstance(manager, UnifiedWebSocketManager)
        print(f"   Factory creates correct type: {'PASS' if is_correct_type else 'FAIL'}")

        return is_correct_type

    except Exception as e:
        print(f"   Factory error: {e}")
        traceback.print_exc()
        return False

async def test_websocket_manager_creation():
    """Test async WebSocket manager creation."""
    print("Testing async WebSocket manager creation...")

    try:
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketManagerMode

        # Test with test mode
        manager = await get_websocket_manager(user_context=None, mode=WebSocketManagerMode.ISOLATED)

        is_correct_type = isinstance(manager, UnifiedWebSocketManager)
        print(f"   Async creation works: {'PASS' if is_correct_type else 'FAIL'}")

        return is_correct_type

    except Exception as e:
        print(f"   Async creation error: {e}")
        traceback.print_exc()
        return False

def test_import_paths():
    """Test that all expected import paths work."""
    print("Testing import paths...")

    import_tests = [
        ("netra_backend.app.websocket_core.websocket_manager", "WebSocketManager"),
        ("netra_backend.app.websocket_core.unified_manager", "UnifiedWebSocketManager"),
        ("netra_backend.app.websocket_core.websocket_manager_factory", "create_websocket_manager"),
    ]

    success_count = 0
    for module_path, class_name in import_tests:
        try:
            module = __import__(module_path, fromlist=[class_name])
            obj = getattr(module, class_name)
            print(f"   {module_path}.{class_name}: PASS")
            success_count += 1
        except Exception as e:
            print(f"   {module_path}.{class_name}: FAIL - {e}")

    return success_count == len(import_tests)

async def main():
    """Run all Golden Path validation tests."""
    print("Starting WebSocket SSOT Golden Path validation...")
    print("=" * 60)

    tests = [
        ("Basic SSOT Redirection", test_basic_ssot_redirection()),
        ("Import Paths", test_import_paths()),
        ("Factory Functionality", test_factory_functionality()),
        ("Async Manager Creation", await test_websocket_manager_creation()),
    ]

    passed = 0
    total = len(tests)

    print("\nTest Results:")
    print("=" * 60)

    for test_name, result in tests:
        status = "PASS" if result else "FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print("=" * 60)
    print(f"Golden Path Status: {passed}/{total} tests passed")

    if passed == total:
        print("Golden Path functionality is protected!")
        return True
    else:
        print("Golden Path has issues that need attention!")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)