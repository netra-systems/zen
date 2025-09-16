#!/usr/bin/env python3
"""
Test script to verify core WebSocket functionality is not broken
by Issue #1090 fix.
"""
import sys
import os
import asyncio
import warnings

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_websocket_manager_import():
    """Test that WebSocketManager can be imported and instantiated"""
    try:
        # Test specific module imports (should not trigger warnings)
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        
        print("✓ WebSocketManager import successful")
        
        # Test instantiation with mock context
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )
        
        manager = WebSocketManager(user_context=context)
        print("✓ WebSocketManager instantiation successful")
        
        # Test basic attributes
        assert hasattr(manager, 'user_context')
        assert hasattr(manager, 'connection_registry')
        print("✓ WebSocketManager has expected attributes")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocketManager test failed: {e}")
        return False

def test_websocket_emitter_import():
    """Test that WebSocket emitter can be imported"""
    try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        print("✓ UnifiedWebSocketEmitter import successful")
        
        # Test critical events are available
        critical_events = UnifiedWebSocketEmitter.CRITICAL_EVENTS
        assert isinstance(critical_events, list)
        print(f"✓ Critical events available: {critical_events}")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocket emitter test failed: {e}")
        return False

def test_websocket_types_import():
    """Test that WebSocket types can be imported"""
    try:
        from netra_backend.app.websocket_core.types import (
            WebSocketConnection,
            WebSocketManagerMode,
            MessageType
        )
        print("✓ WebSocket types import successful")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket types test failed: {e}")
        return False

def test_websocket_init_import():
    """Test that __init__.py import works and triggers warnings correctly"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # This should trigger Issue #1144 warning
        from netra_backend.app.websocket_core import WebSocketManager as WSM
        
        # Check for warnings
        issue_1144_warnings = [warning for warning in w if "ISSUE #1144" in str(warning.message)]
        
        if issue_1144_warnings:
            print("✓ Issue #1144 warning correctly triggered for direct import")
            return True
        else:
            print("❌ Issue #1144 warning NOT triggered for direct import")
            return False

def main():
    """Run all core functionality tests"""
    print("Testing core WebSocket functionality after Issue #1090 fix...")
    print("=" * 60)
    
    tests = [
        test_websocket_manager_import,
        test_websocket_emitter_import,
        test_websocket_types_import,
        test_websocket_init_import
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n{test.__name__}:")
        if test():
            passed += 1
        else:
            print(f"  Failed!")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All core WebSocket functionality tests PASSED")
        return 0
    else:
        print("❌ Some core WebSocket functionality tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())