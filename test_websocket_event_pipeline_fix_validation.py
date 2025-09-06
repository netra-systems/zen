#!/usr/bin/env python3
"""
WebSocket Event Pipeline Fix Validation Test
MISSION CRITICAL: Validates that WebSocket agent events are properly transmitted

This test reproduces the exact issue described in the root cause analysis and validates the fix:
- WHY #1: Using deprecated WebSocketNotifier instead of AgentWebSocketBridge
- WHY #2: Migration from WebSocketNotifier to AgentWebSocketBridge was incomplete  
- WHY #3: Factory pattern migration was implemented but not properly wired
- WHY #4: Singleton pattern conflicts with user isolation requirements
- WHY #5: Architectural inconsistency - refactoring removed singletons but didn't update emission callsites

Business Value: $500K+ ARR - Core chat functionality depends on these 5 events:
1. agent_started - User sees agent began processing  
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows when response is ready
"""

import asyncio
import os
import sys
import time
import uuid
from typing import List, Dict, Any, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Test the exact problematic import chain that causes the issue
def test_websocket_import_chain_issue():
    """
    Test WHY #1: Verify the import chain that causes deprecated WebSocketNotifier usage.
    """
    print("=== WHY #1: Testing Deprecated WebSocketNotifier Import Chain ===")
    
    # Test the exact import from dependencies.py line 16
    try:
        from netra_backend.app.websocket_core import get_websocket_manager
        manager = get_websocket_manager()
        
        print(f"OK Import successful: {type(manager)}")
        print(f"OK Manager class: {manager.__class__.__module__}.{manager.__class__.__name__}")
        
        # Check if this is the deprecated singleton manager
        if hasattr(manager, '__dict__'):
            print(f"OK Manager attributes: {list(manager.__dict__.keys())}")
        
        # The issue: This returns UnifiedWebSocketManager from unified_manager.py
        # which is the DEPRECATED singleton with security warnings
        expected_deprecated_class = "netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager"
        actual_class = f"{manager.__class__.__module__}.{manager.__class__.__name__}"
        
        if expected_deprecated_class == actual_class:
            print("FAIL CONFIRMED ISSUE: Using deprecated singleton WebSocket manager!")
            print("FAIL This explains why WebSocket events aren't being transmitted properly")
            return False
        else:
            print("OK Using correct WebSocket manager")
            return True
            
    except ImportError as e:
        print(f"FAIL Import failed: {e}")
        return False


def test_agent_websocket_bridge_factory():
    """
    Test WHY #2: Verify AgentWebSocketBridge factory exists but isn't being used.
    """
    print("\n=== WHY #2: Testing AgentWebSocketBridge Factory Implementation ===")
    
    try:
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
        from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
        
        # Create a test user context
        user_context = UserExecutionContext(
            user_id="test_user",
            request_id="test_request",
            thread_id="test_thread"
        )
        
        # Test factory function exists and works
        bridge = create_agent_websocket_bridge(user_context)
        print(f"OK Factory function works: {type(bridge)}")
        print(f"OK Bridge class: {bridge.__class__.__module__}.{bridge.__class__.__name__}")
        
        # Test bridge has event emission capabilities
        if hasattr(bridge, 'create_user_emitter'):
            print("OK Bridge has user emitter factory method")
            # Try to create user emitter
            try:
                emitter = bridge.create_user_emitter(user_context)
                print(f"OK User emitter created: {type(emitter)}")
                
                # Check if emitter has critical event methods
                critical_methods = ['notify_agent_started', 'notify_agent_thinking', 
                                  'notify_tool_executing', 'notify_tool_completed', 'notify_agent_completed']
                
                missing_methods = []
                for method in critical_methods:
                    if not hasattr(emitter, method):
                        missing_methods.append(method)
                
                if missing_methods:
                    print(f"FAIL Missing critical methods: {missing_methods}")
                    return False
                else:
                    print("OK All critical event emission methods are available")
                    return True
                    
            except Exception as e:
                print(f"FAIL Failed to create user emitter: {e}")
                return False
        else:
            print("FAIL Bridge missing user emitter factory method")
            return False
            
    except ImportError as e:
        print(f"FAIL Import failed: {e}")
        return False


