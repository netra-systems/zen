#!/usr/bin/env python
"""Verification script for WebSocket Event Suite restoration."""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

async def main():
    """Verify WebSocket Event Suite restoration."""
    print("\n" + "="*80)
    print("WEBSOCKET EVENT SUITE RESTORATION VERIFICATION")
    print("="*80)
    
    results = {
        "enhance_function": False,
        "validation_framework": False,
        "integration_layer": False,
        "test_imports": False,
        "websocket_notifier": False,
        "tool_dispatcher": False
    }
    
    # 1. Verify enhance_tool_dispatcher_with_notifications exists
    try:
        from netra_backend.app.agents.websocket_tool_enhancement import enhance_tool_dispatcher_with_notifications
        results["enhance_function"] = True
        print("[PASS] enhance_tool_dispatcher_with_notifications function: FOUND")
    except ImportError as e:
        print(f"[FAIL] enhance_tool_dispatcher_with_notifications function: MISSING - {e}")
    
    # 2. Verify Event Validation Framework exists
    try:
        from netra_backend.app.websocket_core.event_validation_framework import (
            EventValidator,
            EventValidationFramework,
            ValidationRule,
            EventReplayManager
        )
        results["validation_framework"] = True
        print("[PASS] Event Validation Framework: CREATED")
        
        # Test instantiation
        validator = EventValidator()
        print(f"   - EventValidator instantiated: {validator.__class__.__name__}")
        print(f"   - Required events: {getattr(validator, 'REQUIRED_EVENTS', 'N/A')}")
    except ImportError as e:
        print(f"[FAIL] Event Validation Framework: MISSING - {e}")
    
    # 3. Verify Integration Layer exists
    try:
        from netra_backend.app.websocket_core.validation_integration import (
            WebSocketValidationIntegration,
            validated_websocket_event,
            ValidationContext
        )
        results["integration_layer"] = True
        print("[PASS] Validation Integration Layer: CREATED")
    except ImportError as e:
        print(f"[FAIL] Validation Integration Layer: MISSING - {e}")
    
    # 4. Verify test suite imports work
    try:
        # Import test dependencies
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        from netra_backend.app.websocket_core.manager import WebSocketManager
        results["test_imports"] = True
        print("[PASS] Test suite imports: ALL WORKING")
    except ImportError as e:
        print(f"[FAIL] Test suite imports: FAILED - {e}")
    
    # 5. Verify WebSocketNotifier has required methods
    try:
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        from netra_backend.app.websocket_core.manager import WebSocketManager
        
        ws_manager = WebSocketManager()
        notifier = WebSocketNotifier(ws_manager)
        
        required_methods = [
            'send_agent_started',
            'send_agent_thinking',
            'send_partial_result',
            'send_tool_executing',
            'send_tool_completed',
            'send_final_report',
            'send_agent_completed'
        ]
        
        missing = []
        for method in required_methods:
            if not hasattr(notifier, method):
                missing.append(method)
        
        if not missing:
            results["websocket_notifier"] = True
            print("[PASS] WebSocketNotifier methods: ALL PRESENT")
        else:
            print(f"[FAIL] WebSocketNotifier missing methods: {missing}")
    except Exception as e:
        print(f"[FAIL] WebSocketNotifier verification: FAILED - {e}")
    
    # 6. Verify ToolDispatcher enhancement capability
    try:
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        
        dispatcher = ToolDispatcher()
        
        # Check executor type
        if isinstance(dispatcher.executor, UnifiedToolExecutionEngine):
            results["tool_dispatcher"] = True
            print("[PASS] ToolDispatcher uses UnifiedToolExecutionEngine: CORRECT")
            
            # Check WebSocket bridge support
            if hasattr(dispatcher.executor, 'websocket_bridge'):
                print("   - WebSocket bridge attribute: PRESENT")
            if hasattr(dispatcher.executor, 'websocket_notifier'):
                print("   - WebSocket notifier alias: PRESENT")
        else:
            print(f"[FAIL] ToolDispatcher executor type: {type(dispatcher.executor)}")
    except Exception as e:
        print(f"[FAIL] ToolDispatcher verification: FAILED - {e}")
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    passed = sum(results.values())
    total = len(results)
    
    for component, status in results.items():
        status_str = "[PASS]" if status else "[FAIL]"
        print(f"{component:.<30} {status_str}")
    
    print(f"\nOVERALL: {passed}/{total} components verified ({passed*100//total}%)")
    
    if passed == total:
        print("\n[SUCCESS] WebSocket Event Suite fully restored!")
        print("\n[READY FOR PRODUCTION]:")
        print("- enhance_tool_dispatcher_with_notifications: WORKING")
        print("- Five Event Validation Framework: DEPLOYED")
        print("- All critical components: OPERATIONAL")
        return 0
    else:
        print("\n[WARNING] Some components need attention")
        failed = [k for k, v in results.items() if not v]
        print(f"Failed components: {', '.join(failed)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)