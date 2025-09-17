#!/usr/bin/env python3
"""
Simple supervisor validation script to test core functionality without external dependencies.
Part of Phase 3B - Test Execution Validation for Golden Path.
"""
import asyncio
import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_supervisor_import():
    """Test basic supervisor import."""
    try:
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        print("✅ SupervisorAgent import successful")
        return True
    except Exception as e:
        print(f"❌ SupervisorAgent import failed: {e}")
        traceback.print_exc()
        return False

async def test_supervisor_creation():
    """Test supervisor creation with minimal dependencies."""
    try:
        from unittest.mock import Mock, AsyncMock
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create minimal mocks
        llm_manager = Mock(spec=LLMManager)
        llm_manager._get_model_name = Mock(return_value='test-model')
        llm_manager.ask_llm = AsyncMock(return_value='test response')
        
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        
        # Create supervisor
        supervisor = SupervisorAgent(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        
        print("✅ SupervisorAgent creation successful")
        print(f"   - Name: {supervisor.name}")
        print(f"   - Has agent_factory: {hasattr(supervisor, 'agent_factory')}")
        print(f"   - Has LLM manager: {supervisor.llm_manager is not None}")
        print(f"   - Has WebSocket bridge: {supervisor.websocket_bridge is not None}")
        
        return True
    except Exception as e:
        print(f"❌ SupervisorAgent creation failed: {e}")
        traceback.print_exc()
        return False

async def test_user_execution_context():
    """Test UserExecutionContext import and creation."""
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from unittest.mock import AsyncMock
        
        # Create test context
        context = UserExecutionContext.from_request(
            user_id='test-user-validation',
            thread_id='test-thread-validation', 
            run_id='test-run-validation',
            websocket_client_id='test-connection-validation',
            agent_context={'user_request': 'test validation request'}
        )
        
        # Add mock DB session
        mock_db_session = AsyncMock()
        context = context.with_db_session(mock_db_session)
        
        print("✅ UserExecutionContext creation successful")
        print(f"   - User ID: {context.user_id}")
        print(f"   - Thread ID: {context.thread_id}")
        print(f"   - Run ID: {context.run_id}")
        print(f"   - Has DB session: {context.db_session is not None}")
        
        return True
    except Exception as e:
        print(f"❌ UserExecutionContext creation failed: {e}")
        traceback.print_exc()
        return False

async def test_factory_patterns():
    """Test factory pattern imports and basic functionality."""
    try:
        from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
        from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
        
        print("✅ Factory pattern imports successful")
        print(f"   - AgentInstanceFactory imported")
        print(f"   - AgentClassRegistry imported")
        
        return True
    except Exception as e:
        print(f"❌ Factory pattern imports failed: {e}")
        traceback.print_exc()
        return False

async def test_websocket_integration():
    """Test WebSocket integration imports."""
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.websocket_core.manager import WebSocketManager
        
        print("✅ WebSocket integration imports successful")
        print(f"   - AgentWebSocketBridge imported")
        print(f"   - WebSocketManager imported")
        
        return True
    except Exception as e:
        print(f"❌ WebSocket integration imports failed: {e}")
        traceback.print_exc()
        return False

async def run_validation_suite():
    """Run the complete validation suite."""
    print("🚀 Starting Supervisor Validation Suite - Phase 3B")
    print("=" * 60)
    
    tests = [
        ("Supervisor Import", test_supervisor_import),
        ("Supervisor Creation", test_supervisor_creation), 
        ("UserExecutionContext", test_user_execution_context),
        ("Factory Patterns", test_factory_patterns),
        ("WebSocket Integration", test_websocket_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION RESULTS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nSUMMARY: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - Supervisor infrastructure is healthy!")
        return True
    else:
        print(f"⚠️  {failed} TESTS FAILED - Implementation gaps identified")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_validation_suite())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1)