def test_agent_registry_websocket_wiring():
    """
    Test WHY #3: Verify AgentRegistry WebSocket wiring is incomplete.
    """
    print("\n=== WHY #3: Testing AgentRegistry WebSocket Wiring ===")
    
    try:
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.websocket_core import get_websocket_manager
        from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
        
        # Create test components
        user_context = UserExecutionContext(
            user_id="test_user",
            request_id="test_request", 
            thread_id="test_thread"
        )
        
        # Test AgentRegistry creation and WebSocket manager setup
        registry = AgentRegistry()
        websocket_manager = get_websocket_manager()
        
        print(f"OK AgentRegistry created: {type(registry)}")
        print(f"OK WebSocket manager available: {type(websocket_manager)}")
        
        # Test set_websocket_manager method exists
        if hasattr(registry, 'set_websocket_manager'):
            print("OK set_websocket_manager method exists")
            
            # This is where the issue likely occurs - the method exists but doesn't properly wire events
            try:
                # The method is async, so we need to run it
                async def test_set_websocket():
                    await registry.set_websocket_manager(websocket_manager, user_context)
                    
                    # Check if the bridge was actually created and stored
                    if hasattr(registry, '_websocket_bridge'):
                        print("OK WebSocket bridge created and stored")
                        print(f"OK Bridge type: {type(registry._websocket_bridge)}")
                        return True
                    else:
                        print("FAIL WebSocket bridge not stored in registry")
                        return False
                
                # Run the async test
                result = asyncio.run(test_set_websocket())
                return result
                
            except Exception as e:
                print(f"FAIL set_websocket_manager failed: {e}")
                return False
        else:
            print("FAIL set_websocket_manager method missing")
            return False
            
    except ImportError as e:
        print(f"FAIL Import failed: {e}")
        return False


def test_execution_engine_factory_pattern():
    """
    Test WHY #4: Verify ExecutionEngine factory pattern conflicts with singleton usage.
    """
    print("\n=== WHY #4: Testing ExecutionEngine Factory Pattern Issues ===")
    
    try:
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
        
        # Test ExecutionEngine direct instantiation (should fail)
        try:
            registry = AgentRegistry()
            bridge = create_agent_websocket_bridge()
            user_context = UserExecutionContext(
                user_id="test_user",
                request_id="test_request",
                thread_id="test_thread"
            )
            
            # This should throw RuntimeError according to the code
            engine = ExecutionEngine(registry, bridge, user_context)
            print("FAIL ISSUE CONFIRMED: ExecutionEngine allows direct instantiation when it shouldn't")
            return False
            
        except RuntimeError as e:
            print(f"OK ExecutionEngine properly blocks direct instantiation: {e}")
            
            # Now test if there's a proper factory method available
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import (
                    create_request_scoped_engine
                )
                print("OK Factory method available: create_request_scoped_engine")
                return True
                
            except ImportError:
                print("FAIL ISSUE: No factory method available for ExecutionEngine creation")
                return False
        
        except Exception as e:
            print(f"FAIL Unexpected error: {e}")
            return False
            
    except ImportError as e:
        print(f"FAIL Import failed: {e}")
        return False


def test_event_emission_architecture_inconsistency():
    """
    Test WHY #5: Verify architectural inconsistency in event emission paths.
    """
    print("\n=== WHY #5: Testing Event Emission Architecture Inconsistency ===")
    
    try:
        # Test if agents are still trying to use old WebSocketNotifier patterns
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        
        print("FAIL ISSUE CONFIRMED: Deprecated WebSocketNotifier still importable")
        print("FAIL This means agent code can still import and use the old patterns")
        
        # Check if the deprecation warnings are properly implemented
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Try to create WebSocketNotifier (should trigger deprecation warning)
            from netra_backend.app.websocket_core import get_websocket_manager
            manager = get_websocket_manager()
            notifier = WebSocketNotifier(manager)
            
            if w:
                print(f"OK Deprecation warnings triggered: {len(w)} warnings")
                for warning in w:
                    print(f"   - {warning.message}")
                return True
            else:
                print("FAIL No deprecation warnings - agents can use deprecated code silently")
                return False
                
    except ImportError as e:
        print(f"OK Good: WebSocketNotifier not importable: {e}")
        return True
    except Exception as e:
        print(f"FAIL Unexpected error: {e}")
        return False


