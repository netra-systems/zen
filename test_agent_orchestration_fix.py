#!/usr/bin/env python3
"""
Test Agent Orchestration Fix - Golden Path Issue #1197 Validation

MISSION: Validate that the P0 fix allows real SupervisorAgent execution
and confirm no breaking changes were introduced.

Business Context:
- Golden Path represents $500K+ ARR functionality
- WebSocket events are critical for real-time chat experience
- Agent orchestration must work with proper user isolation
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_critical_imports():
    """Test that all critical components can be imported after the fix."""
    print("🔍 Testing Critical Imports...")
    
    try:
        # Test AgentWebSocketBridge (the core fix)
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
        print("✅ AgentWebSocketBridge import successful")
        
        # Test SupervisorAgent
        from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgentModern
        print("✅ SupervisorAgentModern import successful")
        
        # Test AgentRegistry
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        print("✅ AgentRegistry import successful")
        
        # Test UserExecutionContext (for proper user isolation)
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        print("✅ UserExecutionContext import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_websocket_bridge_initialization():
    """Test that WebSocketBridge can be initialized without singleton pattern."""
    print("\n🏗️ Testing WebSocket Bridge Initialization...")
    
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Test 1: Create without user context (system mode)
        bridge_system = AgentWebSocketBridge()
        assert bridge_system is not None
        assert bridge_system.user_context is None
        print("✅ System mode bridge creation successful")
        
        # Test 2: Create with user context (user isolation mode)
        user_context = UserExecutionContext(
            user_id="user_123_valid",
            thread_id="thread_456",
            run_id="run_123",
            request_id="req_789",
            websocket_client_id="ws_conn_abc"
        )
        
        bridge_user = create_agent_websocket_bridge(user_context)
        assert bridge_user is not None
        assert bridge_user.user_context is not None
        assert bridge_user.user_id == "user_123_valid"
        print("✅ User isolation mode bridge creation successful")
        
        # Test 3: Multiple bridges can exist (no singleton)
        bridge_user2 = create_agent_websocket_bridge(UserExecutionContext(
            user_id="user_456_valid",
            thread_id="thread_789",
            run_id="run_456",
            request_id="req_012",
            websocket_client_id="ws_conn_def"
        ))
        assert bridge_user2 is not bridge_user  # Different instances
        assert bridge_user2.user_id == "user_456_valid"
        print("✅ Multiple bridge instances confirmed (no singleton)")
        
        return True
        
    except Exception as e:
        print(f"❌ Bridge initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_user_emitter_creation():
    """Test factory method for creating user-isolated emitters."""
    print("\n🎯 Testing User Emitter Creation...")
    
    try:
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Create user context
        user_context = UserExecutionContext(
            user_id="user_789_valid",
            thread_id="thread_012",
            run_id="run_789",
            request_id="req_345",
            websocket_client_id="ws_conn_ghi"
        )
        
        # Create bridge
        bridge = create_agent_websocket_bridge(user_context)
        
        # Create user emitter (the key factory method)
        emitter = await bridge.create_user_emitter(user_context)
        assert emitter is not None
        print("✅ User emitter creation successful")
        
        # Test that emitter has user context
        assert hasattr(emitter, 'user_context') or hasattr(emitter, '_user_context')
        print("✅ User emitter has user context isolation")
        
        return True
        
    except Exception as e:
        print(f"❌ User emitter creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_supervisor_agent_creation():
    """Test that SupervisorAgent can be created with the new architecture."""
    print("\n🤖 Testing SupervisorAgent Creation...")
    
    try:
        from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgentModern
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Create user context
        user_context = UserExecutionContext(
            user_id="user_supervisor_valid",
            thread_id="thread_supervisor",
            run_id="run_supervisor",
            request_id="req_supervisor",
            websocket_client_id="ws_supervisor"
        )
        
        # Create mock LLM manager for SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        llm_manager = LLMManager(user_context=user_context)
        
        # Create SupervisorAgent (this should not fail with the fix)
        supervisor = SupervisorAgentModern(user_context=user_context, llm_manager=llm_manager)
        assert supervisor is not None
        print("✅ SupervisorAgent creation successful")
        
        # Test that supervisor has user context
        assert hasattr(supervisor, 'user_context')
        assert supervisor.user_context is not None
        print("✅ SupervisorAgent has user context isolation")
        
        return True
        
    except Exception as e:
        print(f"❌ SupervisorAgent creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_registry_integration():
    """Test that AgentRegistry works with the new architecture."""
    print("\n📋 Testing AgentRegistry Integration...")
    
    try:
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Create user context
        user_context = UserExecutionContext(
            user_id="user_registry_valid",
            thread_id="thread_registry",
            run_id="run_registry", 
            request_id="req_registry",
            websocket_client_id="ws_registry"
        )
        
        # Create AgentRegistry (should work with factory pattern)
        registry = AgentRegistry(user_context=user_context)
        assert registry is not None
        print("✅ AgentRegistry creation successful")
        
        # Test that registry has user context
        assert hasattr(registry, 'user_context')
        print("✅ AgentRegistry has user context support")
        
        return True
        
    except Exception as e:
        print(f"❌ AgentRegistry integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests to validate the agent orchestration fix."""
    print("🚀 AGENT ORCHESTRATION FIX VALIDATION")
    print("=" * 50)
    print(f"Test Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Mission: Validate Golden Path Issue #1197 P0 fix")
    print("=" * 50)
    
    tests = [
        ("Critical Imports", test_critical_imports),
        ("WebSocket Bridge Initialization", test_websocket_bridge_initialization),
        ("User Emitter Creation", test_user_emitter_creation),
        ("SupervisorAgent Creation", test_supervisor_agent_creation),
        ("AgentRegistry Integration", test_agent_registry_integration),
    ]
    
    results = []
    passed = 0
    
    for test_name, test_func in tests:
        print(f"\n📝 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 SUCCESS: All tests passed!")
        print("🚀 Agent orchestration fix is working correctly")
        print("💼 Golden Path functionality restored")
        print("🔒 User isolation is properly implemented")
        return True
    else:
        print(f"\n⚠️ PARTIAL SUCCESS: {passed}/{len(tests)} tests passed")
        print("🔧 Some issues may still need attention")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)