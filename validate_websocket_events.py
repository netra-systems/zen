#!/usr/bin/env python
"""Validate WebSocket critical events are properly implemented.

This script verifies that all 5 critical events are:
1. Defined in the UnifiedWebSocketEmitter
2. Have proper emit methods
3. Have backward compatibility wrappers
"""

import sys
import inspect
from typing import List, Dict, Any

# Add current dir to path
sys.path.insert(0, '.')

def validate_critical_events() -> Dict[str, Any]:
    """Validate all 5 critical WebSocket events."""
    results = {
        'success': True,
        'critical_events_found': [],
        'emit_methods_found': [],
        'notify_methods_found': [],
        'errors': []
    }
    
    try:
        # Import the UnifiedWebSocketEmitter
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Check CRITICAL_EVENTS constant
        critical_events = UnifiedWebSocketEmitter.CRITICAL_EVENTS
        results['critical_events_found'] = critical_events
        
        expected_events = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        # Verify all expected events are present
        for event in expected_events:
            if event not in critical_events:
                results['errors'].append(f"Missing critical event: {event}")
                results['success'] = False
        
        # Check for emit methods
        for event in critical_events:
            emit_method = f'emit_{event}'
            if hasattr(UnifiedWebSocketEmitter, emit_method):
                results['emit_methods_found'].append(emit_method)
                
                # Verify it's an async method
                method = getattr(UnifiedWebSocketEmitter, emit_method)
                if not inspect.iscoroutinefunction(method):
                    results['errors'].append(f"{emit_method} is not async")
                    results['success'] = False
            else:
                results['errors'].append(f"Missing emit method: {emit_method}")
                results['success'] = False
        
        # Check for backward compatibility notify methods
        notify_mappings = {
            'agent_started': 'notify_agent_started',
            'agent_thinking': 'notify_agent_thinking',
            'tool_executing': 'notify_tool_executing',
            'tool_completed': 'notify_tool_completed',
            'agent_completed': 'notify_agent_completed'
        }
        
        for event, notify_method in notify_mappings.items():
            if hasattr(UnifiedWebSocketEmitter, notify_method):
                results['notify_methods_found'].append(notify_method)
        
        # Check WebSocketBridge integration
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Verify bridge can create emitters
        if hasattr(AgentWebSocketBridge, 'create_user_emitter'):
            results['bridge_integration'] = 'create_user_emitter found'
        else:
            results['errors'].append("AgentWebSocketBridge missing create_user_emitter")
            results['success'] = False
            
    except ImportError as e:
        results['errors'].append(f"Import error: {e}")
        results['success'] = False
    except Exception as e:
        results['errors'].append(f"Unexpected error: {e}")
        results['success'] = False
    
    return results


def print_results(results: Dict[str, Any]) -> None:
    """Print validation results."""
    print("=" * 80)
    print("WEBSOCKET CRITICAL EVENTS VALIDATION REPORT")
    print("=" * 80)
    
    if results['success']:
        print("[SUCCESS] VALIDATION SUCCESSFUL - All 5 critical events are properly implemented!")
    else:
        print("[FAILED] VALIDATION FAILED - Critical issues found!")
    
    print("\n[INFO] CRITICAL EVENTS STATUS:")
    print(f"  Found: {results['critical_events_found']}")
    
    print("\n[INFO] EMIT METHODS STATUS:")
    print(f"  Found {len(results['emit_methods_found'])} emit methods:")
    for method in results['emit_methods_found']:
        print(f"    + {method}")
    
    print("\n[INFO] BACKWARD COMPATIBILITY:")
    print(f"  Found {len(results['notify_methods_found'])} notify methods:")
    for method in results['notify_methods_found']:
        print(f"    + {method}")
    
    if 'bridge_integration' in results:
        print(f"\n[INFO] BRIDGE INTEGRATION: {results['bridge_integration']}")
    
    if results['errors']:
        print("\n[ERROR] ERRORS:")
        for error in results['errors']:
            print(f"    * {error}")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  * All 5 critical events defined: {'[YES]' if len(results['critical_events_found']) == 5 else '[NO]'}")
    print(f"  * All emit methods present: {'[YES]' if len(results['emit_methods_found']) == 5 else '[NO]'}")  
    print(f"  * Bridge integration working: {'[YES]' if 'bridge_integration' in results else '[NO]'}")
    print(f"  * Overall Status: {'[OPERATIONAL]' if results['success'] else '[NEEDS FIXING]'}")
    print("=" * 80)


if __name__ == "__main__":
    results = validate_critical_events()
    print_results(results)
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)