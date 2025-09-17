#!/usr/bin/env python3
"""
Test supervisor factory integration - Phase 3B Implementation Gap Fix
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_factory_creation():
    """Test AgentInstanceFactory creation with UserExecutionContext."""
    try:
        from unittest.mock import AsyncMock
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.agents.supervisor.agent_instance_factory import create_agent_instance_factory
        
        # Create test context
        context = UserExecutionContext.from_request(
            user_id='test-factory-user',
            thread_id='test-factory-thread', 
            run_id='test-factory-run',
            websocket_client_id='test-factory-connection',
            agent_context={'user_request': 'test factory request'}
        )
        
        # Add mock DB session
        mock_db_session = AsyncMock()
        context = context.with_db_session(mock_db_session)
        
        # Create factory
        factory = create_agent_instance_factory(context)
        
        print("✅ AgentInstanceFactory creation successful")
        print(f"   - Factory type: {type(factory).__name__}")
        print(f"   - Has configure method: {hasattr(factory, 'configure')}")
        print(f"   - Has create_agent_instance method: {hasattr(factory, 'create_agent_instance')}")
        
        return True
    except Exception as e:
        print(f"❌ AgentInstanceFactory creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_supervisor_with_factory():
    """Test supervisor initialization with proper factory."""
    try:
        from unittest.mock import Mock, AsyncMock
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create test context
        context = UserExecutionContext.from_request(
            user_id='test-supervisor-user',
            thread_id='test-supervisor-thread', 
            run_id='test-supervisor-run',
            websocket_client_id='test-supervisor-connection',
            agent_context={'user_request': 'test supervisor request'}
        )
        
        # Add mock DB session
        mock_db_session = AsyncMock()
        context = context.with_db_session(mock_db_session)
        
        # Create minimal mocks
        llm_manager = Mock(spec=LLMManager)
        llm_manager._get_model_name = Mock(return_value='test-model')
        llm_manager.ask_llm = AsyncMock(return_value='test response')
        
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        
        # Create supervisor with user context (required for factory)
        supervisor = SupervisorAgent(
            llm_manager=llm_manager, 
            websocket_bridge=websocket_bridge,
            user_context=context
        )
        
        print("✅ SupervisorAgent with factory creation successful")
        print(f"   - Name: {supervisor.name}")
        print(f"   - Has agent_factory: {hasattr(supervisor, 'agent_factory')}")
        print(f"   - Has workflow_executor: {hasattr(supervisor, 'workflow_executor')}")
        
        return True
    except Exception as e:
        print(f"❌ SupervisorAgent with factory creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("🔧 Testing Supervisor Factory Integration - Phase 3B")
        print("=" * 60)
        
        # Test 1: Factory creation
        print("\n🔍 Test 1: AgentInstanceFactory Creation")
        factory_result = await test_factory_creation()
        
        # Test 2: Supervisor with factory
        print("\n🔍 Test 2: SupervisorAgent with Factory")
        supervisor_result = await test_supervisor_with_factory()
        
        print("\n" + "=" * 60)
        print("📊 FACTORY INTEGRATION RESULTS")
        print("=" * 60)
        
        results = [
            ("Factory Creation", factory_result),
            ("Supervisor with Factory", supervisor_result)
        ]
        
        passed = sum(1 for _, result in results if result)
        failed = len(results) - passed
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\nSUMMARY: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 Factory integration is working!")
        else:
            print(f"⚠️  {failed} factory integration issues found")
        
        return failed == 0
    
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)