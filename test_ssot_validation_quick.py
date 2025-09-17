#!/usr/bin/env python3
"""Quick SSOT WebSocket Manager validation test for Issue #186 Phase 5"""

import sys
import os
import importlib
import inspect

# Add project root to path
project_root = os.getcwd()
sys.path.insert(0, project_root)

def test_websocket_manager_ssot_compliance():
    """Test if all WebSocketManager imports resolve to the same class."""
    
    print("🔍 Testing WebSocket Manager SSOT Compliance...")
    
    websocket_modules = [
        'netra_backend.app.websocket_core.websocket_manager',
        'netra_backend.app.websocket_core.unified_manager', 
        'netra_backend.app.websocket_core.manager',
        'netra_backend.app.websocket_core.broadcast_core',
        'netra_backend.app.websocket_core.connection_executor'
    ]

    manager_exports = []
    
    for module_path in websocket_modules:
        try:
            module = importlib.import_module(module_path)
            
            # Check for WebSocketManager exports
            if hasattr(module, 'WebSocketManager'):
                ws_manager = getattr(module, 'WebSocketManager')
                manager_exports.append({
                    'module': module_path,
                    'class': 'WebSocketManager',
                    'object_id': id(ws_manager),
                    'type': type(ws_manager).__name__,
                    'object': ws_manager
                })
                
            if hasattr(module, 'UnifiedWebSocketManager'):
                unified_manager = getattr(module, 'UnifiedWebSocketManager')
                manager_exports.append({
                    'module': module_path,
                    'class': 'UnifiedWebSocketManager', 
                    'object_id': id(unified_manager),
                    'type': type(unified_manager).__name__,
                    'object': unified_manager
                })
                
        except ImportError as e:
            print(f'⚠️  Could not import {module_path}: {e}')

    print(f'📊 Found {len(manager_exports)} WebSocketManager exports:')
    for export in manager_exports:
        print(f'   - {export["module"]}.{export["class"]} (id: {export["object_id"]}, type: {export["type"]})')

    # SSOT Compliance Check
    websocket_manager_exports = [e for e in manager_exports if e['class'] == 'WebSocketManager']
    unified_manager_exports = [e for e in manager_exports if e['class'] == 'UnifiedWebSocketManager']
    
    print(f'\n🔍 SSOT Analysis:')
    print(f'   WebSocketManager exports: {len(websocket_manager_exports)}')
    print(f'   UnifiedWebSocketManager exports: {len(unified_manager_exports)}')
    
    # Check if all WebSocketManager exports point to the same object
    if websocket_manager_exports:
        unique_websocket_ids = set(e['object_id'] for e in websocket_manager_exports)
        print(f'   Unique WebSocketManager objects: {len(unique_websocket_ids)}')
        
        if len(unique_websocket_ids) == 1:
            print('✅ PASS: All WebSocketManager exports point to the same object!')
            return True
        else:
            print('❌ FAIL: Multiple different WebSocketManager objects found!')
            for obj_id in unique_websocket_ids:
                matching = [e for e in websocket_manager_exports if e['object_id'] == obj_id]
                print(f'     Object ID {obj_id}:')
                for export in matching:
                    print(f'       - {export["module"]}.{export["class"]}')
            return False
    else:
        print('⚠️  No WebSocketManager exports found!')
        return False

if __name__ == "__main__":
    success = test_websocket_manager_ssot_compliance()
    print(f'\n{"✅ SSOT COMPLIANCE SUCCESS" if success else "❌ SSOT COMPLIANCE FAILURE"}')
    sys.exit(0 if success else 1)