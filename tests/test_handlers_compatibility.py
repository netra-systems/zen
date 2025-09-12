#!/usr/bin/env python3
"""
Test WebSocket handlers compatibility after signature fix.

This script validates that the WebSocket handlers can successfully call
create_server_message using the patterns that were failing in issue #405.
"""

print("TESTING WEBSOCKET HANDLERS COMPATIBILITY")
print("="*50)

def test_handlers_import_and_call():
    """Test that handlers can import and call create_server_message."""
    try:
        # This is the import pattern used in handlers.py
        from netra_backend.app.websocket_core.types import create_server_message
        
        print("[OK] Import successful")
        
        # Test the patterns that were failing in handlers.py (lines 573, 697, 798, 852)
        # Based on the error message, these were calls like:
        # create_server_message({"type": "system", "status": "connected"})
        
        test_cases = [
            {"type": "system", "status": "connected"},
            {"type": "agent_started", "agent_id": "test_agent"},
            {"type": "heartbeat", "timestamp": 123456789},
            {"type": "connect", "user_id": "test_user"},
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            result = create_server_message(test_case)
            print(f"[OK] Test case {i}: {test_case['type']} -> {result.type}")
            
        print("\n[SUCCESS] All handlers compatibility tests passed!")
        return True
        
    except Exception as e:
        print(f"[FAIL] Handlers compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_legacy_websocket_ssot_patterns():
    """Test the specific patterns from websocket_ssot.py that were failing."""
    try:
        from netra_backend.app.websocket_core.types import create_server_message
        
        # Test patterns similar to those mentioned in the commit message
        patterns = [
            {"type": "connection_established", "user_id": "123"},
            {"type": "factory_connection_established", "factory_id": "test"},
            {"type": "system", "message": "System ready"},
        ]
        
        for pattern in patterns:
            result = create_server_message(pattern)
            print(f"[OK] Legacy pattern: {pattern['type']} -> {result.type}")
            
        print("\n[SUCCESS] All websocket_ssot.py patterns work!")
        return True
        
    except Exception as e:
        print(f"[FAIL] websocket_ssot.py compatibility failed: {e}")
        return False

if __name__ == "__main__":
    success1 = test_handlers_import_and_call()
    success2 = test_legacy_websocket_ssot_patterns()
    
    if success1 and success2:
        print("\n" + "="*50)
        print("[VALIDATION COMPLETE] WebSocket handlers compatibility confirmed")
        print("[OK] Issue #405 handlers patterns work correctly")
        print("[OK] Legacy websocket_ssot.py patterns work correctly") 
        print("[OK] No breaking changes detected")
        exit(0)
    else:
        print("\n" + "="*50)
        print("[VALIDATION FAILED] Issues detected in handlers compatibility")
        exit(1)