async def test_complete_websocket_event_flow():
    """
    Test the complete WebSocket event flow to validate the fix works end-to-end.
    """
    print("\n=== COMPLETE WEBSOCKET EVENT FLOW TEST ===")
    
    # Capture events
    events_received = []
    
    class MockWebSocketManager:
        async def send_to_thread(self, thread_id: str, message: Dict[str, Any]):
            events_received.append(message)
            print(f"Event captured: {message.get('type', 'unknown')}")
            return True
    
    try:
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
        
        # Create test context
        user_context = UserExecutionContext(
            user_id="test_user",
            request_id="test_request",
            thread_id="test_thread"
        )
        
        # Create bridge with mock manager
        bridge = create_agent_websocket_bridge(user_context)
        
        # Mock the websocket manager
        bridge._websocket_manager = MockWebSocketManager()
        
        # Create user emitter
        emitter = bridge.create_user_emitter(user_context)
        
        # Test all 5 critical events
        critical_events = [
            ('agent_started', 'notify_agent_started', ['TestAgent', {'run_id': 'test_run'}]),
            ('agent_thinking', 'notify_agent_thinking', ['Analyzing data...', {'step': 1}]),
            ('tool_executing', 'notify_tool_executing', ['data_analyzer', {'purpose': 'analyze'}]),
            ('tool_completed', 'notify_tool_completed', ['data_analyzer', {'result': 'success'}]),
            ('agent_completed', 'notify_agent_completed', ['TestAgent', {'status': 'success'}])
        ]
        
        for event_type, method_name, args in critical_events:
            if hasattr(emitter, method_name):
                method = getattr(emitter, method_name)
                try:
                    await method(*args)
                    print(f"OK {event_type} event emitted successfully")
                except Exception as e:
                    print(f"FAIL {event_type} event failed: {e}")
            else:
                print(f"FAIL {method_name} method not found on emitter")
        
        # Verify all events were captured
        print(f"\nEvents captured: {len(events_received)}")
        event_types = [event.get('type') for event in events_received]
        print(f"Event types: {event_types}")
        
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        missing_events = [e for e in expected_events if e not in event_types]
        
        if missing_events:
            print(f"FAIL Missing critical events: {missing_events}")
            return False
        else:
            print("OK All 5 critical events successfully transmitted!")
            return True
            
    except Exception as e:
        print(f"FAIL Complete flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("MISSION CRITICAL: WebSocket Event Pipeline Fix Validation")
    print("Business Value: $500K+ ARR - Core chat functionality")
    print("=" * 80)
    
    tests = [
        ("WHY #1: Import Chain Issue", test_websocket_import_chain_issue),
        ("WHY #2: Factory Implementation", test_agent_websocket_bridge_factory), 
        ("WHY #3: Registry Wiring", test_agent_registry_websocket_wiring),
        ("WHY #4: Factory Pattern Conflicts", test_execution_engine_factory_pattern),
        ("WHY #5: Architecture Inconsistency", test_event_emission_architecture_inconsistency),
        ("Complete Event Flow", lambda: asyncio.run(test_complete_websocket_event_flow())),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n[RUNNING] Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "OK PASS" if result else "FAIL FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"FAIL ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("[SUMMARY] VALIDATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "OK PASS" if result else "FAIL FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] ALL TESTS PASSED - WebSocket event pipeline is working!")
        return True
    else:
        print("[FAILURE] TESTS FAILED - WebSocket event pipeline needs fixes")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)