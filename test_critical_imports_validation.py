#!/usr/bin/env python3
"""
Test script to validate that all critical imports continue to work correctly
after Issue #1090 fix.
"""
import sys
import os
import warnings

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_all_critical_imports():
    """Test all critical imports that should continue working"""
    
    successful_imports = []
    failed_imports = []
    
    # Test core WebSocket imports (should work without warnings)
    imports_to_test = [
        # Core manager
        ("netra_backend.app.websocket_core.websocket_manager", ["WebSocketManager", "UnifiedWebSocketManager"]),
        
        # Emitters 
        ("netra_backend.app.websocket_core.unified_emitter", ["UnifiedWebSocketEmitter", "WebSocketEmitterFactory"]),
        
        # Types
        ("netra_backend.app.websocket_core.types", ["WebSocketConnection", "MessageType", "WebSocketManagerMode"]),
        
        # Handlers
        ("netra_backend.app.websocket_core.handlers", ["MessageRouter", "UserMessageHandler"]),
        
        # Context
        ("netra_backend.app.websocket_core.context", ["WebSocketContext", "WebSocketRequestContext"]),
        
        # User context extractor
        ("netra_backend.app.websocket_core.user_context_extractor", ["UserContextExtractor", "extract_websocket_user_context"]),
        
        # Migration adapter
        ("netra_backend.app.websocket_core.migration_adapter", ["get_legacy_websocket_manager", "migrate_singleton_usage"]),
    ]
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        for module_name, import_names in imports_to_test:
            try:
                module = __import__(module_name, fromlist=import_names)
                
                # Test that we can get each import
                for import_name in import_names:
                    if hasattr(module, import_name):
                        successful_imports.append(f"{module_name}.{import_name}")
                    else:
                        failed_imports.append(f"{module_name}.{import_name} - not found")
                        
            except Exception as e:
                failed_imports.append(f"{module_name} - {str(e)}")
        
        # Check for Issue #1144 warnings (should not be present for specific imports)
        issue_1144_warnings = [warning for warning in w if "ISSUE #1144" in str(warning.message)]
        
        print(f"✅ Successful imports: {len(successful_imports)}")
        for imp in successful_imports:
            print(f"  - {imp}")
        
        if failed_imports:
            print(f"\n❌ Failed imports: {len(failed_imports)}")
            for imp in failed_imports:
                print(f"  - {imp}")
        
        if issue_1144_warnings:
            print(f"\n❌ Unexpected Issue #1144 warnings: {len(issue_1144_warnings)}")
            for warning in issue_1144_warnings:
                print(f"  - {warning.message}")
                
        return len(failed_imports) == 0 and len(issue_1144_warnings) == 0

def test_legacy_compatibility_imports():
    """Test that legacy compatibility is maintained"""
    
    print("\nTesting legacy compatibility imports...")
    
    try:
        # These should work as backward compatibility
        from netra_backend.app.websocket_core import create_websocket_manager
        from netra_backend.app.websocket_core import get_websocket_manager
        from netra_backend.app.websocket_core import WebSocketEventEmitter  # Backward compatibility alias
        
        print("✅ Legacy compatibility imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Legacy compatibility imports failed: {e}")
        return False

def test_critical_events_availability():
    """Test that critical events are still available"""
    
    print("\nTesting critical events availability...")
    
    try:
        from netra_backend.app.websocket_core import CRITICAL_EVENTS
        
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for event in expected_events:
            if event not in CRITICAL_EVENTS:
                print(f"❌ Missing critical event: {event}")
                return False
        
        print(f"✅ All critical events available: {CRITICAL_EVENTS}")
        return True
        
    except Exception as e:
        print(f"❌ Critical events test failed: {e}")
        return False

def main():
    """Run all import validation tests"""
    print("Validating all critical imports after Issue #1090 fix...")
    print("=" * 60)
    
    tests = [
        ("Core imports", test_all_critical_imports),
        ("Legacy compatibility", test_legacy_compatibility_imports),
        ("Critical events", test_critical_events_availability)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} test categories passed")
    
    if passed == total:
        print("✅ ALL critical imports working correctly")
        return 0
    else:
        print("❌ Some critical imports have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())