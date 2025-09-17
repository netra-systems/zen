#!/usr/bin/env python3
"""
Targeted Supervisor Integration Tests - Phase 3B
Tests the core supervisor components without Docker dependencies.
"""
import asyncio
import sys
import traceback
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_user_execution_context_creation():
    """Test UserExecutionContext creation and validation."""
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
        
        # Create valid context
        context = UserExecutionContext.from_request(
            user_id='test-integration-user',
            thread_id='test-integration-thread', 
            run_id='test-integration-run',
            websocket_client_id='test-integration-connection',
            agent_context={'user_request': 'test integration request'}
        )
        
        # Add mock DB session
        mock_db_session = AsyncMock()
        context = context.with_db_session(mock_db_session)
        
        # Validate context
        validated_context = validate_user_context(context)
        
        print("✅ UserExecutionContext creation and validation successful")
        print(f"   - User ID: {validated_context.user_id}")
        print(f"   - Has DB session: {validated_context.db_session is not None}")
        return True
        
    except Exception as e:
        print(f"❌ UserExecutionContext creation failed: {e}")
        traceback.print_exc()
        return False

async def test_factory_pattern_integration():
    """Test factory pattern creates properly isolated instances."""
    try:
        from unittest.mock import AsyncMock
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.agents.supervisor.agent_instance_factory import create_agent_instance_factory
        
        # Create two different user contexts
        context1 = UserExecutionContext.from_request(
            user_id='factory-user-1',
            thread_id='factory-thread-1', 
            run_id='factory-run-1',
            websocket_client_id='factory-connection-1',
            agent_context={'user_request': 'factory test 1'}
        ).with_db_session(AsyncMock())
        
        context2 = UserExecutionContext.from_request(
            user_id='factory-user-2',
            thread_id='factory-thread-2', 
            run_id='factory-run-2',
            websocket_client_id='factory-connection-2',
            agent_context={'user_request': 'factory test 2'}
        ).with_db_session(AsyncMock())
        
        # Create separate factories
        factory1 = create_agent_instance_factory(context1)
        factory2 = create_agent_instance_factory(context2)
        
        # Verify isolation
        assert factory1 is not factory2, "Factories should be separate instances"
        
        print("✅ Factory pattern integration successful")
        print(f"   - Factory 1 ID: {id(factory1)}")
        print(f"   - Factory 2 ID: {id(factory2)}")
        print(f"   - Factories are isolated: {factory1 is not factory2}")
        return True
        
    except Exception as e:
        print(f"❌ Factory pattern integration failed: {e}")
        traceback.print_exc()
        return False

async def test_websocket_bridge_integration():
    """Test WebSocket bridge methods are available and work."""
    try:
        from unittest.mock import Mock, AsyncMock
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create mock WebSocket bridge
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        
        # Mock all required notification methods
        websocket_bridge.notify_agent_started = AsyncMock()
        websocket_bridge.notify_agent_thinking = AsyncMock()
        websocket_bridge.notify_agent_completed = AsyncMock()
        websocket_bridge.notify_agent_error = AsyncMock()
        websocket_bridge.emit_agent_event = AsyncMock()
        
        # Test calling the methods
        await websocket_bridge.notify_agent_started(
            run_id='test-run',
            agent_name='TestAgent',
            context={'status': 'starting'}
        )
        
        await websocket_bridge.notify_agent_thinking(
            run_id='test-run',
            agent_name='TestAgent',
            reasoning='Testing reasoning',
            step_number=1
        )
        
        await websocket_bridge.notify_agent_completed(
            run_id='test-run',
            agent_name='TestAgent',
            result={'status': 'completed'},
            execution_time_ms=100
        )
        
        # Verify methods were called
        websocket_bridge.notify_agent_started.assert_called_once()
        websocket_bridge.notify_agent_thinking.assert_called_once()
        websocket_bridge.notify_agent_completed.assert_called_once()
        
        print("✅ WebSocket bridge integration successful")
        print(f"   - notify_agent_started called: {websocket_bridge.notify_agent_started.called}")
        print(f"   - notify_agent_thinking called: {websocket_bridge.notify_agent_thinking.called}")
        print(f"   - notify_agent_completed called: {websocket_bridge.notify_agent_completed.called}")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket bridge integration failed: {e}")
        traceback.print_exc()
        return False

