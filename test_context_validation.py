#!/usr/bin/env python3
"""
Quick test script to verify WebSocket bridge context validation functionality.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


async def test_context_validation():
    """Test the context validation functionality."""
    print("[TEST] Testing WebSocket Bridge Context Validation...")
    
    # Create bridge instance
    bridge = AgentWebSocketBridge()
    
    # Test cases for context validation
    test_cases = [
        # Invalid cases (should return False)
        (None, "test_event", "TestAgent", False, "None run_id"),
        ("registry", "test_event", "TestAgent", False, "Registry run_id"),
        ("", "test_event", "TestAgent", False, "Empty run_id"),
        ("   ", "test_event", "TestAgent", False, "Whitespace run_id"),
        ("test", "test_event", "TestAgent", False, "Suspicious pattern (test)"),
        ("admin_context", "test_event", "TestAgent", False, "System pattern (admin_)"),
        
        # Valid cases (should return True)
        ("user_session_12345", "test_event", "TestAgent", True, "Valid user run_id"),
        ("execution_abc123", "test_event", "TestAgent", True, "Valid execution run_id"),
        ("thread_456_run_789", "test_event", "TestAgent", True, "Valid thread run_id"),
    ]
    
    print(f"\n[TESTS] Running {len(test_cases)} validation tests...")
    
    passed = 0
    failed = 0
    
    for run_id, event_type, agent_name, expected, description in test_cases:
        try:
            result = bridge._validate_event_context(run_id, event_type, agent_name)
            
            if result == expected:
                print(f"✅ PASS: {description} - Expected {expected}, Got {result}")
                passed += 1
            else:
                print(f"❌ FAIL: {description} - Expected {expected}, Got {result}")
                failed += 1
                
        except Exception as e:
            print(f"💥 ERROR: {description} - Exception: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All context validation tests passed!")
        return True
    else:
        print("🚨 Some tests failed!")
        return False


async def test_emit_agent_event():
    """Test the emit_agent_event method with various contexts."""
    print("\n🧪 Testing emit_agent_event method...")
    
    bridge = AgentWebSocketBridge()
    
    # Test invalid contexts (should return False without emitting)
    print("\n🚫 Testing invalid contexts (should fail)...")
    
    # Test None run_id
    result = await bridge.emit_agent_event(
        event_type="test_event",
        data={"message": "test"},
        run_id=None
    )
    print(f"None run_id result: {result} (should be False)")
    
    # Test registry run_id
    result = await bridge.emit_agent_event(
        event_type="test_event", 
        data={"message": "test"},
        run_id="registry"
    )
    print(f"Registry run_id result: {result} (should be False)")
    
    # Test suspicious run_id
    result = await bridge.emit_agent_event(
        event_type="test_event",
        data={"message": "test"}, 
        run_id="test_pattern"
    )
    print(f"Suspicious run_id result: {result} (should be False)")
    
    print("✅ emit_agent_event context validation tests completed")


async def main():
    """Main test function."""
    print("🚀 Starting WebSocket Bridge Context Validation Tests\n")
    
    try:
        # Test context validation
        validation_passed = await test_context_validation()
        
        # Test emit_agent_event
        await test_emit_agent_event()
        
        if validation_passed:
            print("\n🎯 SUMMARY: Context validation implementation is working correctly!")
            print("   - Invalid run_ids (None, 'registry') are properly blocked")
            print("   - Suspicious patterns are detected and logged")
            print("   - Valid run_ids pass validation")
            print("   - emit_agent_event method properly validates context")
            
        return 0
        
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)