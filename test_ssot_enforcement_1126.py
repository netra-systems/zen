#!/usr/bin/env python3
"""
Test script to validate SSOT enforcement for Issue #1126
WebSocket Factory dual pattern fragmentation fix
"""

def test_ssot_enforcement():
    """Test SSOT enforcement by checking what's accessible"""
    print("=== Issue #1126 SSOT Enforcement Test ===")
    
    violations = []
    
    # Test 1: Check __all__ exports
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import __all__
        print(f"Factory __all__ exports: {__all__}")
        
        if 'get_websocket_manager_factory' in __all__:
            violations.append("get_websocket_manager_factory is exported in __all__")
        if 'WebSocketManagerFactory' in __all__:
            violations.append("WebSocketManagerFactory is exported in __all__")
            
    except ImportError as e:
        print(f"Could not import __all__: {e}")
    
    # Test 2: Check direct import accessibility
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
        violations.append("get_websocket_manager_factory is still directly importable")
    except ImportError:
        print("GOOD: get_websocket_manager_factory is not directly importable")
    
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        violations.append("WebSocketManagerFactory is still directly importable")
    except ImportError:
        print("GOOD: WebSocketManagerFactory is not directly importable")
    
    # Test 3: Check if factory functions exist in module
    try:
        import netra_backend.app.websocket_core.websocket_manager_factory as factory_module
        if hasattr(factory_module, 'get_websocket_manager_factory'):
            violations.append("get_websocket_manager_factory function exists in module")
        if hasattr(factory_module, 'WebSocketManagerFactory'):
            violations.append("WebSocketManagerFactory class exists in module")
    except ImportError as e:
        print(f"Could not import factory module: {e}")
    
    # Results
    print(f"\n=== RESULTS ===")
    print(f"Total SSOT violations found: {len(violations)}")
    for i, violation in enumerate(violations, 1):
        print(f"{i}. {violation}")
    
    if violations:
        print(f"\nSTATUS: FAIL - {len(violations)} SSOT violations detected")
        return False
    else:
        print("\nSTATUS: PASS - No SSOT violations detected")
        return True

if __name__ == "__main__":
    test_ssot_enforcement()