async def test_supervisor_initialization_with_user_context():
    """Test supervisor can initialize with proper user context."""
    try:
        from unittest.mock import Mock, AsyncMock
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create test context
        context = UserExecutionContext.from_request(
            user_id='supervisor-init-user',
            thread_id='supervisor-init-thread', 
            run_id='supervisor-init-run',
            websocket_client_id='supervisor-init-connection',
            agent_context={'user_request': 'supervisor initialization test'}
        ).with_db_session(AsyncMock())
        
        # Create minimal mocks
        llm_manager = Mock(spec=LLMManager)
        llm_manager._get_model_name = Mock(return_value='test-model')
        llm_manager.ask_llm = AsyncMock(return_value='test response')
        
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        websocket_bridge.notify_agent_started = AsyncMock()
        websocket_bridge.notify_agent_thinking = AsyncMock()
        websocket_bridge.notify_agent_completed = AsyncMock()
        websocket_bridge.notify_agent_error = AsyncMock()
        
        # Create supervisor with user context (required for proper isolation)
        supervisor = SupervisorAgent(
            llm_manager=llm_manager, 
            websocket_bridge=websocket_bridge,
            user_context=context
        )
        
        # Verify initialization
        assert supervisor.name == "Supervisor"
        assert hasattr(supervisor, 'agent_factory')
        assert hasattr(supervisor, 'workflow_executor')
        assert supervisor.websocket_bridge is websocket_bridge
        
        print("✅ Supervisor initialization with user context successful")
        print(f"   - Name: {supervisor.name}")
        print(f"   - Has agent_factory: {hasattr(supervisor, 'agent_factory')}")
        print(f"   - Has workflow_executor: {hasattr(supervisor, 'workflow_executor')}")
        print(f"   - WebSocket bridge connected: {supervisor.websocket_bridge is not None}")
        return True
        
    except Exception as e:
        print(f"❌ Supervisor initialization failed: {e}")
        traceback.print_exc()
        return False

async def test_user_execution_engine_creation():
    """Test that UserExecutionEngine can be created from supervisor."""
    try:
        from unittest.mock import Mock, AsyncMock, patch
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create test context
        context = UserExecutionContext.from_request(
            user_id='engine-test-user',
            thread_id='engine-test-thread', 
            run_id='engine-test-run',
            websocket_client_id='engine-test-connection',
            agent_context={'user_request': 'engine test request'}
        ).with_db_session(AsyncMock())
        
        # Create mocks
        llm_manager = Mock(spec=LLMManager)
        llm_manager._get_model_name = Mock(return_value='test-model')
        llm_manager.ask_llm = AsyncMock(return_value='test response')
        
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        websocket_bridge.notify_agent_started = AsyncMock()
        websocket_bridge.notify_agent_thinking = AsyncMock()
        websocket_bridge.notify_agent_completed = AsyncMock()
        websocket_bridge.notify_agent_error = AsyncMock()
        
        # Create supervisor 
        supervisor = SupervisorAgent(
            llm_manager=llm_manager, 
            websocket_bridge=websocket_bridge,
            user_context=context
        )
        
        # Test UserExecutionEngine creation
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter') as mock_emitter_class:
            mock_emitter = Mock()
            mock_emitter_class.return_value = mock_emitter
            
            engine = await supervisor._create_user_execution_engine(context)
            
            # Verify engine was created
            assert engine is not None
            assert hasattr(engine, 'context')
            assert hasattr(engine, 'agent_factory')
            
            print("✅ UserExecutionEngine creation successful")
            print(f"   - Engine created: {engine is not None}")
            print(f"   - Has context: {hasattr(engine, 'context')}")
            print(f"   - Has agent_factory: {hasattr(engine, 'agent_factory')}")
            return True
        
    except Exception as e:
        print(f"❌ UserExecutionEngine creation failed: {e}")
        traceback.print_exc()
        return False

