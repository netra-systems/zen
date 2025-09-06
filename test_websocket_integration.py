#!/usr/bin/env python3
"""Test script to verify WebSocket integration with AgentRegistry.

This script tests the Phase 3 fixes for WebSocket event pipeline integration.
"""

import asyncio
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_agent_registry_websocket_integration():
    """Test that AgentRegistry properly integrates with WebSocket manager."""
    
    print("Testing AgentRegistry WebSocket integration...")
    
    try:
        # Import required modules
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext  # This is what the agent factories expect
        from netra_backend.app.llm.llm_manager import LLMManager
        
        # Create a mock WebSocket manager for testing
        class MockWebSocketManager:
            def __init__(self):
                self.events = []
                
            def emit(self, event, data):
                self.events.append((event, data))
                print(f"WebSocket event: {event} - {data}")
        
        # Create test components
        print("1. Creating LLM manager...")
        llm_manager = LLMManager()
        
        print("2. Creating AgentRegistry...")
        registry = AgentRegistry(llm_manager)
        
        print("3. Registering default agents...")
        registry.register_default_agents()
        
        print("4. Creating mock WebSocket manager...")
        websocket_manager = MockWebSocketManager()
        
        print("5. Setting WebSocket manager on registry...")
        registry.set_websocket_manager(websocket_manager)
        
        print("6. Creating user execution context...")
        user_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )
        
        print("7. Creating user session...")
        user_session = await registry.get_user_session("test_user")
        
        print("8. Checking user session has WebSocket bridge...")
        has_bridge = user_session._websocket_bridge is not None
        print(f"   User session has WebSocket bridge: {has_bridge}")
        
        print("9. Creating agent for user...")
        try:
            agent = await registry.create_agent_for_user(
                user_id="test_user",
                agent_type="triage",  # This should be registered by default
                user_context=user_context
            )
            print(f"   Created agent: {type(agent).__name__ if agent else 'None'}")
            
            if agent:
                print("10. Testing agent has tool dispatcher...")
                has_dispatcher = hasattr(agent, 'tool_dispatcher') and agent.tool_dispatcher is not None
                print(f"    Agent has tool dispatcher: {has_dispatcher}")
                
                if has_dispatcher:
                    print("11. Testing tool dispatcher has WebSocket integration...")
                    has_websocket_manager = hasattr(agent.tool_dispatcher, 'websocket_manager') and agent.tool_dispatcher.websocket_manager is not None
                    has_websocket_bridge = hasattr(agent.tool_dispatcher, '_websocket_bridge') and agent.tool_dispatcher._websocket_bridge is not None
                    has_websocket_support = hasattr(agent.tool_dispatcher, 'has_websocket_support') and agent.tool_dispatcher.has_websocket_support
                    
                    print(f"    Tool dispatcher has websocket_manager: {has_websocket_manager}")
                    print(f"    Tool dispatcher has _websocket_bridge: {has_websocket_bridge}")
                    print(f"    Tool dispatcher has_websocket_support: {has_websocket_support}")
                    
        except Exception as e:
            print(f"   Error creating agent: {e}")
            import traceback
            traceback.print_exc()
        
        print("12. Diagnosing WebSocket wiring...")
        diagnosis = registry.diagnose_websocket_wiring()
        print(f"    WebSocket health: {diagnosis.get('websocket_health', 'UNKNOWN')}")
        print(f"    Total user sessions: {diagnosis.get('total_user_sessions', 0)}")
        print(f"    Users with bridges: {diagnosis.get('users_with_websocket_bridges', 0)}")
        
        if diagnosis.get('critical_issues'):
            print("    Critical issues:")
            for issue in diagnosis['critical_issues']:
                print(f"      - {issue}")
        
        print("WebSocket integration test completed!")
        
        # Test results summary
        success_indicators = [
            registry.websocket_manager is not None,
            user_session._websocket_bridge is not None,
            diagnosis.get('websocket_health') == 'HEALTHY'
        ]
        
        success_count = sum(success_indicators)
        total_checks = len(success_indicators)
        
        print(f"\nTest Results: {success_count}/{total_checks} checks passed")
        
        if success_count == total_checks:
            print("All WebSocket integration checks PASSED!")
            return True
        else:
            print("Some WebSocket integration checks FAILED!")
            return False
            
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dependencies_integration():
    """Test that dependencies.py works with the new AgentRegistry."""
    
    print("\nTesting dependencies.py integration...")
    
    try:
        # This simulates what happens in get_agent_supervisor
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.models.user_execution_context import UserExecutionContext  # Correct import for WebSocket factory
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        
        # Create components
        print("1. Creating supervisor components...")
        llm_manager = LLMManager()
        registry = AgentRegistry(llm_manager)
        
        # Mock supervisor with agent_registry
        class MockSupervisor:
            def __init__(self):
                self.agent_registry = registry
        
        supervisor = MockSupervisor()
        
        print("2. Creating user context for WebSocket manager...")
        user_context = UserExecutionContext(
            user_id="system",
            thread_id="supervisor_main",
            run_id="run_test",
            request_id="supervisor_init_test"
        )
        
        print("3. Creating WebSocket manager...")
        websocket_manager = create_websocket_manager(user_context)
        
        print("4. Testing set_websocket_manager call (simulating dependencies.py)...")
        if websocket_manager and hasattr(supervisor.agent_registry, 'set_websocket_manager'):
            import asyncio
            # Check if it's async (it shouldn't be after our fix)
            if asyncio.iscoroutinefunction(supervisor.agent_registry.set_websocket_manager):
                print("   set_websocket_manager is async - this will cause issues in sync context")
                return False
            else:
                supervisor.agent_registry.set_websocket_manager(websocket_manager)
                print("   set_websocket_manager called successfully in sync context")
                
                # Verify it was set
                has_manager = supervisor.agent_registry.websocket_manager is not None
                print(f"   Registry has WebSocket manager: {has_manager}")
                return has_manager
        else:
            print("   WebSocket manager not available or supervisor lacks agent_registry")
            return False
            
    except Exception as e:
        print(f"Dependencies integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all integration tests."""
    print("Starting WebSocket integration tests...\n")
    
    test1_passed = await test_agent_registry_websocket_integration()
    test2_passed = await test_dependencies_integration()
    
    total_tests = 2
    passed_tests = sum([test1_passed, test2_passed])
    
    print(f"\nOverall Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("All integration tests PASSED! WebSocket integration is working.")
        return 0
    else:
        print("Some integration tests FAILED! Check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)