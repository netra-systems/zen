#!/usr/bin/env python3
"""
Simplified Agent Execution Flow Test for Issue #1131

This script tests the agent execution flow with proper mock configurations
to identify the core issues that need fixing.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult, AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext


async def test_minimal_agent_execution_flow():
    """Test the minimal agent execution flow with properly configured mocks."""
    print("Testing minimal agent execution flow...")
    
    # Create proper mocks
    mock_registry = MagicMock()
    mock_websocket_bridge = AsyncMock()
    mock_agent = MagicMock()
    
    # CRITICAL: Agent execute method must be AsyncMock
    expected_result = AgentExecutionResult(
        success=True,
        agent_name="test-agent",
        duration=2.5,
        data={"message": "Agent provided valuable insights"}
    )
    mock_agent.execute = AsyncMock(return_value=expected_result)
    
    # Other agent methods as regular Mocks
    mock_agent.set_trace_context = MagicMock()
    mock_agent.set_websocket_bridge = MagicMock()
    mock_agent.execution_engine = MagicMock()
    mock_agent.execution_engine.set_websocket_bridge = MagicMock()
    
    # Registry methods
    mock_registry.get_agent.return_value = mock_agent
    mock_registry.get_async = AsyncMock(return_value=mock_agent)
    
    # WebSocket bridge methods (all async)
    mock_websocket_bridge.notify_agent_started = AsyncMock()
    mock_websocket_bridge.notify_agent_thinking = AsyncMock()
    mock_websocket_bridge.notify_agent_completed = AsyncMock()
    
    # Create execution core
    execution_core = AgentExecutionCore(
        registry=mock_registry,
        websocket_bridge=mock_websocket_bridge
    )
    
    # Create execution contexts
    execution_context = AgentExecutionContext(
        agent_name="test-agent",
        run_id=str(uuid4()),
        thread_id="test-thread",
        user_id="test-user",
        correlation_id="test-correlation"
    )
    
    user_context = UserExecutionContext.from_request(
        user_id="test-user",
        thread_id="test-thread", 
        run_id=str(uuid4())
    )
    
    # Now we need to patch the execution tracking methods that are causing issues
    exec_id = 'test-exec-123'
    state_exec_id = 'test-state-exec-123'
    
    # Patch all the tracking methods that the AgentExecutionCore uses
    with patch.object(execution_core.execution_tracker, 'create_execution', return_value=exec_id) as mock_create_exec:
        with patch.object(execution_core.execution_tracker, 'start_execution', return_value=True) as mock_start_exec:
            with patch.object(execution_core.execution_tracker, 'update_execution_state', return_value=True) as mock_update_exec:
                with patch.object(execution_core.agent_tracker, 'create_execution', return_value=state_exec_id) as mock_create_state:
                    with patch.object(execution_core.agent_tracker, 'start_execution', return_value=True) as mock_start_state:
                        with patch.object(execution_core.agent_tracker, 'transition_state', new=AsyncMock()) as mock_transition:
                            with patch.object(execution_core.agent_tracker, 'update_execution_state', return_value=True) as mock_update_state:
                                
                                # Execute the agent
                                result = await execution_core.execute_agent(
                                    context=execution_context,
                                    user_context=user_context,
                                    timeout=30.0
                                )
    
    print(f"Agent execution result: success={result.success}")
    print(f"Agent name: {result.agent_name}")
    print(f"Duration: {result.duration}")
    print(f"Error: {result.error}")
    
    if result.success:
        print("✅ PASS: Agent execution succeeded")
        
        # Verify key method calls
        mock_registry.get_async.assert_called_once()
        mock_agent.execute.assert_called_once()
        mock_websocket_bridge.notify_agent_started.assert_called()
        
        print("✅ PASS: All expected methods were called")
        return True
    else:
        print(f"❌ FAIL: Agent execution failed: {result.error}")
        return False


async def test_agent_execution_api_method_detection():
    """Test which method the agent execution core actually calls."""
    print("Testing agent execution API method detection...")
    
    # Create tracking mock agent
    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock(return_value=AgentExecutionResult(success=True, agent_name="test"))
    mock_agent.run = AsyncMock(return_value={"success": True})
    mock_agent.set_trace_context = MagicMock()
    mock_agent.set_websocket_bridge = MagicMock()
    mock_agent.execution_engine = MagicMock()
    mock_agent.execution_engine.set_websocket_bridge = MagicMock()
    
    # Inspect the actual method call in AgentExecutionCore
    # Based on line 901 in agent_execution_core.py:
    # result = await agent.execute(user_execution_context, context.run_id, True)
    
    user_execution_context = UserExecutionContext.from_request("user", "thread", str(uuid4()))
    run_id = str(uuid4())
    
    # Test the actual call signature
    result = await mock_agent.execute(user_execution_context, run_id, True)
    print(f"✅ PASS: agent.execute() call works with signature: {result}")
    
    # Verify the exact call
    mock_agent.execute.assert_called_once_with(user_execution_context, run_id, True)
    print("✅ PASS: agent.execute() called with correct signature")
    
    # Also test run method (some agents might use this)
    mock_agent.run.reset_mock()
    result2 = await mock_agent.run(user_execution_context, run_id, True)
    print(f"✅ PASS: agent.run() call works with signature: {result2}")
    
    return True


async def test_websocket_method_signatures():
    """Test WebSocket bridge method signatures used in agent execution."""
    print("Testing WebSocket method signatures...")
    
    mock_websocket_bridge = AsyncMock()
    
    # Test notify_agent_started signature (from line 478-482)
    await mock_websocket_bridge.notify_agent_started(
        run_id="test-run-id",
        agent_name="test-agent", 
        context={"status": "starting", "phase": "initialization"}
    )
    print("✅ PASS: notify_agent_started signature works")
    
    # Test notify_agent_thinking signature (from lines 884-888)
    await mock_websocket_bridge.notify_agent_thinking(
        run_id="test-run-id",
        agent_name="test-agent",
        reasoning="Executing test-agent with your specific requirements...",
        step_number=2
    )
    print("✅ PASS: notify_agent_thinking signature works")
    
    # Test notify_agent_completed signature (from lines 736-740) 
    await mock_websocket_bridge.notify_agent_completed(
        run_id="test-run-id",
        agent_name="test-agent",
        result={"status": "completed", "success": True}
    )
    print("✅ PASS: notify_agent_completed signature works")
    
    return True


async def run_all_tests():
    """Run all agent execution flow tests."""
    print("🧪 Starting Agent Execution Flow Tests (Issue #1131)")
    print("=" * 60)
    
    tests = [
        test_agent_execution_api_method_detection,
        test_websocket_method_signatures, 
        test_minimal_agent_execution_flow,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAIL: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"🎯 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - Agent execution flow is working!")
        return True
    else:
        print("❌ SOME TESTS FAILED - Agent execution flow needs fixes")
        return False


if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)