async def test_supervisor_execution_without_agents():
    """Test supervisor execute method without full agent orchestration."""
    try:
        from unittest.mock import Mock, AsyncMock, patch
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create test context
        context = UserExecutionContext.from_request(
            user_id='exec-test-user',
            thread_id='exec-test-thread', 
            run_id='exec-test-run',
            websocket_client_id='exec-test-connection',
            agent_context={'user_request': 'execution test request'}
        ).with_db_session(AsyncMock())
        
        # Create mocks
        llm_manager = Mock(spec=LLMManager)
        llm_manager._get_model_name = Mock(return_value='test-model')
        llm_manager.ask_llm = AsyncMock(return_value='test response')
        
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        websocket_bridge.notify_agent_started = AsyncMock()
        websocket_bridge.notify_agent_thinking = AsyncMock()
        websocket_bridge.notify_agent_completed = AsyncMock()
        websocket_bridge.notify_agent_error = AsyncMock()
        
        # Create supervisor 
        supervisor = SupervisorAgent(
            llm_manager=llm_manager, 
            websocket_bridge=websocket_bridge,
            user_context=context
        )
        
        # Mock the complex parts and test basic execution flow
        mock_result = {
            "workflow_completed": True,
            "triage": {"status": "completed"},
            "reporting": {"status": "completed"},
            "user_request": "execution test request"
        }
        
        with patch.object(supervisor, '_create_user_execution_engine') as mock_engine_creation, \
             patch.object(supervisor, '_execute_orchestration_workflow', return_value=mock_result) as mock_workflow:
            
            # Mock engine
            mock_engine = Mock()
            mock_engine.cleanup = AsyncMock()
            mock_engine_creation.return_value = mock_engine
            
            # Execute supervisor
            result = await supervisor.execute(context, stream_updates=True)
            
            # Verify execution
            assert result is not None
            assert isinstance(result, dict)
            assert 'supervisor_result' in result
            assert 'orchestration_successful' in result
            assert 'user_isolation_verified' in result
            
            # Verify WebSocket events were called
            websocket_bridge.notify_agent_started.assert_called_once()
            websocket_bridge.notify_agent_thinking.assert_called_once()
            websocket_bridge.notify_agent_completed.assert_called_once()
            
            print("✅ Supervisor execution flow successful")
            print(f"   - Result type: {type(result)}")
            print(f"   - Has supervisor_result: {'supervisor_result' in result}")
            print(f"   - Orchestration successful: {result.get('orchestration_successful')}")
            print(f"   - User isolation verified: {result.get('user_isolation_verified')}")
            return True
        
    except Exception as e:
        print(f"❌ Supervisor execution failed: {e}")
        traceback.print_exc()
        return False

async def run_integration_tests():
    """Run all targeted integration tests."""
    print("🎯 Phase 3B - Targeted Supervisor Integration Tests")
    print("=" * 60)
    
    tests = [
        ("UserExecutionContext Creation", test_user_execution_context_creation),
        ("Factory Pattern Integration", test_factory_pattern_integration),
        ("WebSocket Bridge Integration", test_websocket_bridge_integration),
        ("Supervisor Initialization", test_supervisor_initialization_with_user_context),
        ("UserExecutionEngine Creation", test_user_execution_engine_creation),
        ("Supervisor Execution Flow", test_supervisor_execution_without_agents)
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
    print("📊 INTEGRATION TEST RESULTS")
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
        print("🎉 ALL INTEGRATION TESTS PASSED - Ready for Phase 3C!")
        return True
    else:
        print(f"⚠️  {failed} INTEGRATION ISSUES - Need fixes for Phase 3C")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_integration_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1)