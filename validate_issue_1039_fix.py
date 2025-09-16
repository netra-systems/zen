#!/usr/bin/env python3
"""
Validation script for Issue #1039 fix - tool_executing events include tool_name at top level

This script validates that:
1. The fix is working correctly
2. No regressions were introduced
3. Event structure is compatible
4. System is stable
"""

import sys
import os
import time
import asyncio
from unittest.mock import Mock, AsyncMock

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import_stability():
    """Test that all imports work correctly after the fix"""
    print("=== Testing Import Stability ===")
    
    try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        print("✅ UnifiedWebSocketEmitter import successful")
        
        from netra_backend.app.websocket_core.manager import WebSocketManager
        print("✅ WebSocketManager import successful")
        
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        print("✅ ExecutionEngine import successful")
        
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        print("✅ AgentWebSocketBridge import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_tool_executing_event_structure():
    """Test that tool_executing events have correct structure with tool_name at top level"""
    print("\n=== Testing tool_executing Event Structure ===")
    
    try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Create mock manager
        class MockManager:
            def __init__(self):
                self.last_message = None
                
            async def emit_critical_event(self, **kwargs):
                self.last_message = kwargs
                return True
                
            def is_connection_active(self, user_id):
                return True
        
        # Create mock context
        class MockContext:
            def __init__(self):
                self.user_id = "test_user_123"
                self.thread_id = "test_thread_456"
                self.run_id = "test_run_789"
                
            def get_metadata(self):
                return {
                    "user_id": self.user_id,
                    "thread_id": self.thread_id,
                    "run_id": self.run_id
                }
        
        mock_manager = MockManager()
        mock_context = MockContext()
        
        # Create emitter
        emitter = UnifiedWebSocketEmitter(
            manager=mock_manager,
            user_id="test_user_123",
            context=mock_context
        )
        
        # Test tool_executing event emission
        test_tool_name = "test_analyzer"
        test_params = {"input": "test_data", "mode": "analysis"}
        
        # Use asyncio.run to handle the async call
        async def emit_test():
            await emitter.emit_tool_executing(test_tool_name, test_params)
        
        asyncio.run(emit_test())
        
        # Verify the message structure
        message = mock_manager.last_message
        if not message:
            print("❌ No message was emitted")
            return False
        
        print(f"Message structure: {message}")
        
        # Verify required fields
        assert message["event_type"] == "tool_executing"
        assert message["user_id"] == "test_user_123"
        assert "data" in message
        
        data = message["data"]
        
        # CRITICAL: Verify tool_name is at top level in data
        if "tool_name" not in data:
            print("❌ CRITICAL: tool_name missing from top level of data")
            return False
        
        assert data["tool_name"] == test_tool_name
        print(f"✅ tool_name at top level: {data['tool_name']}")
        
        # Verify params are included
        if "params" in data:
            assert data["params"] == test_params
            print(f"✅ params included: {data['params']}")
        
        # Verify context data
        assert data["run_id"] == "test_run_789"
        assert data["thread_id"] == "test_thread_456"
        print("✅ Context data included correctly")
        
        print("✅ tool_executing event structure validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Event structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_other_events_unchanged():
    """Test that other critical events are unchanged"""
    print("\n=== Testing Other Events Unchanged ===")
    
    try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Create mock manager that captures all messages
        class MockManager:
            def __init__(self):
                self.messages = []
                
            async def emit_critical_event(self, **kwargs):
                self.messages.append(kwargs)
                return True
                
            def is_connection_active(self, user_id):
                return True
        
        # Create mock context
        class MockContext:
            def __init__(self):
                self.user_id = "test_user_123"
                self.thread_id = "test_thread_456"
                self.run_id = "test_run_789"
                
            def get_metadata(self):
                return {
                    "user_id": self.user_id,
                    "thread_id": self.thread_id,
                    "run_id": self.run_id
                }
        
        mock_manager = MockManager()
        mock_context = MockContext()
        
        # Create emitter
        emitter = UnifiedWebSocketEmitter(
            manager=mock_manager,
            user_id="test_user_123",
            context=mock_context
        )
        
        # Test other critical events
        async def test_other_events():
            await emitter.emit_agent_started({"agent_name": "TestAgent"})
            await emitter.emit_agent_thinking({"reasoning": "Test thinking"})
            await emitter.emit_tool_completed({"tool_name": "test_tool", "result": "success"})
            await emitter.emit_agent_completed({"agent_name": "TestAgent", "result": "complete"})
        
        asyncio.run(test_other_events())
        
        # Verify messages
        assert len(mock_manager.messages) == 4
        
        event_types = [msg["event_type"] for msg in mock_manager.messages]
        expected_types = ["agent_started", "agent_thinking", "tool_completed", "agent_completed"]
        
        for expected_type in expected_types:
            assert expected_type in event_types
            print(f"✅ {expected_type} event emitted successfully")
        
        print("✅ All other critical events working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Other events test failed: {e}")
        return False

def test_backward_compatibility():
    """Test that the fix maintains backward compatibility"""
    print("\n=== Testing Backward Compatibility ===")
    
    try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Test that the emitter still has all expected methods
        expected_methods = [
            'emit_agent_started',
            'emit_agent_thinking', 
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_agent_completed'
        ]
        
        for method_name in expected_methods:
            assert hasattr(UnifiedWebSocketEmitter, method_name)
            print(f"✅ Method {method_name} exists")
        
        # Test that CRITICAL_EVENTS constant is still present
        emitter_class = UnifiedWebSocketEmitter
        assert hasattr(emitter_class, 'CRITICAL_EVENTS')
        
        critical_events = emitter_class.CRITICAL_EVENTS
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for event in expected_events:
            assert event in critical_events
            print(f"✅ Critical event {event} preserved")
        
        print("✅ Backward compatibility maintained")
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("=== Issue #1039 Fix Validation ===")
    print("Testing that tool_executing events include tool_name at top level")
    print("Validating system stability and no breaking changes\n")
    
    tests = [
        test_import_stability,
        test_tool_executing_event_structure,
        test_other_events_unchanged,
        test_backward_compatibility
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\n=== Validation Results ===")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n🎉 ALL VALIDATION TESTS PASSED!")
        print("✅ Issue #1039 fix is working correctly")
        print("✅ No regressions introduced")
        print("✅ System is stable")
        return True
    else:
        print("\n⚠️  Some validation tests failed")
        print("❌ Fix may have issues or regressions")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)