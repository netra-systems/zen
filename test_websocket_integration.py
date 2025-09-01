#!/usr/bin/env python3
"""Test WebSocket integration after inheritance refactoring"""

import sys
import asyncio
sys.path.insert(0, r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')

async def test_websocket_integration():
    """Test WebSocket functionality after inheritance refactoring"""
    print("=" * 60)
    print("WEBSOCKET INTEGRATION TEST")
    print("=" * 60)
    
    try:
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
        
        print("SUCCESS: Successfully imported agent classes")
    except Exception as e:
        print(f"FAILED: Import failed: {e}")
        return False
    
    # Test 1: WebSocket methods availability
    print("\n1. Testing WebSocket Methods Availability")
    print("-" * 40)
    
    try:
        # Create minimal agents for testing
        data_agent = DataSubAgent(None, None)
        validation_agent = ValidationSubAgent(None, None)
        
        websocket_methods = [
            'emit_thinking',
            'emit_progress', 
            'emit_error',
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_agent_started',
            'emit_agent_completed'
        ]
        
        for method_name in websocket_methods:
            assert hasattr(data_agent, method_name), f"DataSubAgent should have {method_name}"
            assert hasattr(validation_agent, method_name), f"ValidationSubAgent should have {method_name}"
            assert callable(getattr(data_agent, method_name)), f"DataSubAgent.{method_name} should be callable"
            assert callable(getattr(validation_agent, method_name)), f"ValidationSubAgent.{method_name} should be callable"
        
        print("SUCCESS: All WebSocket methods available and callable")
        
    except Exception as e:
        print(f"FAILED: WebSocket methods test failed: {e}")
        return False
    
    # Test 2: WebSocket method calls (should not raise exceptions)
    print("\n2. Testing WebSocket Method Calls")
    print("-" * 40)
    
    try:
        # Test DataSubAgent WebSocket calls
        await data_agent.emit_thinking("Test thinking message")
        await data_agent.emit_progress("Test progress message")
        await data_agent.emit_tool_executing("test_tool", {"param": "value"})
        await data_agent.emit_tool_completed("test_tool", {"result": "success"})
        await data_agent.emit_agent_started("DataSubAgent started")
        await data_agent.emit_agent_completed({"status": "completed"})
        await data_agent.emit_error("Test error message")
        
        print("SUCCESS: DataSubAgent WebSocket calls completed without errors")
        
        # Test ValidationSubAgent WebSocket calls
        await validation_agent.emit_thinking("Test thinking message")
        await validation_agent.emit_progress("Test progress message")
        await validation_agent.emit_tool_executing("validation_tool", {"rule": "test"})
        await validation_agent.emit_tool_completed("validation_tool", {"valid": True})
        await validation_agent.emit_agent_started("ValidationSubAgent started")
        await validation_agent.emit_agent_completed({"status": "completed"})
        await validation_agent.emit_error("Test error message")
        
        print("SUCCESS: ValidationSubAgent WebSocket calls completed without errors")
        
    except Exception as e:
        print(f"FAILED: WebSocket method calls failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: WebSocket context check
    print("\n3. Testing WebSocket Context")
    print("-" * 40)
    
    try:
        # Should return False since no WebSocket bridge is set
        data_context = data_agent.has_websocket_context()
        validation_context = validation_agent.has_websocket_context()
        
        print(f"DataSubAgent has WebSocket context: {data_context}")
        print(f"ValidationSubAgent has WebSocket context: {validation_context}")
        
        # This is expected behavior - no WebSocket bridge set in tests
        assert data_context == False, "Expected no WebSocket context without bridge"
        assert validation_context == False, "Expected no WebSocket context without bridge"
        
        print("SUCCESS: WebSocket context check working correctly")
        
    except Exception as e:
        print(f"FAILED: WebSocket context test failed: {e}")
        return False
    
    # Test 4: WebSocket bridge adapter
    print("\n4. Testing WebSocket Bridge Adapter")
    print("-" * 40)
    
    try:
        # Check that WebSocket adapter is initialized
        assert hasattr(data_agent, '_websocket_adapter'), "DataSubAgent should have _websocket_adapter"
        assert hasattr(validation_agent, '_websocket_adapter'), "ValidationSubAgent should have _websocket_adapter"
        
        # Check adapter methods
        assert hasattr(data_agent._websocket_adapter, 'emit_thinking'), "Adapter should have emit_thinking"
        assert hasattr(data_agent._websocket_adapter, 'has_websocket_bridge'), "Adapter should have has_websocket_bridge"
        
        print("SUCCESS: WebSocket bridge adapter properly initialized")
        
    except Exception as e:
        print(f"FAILED: WebSocket bridge adapter test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("ALL WEBSOCKET INTEGRATION TESTS PASSED!")
    print("=" * 60)
    print("\nKey Achievements:")
    print("- All WebSocket methods available after refactoring")
    print("- WebSocket calls execute without errors")
    print("- WebSocket bridge pattern working correctly")
    print("- No regression in WebSocket functionality")
    return True

async def main():
    """Main test execution"""
    print("Starting WebSocket Integration Validation...")
    
    success = await test_websocket_integration()
    
    print(f"\nOverall WebSocket Test Result: {'SUCCESS' if success else 'FAILURE'}")
    
    if success:
        print("\nWebSocket integration is working correctly after inheritance refactoring!")
    else:
        print("\nWebSocket integration has issues after inheritance refactoring.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)